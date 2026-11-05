"""The tutorial series of the claims demo: the catalog follows the language, every named file exists, only named files are served."""

import json

from fastapi.testclient import TestClient

from casefile.api.app import Settings, create_app
from casefile.demo.worlds import CONFIG, build_claims

VIDEOS = CONFIG / "claims-demo" / "videos"


def _client(tmp_path, lang):
    root = build_claims(tmp_path / "claims")
    app = create_app(Settings(root=root, config_dir=CONFIG / "claims-demo", secret="t", demo=True, lang=lang))
    client = TestClient(app)
    assert client.post("/api/session", json={"person": "du"}).status_code == 200
    return client


def test_every_file_the_catalog_names_is_there():
    doc = json.loads((CONFIG / "claims-demo" / "videos.json").read_text(encoding="utf-8"))
    for v in doc["videos"]:
        assert (VIDEOS / v["file"]).is_file(), v["file"]
        assert (VIDEOS / v["poster"]).is_file(), v["poster"]
        assert v["lang"] in ("de", "en") and v["seconds"] > 0 and "guides" in v["where"]


def test_the_catalog_follows_the_language_and_the_files_are_served(tmp_path):
    for lang, first in (("de", "Warum Casefile"), ("en", "Why Casefile")):
        client = _client(tmp_path / lang, lang)
        client.post("/api/session/lang", json={"lang": lang})
        vids = client.get("/api/config").json()["videos"]
        assert len(vids) == 9 and vids[0]["title"] == first
        assert all(v["url"].endswith(f"{lang}-{i + 1:02d}.mp4") for i, v in enumerate(vids))
        r = client.get(vids[0]["url"])
        assert r.status_code == 200 and r.headers["content-type"] == "video/mp4"
    assert client.get("/api/videos/videos.json").status_code == 404     # only what the catalog names
    assert client.get("/api/videos/..%2Fstages.json").status_code == 404
