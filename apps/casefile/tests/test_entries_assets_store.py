import threading

import pytest

from casefile.domain import assets, entries as thread
from casefile.models import Entry
from casefile.store import StoreError


def test_thread_roundtrip_keeps_the_pipelines_format_and_the_new_attributes():
    e = Entry(id="REV-004", title="v3 checked", date="2026-09-24 14:05", author="Axel", **{"for": "Akhil"}, status="open",
              stage="30-review-human", resolves="REV-002", step="s-1", **{"from": "20-produce"}, to="30-review-human", files=["substack.md"], text="text here")
    text = "# Review — x\n" + thread.render(e)
    back = thread.parse(text)
    assert len(back) == 1 and back[0] == e
    assert "**Date:** 2026-09-24 14:05 · **Author:** Axel · **For:** Akhil · **Status:** open · **Stage:** 30-review-human" in text
    assert thread.next_id(text) == "REV-005"


def test_old_entries_without_the_new_attributes_parse(store):
    text = store.case_text("FN-106-two-models-agreeing", "review.md")
    entries = thread.parse(text)
    assert [e.id for e in entries] == ["REV-001", "REV-002", "REV-003"]
    assert entries[1].for_ == "Chris" and entries[1].step is None
    assert [e.id for e in thread.open_for(entries, "Chris")] == ["REV-002"]


def test_assets_version_up_and_never_overwrite(store, config):
    n1 = assets.put(store, config, "SP-109-the-intern", "linkedin-image.png", b"\x89PNG1", "Akhil FINAL.png")
    n2 = assets.put(store, config, "SP-109-the-intern", "linkedin-image.png", b"\x89PNG2", "Akhil FINAL2.jpg")
    assert (n1, n2) == ("linkedin-image.png", "linkedin-image.v2.png")
    assert assets.next_name(store.files("SP-109-the-intern"), "linkedin-image.png") == "linkedin-image.v3.png"
    with pytest.raises(StoreError):
        assets.put(store, config, "SP-109-the-intern", "linkedin-image.png", b"MZ", "x.exe")
    with pytest.raises(StoreError):
        assets.put(store, config, "SP-109-the-intern", "nothing.png", b"x", "x.png")
    with pytest.raises(StoreError):
        assets.put(store, config, "SP-109-the-intern", "linkedin-image.png", b"", "x.png")


def test_the_store_refuses_to_overwrite_and_to_lose_a_case(store):
    with pytest.raises(StoreError):
        store.move("FN-105-the-review-that-reads-itself", "99-nowhere")
    (store.root / "40-asset-generation" / "FN-105-the-review-that-reads-itself").mkdir()
    with pytest.raises(StoreError):
        store.find("FN-105-the-review-that-reads-itself")


def test_the_lock_serialises_steps_on_one_case(store):
    order = []

    def worker(n):
        with store.lock("FN-105-the-review-that-reads-itself"):
            order.append(("in", n))
            threading.Event().wait(0.02)
            order.append(("out", n))

    ts = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    # never two "in" without an "out" between them
    depth = 0
    for kind, _ in order:
        depth += 1 if kind == "in" else -1
        assert depth in (0, 1)
