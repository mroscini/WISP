from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class Character:
    id: str
    name: str
    description: str = ""
    instructions: str = ""
    voice_id: str = "disabled"

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Character":
        return cls(
            id=str(value.get("id", "")).strip(),
            name=str(value.get("name", "")).strip(),
            description=str(value.get("description", "")).strip(),
            instructions=str(value.get("instructions", "")).strip(),
            voice_id=str(value.get("voice_id", "disabled")).strip() or "disabled",
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RetrievedPassage:
    text: str
    source_id: str
    semantic_score: float = 0.0
    lexical_score: float = 0.0
    rerank_score: float | None = None


@dataclass(slots=True)
class Answer:
    text: str
    mode: str
    sources: list[str] = field(default_factory=list)

