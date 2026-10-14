from __future__ import annotations

from .models import Answer, Character


class ConversationService:
    def __init__(self, retriever, llm, direct_answer_threshold: float = 1.5):
        self.retriever = retriever
        self.llm = llm
        self.direct_answer_threshold = direct_answer_threshold

    def answer(self, user_text: str, character: Character, child: dict) -> Answer:
        user_text = user_text.strip()
        if not user_text:
            raise ValueError("Message is empty")
        passages = self.retriever.retrieve(user_text, character.id, limit=3)
        best = passages[0] if passages else None
        if best and best.rerank_score is not None and best.rerank_score > self.direct_answer_threshold:
            return Answer(text=best.text, mode="rag-direct", sources=[best.source_id])

        context = "\n\n".join(item.text for item in passages)
        child_name = str(child.get("display_name", "")).strip()
        audience = f" Ti rivolgi a {child_name}." if child_name else ""
        system = (
            f"Interpreta {character.name}. {character.description} {character.instructions}"
            f"{audience} Rispondi in italiano semplice e con massimo due frasi brevi. "
            "Non dire di essere un assistente o un modello. Non inventare dati personali. "
            "Se il contesto non basta, dichiaralo con naturalezza."
        ).strip()
        messages = [{"role": "system", "content": system}]
        if context:
            messages.append(
                {
                    "role": "system",
                    "content": "Contesto locale autorizzato; usalo senza aggiungere fatti:\n" + context,
                }
            )
        messages.append({"role": "user", "content": user_text})
        text = self.llm.complete(messages)
        if not text:
            raise RuntimeError("The model returned an empty response")
        return Answer(text=text, mode="llm-with-rag" if context else "llm", sources=[item.source_id for item in passages])

