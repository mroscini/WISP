from __future__ import annotations

import re
import tempfile
from io import BytesIO
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file

from ..config import ConfigError, ConfigStore
from ..conversation import ConversationService
from ..diagnostics import status_snapshot
from ..llm import LlamaCppClient, LlmError
from ..models import Character
from ..rag import HybridRetriever, IndexBuilder, IndexStore, OnnxEmbeddingBackend, OnnxReranker
from ..storage import DocumentError, DocumentStore
from ..voices import VoiceError, VoiceStore


class Runtime:
    def __init__(self, config_store: ConfigStore):
        self.config_store = config_store
        self._signature = None
        self._embedder = None
        self._reranker = None

    @property
    def config(self):
        return self.config_store.load()

    @property
    def documents(self):
        config = self.config
        return DocumentStore(config["paths"]["data_dir"], int(config["server"]["max_upload_bytes"]))

    @property
    def index(self):
        return IndexStore(self.config["paths"]["data_dir"])

    @property
    def llm(self):
        return LlamaCppClient(self.config["llm"])

    @property
    def voices(self):
        return VoiceStore(self.config["paths"]["voices_dir"])

    def models(self):
        config = self.config
        paths = config["paths"]
        signature = (
            paths["embedding_model"],
            paths["embedding_tokenizer"],
            paths["reranker_model"],
            paths["reranker_tokenizer"],
        )
        if signature != self._signature:
            self._embedder = OnnxEmbeddingBackend(signature[0], signature[1])
            self._reranker = OnnxReranker(signature[2], signature[3])
            self._signature = signature
        return self._embedder, self._reranker

    def conversation(self):
        config = self.config
        embedder, reranker = self.models()
        retriever = HybridRetriever(
            self.index,
            embedder,
            reranker,
            int(config["rag"]["top_k"]),
            int(config["rag"]["lexical_k"]),
        )
        return ConversationService(retriever, self.llm, float(config["rag"]["direct_answer_threshold"]))


def _payload() -> dict:
    value = request.get_json(silent=True)
    if not isinstance(value, dict):
        raise ValueError("A JSON object is required")
    return value


