# video ent. informe

#Agente: video(s) de resorte -> tracking -> calibración -> señal -> ajuste -> informe.

import argparse, os, io, json, contextlib
import numpy as np
import cv2
from uncertainties import ufloat

from tracking import trackear
from calibracion import marcar_dos_puntos, escala_px_por_m, a_metros, fps_real_con_led
from señal import rellenar_nan, procesar, graficar as graficar_senal, comparar_crudo_filtrado
from ajuste import (ajustar, parametros_con_incerteza, cantidades, k_estatico,
                    chequeo_periodo, energias, maximos, graficar as graficar_ajuste)


def fmt(u, unidad=""):
    try:
        s = f"{u:.2uP}"
    except Exception:
        s = f"{u.n:.4g} ± {u.s:.2g}"
    return f"{s} {unidad}".strip()


def analizar(video, a, escala, carpeta):
    nombre = os.path.splitext(os.path.basename(video))[0]
    px_csv, m_csv = f"{carpeta}/{nombre}_px.csv", f"{carpeta}/{nombre}_m.csv"

    filas = trackear(video, px_csv, color=a.color)
    perdidos = float(np.isnan(filas[:, 1]).mean())

    cap = cv2.VideoCapture(video)
    fps_decl = cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    # FPS de uso: medido con LED > --fps-real > declarado por el video
    if getattr(a, "fps_led", None):
        fps_uso, fps_sigma = a.fps_led, a.fps_sigma
        origen = f"medido con LED ({a.f_led} Hz)"
    elif a.fps_real:
        fps_uso, fps_sigma = a.fps_real, 0.0
        origen = "--fps-real (valor informado a mano)"
    else:
        fps_uso, fps_sigma = fps_decl, 0.0
        origen = "declarado por el video (sin verificar)"

    t, xm, ym, sxm, sym = a_metros(px_csv, m_csv, escala[0], escala[1])
    t = t * fps_decl / fps_uso                      # corrección por fps real
    x, sx = (xm, sxm) if a.eje == "x" else (ym, sym)
    x, _ = rellenar_nan(t, x)
    sx = np.where(np.isnan(sx), np.nanmedian(sx), sx)

    m = ufloat(a.masa, a.sigma_masa)
    m_r = ufloat(a.masa_resorte, a.sigma_masa_resorte)

    res = ajustar(t, x, sx)
    if res.covar is None:
        raise RuntimeError("el ajuste no tiene matriz de covarianza (¿no se detecta oscilación?)")
    p = parametros_con_incerteza(res)
    if fps_sigma:
        # los tiempos son t = n/fps: un error relativo del fps escala todos los tiempos,
        # por lo tanto T y γ (y k, vía ω0²) se corrigen por f_usado/f_real
        corr = ufloat(1.0, fps_sigma / fps_uso)
        p["omega"] = p["omega"] * corr
        p["gamma"] = p["gamma"] * corr
    c = cantidades(p, m, m_r)

    r = procesar(t, x, ventana=a.ventana)
    Ec, Ep, Et = energias(r["x_f"], r["v_f"], c["k_con_mef"], c["m_ef"], p["C"])
    i_max = lambda arr: max(arr, key=lambda z: z.n)
    energia = {"Ec_max (J)": i_max(Ec), "Ep_max (J)": i_max(Ep),
               "Et media (J)": np.mean(Et), "Et al inicio (J)": Et[0],
               "Et al final (J)": Et[-1], "ΔEt (final - inicial) (J)": Et[-1] - Et[0]}
    graficar_senal(t, r, f"{carpeta}/{nombre}_senal.png")
    graficar_ajuste(t, x, res, Ec, Ep, Et, f"{carpeta}/{nombre}_ajuste.png")

    T = c["T"]
    mx = maximos(p)
    comp = comparar_crudo_filtrado(r)
    comp["RMS a / a_max del ajuste"] = comp["RMS a (m/s²)"] / mx["a_max (m/s²)"]
    return dict(
        nombre=nombre, T=T, gamma=c["gamma"], k=c["k_con_mef"], k_sin=c["k_sin_mef"],
        A=p["A"], redchi=res.redchi, perdidos=perdidos,
        ciclos=(t[-1] - t[0]) / T.n, muestras_T=T.n * fps_uso,
        fps_decl=fps_decl, fps_uso=fps_uso, fps_sigma=fps_sigma, fps_origen=origen,
        maximos=mx, energia=energia, comp=comp,
    )


