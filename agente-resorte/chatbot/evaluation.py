"""Evaluacion local reproducible de las cuatro consultas de la etapa 3C."""

from __future__ import annotations

from typing import Any, Callable

from .generation import answer_question

STAGE_3C_QUESTIONS = (
    "¿Qué representa la constante elástica de un resorte?",
    "¿Cómo se define el período de oscilación?",
    "¿Qué relación existe entre la energía mecánica, cinética y potencial?",
    "¿Qué es la frecuencia angular?",
)


def evaluate_stage_3c(
    *,
    model: str = "qwen2.5:7b",
    limit: int = 20,
    answerer: Callable[..., dict[str, Any]] = answer_question,
) -> dict[str, Any]:
    """Ejecuta cada consulta localmente y conserva candidatos, decisiones y tiempos."""
    records = []
    for question in STAGE_3C_QUESTIONS:
        result = answerer(question, model=model, limit=limit)
        records.append({"question": question, **result})
    return {
        "model": model,
        "retrieval_limit": limit,
        "query_count": len(records),
        "records": records,
    }
