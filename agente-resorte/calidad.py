"""Chequeos de calidad y de consistencia física del análisis del resorte.

Este módulo no modifica el ajuste: sólo reúne funciones puras para validar las
entradas, estimar el período por cruces por cero, construir intervalos de
confianza y comparar las energías con la solución analítica.
"""

import math

import numpy as np
from scipy import stats
from uncertainties import ufloat


def convertir_masa_a_kg(valor, unidad):
    """Convierte una masa a kg. Acepta 'g'/'gramos' y 'kg'/'kilogramos'."""
    if valor is None:
        return None
    texto = str(unidad).strip().lower()
    if texto in ("g", "gr", "gramo", "gramos"):
        return float(valor) / 1000.0
    if texto in ("kg", "kilogramo", "kilogramos"):
        return float(valor)
    raise ValueError(f"unidad de masa no reconocida: {unidad!r}; usá g o kg")


def advertencias_masas(masa_kg, sigma_masa_kg, masa_resorte_kg, sigma_masa_resorte_kg):
    """Avisos de masas y de sus incertidumbres; nunca abortan el análisis."""
    avisos = []
    masa = float(masa_kg or 0.0)
    sigma_masa = float(sigma_masa_kg or 0.0)
    resorte = float(masa_resorte_kg or 0.0)
    sigma_resorte = float(sigma_masa_resorte_kg or 0.0)

    if sigma_masa <= 0:
        avisos.append(
            "la incertidumbre de la masa colgante es 0: las incertezas de k, "
            "energías y del promedio quedan subestimadas"
        )
    if sigma_resorte <= 0:
        avisos.append(
            "la incertidumbre de la masa del resorte es 0: su aporte a la masa "
            "efectiva no está reflejado en las incertezas"
        )
    if masa > 1.0:
        avisos.append(
            f"la masa colgante ({masa:.4g} kg = {1000*masa:.4g} g) supera 1 kg: "
            "revisá si se ingresó en gramos o si el valor medido es correcto"
        )
    if masa < 0.005:
        avisos.append(
            f"la masa colgante ({1000*masa:.4g} g) es menor que 5 g: "
            "revisá la unidad y el valor medido"
        )
    if resorte > masa:
        avisos.append(
            f"la masa del resorte ({1000*resorte:.4g} g) es mayor que la masa "
            f"colgante ({1000*masa:.4g} g): revisá los valores"
        )
    return avisos


def extension_estatica(masa_kg, k, g=ufloat(9.81, 0.01)):
    """Extensión estática esperada x_eq = m·g/k, en metros, como ufloat."""
    return masa_kg * g / k


def aviso_extension_estatica(x_eq_cm):
    """Aviso cuando la extensión esperada es implausible para este montaje."""
    valor = float(getattr(x_eq_cm, "n", x_eq_cm))
    if math.isfinite(valor) and not (0.5 <= valor <= 50.0):
        return (
            f"la extensión estática esperada ({valor:.1f} cm) está fuera del "
            "rango plausible [0.5, 50] cm: revisá masas y unidades"
        )
    return None