def create_app(config_path: str | Path | None = None, runtime: Runtime | None = None) -> Flask:
    store = ConfigStore(config_path)
    config = store.ensure()
    runtime = runtime or Runtime(store)
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.update(
        MAX_CONTENT_LENGTH=int(config["server"]["max_upload_bytes"]),
        JSON_SORT_KEYS=False,
    )

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; media-src 'self' blob:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'"
        )
        return response

    @app.errorhandler(ConfigError)
    @app.errorhandler(DocumentError)
    @app.errorhandler(VoiceError)
    @app.errorhandler(ValueError)
    def bad_request(error):
        return jsonify(error=str(error)), 400

    @app.errorhandler(FileNotFoundError)
    def not_found(error):
        return jsonify(error=f"Not found: {error}"), 404

    @app.errorhandler(LlmError)
    def upstream_error(error):
        return jsonify(error=str(error)), 503

    @app.errorhandler(413)
    def too_large(_error):
        return jsonify(error="Upload exceeds the configured size limit"), 413

    @app.get("/")
    def home():
        return render_template("index.html")

    @app.get("/api/access")
    def access():
        url = str(runtime.config["server"].get("public_url") or request.host_url).rstrip("/")
        return jsonify(url=url)

    @app.get("/access-qr.svg")
    def access_qr():
        try:
            import qrcode
            from qrcode.image.svg import SvgPathImage
        except ImportError as error:
            raise RuntimeError("qrcode is not installed") from error
        url = str(runtime.config["server"].get("public_url") or request.host_url).rstrip("/")
        image = qrcode.make(url, image_factory=SvgPathImage, border=2)
        stream = BytesIO()
        image.save(stream)
        stream.seek(0)
        return send_file(stream, mimetype="image/svg+xml", max_age=0)

    @app.get("/api/status")
    def status():
        return jsonify(status_snapshot(runtime.config, runtime.documents, runtime.index, runtime.llm))

    @app.get("/api/config")
    def get_config():
        return jsonify(runtime.config)

    @app.put("/api/child")
    def put_child():
        value = _payload()
        allowed = {"display_name", "age_range", "story_preferences"}
        if set(value) - allowed:
            raise ValueError("Unsupported child setting")
        cfg = runtime.config
        cfg["child"] = {key: str(value.get(key, "")).strip() for key in allowed}
        return jsonify(store.save(cfg)["child"])

    @app.get("/api/characters")
    def list_characters():
        cfg = runtime.config
        return jsonify(items=cfg["characters"], active_id=cfg["active_character_id"])

    @app.post("/api/characters")
    def create_character():
        value = _payload()
        character = Character.from_dict(value)
        if not character.id:
            character.id = re.sub(r"[^a-z0-9]+", "-", character.name.lower()).strip("-")[:64]
        if character.voice_id not in {"disabled", "command"}:
            runtime.voices.get(character.voice_id)
        cfg = runtime.config
        if character.id in {item["id"] for item in cfg["characters"]}:
            raise ValueError("Character id already exists")
        cfg["characters"].append(character.to_dict())
        store.save(cfg)
        return jsonify(character.to_dict()), 201

    @app.put("/api/characters/<character_id>")
    def update_character(character_id):
        value = _payload()
        cfg = runtime.config
        for index, item in enumerate(cfg["characters"]):
            if item["id"] == character_id:
                value["id"] = character_id
                character = Character.from_dict(value)
                if character.voice_id not in {"disabled", "command"}:
                    runtime.voices.get(character.voice_id)
                cfg["characters"][index] = character.to_dict()
                store.save(cfg)
                return jsonify(cfg["characters"][index])
        raise FileNotFoundError(character_id)

    @app.delete("/api/characters/<character_id>")
    def delete_character(character_id):
        cfg = runtime.config
        remaining = [item for item in cfg["characters"] if item["id"] != character_id]
        if len(remaining) == len(cfg["characters"]):
            raise FileNotFoundError(character_id)
        if not remaining:
            raise ValueError("At least one character is required")
        cfg["characters"] = remaining
        if cfg["active_character_id"] == character_id:
            cfg["active_character_id"] = remaining[0]["id"]
        store.save(cfg)
        return "", 204

    @app.post("/api/characters/<character_id>/activate")
    def activate_character(character_id):
        cfg = runtime.config
        if character_id not in {item["id"] for item in cfg["characters"]}:
            raise FileNotFoundError(character_id)
        cfg["active_character_id"] = character_id
        store.save(cfg)
        return jsonify(active_id=character_id)

    @app.get("/api/documents")
    def list_documents():
        return jsonify(items=runtime.documents.list())

    @app.post("/api/documents")
    def create_document():
        value = _payload()
        document = runtime.documents.create(
            str(value.get("title", "")), str(value.get("text", "")), value.get("character_ids", [])
        )
        return jsonify(document), 201

    @app.post("/api/documents/upload")
    def upload_document():
        upload = request.files.get("file")
        if not upload or not upload.filename:
            raise ValueError("A file is required")
        character_ids = request.form.getlist("character_ids")
        document = runtime.documents.import_upload(upload.filename, upload.read(), character_ids)
        return jsonify(document), 201

    @app.get("/api/documents/<document_id>")
    def get_document(document_id):
        return jsonify(runtime.documents.get(document_id))

    @app.put("/api/documents/<document_id>")
    def update_document(document_id):
        return jsonify(runtime.documents.update(document_id, _payload()))

    @app.delete("/api/documents/<document_id>")
    def delete_document(document_id):
        runtime.documents.delete(document_id)
        return "", 204

    @app.post("/api/index/rebuild")
    def rebuild_index():
        config = runtime.config
        embedder, _ = runtime.models()
        result = IndexBuilder(
            runtime.documents,
            runtime.index,
            embedder,
            int(config["rag"]["max_chunk_chars"]),
        ).rebuild()
        return jsonify(result)

    @app.post("/api/chat")
    def chat():
        value = _payload()
        config = runtime.config
        character = next(
            Character.from_dict(item)
            for item in config["characters"]
            if item["id"] == config["active_character_id"]
        )
        answer = runtime.conversation().answer(str(value.get("message", "")), character, config["child"])
        return jsonify(text=answer.text, mode=answer.mode, sources=answer.sources)

    @app.get("/api/voices")
    def voices():
        return jsonify(items=runtime.voices.list())

    @app.post("/api/voices/<voice_id>/install")
    def install_voice(voice_id):
        return jsonify(runtime.voices.install_piper(voice_id))

    @app.post("/api/voices/<voice_id>/preview")
    def voice_preview(voice_id):
        value = _payload()
        text = str(value.get("text", "Ciao! Questa è la mia voce.")).strip()
        if not 1 <= len(text) <= 240:
            raise ValueError("Il testo di prova deve contenere da 1 a 240 caratteri")
        synthesizer = runtime.voices.synthesizer(voice_id)
        with tempfile.TemporaryDirectory(prefix="wisp-preview-") as temporary:
            output = Path(temporary) / "preview.wav"
            synthesizer.synthesize(text, output)
            payload = output.read_bytes()
        return send_file(BytesIO(payload), mimetype="audio/wav", download_name="wisp-preview.wav")

    return app

