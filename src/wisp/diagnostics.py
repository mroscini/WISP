from __future__ import annotations

import os
import shutil
import time
from pathlib import Path


def _load() -> list[float] | None:
    try:
        return [round(value, 2) for value in os.getloadavg()]
    except (AttributeError, OSError):
        return None


def status_snapshot(config: dict, documents, index, llm) -> dict:
    data_dir = Path(config["paths"]["data_dir"]).resolve()
    usage = shutil.disk_usage(data_dir if data_dir.exists() else data_dir.parent)
    indexed = index.load()
    return {
        "timestamp": time.time(),
        "llm_online": llm.health(),
        "model": Path(config["paths"]["llama_model"]).name,
        "load_average": _load(),
        "disk": {"total": usage.total, "used": usage.used, "free": usage.free},
        "documents": len(documents.list()),
        "indexed_chunks": int(len(indexed.get("texts", []))),
        "active_character_id": config["active_character_id"],
        "audio": config.get("audio", {}),
    }

