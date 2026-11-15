import math
import sys
import unittest
from pathlib import Path

import numpy as np
from uncertainties import ufloat

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from calidad import (  # noqa: E402
    advertencias_masas,
    aviso_extension_estatica,
    convertir_masa_a_kg,
    criterios_calidad,
    energia_analitica,
    extension_estatica,
    ic95_media_t,
    periodo_por_cruces,
)


class ConversionMasasTests(unittest.TestCase):
    def test_gramos_a_kg(self):
        self.assertAlmostEqual(convertir_masa_a_kg(64.55, "g"), 0.06455)
        self.assertAlmostEqual(convertir_masa_a_kg(64.55, "gramos"), 0.06455)

    def test_kg_no_cambia(self):
        self.assertAlmostEqual(convertir_masa_a_kg(0.06455, "kg"), 0.06455)

    def test_unidad_invalida(self):
        with self.assertRaises(ValueError):
            convertir_masa_a_kg(1.0, "libras")


class AvisosMasasTests(unittest.TestCase):
    def test_masas_correctas_sin_avisos(self):
        self.assertEqual(advertencias_masas(0.06455, 0.000014, 0.00973, 0.00001), [])

    def test_masa_mal_en_kg_genera_aviso(self):
        avisos = advertencias_masas(3.09, 0.001, 0.973, 0.0001)
        self.assertTrue(any("supera 1 kg" in a for a in avisos))

    def test_resorte_mas_pesado_que_la_masa(self):
        avisos = advertencias_masas(0.05, 0.001, 0.10, 0.0001)
        self.assertTrue(any("masa del resorte" in a for a in avisos))

    def test_incertidumbres_cero_generan_avisos(self):
        avisos = advertencias_masas(0.06455, 0.0, 0.00973, 0.0)
        self.assertEqual(len(avisos), 2)

    def test_masa_muy_pequena_genera_aviso(self):
        avisos = advertencias_masas(0.001, 0.0001, 0.00973, 0.00001)
        self.assertTrue(any("menor que 5 g" in a for a in avisos))


class ExtensionEstaticaTests(unittest.TestCase):
    def test_extension_g8(self):
        k = ufloat(6.49, 0.0015)
        x_eq = extension_estatica(ufloat(0.06455, 0.000014), k)
        self.assertAlmostEqual(x_eq.nominal_value * 100, 9.757, delta=0.01)

    def test_aviso_fuera_de_rango(self):
        self.assertIsNone(aviso_extension_estatica(9.76))
        self.assertIsNotNone(aviso_extension_estatica(97.6))
        self.assertIsNotNone(aviso_extension_estatica(0.2))
        self.assertIsNone(aviso_extension_estatica(ufloat(9.76, 0.01)))


class PeriodoCrucesTests(unittest.TestCase):
    def test_recupera_periodo_de_una_senoide(self):
        T = 2.0
        t = np.arange(0.0, 10.0, 0.01)
        x = np.sin(2 * np.pi * t / T + 0.3)
        salida = periodo_por_cruces(t, x)
        self.assertAlmostEqual(salida["T_s"], T, delta=1e-6)
        self.assertGreaterEqual(salida["N_ciclos"], 4)
        self.assertEqual(len(salida["periodos_s"]), salida["N_ciclos"])

    def test_senal_corta_no_inventa_periodo(self):
        salida = periodo_por_cruces([0.0, 0.1], [0.0, 1.0])
        self.assertIsNone(salida["T_s"])
        self.assertEqual(salida["N_ciclos"], 0)


class EnergiaAnaliticaTests(unittest.TestCase):
    def test_energia_conservada_sin_amortiguamiento(self):
        t = np.linspace(0.0, 2 * np.pi, 100)
        Et = energia_analitica(
            t, A=0.1, gamma=0.0, omega=1.0, phi=0.0, C=0.0, k=1.0, m_ef=1.0
        )
        self.assertTrue(np.allclose(Et, 0.005))

    def test_amortiguamiento_reduce_energia(self):
        t = np.linspace(0.0, 10.0, 100)
        Et = energia_analitica(
            t, A=0.1, gamma=0.1, omega=1.0, phi=0.0, C=0.0, k=1.0, m_ef=1.0
        )
        self.assertLess(Et[-1], Et[0])


class CriteriosCalidadTests(unittest.TestCase):
    def test_caso_aceptable(self):
        c = criterios_calidad(0.0, 10.0, 30.0, 0.001, 0.05)
        self.assertTrue(c["aceptable"])
        self.assertEqual(c["motivos"], [])

    def test_caso_con_varios_motivos(self):
        c = criterios_calidad(0.10, 3.0, 5.0, 0.01, 0.05)
        self.assertFalse(c["aceptable"])
        self.assertEqual(len(c["motivos"]), 4)

    def test_rms_infinito_no_rompe(self):
        c = criterios_calidad(0.0, 10.0, 30.0, math.inf, 0.05)
        self.assertFalse(c["aceptable"])
        self.assertTrue(math.isinf(c["residuo_pct_amplitud"]))

    def test_umbral_configurable(self):
        c = criterios_calidad(0.0, 10.0, 30.0, 0.003, 0.05, residuo_max_pct=5.0)
        self.assertFalse(c["aceptable"])
        self.assertIn("RMS del residuo", c["motivos"][0])


class IntervaloConfianzaTests(unittest.TestCase):
    def test_tres_videos(self):
        ic = ic95_media_t(3, 1.0, 0.01)
        self.assertEqual(ic["gl"], 2)
        self.assertAlmostEqual(ic["t_critico"], 4.302652729749462)
        self.assertAlmostEqual(ic["semiancho"], 0.04302652729749462)
        self.assertAlmostEqual(ic["inferior"], 0.9569734727025054)
        self.assertAlmostEqual(ic["superior"], 1.0430265272974946)

    def test_fuera_de_rango(self):
        self.assertIsNone(ic95_media_t(1, 1.0, 0.01))
        self.assertIsNone(ic95_media_t(10, 1.0, 0.01))


if __name__ == "__main__":
    unittest.main()
