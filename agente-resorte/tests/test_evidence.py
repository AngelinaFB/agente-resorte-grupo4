import unittest

from chatbot.evidence import select_evidence, validate_claims


def fragment(text, *, page=4, flags=None, needs_ocr=False, chunk="doc:p4:c0"):
    return {
        "source_path": "Bibliografia/fisica.pdf",
        "title": "Fisica",
        "page": page,
        "chunk_id": chunk,
        "text": text,
        "quality_flags": flags or [],
        "needs_ocr": needs_ocr,
    }


class EvidenceTests(unittest.TestCase):
    def test_unrelated_exercise_is_rejected(self):
        exercise = fragment(
            "Problema: un bloque comprime un resorte y se mueve por una superficie. "
            "Calcule la distancia recorrida usando los datos indicados en el ejercicio."
        )
        selected = select_evidence("Que representa la constante elastica de un resorte?", [exercise])
        self.assertEqual(selected["accepted"], [])
        self.assertTrue(selected["discarded"])

    def test_formula_absent_from_evidence_is_rejected(self):
        evidence = [{"id": "F1", "text": "La frecuencia angular es una magnitud del movimiento oscilatorio."}]
        result = validate_claims("La frecuencia angular se calcula con omega = 2 pi / T [F1]", evidence)
        self.assertEqual(result["verified"], [])
        self.assertIn("formula", result["rejected"][0]["reason"])

    def test_changed_formula_punctuation_is_not_an_exact_quote(self):
        evidence = [{"id": "F1", "text": "w=2pn por lo tanto T 2p w= Introduccion."}]
        result = validate_claims("w=2pn por lo tanto T 2p w. [F1]", evidence)
        self.assertEqual(result["verified"], [])
        self.assertEqual(len(result["rejected"]), 1)

    def test_derived_calculation_from_example_is_rejected(self):
        evidence = [{"id": "F1", "text": "El ejemplo presenta una frecuencia de 4 Hz para el sistema."}]
        result = validate_claims(
            "El ejemplo presenta una frecuencia de 4 Hz para el sistema. "
            "El periodo es 0,25 s. [F1]",
            evidence,
            "Que frecuencia aparece en el ejemplo?",
        )
        self.assertEqual(len(result["verified"]), 1)
        self.assertEqual(len(result["rejected"]), 1)

    def test_uncited_claim_is_rejected(self):
        result = validate_claims("El período es el tiempo de un ciclo.", [{"id": "F1", "text": "El período es el tiempo de un ciclo."}])
        self.assertEqual(result["verified"], [])
        self.assertIn("sin referencia", result["rejected"][0]["reason"])

    def test_invented_reference_is_rejected(self):
        result = validate_claims("El periodo es el tiempo de un ciclo [F9].", [{"id": "F1", "text": "El periodo es el tiempo de un ciclo."}])
        self.assertIn("F9", result["rejected"][0]["reason"])

    def test_off_topic_claim_is_rejected(self):
        evidence = [{"id": "F1", "text": "El periodo es el tiempo que tarda un ciclo completo de oscilacion."}]
        result = validate_claims("La masa determina la constante elastica del resorte [F1].", evidence)
        self.assertEqual(result["verified"], [])

    def test_exact_claim_with_verifiable_reference_is_accepted(self):
        sentence = "El periodo es el tiempo que tarda un ciclo completo de oscilacion."
        result = validate_claims(sentence + " [F1]", [{"id": "F1", "text": sentence}])
        self.assertEqual(result["status"], "respaldada")
        self.assertEqual(result["verified"][0]["references"], ["F1"])

    def test_partial_energy_evidence_is_reported_partial(self):
        source = fragment(
            "La energia mecanica es la suma de la energia cinetica del sistema. "
            "El texto explica esa relacion para el caso mencionado en el apartado."
        )
        selected = select_evidence(
            "Que relacion existe entre la energia mecanica, cinetica y potencial?", [source]
        )
        self.assertEqual(selected["status"], "parcial")
        self.assertIn("energia_potencial", selected["missing_groups"])

    def test_no_evidence_abstains(self):
        selected = select_evidence("Que es la frecuencia angular?", [])
        self.assertEqual(selected["status"], "sin evidencia suficiente")
        self.assertEqual(selected["accepted"], [])

    def test_low_quality_page_cannot_be_accepted(self):
        source = fragment(
            "El periodo es el tiempo al cabo del cual se repiten los valores del sistema. "
            "En un resorte, corresponde al tiempo de una oscilacion completa.",
            flags=["palabras_muy_cortas"],
        )
        selected = select_evidence("Como se define el periodo de oscilacion?", [source])
        self.assertEqual(selected["accepted"], [])
        self.assertTrue(any("calidad" in r for r in selected["discarded"][0]["reasons"]))

    def test_single_replacement_glyph_marks_extraction_unreliable(self):
        source = fragment(
            "El periodo es el tiempo al cabo del cual se repiten los valores del sistema. "
            "En un resorte corresponde al tiempo de una oscilacion completa. \ufffd"
        )
        selected = select_evidence("Como se define el periodo de oscilacion?", [source])
        self.assertEqual(selected["accepted"], [])
        self.assertTrue(any("reemplazo" in r for r in selected["discarded"][0]["reasons"]))

    def test_hooke_exercise_without_explicit_constant_definition_is_rejected(self):
        source = fragment(
            "Un resorte colgante obedece la ley de Hooke. El cuerpo está en equilibrio y se mueve "
            "respecto de su posición; la fuerza neta será proporcional al desplazamiento."
        )
        selected = select_evidence("Que representa la constante elastica de un resorte?", [source])
        self.assertEqual(selected["accepted"], [])

    def test_energy_example_is_not_generalized_as_definition(self):
        source = fragment(
            "Ejemplo: la energia cinetica que adquirio el cuerpo fue entregada por el resorte. "
            "La energia mecanica no cambia en este caso particular, segun el texto del ejercicio."
        )
        selected = select_evidence(
            "Que relacion existe entre la energia mecanica, cinetica y potencial?", [source]
        )
        self.assertEqual(selected["accepted"], [])

    def test_fragmented_physics_words_are_quality_warning(self):
        source = fragment(
            "La constante elastica es una medi a grafico; la constant e es la pendiente "
            "de la recta del grafico fuerza en funcion del resorte."
        )
        selected = select_evidence("Que representa la constante elastica?", [source])
        self.assertEqual(selected["accepted"], [])

    def test_citation_at_end_of_line_applies_to_each_exact_sentence(self):
        first = "El periodo es el tiempo que tarda un ciclo."
        second = "El periodo siempre es positivo."
        evidence = [{"id": "F1", "text": first + " " + second}]
        result = validate_claims(first + " " + second + " [F1]", evidence)
        self.assertEqual(len(result["verified"]), 2)
        self.assertEqual(result["rejected"], [])

    def test_sears_468_v_and_p_are_not_interpreted_as_omega_and_pi(self):
        source = fragment("La frecuencia angular v es 2 p veces la frecuencia.")
        selected = select_evidence("Que es la frecuencia angular?", [source])
        self.assertEqual(selected["accepted"], [])
        self.assertTrue(any("ambigua" in reason for reason in selected["discarded"][0]["reasons"]))
        result = validate_claims(
            "La frecuencia angular v es 2 p veces la frecuencia. [F1]",
            [{"id": "F1", "text": source["text"]}],
            "Que es la frecuencia angular?",
        )
        self.assertEqual(result["verified"], [])

    def test_superscript_is_not_equal_to_plain_digit(self):
        result = validate_claims(
            "La elongacion x2 caracteriza el movimiento. [F1]",
            [{"id": "F1", "text": "La elongacion x² caracteriza el movimiento."}],
            "Que caracteriza la elongacion?",
        )
        self.assertEqual(result["verified"], [])

    def test_subscript_is_not_equal_to_plain_letter(self):
        result = validate_claims(
            "La fuerza Fk actua sobre el resorte. [F1]",
            [{"id": "F1", "text": "La fuerza Fₖ actua sobre el resorte."}],
            "Que fuerza actua sobre el resorte?",
        )
        self.assertEqual(result["verified"], [])

    def test_incomplete_formula_is_not_accepted(self):
        source = fragment("La frecuencia angular omega =")
        selected = select_evidence("Que es la frecuencia angular?", [source])
        self.assertEqual(selected["accepted"], [])

    def test_announced_but_unreadable_formula_is_not_accepted(self):
        source = fragment(
            "Esa energia cinetica adquirida fue entregada por el resorte y se relaciona "
            "con energia mecanica. La formula que da la energia almacenada es: La E m "
            "el tipo tiene en ese momento, segun el fragmento extraido del libro."
        )
        selected = select_evidence(
            "Que relacion existe entre la energia mecanica, cinetica y potencial?", [source]
        )
        self.assertEqual(selected["accepted"], [])
        self.assertTrue(any("formula" in reason for reason in selected["discarded"][0]["reasons"]))

    def test_definition_sounding_exercise_is_not_general_definition(self):
        source = fragment(
            "Problema 4: representa la constante elastica como rigidez; calcule la fuerza "
            "proporcional a la deformacion para el resorte indicado en el enunciado."
        )
        selected = select_evidence("Que representa la constante elastica?", [source])
        self.assertEqual(selected["accepted"], [])
        self.assertTrue(any("ejercicio" in reason for reason in selected["discarded"][0]["reasons"]))

    def test_example_with_definition_words_is_not_general_definition(self):
        source = fragment(
            "Ejemplo: la constante elastica representa la rigidez; para este resorte "
            "la fuerza es proporcional a la deformacion observada en el ensayo descrito."
        )
        selected = select_evidence("Que representa la constante elastica?", [source])
        self.assertEqual(selected["accepted"], [])

    def test_two_partial_energy_fragments_do_not_prove_three_way_relation(self):
        sources = [
            fragment(
                "La energia mecanica es la suma de la energia cinetica del sistema, "
                "segun la explicacion teorica del texto citado.", chunk="a"
            ),
            fragment(
                "La energia mecanica se relaciona con la energia potencial dentro del "
                "sistema descrito en esta seccion teorica.", chunk="b"
            ),
        ]
        selected = select_evidence(
            "Que relacion existe entre la energia mecanica, cinetica y potencial?", sources
        )
        self.assertEqual(selected["status"], "parcial")
        self.assertFalse(selected["coverage_complete"])
        self.assertIn("relacion_directa_entre_tres_energias", selected["missing_groups"])

    def test_off_topic_clause_in_literal_quote_is_rejected_individually(self):
        period = "El periodo es el tiempo que tarda un ciclo completo."
        unrelated = "La masa de la Luna es distinta a la masa del sistema."
        result = validate_claims(
            period + "; " + unrelated + " [F1]",
            [{"id": "F1", "text": period + " " + unrelated}],
            "Como se define el periodo de oscilacion?",
        )
        self.assertEqual(len(result["verified"]), 1)
        self.assertEqual(len(result["rejected"]), 1)
        self.assertEqual(result["status"], "parcial")

    def test_unlisted_split_physics_word_is_rejected(self):
        source = fragment(
            "Supondremos que la fuerza que de sarro lla el resorte es proporcional a "
            "su deformacion; la constante elastica caracteriza esa respuesta mecanica."
        )
        selected = select_evidence("Que representa la constante elastica?", [source])
        self.assertEqual(selected["accepted"], [])

    def test_clean_constant_and_period_evidence_remain_usable(self):
        constant = fragment(
            "La constante elastica k caracteriza la rigidez del resorte; la fuerza es "
            "proporcional a la deformacion y se expresa F = kx."
        )
        period = fragment(
            "El periodo de oscilacion es el tiempo que tarda el sistema en efectuar "
            "una oscilacion completa."
        )
        self.assertEqual(
            select_evidence("Que representa la constante elastica?", [constant])["status"],
            "respaldada",
        )
        self.assertEqual(
            select_evidence("Como se define el periodo de oscilacion?", [period])["status"],
            "respaldada",
        )

    def test_angular_frequency_ambiguous_evidence_does_not_pass(self):
        sources = [
            fragment("La frecuencia angular v es 2 p veces la frecuencia.", page=468),
            fragment("frecuencia angular (w), relacionada mediante w=2pn y T 2p w=", page=2),
        ]
        selected = select_evidence("Que es la frecuencia angular?", sources)
        self.assertNotEqual(selected["status"], "respaldada")
        self.assertEqual(selected["accepted"], [])


if __name__ == "__main__":
    unittest.main()
