# video ent. informe

#Agente: video(s) de resorte -> tracking -> calibración -> señal -> ajuste -> informe.

import argparse, os, io, json, contextlib
import numpy as np
import cv2
from uncertainties import ufloat

from tracking import trackear
from calibracion import marcar_dos_puntos, escala_px_por_m, a_metros
from señal import rellenar_nan, procesar, graficar as graficar_senal
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
    fps_uso = a.fps_real if a.fps_real else fps_decl

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
    c = cantidades(p, m, m_r)

    r = procesar(t, x, ventana=a.ventana)
    C = p["C"].nominal_value
    Ec, Ep, Et = energias(r["x_f"], r["v_f"], c["k_con_mef"].nominal_value,
                          c["m_ef"].nominal_value, C)
    graficar_senal(t, r, f"{carpeta}/{nombre}_senal.png")
    graficar_ajuste(t, x, res, Ec, Ep, Et, f"{carpeta}/{nombre}_ajuste.png")

    T = c["T"]
    return dict(
        nombre=nombre, T=T, gamma=c["gamma"], k=c["k_con_mef"], k_sin=c["k_sin_mef"],
        A=p["A"], redchi=res.redchi, perdidos=perdidos,
        ciclos=(t[-1] - t[0]) / T.n, muestras_T=T.n * fps_uso,
        fps_decl=fps_decl, fps_uso=fps_uso,
        maximos=maximos(t, r["x_f"], r["v_f"], r["a_f"], C),
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

        L += ["", "## Máximos (primer video, datos filtrados, x desde el equilibrio)", ""]
        for k_, v in res[0]["maximos"].items():
            L.append(f"- {k_.strip()}: {v:.4f}")

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
    if not a.fps_real:
        lim.append("fps real no verificado: se usó el fps declarado por el video.")
    if k_e is None:
        lim.append("No se hizo el chequeo del período: falta k estático independiente.")
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
    ap.add_argument("--sigma-px-por-m", type=float, default=0.0)
    ap.add_argument("--regla-m", type=float, help="largo real de la regla (m); marcar 2 puntos en el 1er video")
    ap.add_argument("--fps-real", type=float, help="fps verificado con LED o cronómetro")
    ap.add_argument("--eje", choices=["x", "y"], default="x", help="x: horizontal, y: vertical")
    ap.add_argument("--ventana", type=int, default=11)
    ap.add_argument("--masas-estaticas", type=float, nargs="+")
    ap.add_argument("--elongaciones", type=float, nargs="+")
    ap.add_argument("--salidas", default="salidas")
    ap.add_argument("--color", choices=["rojo", "naranja", "amarillo", "verde", "azul", "negro"], default="rojo")
    a = ap.parse_args()

    if a.px_por_m is None and a.regla_m is None:
        ap.error("dar --px-por-m o --regla-m")
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
        k_e = k_estatico(a.masas_estaticas, a.elongaciones)

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