#Receta del enunciado: filtrar x, derivar a v, filtrar v, derivar a a, filtrar a. 
#También compara crudo vs filtrado.

import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter, detrend, butter, sosfilt, hilbert


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


def _frecuencia_dominante(t, x, fraccion_final=0.3):
    """Frecuencia del pico espectral en el tramo final, sin la deriva lenta."""
    if len(t) < 12:
        return None
    inicio = max(0, int((1.0 - fraccion_final) * len(t)))
    tramo = detrend(np.asarray(x[inicio:], dtype=float))
    if len(tramo) < 8 or not np.any(np.isfinite(tramo)):
        return None
    dt = float(np.median(np.diff(t)))
    if not np.isfinite(dt) or dt <= 0:
        return None
    ventana = np.hanning(len(tramo))
    espectro = np.abs(np.fft.rfft(tramo * ventana))
    frecuencias = np.fft.rfftfreq(len(tramo), dt)
    # Evita la deriva y el ruido de alta frecuencia; el resorte real cae en este rango.
    banda = (frecuencias >= 0.2) & (frecuencias <= min(5.0, 0.45 / dt))
    if not np.any(banda):
        return None
    indices = np.flatnonzero(banda)
    indice = indices[int(np.argmax(espectro[banda]))]
    frecuencia = float(frecuencias[indice])
    return frecuencia if np.isfinite(frecuencia) and frecuencia > 0 else None


def detectar_inicio_detalle(t, x, ventana_s=0.5, umbral=0.15):
    """Detecta el inicio de la oscilación sostenida y devuelve (t_inicio, detalle).

    La decisión se toma sobre la envolvente de la componente oscilatoria, no sobre
    el desvío total: así un movimiento lento de la mano o un reacomodo de la masa
    no se confunde con la liberación. El umbral es una fracción de la amplitud
    final de la envolvente (percentil 90 del último 20 % del registro). Si no hay
    un prefijo quieto, el inicio es t[0], porque no hay nada que recortar.
    """
    t = np.asarray(t, dtype=float)
    x = np.asarray(x, dtype=float)
    if len(t) < 5 or len(x) != len(t):
        return (float(t[0]) if len(t) else 0.0), {
            "metodo": "envolvente de la oscilación",
            "motivo": "registro demasiado corto",
        }
    dt = float(np.median(np.diff(t)))
    if not np.isfinite(dt) or dt <= 0:
        return float(t[0]), {"metodo": "envolvente de la oscilación", "motivo": "dt inválido"}
    n_ventana = max(5, min(int(round(ventana_s / dt)), len(x)))
    info = {
        "metodo": "envolvente de la oscilación",
        "ventana_s": float(ventana_s),
        "umbral_relativo": float(umbral),
        "frecuencia_hz": None,
        "amplitud_final": None,
        "inicio_en_t0": True,
        "motivo": "",
    }

    frecuencia = _frecuencia_dominante(t, x)
    if frecuencia is None:
        info["motivo"] = "no se pudo estimar la frecuencia de oscilación"
        return float(t[0]), info
    info["frecuencia_hz"] = frecuencia

    # La banda ancha tolera que el período cambie algo por la masa del resorte o
    # por una ligera no linealidad, pero descarta la deriva y el movimiento lento.
    nyquist = 0.5 / dt
    bajo = max(0.12, 0.55 * frecuencia)
    alto = min(0.98 * nyquist, 1.8 * frecuencia)
    if alto <= bajo:
        info["motivo"] = "banda de oscilación inválida"
        return float(t[0]), info
    try:
        sos = butter(4, [bajo, alto], btype="band", fs=1.0 / dt, output="sos")
        oscilacion = sosfilt(sos, detrend(x))
        envolvente = np.abs(hilbert(oscilacion))
    except (ValueError, FloatingPointError):
        info["motivo"] = "no se pudo filtrar la oscilación"
        return float(t[0]), info

    # Suavizado causal de la envolvente: conserva el orden temporal y exige que
    # la oscilación se mantenga, no sólo un pico aislado.
    kernel = np.ones(n_ventana) / n_ventana
    envolvente = np.convolve(envolvente, kernel, mode="full")[:len(envolvente)]
    final = max(n_ventana, int(round(0.2 * len(envolvente))))
    amp_final = float(np.nanpercentile(envolvente[-final:], 90))
    info["amplitud_final"] = amp_final
    if not np.isfinite(amp_final) or amp_final <= 0:
        info["motivo"] = "amplitud final nula o no finita"
        return float(t[0]), info

    limite = umbral * amp_final
    info["amplitud_umbral"] = float(limite)
    sobre = envolvente > limite
    corrida = 0
    for indice, activo in enumerate(sobre):
        corrida = corrida + 1 if activo else 0
        if corrida >= n_ventana:
            inicio = indice - n_ventana + 1
            # Si la ventana ya estaba activa desde el comienzo, no hay prefijo
            # quieto: se conserva t[0] y se informa para que el usuario revise.
            if inicio <= 0 or (float(t[inicio]) - float(t[0])) <= ventana_s:
                info["inicio_en_t0"] = True
                info["motivo"] = "la oscilación ya está presente desde el primer cuadro"
                return float(t[0]), info
            inicio_sin_compensar = float(t[inicio])
            # La media móvil causal introduce un retardo de media ventana. Se
            # compensa para no recortar el primer máximo de la liberación.
            compensacion = 0.5 * ventana_s
            info["inicio_en_t0"] = False
            info["inicio_sin_compensar_s"] = inicio_sin_compensar
            info["compensacion_s"] = compensacion
            info["motivo"] = "primer tramo sostenido por encima del umbral"
            return max(float(t[0]), inicio_sin_compensar - compensacion), info
    info["motivo"] = "no se encontró un tramo oscilatorio sostenido"
    return float(t[0]), info


def detectar_inicio(t, x, ventana_s=0.5, umbral=0.15):
    """Segundo en que comienza la oscilación; compatible con la interfaz anterior."""
    return detectar_inicio_detalle(t, x, ventana_s=ventana_s, umbral=umbral)[0]


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