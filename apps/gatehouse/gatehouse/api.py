"""HTTP surface and the browser UI.

Server-rendered HTML, no build step (ADR-010). The JSON endpoints exist
so a run can be driven without a browser; the HTML pages are what the
client sees.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import __version__, elicit, synthesize
from .adapters import Registry
from .audit import AuditLog
from .config import Config
from .instance import Instance
from .pack import load as load_pack

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def create_app(config: Config) -> FastAPI:
    pack = load_pack(config.pack_path)
    audit = AuditLog(config.instance_path)
    models = Registry(config, audit)
    instance = Instance(config.instance_path, pack)

    app = FastAPI(title="Gatehouse", version=__version__)

    def page(request: Request, name: str, **context) -> HTMLResponse:
        return TEMPLATES.TemplateResponse(
            request=request,
            name=name,
            context={
                "pack": pack,
                "destinations": config.destinations,
                "version": __version__,
                **context,
            },
        )

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request):
        run = instance.load()
        if run is None:
            return page(request, "start.html")
        return RedirectResponse(f"/block/{run.current_block}", status_code=303)

    @app.post("/start")
    def start(client: str = Form(...)):
        run = instance.start(client.strip() or "unnamed")
        audit.record(event="run_started", client=run.client, pack=pack.name)
        return RedirectResponse(f"/block/{run.current_block}", status_code=303)

    @app.get("/block/{block_id}", response_class=HTMLResponse)
    def show_block(request: Request, block_id: str, incomplete: str = ""):
        run = instance.load()
        if run is None:
            return page(request, "empty.html", heading="No run started",
                        detail="Start a run before opening a block.")
        block = pack.block(block_id)
        run.current_block = block_id
        instance.save(run)
        return page(
            request, "block.html", run=run, block=block,
            incomplete=[i for i in incomplete.split(",") if i],
        )

    @app.post("/block/{block_id}/answer")
    def answer(
        block_id: str,
        question_id: str = Form(...),
        text: str = Form(""),
        marker: str = Form("AS-IS"),
    ):
        run = _require_run(instance)
        block = pack.block(block_id)
        recorded = instance.record(run, question_id, text, marker)

        question = next(q for q in block.questions if q.id == question_id)
        recorded.follow_ups = elicit.follow_ups(models, pack, block, question, text)
        instance.save(run)

        return RedirectResponse(f"/block/{block_id}#{question_id}", status_code=303)

    @app.post("/block/{block_id}/close")
    def close_block(block_id: str):
        run = _require_run(instance)
        block = pack.block(block_id)

        unanswered = [
            q.id for q in block.questions
            if not run.answers.get(q.id) or not run.answers[q.id].text.strip()
        ]
        if unanswered:
            # Do not navigate away mid-interview. The operator is sitting
            # with a client; they need to see which questions are open, on
            # the page they are already on.
            return RedirectResponse(
                f"/block/{block_id}?incomplete={','.join(unanswered)}",
                status_code=303,
            )

        if block_id not in run.closed_blocks:
            run.closed_blocks.append(block_id)
        audit.record(event="block_closed", block=block_id)

        following = _next_block_id(pack, block_id)
        run.current_block = following or block_id
        instance.save(run)

        if following is None:
            target = "/analysis" if pack.synthesis else "/artifacts"
            return RedirectResponse(target, status_code=303)
        return RedirectResponse(f"/block/{following}", status_code=303)

    @app.get("/artifacts", response_class=HTMLResponse)
    def artifacts(request: Request):
        run = instance.load()
        if run is None:
            return page(request, "empty.html", heading="No artifacts yet",
                        detail="Nothing has been elicited. Start a run first.")
        return page(
            request,
            "artifacts.html",
            run=run,
            interview=instance.interview_file.read_text(encoding="utf-8"),
            interview_path=instance.interview_file,
        )

    @app.get("/analysis", response_class=HTMLResponse)
    def analysis(request: Request):
        run = instance.load()
        if run is None:
            return page(request, "empty.html", heading="Nothing to read yet",
                        detail="Answer some questions first.")
        if pack.synthesis is None:
            return page(request, "empty.html", heading="This pack offers no reading",
                        detail=f"Pack '{pack.name}' defines no synthesis.")

        existing = (
            instance.analysis_file.read_text(encoding="utf-8")
            if instance.analysis_file.exists()
            else ""
        )
        return page(
            request, "analysis.html", run=run, body=existing,
            answered=len([a for a in run.answers.values() if a.text.strip()]),
            total=sum(len(b.questions) for b in pack.blocks),
            path=instance.analysis_file,
        )

    @app.post("/analysis/run")
    def analysis_run(request: Request):
        run = _require_run(instance)
        try:
            body = synthesize.read_back(models, pack, run)
        except synthesize.SynthesisUnavailable as exc:
            # Stay on the page. The operator may be standing in front of
            # someone; a stack trace or a redirect loses the room.
            return page(
                request, "analysis.html", run=run, body="", error=str(exc),
                answered=len([a for a in run.answers.values() if a.text.strip()]),
                total=sum(len(b.questions) for b in pack.blocks),
                path=instance.analysis_file,
            )

        instance.save_analysis(run, pack.synthesis.title, pack.synthesis.lead, body)
        audit.record(event="analysis_written", answers=len(run.answers))
        return RedirectResponse("/analysis", status_code=303)

    @app.get("/audit", response_class=HTMLResponse)
    def audit_view(request: Request):
        return page(request, "audit.html", entries=list(reversed(audit.entries())))

    @app.get("/api/v1/run")
    def api_run():
        run = _require_run(instance)
        return run

    @app.exception_handler(StarletteHTTPException)
    def http_error(request: Request, exc: StarletteHTTPException):
        if request.url.path.startswith("/api/"):
            return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
        return TEMPLATES.TemplateResponse(
            request=request,
            name="empty.html",
            context={
                "pack": pack,
                "destinations": config.destinations,
                "version": __version__,
                "heading": "That page is not available",
                "detail": str(exc.detail),
            },
            status_code=exc.status_code,
        )

    return app


def _require_run(instance: Instance):
    run = instance.load()
    if run is None:
        raise HTTPException(404, "No run started yet.")
    return run


def _next_block_id(pack, block_id: str) -> str | None:
    ids = [b.id for b in pack.blocks]
    index = ids.index(block_id)
    return ids[index + 1] if index + 1 < len(ids) else None