def agregado(vals):
    """Lista de ufloat -> (media ± error estándar de la media, desvío entre repeticiones)."""
    n = np.array([v.n for v in vals])
    if len(n) < 2:
        return vals[0], None
    s = n.std(ddof=1)
    return ufloat(n.mean(), s / np.sqrt(len(n))), s


def escribir_informe(res, fallidos, a, escala, k_e, ruta):
    L = ["# Informe automático: resorte (MAS)", ""]
    L.append(f"- Videos analizados: {len(res)} | fallidos: {len(fallidos)}")
    L.append(f"- Masa colgante: {fmt(ufloat(a.masa, a.sigma_masa), 'kg')} | "
             f"masa del resorte: {fmt(ufloat(a.masa_resorte, a.sigma_masa_resorte), 'kg')}")
    L.append(f"- Escala espacial: {fmt(ufloat(*escala), 'px/m')}")
    L.append(f"- Eje de oscilación: {a.eje} | ventana Savitzky-Golay: {a.ventana}")
    if res:
        r0 = res[0]
        if r0["fps_sigma"]:
            delta = (r0["fps_uso"] - r0["fps_decl"]) / r0["fps_decl"] if r0["fps_decl"] else 0.0
            L.append(f"- fps usado: {r0['fps_uso']:.4f} ± {r0['fps_sigma']:.4f} fps | "
                     f"origen: {r0['fps_origen']} | σ propagada a T, γ y k | "
                     f"declarado por los videos: {r0['fps_decl']:.4f} fps ({100 * delta:+.1f} %)")
        else:
            L.append(f"- fps usado: {r0['fps_uso']:.4f} fps | "
                     f"origen: {r0['fps_origen']} | sin incerteza estimada")
    L += ["", "## Resultados por video", "",
          "| video | T (s) | γ (1/s) | k con m_ef (N/m) | k sin m_ef (N/m) | χ² red. |",
          "|---|---|---|---|---|---|"]
    for r in res:
        L.append(f"| {r['nombre']} | {fmt(r['T'])} | {fmt(r['gamma'])} | {fmt(r['k'])} | "
                 f"{fmt(r['k_sin'])} | {r['redchi']:.2f} |")

    T_med = None
    if res:
        L += ["", "## Resultado agregado (media ± error estándar de la media)", ""]
        for clave, nom, unid in (("T", "T", "s"), ("gamma", "γ", "1/s"),
                                 ("k", "k (con m_ef)", "N/m"), ("k_sin", "k (sin m_ef)", "N/m")):
            media, s = agregado([r[clave] for r in res])
            extra = f" | dispersión entre repeticiones s = {s:.3g} {unid}" if s is not None else ""
            L.append(f"- {nom} = {fmt(media, unid)}{extra}")
            if clave == "T":
                T_med = media

        L += ["", "## Máximos (primer video, valores del ajuste con incerteza, x desde el equilibrio)", ""]
        for k_, v in res[0]["maximos"].items():
            L.append(f"- {k_}: {fmt(v)}")

        L += ["", "## Energía (primer video, datos filtrados, incerteza propagada)", "",
              "| cantidad | valor con incerteza |", "|---|---|"]
        for k_, v in res[0]["energia"].items():
            L.append(f"| {k_} | {fmt(v)} |")

        claves = list(res[0]["comp"].keys())
        L += ["", f"## Crudo vs filtrado (Savitzky-Golay, ventana = {a.ventana} cuadros)", "",
              "| video | " + " | ".join(claves) + " |",
              "|---|" + "---|" * len(claves)]
        prom = {k_: [] for k_ in claves}
        for r in res:
            celdas = []
            for k_ in claves:
                v = r["comp"][k_]
                celdas.append(fmt(v) if hasattr(v, "n") else f"{v:.4f}")
                prom[k_].append(v)
            L.append(f"| {r['nombre']} | " + " | ".join(celdas) + " |")
        promedio = []
        for k_ in claves:
            vals = prom[k_]
            media = (sum(vals) / len(vals)) if hasattr(vals[0], "n") else float(np.mean(vals))
            promedio.append(fmt(media) if hasattr(media, "n") else f"{media:.4f}")
        L.append("| promedio | " + " | ".join(promedio) + " |")
        L.append("")
        L.append("El RMS de a crudo sobre la amplitud de a del ajuste mide cuánto amplifica "
                 "el ruido la segunda derivada sin filtrar.")

    if k_e is not None and T_med is not None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            chequeo_periodo(k_e, ufloat(a.masa, a.sigma_masa),
                            ufloat(a.masa_resorte, a.sigma_masa_resorte), T_med)
        L += ["", "## Chequeo físico: período con y sin masa efectiva", "",
              f"k estático = {fmt(k_e, 'N/m')}", "", "```", buf.getvalue().rstrip(), "```"]

    # Limitaciones detectadas automáticamente
    lim = []
    for r in res:
        if r["perdidos"] > 0.05:
            lim.append(f"{r['nombre']}: {100 * r['perdidos']:.1f} % de cuadros sin detección (rellenados por interpolación).")
        if r["redchi"] > 3 or r["redchi"] < 0.3:
            lim.append(f"{r['nombre']}: χ² reducido = {r['redchi']:.2f}; σ del tracking mal estimadas o modelo inadecuado.")
        if r["ciclos"] < 5:
            lim.append(f"{r['nombre']}: solo {r['ciclos']:.1f} ciclos observados; T y k menos precisos.")
        if r["muestras_T"] < 10:
            lim.append(f"{r['nombre']}: {r['muestras_T']:.1f} cuadros por período (<10); riesgo de submuestreo.")
        if r["gamma"].n < 2 * r["gamma"].s:
            lim.append(f"{r['nombre']}: γ compatible con 0 (amortiguamiento no detectable).")
    if len(res) < 5:
        lim.append(f"Solo {len(res)} repeticiones; la receta pide entre 5 y 20.")
    if not a.fps_real and not getattr(a, "fps_led", None):
        lim.append("fps real no verificado: se usó el fps declarado por el video.")
    if getattr(a, "fps_led_aviso", None):
        lim.append(a.fps_led_aviso + ".")
    if k_e is None:
        lim.append("No se hizo el chequeo del período: falta k estático independiente.")
    elif a.sigma_elongacion is None:
        lim.append("k estático sin --sigma-elongacion: la incerteza de k no incluye la de las "
                   "elongaciones medidas (sólo la dispersión de la recta y σg).")
    for nombre, err in fallidos:
        lim.append(f"{nombre}: falló el análisis ({err}).")
    L += ["", "## Limitaciones detectadas automáticamente", ""] + [f"- {x}" for x in lim]
    L += ["", "## Limitaciones (completar a mano)", "",
          "- Qué falló:", "- En qué condición se rompe:", "- Qué quedó sin resolver:"]

    with open(ruta, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser(description="Agente de análisis de resorte (offline).")
    ap.add_argument("videos", nargs="+")
    ap.add_argument("--masa", type=float, required=True, help="masa colgante (kg)")
    ap.add_argument("--sigma-masa", type=float, default=0.001)
    ap.add_argument("--masa-resorte", type=float, default=0.0)
    ap.add_argument("--sigma-masa-resorte", type=float, default=0.0001)
    ap.add_argument("--px-por-m", type=float, help="escala conocida (px/m)")
    ap.add_argument("--sigma-px-por-m", type=float,
                    help="incerteza de la escala (px/m); obligatoria junto con --px-por-m")
    ap.add_argument("--regla-m", type=float, help="largo real de la regla (m); marcar 2 puntos en el 1er video")
    ap.add_argument("--fps-real", type=float, help="fps verificado con LED o cronómetro")
    ap.add_argument("--video-led", help="video de un LED que parpadea a --f-led Hz (mismo setup que los videos)")
    ap.add_argument("--f-led", type=float, help="frecuencia conocida del LED (Hz)")
    ap.add_argument("--roi", type=int, nargs=4, metavar=("X", "Y", "W", "H"),
                    help="región del LED en el cuadro; si no se da, se usa todo el cuadro")
    ap.add_argument("--eje", choices=["x", "y"], default="x", help="x: horizontal, y: vertical")
    ap.add_argument("--ventana", type=int, default=11)
    ap.add_argument("--masas-estaticas", type=float, nargs="+")
    ap.add_argument("--elongaciones", type=float, nargs="+")
    ap.add_argument("--sigma-elongacion", type=float,
                    help="incerteza de cada elongación (m); si no se da, se anota en limitaciones")
    ap.add_argument("--sigma-g", type=float, default=0.01,
                    help="incerteza de g en el k estático (m/s², default 0.01)")
    ap.add_argument("--salidas", default="salidas")
    ap.add_argument("--color", choices=["rojo", "naranja", "amarillo", "verde", "azul", "negro"], default="rojo")
    a = ap.parse_args()

    if a.px_por_m is None and a.regla_m is None:
        ap.error("dar --px-por-m o --regla-m")
    if a.px_por_m is not None and a.sigma_px_por_m is None:
        ap.error("falta --sigma-px-por-m: con --px-por-m hay que indicar la incerteza de la "
                 "escala en px/m (p. ej. --sigma-px-por-m 2); sin ella la incerteza de la "
                 "calibración sería 0 y las incertezas de x, y y k quedarían subestimadas")
    if a.video_led and a.f_led is None:
        ap.error("--video-led requiere también --f-led HZ")
    if a.f_led is not None and not a.video_led:
        ap.error("--f-led requiere también --video-led RUTA")

    # fps medido con LED: tiene prioridad sobre --fps-real
    a.fps_led, a.fps_sigma = None, 0.0
    if a.video_led:
        try:
            a.fps_led, a.fps_sigma = fps_real_con_led(a.video_led, a.roi, a.f_led)
        except RuntimeError as e:
            ap.error(f"--video-led: {e}")
        print(f"fps real (LED): {a.fps_led:.4f} ± {a.fps_sigma:.4f} fps "
              f"(f_led = {a.f_led} Hz, {'ROI ' + str(a.roi) if a.roi else 'cuadro completo'})")
        _cap = cv2.VideoCapture(a.videos[0])
        _decl = _cap.get(cv2.CAP_PROP_FPS)
        _cap.release()
        _dif = abs(a.fps_led - _decl) / _decl if _decl else 0.0
        a.fps_led_aviso = None
        if _dif > 0.10:
            a.fps_led_aviso = (
                f"fps medido con LED ({a.fps_led:.3f}) difiere en {100 * _dif:.0f}% del declarado por "
                f"los videos de experimentación ({_decl:.3f}): verificar que el video del LED sea del "
                f"mismo setup y que --f-led ({a.f_led} Hz) sea la frecuencia real del parpadeo")
            print("ADVERTENCIA: " + a.fps_led_aviso)
    else:
        a.fps_led_aviso = None

    os.makedirs(a.salidas, exist_ok=True)

    # Escala: una vez, para todos los videos (se asume el mismo setup)
    if a.px_por_m is not None:
        escala = (a.px_por_m, a.sigma_px_por_m)
    else:
        p1, p2 = marcar_dos_puntos(a.videos[0])
        escala = escala_px_por_m(p1, p2, a.regla_m)

    k_e = None
    if a.masas_estaticas and a.elongaciones:
        if len(a.masas_estaticas) != len(a.elongaciones) or len(a.masas_estaticas) < 3:
            ap.error("--masas-estaticas y --elongaciones: misma cantidad, mínimo 3")
        k_e = k_estatico(a.masas_estaticas, a.elongaciones,
                         sigma_g=a.sigma_g, sigma_elongacion=a.sigma_elongacion)

    res, fallidos = [], []
    for v in a.videos:
        try:
            res.append(analizar(v, a, escala, a.salidas))
            print(f"OK  {v}")
        except Exception as e:
            fallidos.append((os.path.basename(v), str(e)))
            print(f"FALLÓ {v}: {e}")

    escribir_informe(res, fallidos, a, escala, k_e, f"{a.salidas}/informe.md")
    with open(f"{a.salidas}/resultados.json", "w") as f:
        json.dump([{c: (r[c].n, r[c].s) for c in ("T", "gamma", "k", "k_sin")} | {"video": r["nombre"]}
                   for r in res], f, indent=2)
    print(f"Informe: {a.salidas}/informe.md")


if __name__ == "__main__":
    main()