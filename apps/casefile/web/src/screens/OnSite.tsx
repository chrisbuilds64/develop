// At the car (theme.onsite): one case on a tablet or phone. Photos by view — the photo standard's required views and the details —
// straight from the camera into the next place of the series; a note that becomes the dictation; and the AI's hints in rounds: what to
// photograph, what to clarify, what it noticed. The assessor ticks, answers or takes the photo, asks again, and closes the inspection.
// The AI suggests; nothing it says settles anything.
import { useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError, BASE, onsite, sample as putSample, stepId, type ConfigView, type OnsiteConf, type OnsiteHint, type OnsiteHints, type OnsiteState, type SlotView } from "../api";
import { paper } from "../moments";
import type { words } from "../words";

/** A photo from the camera, made small on the device: the long edge at most 1600 px, JPEG. What cannot be read goes up as it is. */
async function shrink(file: File): Promise<File> {
  try {
    const url = URL.createObjectURL(file);
    const img = await new Promise<HTMLImageElement>((ok, no) => { const i = new Image(); i.onload = () => ok(i); i.onerror = no; i.src = url; });
    const k = Math.min(1, 1600 / Math.max(img.naturalWidth, img.naturalHeight));
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(img.naturalWidth * k); canvas.height = Math.round(img.naturalHeight * k);
    canvas.getContext("2d")!.drawImage(img, 0, 0, canvas.width, canvas.height);
    URL.revokeObjectURL(url);
    const blob = await new Promise<Blob | null>((ok) => canvas.toBlob(ok, "image/jpeg", 0.82));
    return blob ? new File([blob], "foto.jpg", { type: "image/jpeg" }) : file;
  } catch {
    return file;
  }
}

const seriesRe = (series: string) => new RegExp("^" + series.replace(/[.]/g, "\\.").replace("{n}", "(\\d+)") + "$");

