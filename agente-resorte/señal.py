#Receta del enunciado: filtrar x, derivar a v, filtrar v, derivar a a, filtrar a. 
#También compara crudo vs filtrado.

import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter


def cargar(csv):
    d = np.genfromtxt(csv, delimiter=",", names=True)
    return d["t_s"], d["x_m"], d["sx_m"]


def rellenar_nan(t, x):
    """Interpola linealmente los cuadros sin detección. Devuelve x y cuántos se rellenaron."""
    malos = np.isnan(x)
    if malos.any():
        x = x.copy()
        x[malos] = np.interp(t[malos], t[~malos], x[~malos])
    return x, int(malos.sum())


def derivar(t, y):
    """Diferencias finitas centrales (np.gradient)."""
    return np.gradient(y, t)


def filtrar(y, ventana=11, orden=3):
    """Savitzky-Golay. La ventana debe ser impar y mayor que el orden."""
    ventana = min(ventana, len(y) - (1 - len(y) % 2))
    return savgol_filter(y, ventana, orden)


def procesar(t, x, ventana=11, orden=3):
    # Crudo: derivadas directas
    v_c = derivar(t, x)
    a_c = derivar(t, v_c)
    # Filtrado: x -> v -> a, filtrando en cada etapa
    x_f = filtrar(x, ventana, orden)
    v_f = filtrar(derivar(t, x_f), ventana, orden)
    a_f = filtrar(derivar(t, v_f), ventana, orden)
    return dict(x_c=x, v_c=v_c, a_c=a_c, x_f=x_f, v_f=v_f, a_f=a_f)


def incerteza_cruda(dt, sx):
    """Propagación de σx a σv y σa por diferencias finitas (ruido no correlacionado)."""
    sv = np.sqrt(2) * sx / (2 * dt)        # v = (x[i+1]-x[i-1]) / (2dt)
    sa = np.sqrt(2) * sv / (2 * dt)        # idem sobre v
    return sv, sa


def comparar_crudo_filtrado(r, corr_v=None):
    """RMS de (crudo - filtrado) para x, v y a con la ventana vigente: cuánto mueve el
    filtro a cada magnitud. Devuelve {magnitud con unidad: float o ufloat}.

    corr_v: ufloat(1, σ_fps/fps), si se conoce la incerteza del fps. v = Δx/Δt ∝ fps y
    a ∝ fps², así que se escalan por corr_v y corr_v²; x no depende del fps. None = sin
    σ_fps (valores planos, como antes).
    """
    def rms(k):
        return float(np.sqrt(np.mean((np.asarray(r[k + "_c"]) - np.asarray(r[k + "_f"])) ** 2)))
    out = {"RMS x (m)": rms("x"), "RMS v (m/s)": rms("v"), "RMS a (m/s²)": rms("a")}
    if corr_v is not None:
        out["RMS v (m/s)"] = out["RMS v (m/s)"] * corr_v
        out["RMS a (m/s²)"] = out["RMS a (m/s²)"] * corr_v ** 2
    return out


def graficar(t, r, salida="salidas/señal.png"):
    import os
    os.makedirs(os.path.dirname(salida), exist_ok=True)
    fig, ax = plt.subplots(3, 1, figsize=(9, 8), sharex=True)
    for a, (c, f, lab) in zip(ax, [("x_c", "x_f", "x (m)"),
                                   ("v_c", "v_f", "v (m/s)"),
                                   ("a_c", "a_f", "a (m/s²)")]):
        a.plot(t, r[c], color="0.7", label="crudo")
        a.plot(t, r[f], color="C3", label="filtrado")
        a.set_ylabel(lab)
        a.legend(loc="upper right")
    ax[-1].set_xlabel("t (s)")
    fig.tight_layout()
    fig.savefig(salida, dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    t, x, sx = cargar("tabla_m.csv")
    x, n_nan = rellenar_nan(t, x)
    dt = np.median(np.diff(t))
    r = procesar(t, x, ventana=11, orden=3)
    sv, sa = incerteza_cruda(dt, np.nanmedian(sx))
    graficar(t, r)
    print(f"Cuadros rellenados por interpolación: {n_nan}")
    print(f"dt = {dt:.5f} s")
    print(f"σx = {np.nanmedian(sx):.2e} m | σv (crudo) ≈ {sv:.2e} m/s | σa (crudo) ≈ {sa:.2e} m/s²")
    print(f"RMS a crudo = {np.sqrt(np.mean(r['a_c']**2)):.3f} m/s² | filtrado = {np.sqrt(np.mean(r['a_f']**2)):.3f} m/s²")
    print("Gráfico en salidas/señal.png")