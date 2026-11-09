import unittest
from unittest.mock import patch

from chatbot.generation import (
    DEFAULT_GENERATION_MODEL,
    INSUFFICIENT_CONTEXT,
    answer_question,
)


def source(text, page=1, chunk_id="doc:p1:c0", quality_flags=None, needs_ocr=False):
    return {
        "source_path": "Bibliografia/fisica.pdf",
        "title": "Fisica",
        "page": page,
        "chunk_id": chunk_id,
        "text": text,
        "quality_flags": quality_flags or [],
        "needs_ocr": needs_ocr,
    }


class GenerationTests(unittest.TestCase):
    def run_answer(self, question, fragments):
        calls = {}

        def retrieve(received_question, limit):
            calls["question"] = received_question
            calls["limit"] = limit
            return fragments

        def check_model(model, base_url, timeout):
            calls["model"] = model
            return [model]

        def complete(system_prompt, user_prompt, model, base_url, timeout):
            calls["system"] = system_prompt
            calls["prompt"] = user_prompt
            return "Respuesta basada en el contexto [F1]."

        result = answer_question(
            question,
            retriever=retrieve,
            model_checker=check_model,
            chat_completion=complete,
        )
        return result, calls

    def test_spring_constant_answer_uses_retrieved_context(self):
        text = "La constante elastica k caracteriza la rigidez del resorte; la fuerza es proporcional a la deformacion y se expresa F = kx."
        result, calls = self.run_answer(
            "Que representa la constante elastica?", [source(text)]
        )
        self.assertIn(text, calls["prompt"])
        self.assertIn("[F1]", calls["prompt"])
        self.assertEqual(result["references"][0]["text"], text)
        self.assertTrue(result["generated"])

    def test_oscillation_period_context(self):
        text = "El periodo de oscilacion es el tiempo que tarda el sistema en efectuar una oscilacion completa."
        result, calls = self.run_answer("Como se define el periodo de oscilacion?", [source(text)])
        self.assertIn(text, calls["prompt"])
        self.assertEqual(result["references"][0]["page"], 1)

    def test_mechanical_energy_context(self):
        text = "La energia mecanica se expresa como suma de energia cinetica y energia potencial; E mec = E cin + E pot."
        _, calls = self.run_answer("Que relacion existe entre energia mecanica, cinetica y potencial?", [source(text)])
        self.assertIn(text, calls["prompt"])

    def test_angular_frequency_context(self):
        text = "La frecuencia angular omega se define mediante la relacion omega = 2 pi f. El pasaje identifica esa magnitud para describir la oscilacion."
        _, calls = self.run_answer("Que es la frecuencia angular?", [source(text)])
        self.assertIn("La frecuencia angular omega se define mediante la relacion omega = 2 pi f.", calls["prompt"])

    def test_multiple_fragments_and_references_are_preserved(self):
        fragments = [
            source("La masa y la elongacion caracterizan el movimiento del cuerpo dentro del sistema fisico considerado.", page=2, chunk_id="d:p2:c0"),
            source("La rigidez y la masa caracterizan la respuesta del sistema fisico durante el movimiento estudiado.", page=4, chunk_id="d:p4:c0"),
        ]
        result, calls = self.run_answer("Que relacion existe entre masa elongacion y rigidez?", fragments)
        for evidence in result["accepted_evidence"]:
            self.assertIn(evidence["text"], calls["prompt"])
        self.assertEqual([r["id"] for r in result["references"]], ["F1", "F2"])
        self.assertEqual([r["page"] for r in result["references"]], [2, 4])

    def test_ollama_unavailable(self):
        def unavailable(*args):
            raise RuntimeError("Ollama no esta disponible")

        result = answer_question(
                "Como se define el periodo de oscilacion?",
                retriever=lambda *args, **kwargs: [source("El periodo de oscilacion es el tiempo que tarda el sistema en efectuar una oscilacion completa.")],
                model_checker=unavailable,
                chat_completion=lambda *args: "no debe llamarse",
            )
        self.assertIn("no esta disponible", result["generation_error"])
        self.assertTrue(result["extractive_fallback"])

    def test_model_not_installed(self):
        def missing(model, *args):
            raise FileNotFoundError(f"{model} no esta instalado")

        result = answer_question(
                "Como se define el periodo de oscilacion?",
                retriever=lambda *args, **kwargs: [source("El periodo de oscilacion es el tiempo que tarda el sistema en efectuar una oscilacion completa.")],
                model_checker=missing,
                chat_completion=lambda *args: "no debe llamarse",
            )
        self.assertIn(DEFAULT_GENERATION_MODEL, result["generation_error"])
        self.assertTrue(result["extractive_fallback"])

    def test_model_checker_accepts_implicit_latest_tag(self):
        with patch(
            "chatbot.generation._request_json",
            return_value={"models": [{"name": "bge-m3:latest"}]},
        ):
            from chatbot.generation import check_ollama_model

            self.assertEqual(check_ollama_model("bge-m3"), ["bge-m3:latest"])

    def test_empty_context_abstains_without_calling_ollama(self):
        def should_not_run(*args):
            self.fail("No debe consultar Ollama cuando el contexto esta vacio")

        result = answer_question(
            "pregunta",
            retriever=lambda *args, **kwargs: [],
            model_checker=should_not_run,
            chat_completion=should_not_run,
        )
        self.assertEqual(result["answer"], INSUFFICIENT_CONTEXT)
        self.assertEqual(result["references"], [])
        self.assertFalse(result["generated"])


if __name__ == "__main__":
    unittest.main()
