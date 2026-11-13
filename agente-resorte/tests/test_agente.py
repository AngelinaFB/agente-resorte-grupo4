import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ajuste import ajustar, cantidades  # noqa: E402
from señal import detectar_inicio  # noqa: E402


def oscilacion(t, A=0.05, gamma=0.15, k=12.0, m=0.2):
    omega = np.sqrt(k / m - gamma**2)
    return A * np.exp(-gamma * t) * np.cos(omega * t)


class DetectarInicioTests(unittest.TestCase):
    def test_sin_prefijo_empieza_en_cero(self):
        t = np.arange(0.0, 6.0, 1 / 30)
        x = oscilacion(t)
        self.assertLess(detectar_inicio(t, x), 0.1)

    def test_con_prefijo_estatico(self):
        t = np.arange(0.0, 8.0, 1 / 30)
        x = np.where(t < 2.0, 0.0, oscilacion(t - 2.0))
        inicio = detectar_inicio(t, x)
        self.assertGreaterEqual(inicio, 1.9)
        self.assertLessEqual(inicio, 2.2)

    def test_senal_ruidosa_no_adelanta_el_inicio(self):
        rng = np.random.default_rng(0)
        t = np.arange(0.0, 8.0, 1 / 30)
        x = np.where(t < 2.0, 0.0, oscilacion(t - 2.0)) + rng.normal(0, 2e-4, len(t))
        inicio = detectar_inicio(t, x)
        self.assertGreaterEqual(inicio, 1.8)
        self.assertLessEqual(inicio, 2.4)


class AjusteTests(unittest.TestCase):
    def test_recupera_periodo_y_amortiguamiento(self):
        rng = np.random.default_rng(1)
        t = np.arange(0.0, 8.0, 1 / 30)
        x = oscilacion(t) + rng.normal(0, 2e-4, len(t))
        res = ajustar(t, x, np.full_like(t, 2e-4))
        T = 2 * np.pi / res.params["omega"].value
        self.assertAlmostEqual(T, 0.8113, delta=0.01)
        self.assertAlmostEqual(res.params["gamma"].value, 0.15, delta=0.02)

    def test_ajuste_robusto_tolera_outliers(self):
        rng = np.random.default_rng(2)
        t = np.arange(0.0, 8.0, 1 / 30)
        x = oscilacion(t) + rng.normal(0, 2e-4, len(t))
        x[40:43] += 0.02
        res = ajustar(t, x, np.full_like(t, 2e-4))
        self.assertAlmostEqual(res.params["gamma"].value, 0.15, delta=0.03)

    def test_cantidades_concuerdan_con_k(self):
        from uncertainties import ufloat

        t = np.arange(0.0, 8.0, 1 / 30)
        res = ajustar(t, oscilacion(t), np.full_like(t, 2e-4))
        p = {n: ufloat(res.params[n].value, res.params[n].stderr or 0.0) for n in res.var_names}
        c = cantidades(p, ufloat(0.2, 0.001), ufloat(0.0, 0.0001))
        self.assertAlmostEqual(c["k_con_mef"].nominal_value, 12.0, delta=0.1)


if __name__ == "__main__":
    unittest.main()
