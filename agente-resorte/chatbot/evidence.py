"""Seleccion determinista de evidencia y validacion extractiva de afirmaciones.

No utiliza otro modelo. Para las consultas conceptuales cubiertas se exigen
senales tematicas y definitorias en el mismo fragmento; el score de busqueda
solo conserva el orden de candidatos y nunca basta para aceptarlos.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any


STOPWORDS = {
    "a", "al", "algo", "como", "con", "de", "del", "desde", "el", "en",
    "es", "esta", "existe", "la", "las", "lo", "los", "mas", "me", "mi",
    "o", "para", "por", "que", "se", "su", "un", "una", "y", "entre",
}

INSUFFICIENT_EVIDENCE = (
    "No se encontro evidencia bibliografica pertinente y confiable para responder."
)


def normalize_text(text: str) -> str:
    text = (text or "").casefold()
    # These mappings are for topic matching only. They do not rewrite cited text,
    # and Latin w/v/p are deliberately not treated as Greek symbols.
    for symbol, word in (("ω", " omega "), ("π", " pi "), ("ν", " nu "), ("θ", " theta ")):
        text = text.replace(symbol.casefold(), word)
    decomposed = unicodedata.normalize("NFD", text)
    plain = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(re.findall(r"[a-z0-9]+", plain))


def _tokens(text: str) -> set[str]:
    return set(normalize_text(text).split())


def _has(text: str, phrase: str) -> bool:
    normalized = normalize_text(text)
    target = normalize_text(phrase)
    return bool(target) and f" {target} " in f" {normalized} "


def _has_any(text: str, phrases: tuple[str, ...] | list[str]) -> bool:
    return any(_has(text, phrase) for phrase in phrases)


def detect_intent(question: str) -> str:
    terms = _tokens(question)
    if "constante" in terms and ("elastica" in terms or "resorte" in terms):
        return "constante_elastica"
    if "periodo" in terms and "oscilacion" in terms:
        return "periodo"
    if "energia" in terms and "mecanica" in terms and (
        "cinetica" in terms or "potencial" in terms
    ):
        return "energia_mecanica"
    if "frecuencia" in terms and "angular" in terms:
        return "frecuencia_angular"
    return "generica"


def _profile_groups(intent: str, text: str, question: str = "") -> dict[str, bool]:
    normalized = normalize_text(text)
    terms = set(normalized.split())
    if intent == "constante_elastica":
        concept = _has_any(
            normalized,
            (
                "constante elastica", "constante recuperadora", "constante de fuerza",
                "rigidez k", "pendiente de la recta fuerza deformacion",
            ),
        )
        force = _has_any(normalized, ("fuerza", "f=kx", "f kx"))
        deformation = _has_any(
            normalized, ("deformacion", "desplazamiento", "elongacion", "pendiente")
        )
        relationship = (
            ("proporcional" in terms and deformation)
            or ("pendiente" in terms and force)
            or (force and deformation and _has_any(normalized, ("f=kx", "f kx", "k x")))
        )
        return {"concepto": concept, "relacion_fuerza_deformacion": relationship}

    if intent == "periodo":
        period = "periodo" in terms or "periodicidad" in terms
        time = _has_any(normalized, ("tiempo", "tarda", "intervalo de tiempo"))
        cycle = _has_any(
            normalized,
            ("ciclo", "oscilacion completa", "vuelta completa", "mismos valores"),
        )
        return {
            "periodo": period,
            "definicion_tiempo_ciclo": time and cycle and _has_any(
                normalized,
                ("es el tiempo", "tiempo que tarda", "se define", "se denomina"),
            ),
        }

    if intent == "energia_mecanica":
        mechanical = _has_any(normalized, ("energia mecanica", "e mec"))
        kinetic = _has_any(normalized, ("energia cinetica", "e cin"))
        potential = _has_any(normalized, ("energia potencial", "e pot"))
        relationship = _has_any(
            normalized,
            ("suma", "transforma", "se conserva", "conservacion", "igual a", "no cambia", "se relaciona", "relaciona"),
        ) or _has_energy_equation(text)
        direct_three_way = mechanical and kinetic and potential and _has_direct_energy_relation(text)
        return {
            "energia_mecanica": mechanical,
            "energia_cinetica": kinetic,
            "energia_potencial": potential,
            "relacion_entre_energias": relationship,
            "relacion_directa_entre_tres_energias": direct_three_way,
        }

    if intent == "frecuencia_angular":
        concept = _has_any(normalized, ("frecuencia angular", "omega"))
        relation = _has_any(
            normalized,
            (
                "2 pi f", "2 pi frecuencia", "2 pi t", "veces la frecuencia",
                "relacionada con la frecuencia", "relacionada con las anteriores",
                "dado por", "frecuencia angular es",
            ),
        ) or _has_angular_equation(text)
        return {"frecuencia_angular": concept, "definicion_o_relacion": relation}

    query_terms = [t for t in _tokens(question) if len(t) >= 4 and t not in STOPWORDS]
    return {f"termino:{term}": term in terms for term in query_terms[:8]}


def _has_energy_equation(text: str) -> bool:
    raw = normalize_text(text)
    compact = re.sub(r"\s+", "", raw)
    return bool(
        re.search(r"emec=?ecin\+?epot", compact)
        or re.search(r"em=?ec\+?ep", compact)
    )


def _has_direct_energy_relation(text: str) -> bool:
    """Requires a single explicit expression joining mechanical, kinetic and potential energy."""
    normalized = normalize_text(text)
    if all(_has_any(normalized, choices) for choices in (
        ("energia mecanica", "e mec"),
        ("energia cinetica", "e cin"),
        ("energia potencial", "e pot"),
    )) and _has_energy_equation(text):
        return True
    relation_patterns = (
        r"energia mecanica.{0,100}suma.{0,100}energia cinetica.{0,100}energia potencial",
        r"energia mecanica.{0,100}suma.{0,100}energia potencial.{0,100}energia cinetica",
        r"energia cinetica.{0,80}energia potencial.{0,80}energia mecanica",
        r"energia potencial.{0,80}energia cinetica.{0,80}energia mecanica",
    )
    return any(re.search(pattern, normalized) for pattern in relation_patterns)


def _has_angular_equation(text: str) -> bool:
    raw = normalize_text(text)
    compact = re.sub(r"\s+", "", raw)
    return bool(
        re.search(r"omega=?2pi(f|frecuencia)", compact)
        or re.search(r"omega=?2pi/?t", compact)
    )


def _math_notation_problems(intent: str, text: str) -> list[str]:
    """Detecta ambiguedad/extraccion matematica dudosa sin reparar la formula."""
    problems = []
    if not text:
        return problems

    math_context = bool(re.search(
        r"(?:=|\+|\u2212|\u00d7|\u00f7|\u221a|\u2211|\u222b|\u00bd|\u00bc|\u00be|"
        r"[\u2070-\u2079\u2080-\u2089]|\\(?:frac|sqrt))",
        text,
    ))
    cue = re.search(r"\b(?:f[oó]rmula|ecuaci[oó]n|expresi[oó]n matem[aá]tica)\b", text, re.I)
    if cue:
        # Check near the cue, not elsewhere in the chunk: an unrelated equation
        # later in the passage cannot repair a damaged expression.
        expression_window = text[cue.end() : cue.end() + 180]
        if not re.search(r"(?:=|\+|\-|/|\^|_|[\u00d7\u00f7\u22c5]|[\u2070-\u2079\u2080-\u2089])", expression_window):
            problems.append("se anuncia una formula o ecuacion, pero la expresion no se pudo verificar")
    if math_context and re.search(r"(?:=|\+|\u2212|\u00d7|\u00f7|/|\^|_)\s*(?:$|[.,;:])", text):
        problems.append("expresion matematica posiblemente incompleta")

    if intent == "frecuencia_angular":
        explicit_omega = "\u03c9" in text or bool(re.search(r"\bomega\b", text, re.I))
        explicit_pi = "\u03c0" in text or bool(re.search(r"\bpi\b", text, re.I))
        if math_context and not explicit_omega and re.search(r"\b[vw]\b", text, re.I):
            problems.append("variable ASCII v/w ambigua; no se equipara con omega")
        if math_context and not explicit_pi and re.search(r"(?:\b2\s*p\b|\b2p(?:\b|[a-z]))", text, re.I):
            problems.append("letra p ambigua; no se equipara con pi")
        # Sears p.468 has no '=' sign, but its symbol claim is still mathematical
        # notation and must not be treated as a verified equation by literal match.
        if not explicit_omega and re.search(r"\bfrecuencia\s+angular\s+v\b", text, re.I):
            problems.append("simbolo v ambiguo en la definicion de frecuencia angular")
        if not explicit_pi and re.search(r"\b2\s+p\s+veces\b", text, re.I):
            problems.append("secuencia 2 p ambigua en una relacion matematica")

    return problems


def _quality_problems(candidate: dict[str, Any]) -> list[str]:
    problems = []
    if candidate.get("needs_ocr") is True:
        problems.append("la pagina requiere OCR")
    if candidate.get("needs_ocr") is None:
        problems.append("no hay metadato de estado OCR")
    flags = candidate.get("quality_flags") or []
    if isinstance(flags, str):
        flags = [flags]
    problems.extend(f"marca de calidad: {flag}" for flag in flags)
    source_path = str(candidate.get("source_path") or "").replace("\\", "/")
    if not re.match(r"^bibliograf[ií]a/", source_path, re.I):
        problems.append("fuente fuera de la bibliografia local permitida")
    text = str(candidate.get("text") or "")
    if len(text.strip()) < 80:
        problems.append("texto insuficiente (menos de 80 caracteres)")
    if "\ufffd" in text:
        problems.append("extraccion con caracter de reemplazo")
    if any("\ue000" <= char <= "\uf8ff" for char in text):
        problems.append("extraccion con simbolo de fuente no decodificado")
    # OCR/PDF extraction sometimes substitutes unknown glyphs with literal '?'.
    # Reject only dense corruption; isolated punctuation remains usable.
    if text and text.count("?") / len(text) > 0.02:
        problems.append("extraccion con alta proporcion de signos de reemplazo (?)")
    if re.search(
        r"\b(?:medi|constant|resor|fuerz|energ|potenci|cinetic|oscil|defin|amorti|frecuenc)\s+[aeiou]\b|\bsarro\s+lla\b",
        text,
    ):
        problems.append("extraccion con palabras fisicas fragmentadas")
    meaningful = re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{3,}", text)
    if len(meaningful) < 8:
        problems.append("contenido legible insuficiente")
    return problems


def _content_kind(text: str) -> str:
    """Clasifica indicadores explicitos de contexto; no trata 'problema' suelto como ejercicio."""
    value = (text or "").strip()
    header = re.match(
        r"(?is)^(?:problema|ejercicio|ejemplo|solucion|resolucion|respuesta|rta)"
        r"(?:\s*(?:n(?:ro|umero)?\.?\s*\d+|#\s*\d+))?\s*(?:[:.)=\-]|\b)",
        value,
    )
    if header:
        label = normalize_text(header.group(0))
        if label.startswith(("problema", "ejercicio")):
            return "ejercicio"
        if label.startswith("ejemplo"):
            return "ejemplo"
        if label.startswith(("solucion", "resolucion")):
            return "procedimiento"
        return "resultado"
    if re.search(r"(?i)\b(?:calcule|determine|resuelva|halle|obtenga|demuestre)\b", value):
        return "procedimiento"
    return "teoria_o_no_clasificado"


def _candidate_context_problem(intent: str, excerpt: str, full_text: str) -> list[str]:
    if intent == "generica":
        return []
    for text in (excerpt, full_text):
        kind = _content_kind(text)
        if kind in {"ejercicio", "ejemplo", "procedimiento", "resultado"}:
            return [f"contenido clasificado como {kind}; no se usa para una respuesta conceptual general"]
    return []


def _assess_profile(
    intent: str, excerpt: str, question: str = ""
) -> tuple[bool, float, list[str], dict[str, bool]]:
    groups = _profile_groups(intent, excerpt, question)
    matched = [name for name, value in groups.items() if value]
    missing = [name for name, value in groups.items() if not value]
    score = len(matched) / max(1, len(groups))
    if intent in {"constante_elastica", "periodo", "frecuencia_angular"}:
        required = 2 if intent != "periodo" else 3
        relevant = len(matched) == len(groups) or (
            intent == "periodo" and groups.get("periodo") and groups.get("definicion_tiempo_ciclo")
        )
        if intent == "constante_elastica":
            relevant = groups.get("concepto", False) and groups.get(
                "relacion_fuerza_deformacion", False
            )
        if intent == "frecuencia_angular":
            relevant = groups.get("frecuencia_angular", False) and groups.get(
                "definicion_o_relacion", False
            )
    elif intent == "energia_mecanica":
        relevant = (
            groups.get("energia_mecanica", False)
            and groups.get("relacion_entre_energias", False)
            and (groups.get("energia_cinetica", False) or groups.get("energia_potencial", False))
        )
    else:
        relevant = len(matched) >= 2 and score >= 0.5
    reasons = []
    if matched:
        reasons.append("senales presentes: " + ", ".join(matched))
    if missing:
        reasons.append("faltan senales: " + ", ".join(missing))
    return relevant, score, reasons, groups


def _sentence_windows(text: str, max_chars: int = 1000) -> list[str]:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\r?\n+", text) if s.strip()]
    if not sentences:
        return [text.strip()] if text.strip() else []
    windows = []
    for width in (1, 2, 3):
        for start in range(0, len(sentences) - width + 1):
            window = " ".join(sentences[start : start + width])
            if len(window) <= max_chars:
                windows.append(window)
    return windows or [text[:max_chars].strip()]


def _best_excerpt(intent: str, text: str, question: str = "") -> str:
    windows = _sentence_windows(text)
    ranked = []
    for window in windows:
        relevant, score, _, _ = _assess_profile(intent, window, question)
        ranked.append((relevant, score, -len(window), window))
    relevant_windows = [item for item in ranked if item[0]]
    if relevant_windows:
        return max(relevant_windows)[3]
    if not windows:
        return ""
    return max(ranked)[3]


def assess_relevance(question: str, candidate: dict[str, Any]) -> dict[str, Any]:
    """Evalua tema y calidad; el score del retriever no decide relevancia."""
    intent = detect_intent(question)
    text = str(candidate.get("text") or "")
    excerpt = _best_excerpt(intent, text, question)
    relevant, score, reasons, groups = _assess_profile(intent, excerpt, question)
    quality = _quality_problems(candidate)
    full_text = str(candidate.get("text") or "")
    context_problems = _candidate_context_problem(intent, excerpt, full_text)
    # Inspect the whole chunk: a clean-looking sentence must not be detached
    # from a damaged formula or notation in its surrounding passage.
    math_problems = _math_notation_problems(intent, full_text)
    quality.extend(math_problems)
    if context_problems:
        reasons.extend(context_problems)
        relevant = False
    if math_problems:
        relevant = False
    if quality:
        reasons.extend(quality)
        relevant = False
    if relevant:
        reasons.append("aceptado: correspondencia tematica y evidencia directa")
    elif not quality and not any("faltan senales" in reason for reason in reasons):
        reasons.append("descartado: no supera las reglas de evidencia directa")
    return {
        "intent": intent,
        "relevant": relevant,
        "relevance_score": score,
        "matched_groups": [name for name, matched in groups.items() if matched],
        "expected_groups": list(groups),
        "reasons": reasons,
        "quality_problems": quality,
        "content_kind": _content_kind(excerpt),
        "direct_groups_complete": bool(groups) and all(groups.values()),
        "excerpt": excerpt,
    }


def select_evidence(question: str, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """Separa candidatos en evidencia utilizable y descartes explicados."""
    accepted = []
    discarded = []
    assessments = []
    covered: set[str] = set()
    intent = detect_intent(question)
    for candidate in candidates:
        assessment = assess_relevance(question, candidate)
        diagnostics = {
            "chunk_id": candidate.get("chunk_id"),
            "source_path": candidate.get("source_path"),
            "page": candidate.get("page"),
            "score": candidate.get("score"),
            "sources": candidate.get("sources", []),
            "text": candidate.get("text", ""),
            **assessment,
        }
        assessments.append(diagnostics)
        if not assessment["relevant"]:
            discarded.append(diagnostics)
            continue
        evidence_id = f"F{len(accepted) + 1}"
        flags = candidate.get("quality_flags") or []
        accepted_item = {
            "id": evidence_id,
            "chunk_id": candidate.get("chunk_id"),
            "doc_id": candidate.get("doc_id"),
            "document": candidate.get("title") or candidate.get("source_path", ""),
            "source_path": candidate.get("source_path", ""),
            "page": candidate.get("page"),
            "score": candidate.get("score"),
            "text": assessment["excerpt"],
            "chunk_text": candidate.get("text", ""),
            "needs_ocr": candidate.get("needs_ocr"),
            "quality_flags": flags,
            "relevance_score": assessment["relevance_score"],
            "matched_groups": assessment["matched_groups"],
            "expected_groups": assessment["expected_groups"],
        }
        accepted.append(accepted_item)
        covered.update(assessment["matched_groups"])
    expected = []
    if assessments:
        expected = assessments[0]["expected_groups"]
    missing = [group for group in expected if group not in covered]
    direct_complete = any(
        bool(expected) and set(expected).issubset(set(item["matched_groups"]))
        for item in accepted
    )
    if accepted and not direct_complete and not missing:
        missing.append("relacion_directa_en_un_mismo_fragmento")
    if intent == "energia_mecanica" and accepted and not direct_complete:
        if "relacion_directa_entre_las_tres_energias" not in missing:
            missing.append("relacion_directa_entre_las_tres_energias")
    return {
        "intent": intent,
        "accepted": accepted,
        "discarded": discarded,
        "assessments": assessments,
        "covered_groups": sorted(covered),
        "expected_groups": expected,
        "missing_groups": missing,
        "coverage_complete": direct_complete,
        "status": "sin evidencia suficiente" if not accepted else (
            "respaldada" if direct_complete else "parcial"
        ),
    }


def split_claims(answer: str) -> list[str]:
    claims = []
    for line in (answer or "").splitlines():
        line = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line).strip()
        if not line:
            continue
        citations = re.search(r"(?:\s*\[F\d+(?:\s*,\s*F\d+)*\])+$", line)
        suffix = citations.group(0).strip() if citations else ""
        body = line[: citations.start()].rstrip() if citations else line
        parts = [part.strip() for part in re.split(
            r";\s*|(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÜ¿¡\[])", body
        ) if part.strip()]
        if suffix:
            parts = [f"{part} {suffix}" for part in parts]
        claims.extend(parts)
    return claims


def _exact_quote(claim: str, evidence_text: str) -> bool:
    no_citations = re.sub(r"\[(?:F\d+)(?:\s*,\s*F\d+)*\]", "", claim)

    def quote_normalize(value: str) -> str:
        value = unicodedata.normalize("NFC", value or "").casefold()
        value = value.strip().strip("\"'“”‘’«»")
        return " ".join(value.split())

    claim_norm = quote_normalize(no_citations)
    evidence_norm = quote_normalize(evidence_text)
    if not claim_norm:
        return False
    start = 0
    while True:
        index = evidence_norm.find(claim_norm, start)
        if index < 0:
            return False
        end = index + len(claim_norm)
        left_ok = index == 0 or not (evidence_norm[index - 1].isalnum() or evidence_norm[index - 1] == "_")
        right_ok = end == len(evidence_norm) or not (evidence_norm[end].isalnum() or evidence_norm[end] == "_")
        if left_ok and right_ok:
            formula = _formula_like(claim_norm)
            left = evidence_norm[index - 1] if index else ""
            right = evidence_norm[end] if end < len(evidence_norm) else ""
            math_ops = "=+-*/^_"
            if formula and ((left and left in math_ops) or (right and right in math_ops)):
                start = index + 1
                continue
            return True
        start = index + 1


def _formula_like(claim: str) -> bool:
    return bool(re.search(
        r"[=+*/^_]|\\(?:\[|\(|frac|sqrt)|[√∑∫∞≤≥≠≈±×÷]|"
        r"[⁰¹²³⁴⁵⁶⁷⁸⁹₀₁₂₃₄₅₆₇₈₉]|[¼½¾]|\b\d+(?:[.,]\d+)?\s*(?:Hz|N|kg|m/s|rad)\b",
        claim,
        re.I,
    ))


def _claim_relevance_problems(question: str, claim: str) -> list[str]:
    intent = detect_intent(question)
    normalized = normalize_text(claim)
    terms = set(normalized.split())
    if intent == "constante_elastica":
        relevant = bool(terms.intersection({"constante", "elastica", "recuperadora", "rigidez", "deformacion", "fuerza"}))
    elif intent == "periodo":
        relevant = bool(terms.intersection({"periodo", "ciclo", "oscilacion", "tiempo", "tarda"}))
    elif intent == "energia_mecanica":
        relevant = bool(terms.intersection({"energia", "mecanica", "cinetica", "potencial"}))
    elif intent == "frecuencia_angular":
        relevant = "frecuencia" in terms and "angular" in terms or "omega" in terms
    else:
        query_terms = {t for t in _tokens(question) if len(t) >= 4 and t not in STOPWORDS}
        relevant = len(terms.intersection(query_terms)) >= 1
    return [] if relevant else ["afirmacion fuera del tema solicitado"]


def validate_claims(
    answer: str,
    evidence: list[dict[str, Any]],
    question: str = "",
) -> dict[str, Any]:
    """Valida cada proposicion literal, citada y pertinente a la pregunta."""
    by_id = {item["id"]: item for item in evidence}
    verified = []
    rejected = []
    for claim in split_claims(answer):
        relevance_problems = _claim_relevance_problems(question, claim) if question else []
        if relevance_problems:
            rejected.append({"claim": claim, "reason": "; ".join(relevance_problems)})
            continue
        citation_ids = re.findall(r"\[(F\d+)(?:\s*,\s*(F\d+))*\]", claim)
        flat_ids = []
        for first, second in citation_ids:
            flat_ids.append(first)
            if second:
                flat_ids.append(second)
        # Also accept a list with more than two F references.
        flat_ids = re.findall(r"\bF\d+\b", " ".join(re.findall(r"\[[^\]]+\]", claim)))
        unknown = sorted(set(flat_ids) - set(by_id))
        if not flat_ids:
            rejected.append({"claim": claim, "reason": "afirmacion sin referencia"})
            continue
        if unknown:
            rejected.append({"claim": claim, "reason": "referencias no entregadas: " + ", ".join(unknown)})
            continue
        cited = [by_id[ref_id] for ref_id in dict.fromkeys(flat_ids)]
        evidence_problems = []
        for item in cited:
            if item.get("needs_ocr") is True:
                evidence_problems.append("la fuente requiere OCR")
            if item.get("quality_flags"):
                evidence_problems.append("la fuente tiene marcas de calidad")
            evidence_problems.extend(_math_notation_problems(detect_intent(question), item.get("text", "")))
        if evidence_problems:
            rejected.append({"claim": claim, "reason": "; ".join(dict.fromkeys(evidence_problems))})
            continue
        if any(_exact_quote(claim, item["text"]) for item in cited):
            verified.append({"claim": claim, "references": list(dict.fromkeys(flat_ids))})
            continue
        if _formula_like(claim):
            reason = "formula o valor no coincide literalmente con la evidencia citada"
        else:
            reason = "afirmacion no es una cita textual continua de la evidencia citada"
        rejected.append({"claim": claim, "reason": reason})
    if verified and not rejected:
        status = "respaldada"
    elif verified:
        status = "parcial"
    else:
        status = "sin evidencia suficiente"
    return {"verified": verified, "rejected": rejected, "status": status}


def extractive_answer(evidence: list[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    """Construye citas textuales verificables como alternativa segura a Qwen."""
    return [
        {"claim": item["text"], "references": [item["id"]], "extractive": True}
        for item in evidence[: max(1, limit)]
        if item.get("text")
    ]
