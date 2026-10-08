import os
import numpy as np
import matplotlib.pyplot as plt
from lmfit import Model
from uncertainties import ufloat, correlated_values, umath

from señal import cargar, rellenar_nan, procesar


def modelo(t, A, gamma, omega, phi, C):
    """MAS amortiguado: x(t) = A e^(-γt) cos(ωt + φ) + C"""
    return A * np.exp(-gamma * t) * np.cos(omega * t + phi) + C


def ajustar(t, x, sx):
    """Ajuste por cuadrados mínimos ponderado. Devuelve el resultado de lmfit."""
    dt = np.median(np.diff(t))
    freqs = np.fft.rfftfreq(len(t), dt)
    espectro = np.abs(np.fft.rfft(x - x.mean()))
    omega0 = 2 * np.pi * freqs[1:][np.argmax(espectro[1:])]   # semilla desde la FFT
    p = Model(modelo).make_params(
        A=(x.max() - x.min()) / 2, gamma=0.05, omega=omega0, phi=0.0, C=x.mean()
    )
    p["gamma"].min = 0
    p["A"].min = 0
    return Model(modelo).fit(x, p, t=t, weights=1 / sx)


def parametros_con_incerteza(res):
    """Parámetros del ajuste como ufloat, con correlaciones incluidas."""
    nombres = res.var_names
    valores = [res.params[n].value for n in nombres]
    u = correlated_values(valores, res.covar)
    return dict(zip(nombres, u))


def cantidades(p, m, m_r):
    """T, k (con y sin masa efectiva del resorte). m y m_r: ufloat en kg."""
    w, g = p["omega"], p["gamma"]
    w0_cuad = w**2 + g**2                  # ω0² = k/m_ef
    m_ef = m + m_r / 3
    return dict(
        T=2 * np.pi / w,
        gamma=g,
        k_con_mef=m_ef * w0_cuad,
        k_sin_mef=m * w0_cuad,
        m_ef=m_ef,
    )


def k_estatico(masas_kg, elong_m, g=9.81, sigma_g=0.01, sigma_elongacion=None):
    """k desde el experimento estático: F = m g vs elongación, pendiente por regresión (≥3 puntos).

    sigma_g: incerteza de g en m/s² (default 0.01 m/s²). Es común a todos los puntos
    (k ∝ g), así que se propaga como δk = (k/g)·σg.
    sigma_elongacion: incerteza de cada elongación en m, escalar o un valor por punto.
    None = no se incluye esa contribución y k sólo lleva la dispersión de la recta.
    """
    e = np.asarray(elong_m, dtype=float)
    F = np.asarray(masas_kg, dtype=float) * g
    (k, _), cov = np.polyfit(e, F, 1, cov=True)
    sigma_k = float(np.sqrt(cov[0, 0]))
    sigma_k = np.hypot(sigma_k, k / g * sigma_g)
    if sigma_elongacion is not None:
        Sxx = np.sum((e - e.mean()) ** 2)
        dk_de = ((F - F.mean()) - k * (e - e.mean())) / Sxx     # ∂k/∂e_j (recta con ordenada)
        sig_e = np.broadcast_to(np.asarray(sigma_elongacion, dtype=float), e.shape)
        sigma_k = np.hypot(sigma_k, np.sqrt(np.sum((dk_de * sig_e) ** 2)))
    return ufloat(k, sigma_k)


def chequeo_periodo(k_est, m, m_r, T_med):
    """Chequeo físico: T predicho con y sin masa efectiva vs T medido."""
    T_sin = 2 * np.pi * umath.sqrt(m / k_est)
    T_con = 2 * np.pi * umath.sqrt((m + m_r / 3) / k_est)
    for nombre, T in (("sin m_ef", T_sin), ("con m_ef", T_con)):
        dif = T - T_med
        print(f"  T {nombre}: {T:.4f} s | diferencia con T medido: {dif:.4f} s "
              f"({abs(dif.nominal_value) / dif.std_dev:.1f} σ)")


def energias(x_f, v_f, k, m_ef, C):
    """Ec = ½ m_ef v², Ep = ½ k (x-C)². x medido desde el equilibrio C.

    k, m_ef y C pueden ser ufloat: la incerteza se propaga a Ec, Ep y Et, que quedan
    como arreglos de objetos (para graficar usar los valores nominales, ver graficar()).
    """
    Ec = 0.5 * m_ef * v_f**2
    Ep = 0.5 * k * (x_f - C) ** 2
    return Ec, Ep, Ec + Ep