export function OnSiteScreen({ id, config, go, w }: { id: string; config: ConfigView; go: (p: string) => void; w: ReturnType<typeof words> }) {
  const qc = useQueryClient();
  const conf = (config.theme as { onsite?: OnsiteConf }).onsite;
  const samples = ((config.theme as { samples?: string[] }).samples ?? []);
  const q = useQuery({ queryKey: ["case", id], queryFn: () => api.case(id), retry: false, refetchInterval: (query) => (query.state.data?.group === "claude" ? 2000 : 20_000) });
  const [note, setNote] = useState<string | null>(null);              // null until the saved note is read
  const [saved, setSaved] = useState("");
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [refused, setRefused] = useState<string | null>(null);
  const camera = useRef<HTMLInputElement>(null);
  const aim = useRef<{ view: string; hint?: string } | null>(null);
  const refresh = () => qc.invalidateQueries({ queryKey: ["case", id] });
  const fail = (e: unknown) => setRefused(e instanceof ApiError ? e.message : String(e));

  const v = q.data;
  const noteSlot = v?.slots.find((s) => s.file === conf?.note);
  const noteUrl = noteSlot?.present ? noteSlot.versions[noteSlot.versions.length - 1].url : null;
  useEffect(() => {                                                    // the newest note, once, so the field starts where the dictation stands
    if (note !== null || !v) return;
    if (!noteUrl) { setNote(""); return; }
    fetch(BASE + noteUrl, { credentials: "same-origin" }).then((r) => (r.ok ? r.text() : "")).then((t) => { setNote(t); setSaved(t); }).catch(() => setNote(""));
  }, [v, noteUrl, note]);

  if (!conf) return <main className="main"><p className="empty">—</p></main>;
  if (q.isLoading || !v) return <main className="main"><p className="empty">{q.error ? w.notHere : "…"}</p></main>;

  const data = (v as unknown as { data?: Record<string, unknown> }).data ?? {};
  const state = (data[conf.state] as OnsiteState | undefined) ?? {};
  const hints = data[conf.hints] as OnsiteHints | undefined;
  const thinking = v.group === "claude";
  const re = seriesRe(conf.series);
  const series = v.slots.filter((s) => re.test(s.file)).sort((a, b) => Number(re.exec(a.file)![1]) - Number(re.exec(b.file)![1]));
  const taken = series.filter((s) => s.present);
  const free = series.find((s) => !s.present);
  const viewOf = (s: SlotView) => state.photos?.[s.file] ?? "weitere";
  const shotsOf = (view: string) => taken.filter((s) => viewOf(s) === view);
  const required = conf.views.filter((x) => x.required);
  const covered = required.filter((x) => shotsOf(x.id).length > 0).length;
  const sampleFor = (...keys: (string | undefined)[]) => keys.map((k) => k && `vorort-${k}.jpg`).find((f) => f && samples.includes(f));
  const general = (view?: string) => !!view && view !== "schaden" && view !== "weitere";       // a required view, not a particular detail
  const settled = (h: OnsiteHint) => !!state.hints?.[h.id]?.done || (general(h.view) && shotsOf(h.view!).length > 0);

  const placed = async (name: string, view: string, hint?: string) => {
    await onsite.put(id, { photos: { [name]: view }, hints: hint ? { [hint]: { done: true, text: w.photoDone(name) } } : undefined });
    paper(); refresh();
  };
  const shoot = (view: string, hint?: string) => { aim.current = { view, hint }; camera.current?.click(); };
  const fromCamera = async (file: File | undefined) => {
    const target = aim.current; aim.current = null;
    if (!file || !target || !free) return;
    setBusy(target.hint ?? target.view); setRefused(null);
    try {
      const r = await api.asset(id, free.file, stepId("photo"), await shrink(file));
      await placed(r.name, target.view, target.hint);
    } catch (e) { fail(e); } finally { setBusy(null); }
  };
  const fromSample = async (source: string, view: string, hint?: string) => {
    if (!free) return;
    setBusy(hint ?? view); setRefused(null);
    try {
      const r = await putSample(id, free.file, stepId("photo"), source);
      await placed(r.name, view, hint);
    } catch (e) { fail(e); } finally { setBusy(null); }
  };
  const keepNote = async (text: string) => {
    if (!text.trim() || text === saved) return;
    await api.asset(id, conf.note, stepId("note"), new File([text], conf.note, { type: "text/markdown" }));
    setSaved(text);
  };
  const ask = async () => {
    setBusy("ask"); setRefused(null);
    try {
      await keepNote(note ?? "");
      await api.run(id, { skill: conf.helper, note: w.round((hints?.round ?? 0) + 1), request_id: stepId("onsite") });
      refresh();
    } catch (e) { fail(e); } finally { setBusy(null); }
  };
  const settle = async (h: OnsiteHint, text = "") => {
    setBusy(h.id); setRefused(null);
    try { await onsite.put(id, { hints: { [h.id]: { done: true, text } } }); refresh(); } catch (e) { fail(e); } finally { setBusy(null); }
  };
  const close = async () => {
    setBusy("close"); setRefused(null);
    const answered = (hints?.clarify ?? []).filter((h) => state.hints?.[h.id]?.text);
    const text = (note ?? "").trim() + (answered.length ? `\n\n## ${w.settledOnSite}\n\n${answered.map((h) => `- ${h.text}: ${state.hints![h.id].text}`).join("\n")}\n` : "\n");
    try {
      await keepNote(text);
      const r = await api.step(id, conf.close, stepId(conf.close), {});
      if (!r.ok) { setRefused(r.reason ?? ""); return; }
      go(`/case/${encodeURIComponent(id)}`);
    } catch (e) { fail(e); } finally { setBusy(null); }
  };

  const canClose = !!(note ?? "").trim() && taken.length > 0 && !thinking && !busy && v.my_turns.some((t) => t.action === conf.close);
  const hintItem = (kind: "photograph" | "clarify" | "notice", h: OnsiteHint) => {
    const done = settled(h);
    const src = kind === "photograph" ? sampleFor(h.id, h.view) : undefined;
    return (
      <li key={h.id} className={`os-hint ${kind}${done ? " done" : ""}`} data-hint={h.id}>
        <span className="tick" aria-hidden="true">{done ? "✓" : ""}</span>
        <div className="body">
          <p className="t">{h.text}</p>
          {h.why && <p className="why">{h.why}</p>}
          {done && state.hints?.[h.id]?.text && <p className="said">{state.hints[h.id].text}</p>}
          {!done && kind === "photograph" && (
            <div className="row">
              <button type="button" className="btn small" disabled={!!busy || !free} onClick={() => shoot(h.view ?? "weitere", h.id)}>{busy === h.id ? "…" : `◉ ${w.takePhoto}`}</button>
              {src && <button type="button" className="chip" data-sample={h.id} disabled={!!busy || !free} onClick={() => fromSample(src, h.view ?? "weitere", h.id)}>{w.sampleShot}</button>}
            </div>
          )}
          {!done && kind === "clarify" && (
            <form className="row" onSubmit={(e) => { e.preventDefault(); if ((answers[h.id] ?? "").trim()) settle(h, answers[h.id].trim()); }}>
              <input value={answers[h.id] ?? ""} onChange={(e) => setAnswers({ ...answers, [h.id]: e.target.value })} placeholder={w.settlePh} />
              <button type="submit" className="btn small" data-settle={h.id} disabled={!!busy || !(answers[h.id] ?? "").trim()}>{w.settle}</button>
            </form>
          )}
          {!done && kind === "notice" && <div className="row"><button type="button" className="chip" data-settle={h.id} disabled={!!busy} onClick={() => settle(h)}>{w.seen}</button></div>}
        </div>
      </li>
    );
  };

  return (
    <main className="main onsite">
      <header className="os-head">
        <button type="button" className="btn ghost small" onClick={() => go(`/case/${encodeURIComponent(id)}`)}>← {w.backToCase}</button>
        <div className="os-who">
          <span className="ref">{v.external_id || v.id}</span>
          <h1>{v.title}</h1>
          {v.meta?.subtitle ? <p className="sub">{String(v.meta.subtitle)}</p> : null}
        </div>
      </header>
      {refused && <div className="refused">{refused}</div>}
      <input ref={camera} type="file" accept="image/*" capture="environment" hidden onChange={(e) => { fromCamera(e.target.files?.[0]); e.target.value = ""; }} />

      <div className="os-body">
        <section className="os-photos" aria-label={w.photos}>
          <p className="kicker">{w.photos} · {w.viewsCount(covered, required.length)}</p>
          <div className="os-views">
            {conf.views.map((x) => {
              const shots = shotsOf(x.id);
              const src = sampleFor(x.id);
              return (
                <div key={x.id} className={`os-view${shots.length ? " has" : x.required ? " needed" : ""}`} data-view={x.id}>
                  <button type="button" className="shot" disabled={!!busy || !free} onClick={() => shoot(x.id)} aria-label={`${x.word} · ${w.takePhoto}`}>
                    {shots.length ? <img src={BASE + shots[shots.length - 1].versions[shots[shots.length - 1].versions.length - 1].url} alt="" /> : <span className="cam" aria-hidden="true">◉</span>}
                    {shots.length > 1 && <span className="n">{shots.length}</span>}
                    {busy === x.id && <span className="n">…</span>}
                  </button>
                  <span className="word">{x.word}</span>
                  {src && !shots.length && <button type="button" className="chip small" data-sample={x.id} disabled={!!busy || !free} onClick={() => fromSample(src, x.id)}>{w.sampleShot}</button>}
                </div>
              );
            })}
          </div>
        </section>

        <section className="os-talk">
          <label className="os-note">
            <span className="kicker">{w.onsiteNote}</span>
            <textarea value={note ?? ""} onChange={(e) => setNote(e.target.value)} onBlur={() => keepNote(note ?? "").catch(fail)} placeholder={w.onsiteNotePh} rows={5} />
          </label>
          <button type="button" className="btn os-ask" data-ask="1" disabled={!!busy || thinking || taken.length === 0} onClick={ask}>
            {thinking ? w.aiLooking(v.agent) : hints ? w.askAgain(v.agent) : w.askClaude(v.agent)}
          </button>

          <div className="os-hints" aria-live="polite">
            {!hints && !thinking && <p className="empty">{w.hintsEmpty(v.agent)}</p>}
            {thinking && <p className="os-thinking"><span className="pulse" />{w.aiLooking(v.agent)}</p>}
            {hints && (
              <>
                <p className="kicker">{v.agent} · {w.round(hints.round ?? 1)}</p>
                {hints.summary && <p className="os-summary">{hints.summary}</p>}
                {(["photograph", "clarify", "notice"] as const).map((kind) => (hints[kind]?.length ?? 0) > 0 && (
                  <div key={kind} className="os-group">
                    <p className="kicker">{kind === "photograph" ? w.photograph : kind === "clarify" ? w.clarify : w.notice}</p>
                    <ul>{hints[kind]!.map((h) => hintItem(kind, h))}</ul>
                  </div>
                ))}
              </>
            )}
          </div>
        </section>
      </div>

      <footer className="foot">
        {!canClose && !thinking && <span className="says">{w.closeNeeds}</span>}
        <button type="button" className="btn" data-action={conf.close} disabled={!canClose} onClick={close}>{busy === "close" ? "…" : `${w.closeInspection} →`}</button>
      </footer>
    </main>
  );
}
