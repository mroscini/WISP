from __future__ import annotations

from wisp.config import ConfigStore
from wisp.web import create_app


def make_client(tmp_path):
    config_path = tmp_path / "config.json"
    store = ConfigStore(config_path)
    config = store.defaults()
    config["paths"]["data_dir"] = str(tmp_path / "data")
    store.save(config)
    app = create_app(config_path)
    app.config.update(TESTING=True)
    return app.test_client()


def test_home_and_config_api(tmp_path):
    client = make_client(tmp_path)
    assert client.get("/").status_code == 200
    response = client.get("/api/config")
    assert response.status_code == 200
    assert response.get_json()["active_character_id"] == "spider-man"
    assert client.put("/api/config", json={}).status_code == 405
    assert client.get("/api/access").get_json()["url"] == "http://192.168.0.250:8787"
    qr = client.get("/access-qr.svg")
    assert qr.status_code == 200
    assert qr.mimetype == "image/svg+xml"


def test_child_settings_are_allowlisted(tmp_path):
    client = make_client(tmp_path)
    response = client.put(
        "/api/child",
        json={"display_name": "Alex", "age_range": "6-8", "story_preferences": "Spazio"},
    )
    assert response.status_code == 200
    assert response.get_json()["display_name"] == "Alex"
    rejected = client.put("/api/child", json={"paths": {"data_dir": "/tmp"}})
    assert rejected.status_code == 400


def test_character_and_document_api(tmp_path):
    client = make_client(tmp_path)
    created = client.post(
        "/api/characters",
        json={"name": "Luna Blu", "description": "Calma", "voice_id": "piper-paola"},
    )
    assert created.status_code == 201
    assert created.get_json()["id"] == "luna-blu"
    saved = client.get("/api/config").get_json()
    moon = next(item for item in saved["characters"] if item["id"] == "luna-blu")
    assert moon["voice_id"] == "piper-paola"
    activated = client.post("/api/characters/luna-blu/activate")
    assert activated.get_json()["active_id"] == "luna-blu"

    document = client.post(
        "/api/documents",
        json={"title": "Luna", "text": "Una storia originale.", "character_ids": ["luna-blu"]},
    )
    assert document.status_code == 201
    document_id = document.get_json()["id"]
    assert client.get(f"/api/documents/{document_id}").get_json()["title"] == "Luna"
    assert client.delete(f"/api/documents/{document_id}").status_code == 204


def test_voice_catalog_exposes_piper_presets(tmp_path):
    client = make_client(tmp_path)
    response = client.get("/api/voices")
    assert response.status_code == 200
    voices = {item["id"]: item for item in response.get_json()["items"]}
    assert voices["piper-paola"]["model"] == "it_IT-paola-medium"
    assert voices["piper-riccardo"]["model"] == "it_IT-riccardo-x_low"
    rejected = client.post(
        "/api/characters",
        json={"name": "Voce rotta", "voice_id": "not-a-real-voice"},
    )
    assert rejected.status_code == 404


def test_upload_guards(tmp_path):
    client = make_client(tmp_path)
    response = client.post(
        "/api/documents/upload",
        data={"file": (bytes("not text", "utf-8"), "bad.exe")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400