def maximos(p):
    """Máximos de |x|, |v| y |a| de la solución ajustada, con incerteza y con el
    instante y la posición en que ocurren.

    Analítico sobre x(t) = A e^(-γt) cos(ωt+φ) + C: se toma el primer máximo con t ≥ 0.
    p son los parámetros del ajuste como ufloat (parametros_con_incerteza), de modo que
    la covarianza del ajuste entra en los valores, las posiciones y los tiempos.
    Las posiciones van medidas desde el equilibrio C.
    """
    A, w, g, phi = p["A"], p["omega"], p["gamma"], p["phi"]
    if w.n <= 0:
        raise RuntimeError("omega ajustada no positiva: no se pueden calcular los máximos")

    def t_y_n(base):
        """t ≥ 0 del primer máximo en θ = base + nπ (w > 0); devuelve (t, n)."""
        b = base.n if hasattr(base, "n") else float(base)
        n = int(np.ceil((phi.n - b) / np.pi))         # base + nπ ≥ φ  <=>  t ≥ 0
        return (base + n * np.pi - phi) / w, n

    envolvente = lambda t: A * umath.exp(-g * t)      # decae con el tiempo
    R = umath.sqrt(w**2 + g**2)                       # |v| máx = A·R·e^(-γt)
    S = w**2 + g**2                                   # |a| máx = A·S·e^(-γt)
    th_v = umath.atan2(w, g)                          # donde γcosθ + ωsinθ toma ±R
    th_a = umath.atan2(2 * g * w, g * g - w * w)      # donde (γ²-ω²)cosθ + 2γωsinθ toma ±S
    signo = lambda n: 1 if n % 2 == 0 else -1

    t_x, n_x = t_y_n(0.0)                             # |x - C| y |a| máximos en θ = nπ
    t_v, n_v = t_y_n(th_v)
    t_a, n_a = t_y_n(th_a)

    pos_x = envolvente(t_x) * signo(n_x)
    pos_v = envolvente(t_v) * umath.cos(th_v) * signo(n_v)
    pos_a = envolvente(t_a) * umath.cos(th_a) * signo(n_a)

    return {
        "x_max (m)": envolvente(t_x),
        "posición en x_max (m)": pos_x,
        "t en x_max (s)": t_x,
        "v_max (m/s)": envolvente(t_v) * R,
        "posición en v_max (m)": pos_v,
        "t en v_max (s)": t_v,
        "a_max (m/s²)": envolvente(t_a) * S,
        "posición en a_max (m)": pos_a,
        "t en a_max (s)": t_a,
    }


def graficar(t, x, res, Ec, Ep, Et, salida="salidas/ajuste.png"):
    def nom(v):   # Ec/Ep/Et pueden traer incerteza: el PNG usa los nominales
        return np.array([z.n for z in v])
    Ec, Ep, Et = nom(Ec), nom(Ep), nom(Et)
    os.makedirs(os.path.dirname(salida), exist_ok=True)
    fig, ax = plt.subplots(3, 1, figsize=(9, 9), sharex=True)
    ax[0].plot(t, x, ".", ms=3, color="0.6", label="datos")
    ax[0].plot(t, res.best_fit, color="C3", label="ajuste")
    ax[0].set_ylabel("x (m)"); ax[0].legend()
    ax[1].plot(t, x - res.best_fit, ".", ms=3)
    ax[1].axhline(0, color="k", lw=0.5); ax[1].set_ylabel("residuo (m)")
    ax[2].plot(t, Ec, label="cinética"); ax[2].plot(t, Ep, label="elástica")
    ax[2].plot(t, Et, "k", label="total"); ax[2].set_ylabel("E (J)"); ax[2].legend()
    ax[2].set_xlabel("t (s)")
    fig.tight_layout(); fig.savefig(salida, dpi=150); plt.close(fig)


if __name__ == "__main__":
    # Datos del experimento (cambiar con los reales). En el sintético: m = 0.200 kg, resorte sin masa.
    m = ufloat(0.200, 0.001)       # kg ± balanza
    m_r = ufloat(0.0, 0.0001)      # kg, masa del resorte (pesarlo en los reales)

    t, x, sx = cargar("tabla_m.csv")
    x, _ = rellenar_nan(t, x)
    sx = np.where(np.isnan(sx), np.nanmedian(sx), sx)

    res = ajustar(t, x, sx)
    p = parametros_con_incerteza(res)
    c = cantidades(p, m, m_r)

    print(f"χ² reducido = {res.redchi:.2f}  (≈1: ajuste y σ consistentes)")
    print(f"A = {p['A']:.4f} m | C = {p['C']:.5f} m | φ = {p['phi']:.3f} rad")
    print(f"T = {c['T']:.4f} s | γ = {c['gamma']:.4f} 1/s")
    print(f"k (con m_ef) = {c['k_con_mef']:.3f} N/m | k (sin m_ef) = {c['k_sin_mef']:.3f} N/m")

    r = procesar(t, x)
    Ec, Ep, Et = energias(r["x_f"], r["v_f"], c["k_con_mef"], c["m_ef"], p["C"])
    for nombre, valor in maximos(p).items():
        print(f"{nombre}: {valor:.4f}")

    graficar(t, x, res, Ec, Ep, Et)
    print("Gráfico en salidas/ajuste.png")

    # Chequeo del período (con datos reales, usar el k estático):
    # k_e = k_estatico([0.1, 0.2, 0.3, 0.4], [0.082, 0.165, 0.249, 0.330])
    # chequeo_periodo(k_e, m, m_r, c["T"])