def periodo_por_cruces(t, x, equilibrio=0.0):
    """Período medio por cruces por cero interpolados de la señal filtrada.

    Usa cruces ascendentes. Si hay menos de dos, recurre a todos los cruces y
    duplica el intervalo para estimar el período. Devuelve media, desvío por
    ciclo, cantidad de ciclos y las listas de cruces/períodos.
    """
    t = np.asarray(t, dtype=float)
    x = np.asarray(x, dtype=float)
    centro = float(getattr(equilibrio, "n", equilibrio))
    y = x - centro
    valido = np.isfinite(t) & np.isfinite(y)
    t, y = t[valido], y[valido]
    salida = {
        "T_s": None,
        "sigma_T_s": None,
        "N_ciclos": 0,
        "periodos_s": [],
        "cruces_s": [],
        "metodo": "cruces ascendentes interpolados",
    }
    if len(t) < 4:
        return salida

    negativos = y < 0
    indices = np.flatnonzero(negativos[:-1] & ~negativos[1:])
    factor = 1.0
    if len(indices) < 2:
        indices = np.flatnonzero(negativos[:-1] != negativos[1:])
        factor = 2.0
        salida["metodo"] = "todos los cruces interpolados (período = 2×intervalo)"
    if len(indices) < 2:
        return salida

    y0, y1 = y[indices], y[indices + 1]
    cruces = t[indices] + (0.0 - y0) * (t[indices + 1] - t[indices]) / (y1 - y0)
    periodos = factor * np.diff(cruces)
    periodos = periodos[np.isfinite(periodos) & (periodos > 0)]
    if len(periodos) == 0:
        return salida

    salida.update({
        "T_s": float(np.mean(periodos)),
        "sigma_T_s": float(np.std(periodos, ddof=1)) if len(periodos) > 1 else 0.0,
        "N_ciclos": int(len(periodos)),
        "periodos_s": [float(p) for p in periodos],
        "cruces_s": [float(c) for c in cruces],
    })
    return salida


def energia_analitica(t, A, gamma, omega, phi, C, k, m_ef):
    """Et(t) de la solución ajustada, con los valores nominales indicados."""
    t = np.asarray(t, dtype=float)
    fase = omega * t + phi
    envolvente = A * np.exp(-gamma * t)
    x = envolvente * np.cos(fase) + C
    v = -envolvente * (gamma * np.cos(fase) + omega * np.sin(fase))
    return 0.5 * m_ef * v ** 2 + 0.5 * k * (x - C) ** 2


def criterios_calidad(perdidos_analisis, ciclos, muestras_T, rms_residuo,
                      amplitud, residuo_max_pct=8.0):
    """Criterio Aceptable independiente del χ², con los motivos explícitos."""
    perdidos = float(perdidos_analisis)
    ciclos = float(ciclos)
    muestras_T = float(muestras_T)
    amplitud = float(amplitud)
    rms = float(rms_residuo)
    if not np.isfinite(rms):
        rms = float("inf")
    residuo_pct = 100.0 * rms / amplitud if amplitud > 0 else float("inf")
    motivos = []
    if perdidos > 0.05:
        motivos.append(
            f"más de 5 % de cuadros sin detección en el tramo analizado ({100*perdidos:.1f} %)"
        )
    if ciclos < 5:
        motivos.append(f"menos de 5 ciclos observados ({ciclos:.2f})")
    if muestras_T < 10:
        motivos.append(f"menos de 10 cuadros por período ({muestras_T:.1f})")
    if residuo_pct > float(residuo_max_pct):
        motivos.append(
            f"RMS del residuo {residuo_pct:.1f} % de la amplitud "
            f"(umbral {float(residuo_max_pct):.1f} %)"
        )
    return {
        "aceptable": not motivos,
        "motivos": motivos,
        "perdidos_analisis": perdidos,
        "ciclos": ciclos,
        "muestras_T": muestras_T,
        "rms_residuo": rms,
        "amplitud": amplitud,
        "residuo_pct_amplitud": residuo_pct,
        "residuo_max_pct": float(residuo_max_pct),
    }


def ic95_media_t(n, media, sigma_est):
    """IC 95 % de la media con t de Student para σ_est cuando 2 ≤ N < 10."""
    n = int(n)
    if n < 2 or n >= 10 or not np.isfinite(sigma_est) or sigma_est < 0:
        return None
    gl = n - 1
    t_critico = float(stats.t.ppf(0.975, gl))
    semiancho = t_critico * float(sigma_est)
    return {
        "nivel": 0.95,
        "gl": gl,
        "t_critico": t_critico,
        "semiancho": semiancho,
        "inferior": float(media) - semiancho,
        "superior": float(media) + semiancho,
    }
