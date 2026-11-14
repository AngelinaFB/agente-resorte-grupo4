# video ent. informe

#Agente: video(s) de resorte -> tracking -> calibración -> señal -> ajuste -> informe.

import argparse, os, io, json, contextlib, tempfile
import numpy as np
import cv2
from uncertainties import ufloat

from tracking import trackear, guardar_metadatos, ruta_metadatos
from calibracion import marcar_dos_puntos, escala_px_por_m, a_metros, fps_real_con_led
from señal import (rellenar_nan, procesar, detectar_inicio, detectar_inicio_detalle,
                   graficar as graficar_senal, comparar_crudo_filtrado)
from ajuste import (ajustar, parametros_con_incerteza, cantidades, k_estatico,
                    chequeo_periodo, energias, maximos, graficar as graficar_ajuste)


def fmt(u, unidad=""):
    try:
        s = f"{u:.2uP}"
    except Exception:
        s = f"{u.n:.4g} ± {u.s:.2g}"
    return f"{s} {unidad}".strip()


TAG_COMUN = "comun:"


def advertencias_comunes(a):
    """Avisos que no impiden el análisis pero sí afectan la interpretación."""
    avisos = []
    if float(getattr(a, "sigma_masa", 0.0) or 0.0) <= 0:
        avisos.append(
            "la incertidumbre de la masa colgante es 0: las incertezas de k, "
            "energías y del promedio quedan subestimadas"
        )
    if float(getattr(a, "sigma_masa_resorte", 0.0) or 0.0) <= 0:
        avisos.append(
            "la incertidumbre de la masa del resorte es 0: su aporte a la masa "
            "efectiva no está reflejado en las incertezas"
        )
    return avisos


def _normalizar_clave(valor):
    return os.path.normcase(str(valor).strip().replace("\\", "/"))


def _claves_video(ruta):
    ruta = str(ruta)
    base = os.path.basename(ruta)
    tallo = os.path.splitext(base)[0]
    return {
        _normalizar_clave(ruta),
        _normalizar_clave(os.path.abspath(ruta)),
        _normalizar_clave(base),
        _normalizar_clave(tallo),
    }


def _punto_desde_valor(valor):
    if isinstance(valor, dict):
        if "punto" in valor:
            return _punto_desde_valor(valor["punto"])
        try:
            return float(valor["x"]), float(valor["y"])
        except (KeyError, TypeError, ValueError):
            return None
    if isinstance(valor, (list, tuple)) and len(valor) >= 2:
        try:
            return float(valor[0]), float(valor[1])
        except (TypeError, ValueError):
            return None
    return None


def cargar_puntos_json(ruta):
    """Lee un JSON {video: [x,y]} o una lista de {video|nombre, x, y}."""
    with open(ruta, encoding="utf-8") as f:
        datos = json.load(f)
    if isinstance(datos, dict) and "puntos" in datos:
        datos = datos["puntos"]
    puntos = {}
    if isinstance(datos, dict):
        for clave, valor in datos.items():
            punto = _punto_desde_valor(valor)
            if punto is not None:
                puntos[_normalizar_clave(clave)] = punto
        return puntos
    if isinstance(datos, list):
        for item in datos:
            if not isinstance(item, dict):
                continue
            clave = item.get("video") or item.get("nombre") or item.get("archivo")
            punto = _punto_desde_valor(item)
            if clave is not None and punto is not None:
                puntos[_normalizar_clave(clave)] = punto
        return puntos
    raise ValueError(f"{ruta}: se esperaba un objeto o una lista de puntos")


def cargar_instantes_json(ruta):
    """Lee instantes opcionales por video junto con los puntos del JSON."""
    with open(ruta, encoding="utf-8") as f:
        datos = json.load(f)
    if isinstance(datos, dict) and "puntos" in datos:
        datos = datos["puntos"]
    elementos = datos.items() if isinstance(datos, dict) else (
        ((item.get("video") or item.get("nombre") or item.get("archivo")), item)
        for item in datos if isinstance(item, dict)
    ) if isinstance(datos, list) else []
    instantes = {}
    for clave, valor in elementos:
        if clave is None or not isinstance(valor, dict):
            continue
        tiempo = next((valor[k] for k in ("t_punto_s", "t_punto", "instante_punto_s") if k in valor), None)
        if tiempo is not None:
            instantes[_normalizar_clave(clave)] = float(tiempo)
    return instantes


def resolver_punto(puntos, video):
    """Devuelve ((x,y), clave) del punto que corresponde exactamente a ese video."""
    for clave in _claves_video(video):
        if clave in puntos:
            return puntos[clave], clave
    return None, None


def cargar_trayectoria(ruta):
    """Carga un CSV de trayectoria y su JSON de metadatos, si existe."""
    if not os.path.isfile(ruta):
        raise RuntimeError(f"no existe la trayectoria: {ruta}")
    datos = np.genfromtxt(ruta, delimiter=",", names=True)
    columnas = ("t_s", "x_px", "y_px", "sx_px", "sy_px")
    if datos.dtype.names:
        faltan = [c for c in columnas if c not in datos.dtype.names]
        if faltan:
            raise RuntimeError(f"{ruta}: faltan columnas {', '.join(faltan)}")
        filas = np.column_stack([np.asarray(datos[c], dtype=float) for c in columnas])
    else:
        filas = np.asarray(datos, dtype=float).reshape(-1, 5)
    if filas.ndim != 2 or filas.shape[1] != 5 or len(filas) == 0:
        raise RuntimeError(f"{ruta}: no tiene una tabla de trayectoria válida")

    metadatos = {}
    candidatos = [
        ruta_metadatos(ruta),
        os.path.splitext(ruta)[0] + "_meta.json",
        os.path.splitext(ruta)[0] + ".json",
    ]
    for candidato in candidatos:
        if os.path.isfile(candidato):
            with open(candidato, encoding="utf-8") as f:
                metadatos = json.load(f)
            break

    seguimiento = dict(metadatos.get("resumen") or metadatos.get("seguimiento") or {})
    n = len(filas)
    detectados = int(np.isfinite(filas[:, 1]).sum())
    seguimiento.setdefault("cuadros", n)
    seguimiento.setdefault("detectados", detectados)
    seguimiento.setdefault("perdidos", n - detectados)
    seguimiento.setdefault("saltos_descartados", 0)
    seguimiento.setdefault("frames_con_multiples_candidatos", 0)
    seguimiento.setdefault("metodo", metadatos.get("metodo", "trayectoria existente"))
    nombre = os.path.splitext(os.path.basename(metadatos.get("archivo_video") or ruta))[0]
    if nombre.endswith("_px"):
        nombre = nombre[:-3]
    return {
        "filas": filas,
        "seguimiento": seguimiento,
        "metadatos": metadatos,
        "nombre": nombre,
        "video": metadatos.get("video"),
        "fps_declarado": metadatos.get("fps_declarado"),
    }


VARIABLES_AGREGADAS = (
    ("T", "T", "s"),
    ("omega", "ω", "rad/s"),
    ("gamma", "γ", "1/s"),
    ("k", "k (con m_ef)", "N/m"),
    ("k_sin", "k (sin m_ef)", "N/m"),
)


def estado_video(r):
    """Criterio orientativo único para decidir si una repetición es promediable."""
    perdidos = r.get("perdidos_analisis", r["perdidos"])
    if r.get("estado") == "invalido" or perdidos > .30 or r.get("ciclos", 0) < 5 or r.get("singular"):
        return "invalido"
    return "aceptable" if (
        perdidos <= .05
        and .3 <= r["redchi"] <= 3
        and r["ciclos"] >= 5
        and r.get("muestras_T", 0) >= 10
    ) else "revisar"


def variables_comunes(a):
    """ufloats que comparten TODOS los videos de una corrida, creados una sola vez.

    Se etiquetan con TAG_COMUN para que agregado() separe su aporte sistemático y
    NO lo divida por √N. La masa, la masa del resorte y el fps son comunes porque
    salen de un único valor de CLI/LED para toda la corrida. La escala espacial
    también se calcula una vez y se aplica a todos, pero T, ω, γ y k no dependen de
    ella (sólo de los tiempos y de m/m_r); sí entraría en A, x y energías, que hoy
    no se agregan.
    """
    m = ufloat(a.masa, a.sigma_masa, tag=TAG_COMUN + "masa")
    m_r = ufloat(a.masa_resorte, a.sigma_masa_resorte, tag=TAG_COMUN + "masa_resorte")
    sigma_fps = float(getattr(a, "fps_sigma", 0.0) or 0.0)
    fps = getattr(a, "fps_led", None)
    if fps is None:
        fps = getattr(a, "fps_real", None)
    corr = None
    if sigma_fps and fps:
        corr = ufloat(1.0, sigma_fps / fps, tag=TAG_COMUN + "fps")
    return m, m_r, corr


def fmt_agregado(agg, unidad=""):
    txt = (f"{agg['media']:.6g} ± {agg['est']:.2g} (est) ± "
           f"{agg['sis']:.2g} (sis) [σ_tot = {agg['tot']:.2g}]")
    return f"{txt} {unidad}".strip()


def preanalizar_video(video, progreso=None, punto_inicial=None, frame_callback=None, desde_s=0.0):
    """Rastrea el video una vez y conserva la trayectoria para análisis posteriores."""
    with tempfile.TemporaryDirectory(prefix="resorte-preanalisis-") as temp_dir:
        csv_px = os.path.join(temp_dir, "trayectoria_px.csv")
        filas = trackear(
            video, csv_px, progreso=progreso, punto_inicial=punto_inicial,
            frame_callback=frame_callback,
            desde_s=desde_s,
        )
        return {
            "filas": np.asarray(filas).copy(),
            "seguimiento": dict(getattr(filas, "resumen", {})),
            "metadatos": dict(getattr(filas, "metadatos", {})),
            "nombre": os.path.splitext(os.path.basename(video))[0],
            "video": os.path.abspath(video),
        }


def analizar_desde_preanalisis(video, a, escala, carpeta, preanalisis):
    """Completa el informe usando una trayectoria ya extraída del video o CSV."""
    nombre = preanalisis.get("nombre") or os.path.splitext(
        os.path.basename(video or "trayectoria")
    )[0]
    px_csv, m_csv = f"{carpeta}/{nombre}_px.csv", f"{carpeta}/{nombre}_m.csv"

    filas = preanalisis["filas"]
    np.savetxt(
        px_csv, filas, delimiter=",",
        header="t_s,x_px,y_px,sx_px,sy_px", comments="",
    )
    perdidos = float(np.isnan(filas[:, 1]).mean())
    seguimiento = dict(preanalisis.get("seguimiento", {}))
    metadatos = dict(preanalisis.get("metadatos", {}))

    fps_decl = preanalisis.get("fps_declarado")
    if video and os.path.isfile(str(video)):
        cap = cv2.VideoCapture(video)
        declarado_video = cap.get(cv2.CAP_PROP_FPS)
        cap.release()
        if declarado_video and declarado_video > 0:
            fps_decl = declarado_video
    if not fps_decl or fps_decl <= 0:
        t_bruto = np.asarray(filas[:, 0], dtype=float)
        dt_bruto = np.median(np.diff(t_bruto)) if len(t_bruto) > 1 else 0.0
        fps_decl = 1.0 / dt_bruto if dt_bruto > 0 else 1.0
    fps_decl = float(fps_decl)

    # FPS de uso: medido con LED > --fps-real > declarado por el video
    if getattr(a, "fps_led", None):
        fps_uso, fps_sigma = a.fps_led, a.fps_sigma
        origen = f"medido con LED ({a.f_led} Hz)"
    elif getattr(a, "fps_real", None):
        fps_uso, fps_sigma = a.fps_real, 0.0
        origen = "--fps-real (valor informado a mano)"
    else:
        fps_uso, fps_sigma = fps_decl, 0.0
        origen = "declarado por el video (sin verificar)"

    t, xm, ym, sxm, sym = a_metros(px_csv, m_csv, escala[0], escala[1])
    t = t * fps_decl / fps_uso                      # corrección por fps real
    std_x = np.nanstd(xm)
    std_y = np.nanstd(ym)
    eje_pedido = getattr(a, "eje", "auto") or "auto"
    if eje_pedido not in ("auto", "x", "y"):
        raise ValueError(f"eje inválido: {eje_pedido!r}; usá auto, x o y")
    eje = ("y" if std_y > std_x else "x") if eje_pedido == "auto" else eje_pedido
    x, sx = (ym, sym) if eje == "y" else (xm, sxm)
    sx = np.where(np.isfinite(sx), sx, np.nanmedian(sx[np.isfinite(sx)]))
    x_rell, n_rellenados = rellenar_nan(t, x)

    # Recorte del tramo previo a la liberación. La detección automática se calcula
    # siempre para poder compararla con un --inicio manual y explicar diferencias.
    inicio_auto, info_inicio = detectar_inicio_detalle(
        t, x_rell,
        ventana_s=getattr(a, "ventana_inicio", 0.5),
        umbral=getattr(a, "umbral_inicio", 0.15),
    )
    inicio_manual = getattr(a, "inicio", None)
    if inicio_manual is not None:
        inicio = inicio_manual
        origen_inicio = "manual (--inicio)"
    elif getattr(a, "recorte_auto", True):
        inicio = inicio_auto
        origen_inicio = "automático"
    else:
        inicio = float(t[0])
        origen_inicio = "sin recorte (--sin-recorte)"
    inicio = float(np.clip(inicio, t[0], t[-1]))
    fin = getattr(a, "fin", None)
    fin = float(t[-1]) if fin is None else float(np.clip(fin, t[0], t[-1]))
    if fin <= inicio:
        raise RuntimeError(
            f"el fin de análisis ({fin:.3f} s) debe ser posterior al inicio ({inicio:.3f} s)"
        )
    mascara = (t >= inicio) & (t <= fin)
    if int(mascara.sum()) < 20:
        raise RuntimeError(
            f"el tramo de análisis ({inicio:.3f}–{fin:.3f} s) deja menos de 20 cuadros"
        )
    t_rec, x_rec, sx_rec = t[mascara], x_rell[mascara], sx[mascara]
    perdidos_analisis = float(np.isnan(x[mascara]).mean())
    x_fit = x[mascara]
    valido = np.isfinite(x_fit) & np.isfinite(sx_rec) & (sx_rec > 0)
    if int(valido.sum()) < 20:
        raise RuntimeError(
            "muy pocos cuadros con detección válida después del recorte; "
            "revisá el punto de tracking o el inicio del análisis"
        )
    t_fit, x_fit, sx_fit = t_rec[valido], x_fit[valido], sx_rec[valido]

    m = getattr(a, "masa_u", None)
    if m is None:
        m = ufloat(a.masa, a.sigma_masa, tag=TAG_COMUN + "masa")
    m_r = getattr(a, "masa_resorte_u", None)
    if m_r is None:
        m_r = ufloat(a.masa_resorte, a.sigma_masa_resorte, tag=TAG_COMUN + "masa_resorte")

    # El ajuste usa solo cuadros con detección: no se inventan datos en huecos largos.
    # Se toma t=0 en el inicio del tramo para que A sea la amplitud de liberación.
    res = ajustar(t_fit - inicio, x_fit, sx_fit)
    if res.covar is None:
        omega_estimado = float(res.params["omega"].value)
        periodo_estimado = 2 * np.pi / omega_estimado if omega_estimado > 0 else np.nan
        ciclos_estimados = (
            (t_fit[-1] - t_fit[0]) / periodo_estimado
            if np.isfinite(periodo_estimado) and periodo_estimado > 0
            else 0.0
        )
        return dict(nombre=nombre, estado="invalido", motivo="ajuste singular (matriz de covarianza singular)",
                    singular=True, perdidos=perdidos, perdidos_analisis=perdidos_analisis,
                    seguimiento=seguimiento, inicio_s=inicio, fin_s=fin,
                    inicio_auto_s=float(inicio_auto), inicio_origen=origen_inicio,
                    inicio_info=info_inicio, punto_inicial_px=metadatos.get("punto_inicial_px"),
                    ciclos=ciclos_estimados, muestras_T=0.0, eje=eje, trayectoria_csv=os.path.basename(px_csv),
                    fps_decl=fps_decl, fps_uso=fps_uso, fps_sigma=fps_sigma, fps_origen=origen)
    p = parametros_con_incerteza(res)
    corr = getattr(a, "corr_fps", None)
    if corr is None and fps_sigma:
        # los tiempos son t = n/fps: un error relativo del fps escala todos los tiempos,
        # por lo tanto T y γ (y k, vía ω0²) se corrigen por f_usado/f_real
        corr = ufloat(1.0, fps_sigma / fps_uso, tag=TAG_COMUN + "fps")
    if corr is not None:
        p["omega"] = p["omega"] * corr
        p["gamma"] = p["gamma"] * corr
    c = cantidades(p, m, m_r)

    r = procesar(t_rec, x_rec, ventana=a.ventana)
    # corr es el mismo objeto que escaló ω y γ: así Ec/Et y Ep/k comparten la
    # incerteza del fps y no se cuenta dos veces en Et ni en RMS a / a_max
    Ec, Ep, Et = energias(r["x_f"], r["v_f"], c["k_con_mef"], c["m_ef"], p["C"], corr_v=corr)
    i_max = lambda arr: max(arr, key=lambda z: z.n)
    energia = {"Ec_max (J)": i_max(Ec), "Ep_max (J)": i_max(Ep),
               "Et media (J)": np.mean(Et), "Et al inicio (J)": Et[0],
               "Et al final (J)": Et[-1], "ΔEt (final - inicial) (J)": Et[-1] - Et[0]}
    graficar_senal(t_rec, r, f"{carpeta}/{nombre}_senal.png")
    # El ajuste se hizo con los puntos válidos; se evalúa sobre la grilla completa
    # recortada para que el gráfico y las energías queden alineados.
    from types import SimpleNamespace
    res_plot = SimpleNamespace(best_fit=res.eval(t=t_rec - inicio))
    graficar_ajuste(t_rec, x_rec, res_plot, Ec, Ep, Et, f"{carpeta}/{nombre}_ajuste.png")

    T = c["T"]
    mx = maximos(p)
    comp = comparar_crudo_filtrado(r, corr_v=corr)
    comp["RMS a / a_max del ajuste"] = comp["RMS a (m/s²)"] / mx["a_max (m/s²)"]
    ciclos = (t_rec[-1] - t_rec[0]) / T.n
    muestras_T = T.n * fps_uso
    meta_salida = dict(metadatos)
    meta_salida.update({
        "archivo_csv": os.path.basename(px_csv),
        "nombre_analisis": nombre,
        "video": metadatos.get("video", video),
        "fps_declarado": float(fps_decl),
        "punto_inicial_px": metadatos.get("punto_inicial_px"),
        "metodo": seguimiento.get("metodo", "trayectoria existente"),
        "resumen": seguimiento,
        "recorte": {
            "inicio_s": float(inicio),
            "fin_s": float(fin),
            "origen": origen_inicio,
            "inicio_automatico_s": float(inicio_auto),
            "info_inicio": info_inicio,
        },
    })
    guardar_metadatos(ruta_metadatos(px_csv), meta_salida)
    resultado = dict(
        nombre=nombre, eje=eje, T=T, omega=p["omega"], gamma=c["gamma"],
        k=c["k_con_mef"], k_sin=c["k_sin_mef"],
        A=p["A"], C=p["C"], phi=p["phi"],
        redchi=float(getattr(res, "redchi_estandar", res.redchi)),
        perdidos=perdidos,
        perdidos_analisis=perdidos_analisis, seguimiento=seguimiento,
        inicio_s=inicio, fin_s=fin, inicio_auto_s=float(inicio_auto),
        inicio_origen=origen_inicio, inicio_info=info_inicio,
        punto_inicial_px=metadatos.get("punto_inicial_px"),
        trayectoria_csv=os.path.basename(px_csv),
        n_rellenados=n_rellenados,
        rms_residuo=float(getattr(res, "rms_residuo", np.nan)),
        sigma_extra=float(getattr(res, "sigma_extra", 0.0)),
        sigma_tracking_px=float(np.nanmedian(sx_fit)) * escala[0],
        redchi_sin_piso=float(getattr(res, "redchi_sin_piso", res.redchi)),
        ciclos=ciclos, muestras_T=muestras_T,
        fps_decl=fps_decl, fps_uso=fps_uso, fps_sigma=fps_sigma, fps_origen=origen,
        maximos=mx, energia=energia, comp=comp,
    )
    resultado["estado"] = estado_video(resultado)
    if resultado["estado"] == "invalido":
        if perdidos_analisis > .30:
            resultado["motivo"] = f"más de 30 % de cuadros perdidos en el tramo ({100*perdidos_analisis:.1f} %)"
        elif ciclos < 5:
            resultado["motivo"] = f"menos de 5 ciclos observados ({ciclos:.2f})"
    return resultado


def analizar(video, a, escala, carpeta, progreso=None, punto_inicial=None,
             preanalisis=None, frame_callback=None, desde_s=0.0):
    """Interfaz compatible: permite pasar tracking ya calculado para reutilizarlo."""
    if preanalisis is None:
        preanalisis = preanalizar_video(
            video, progreso=progreso, punto_inicial=punto_inicial,
            frame_callback=frame_callback,
            desde_s=desde_s,
        )
    return analizar_desde_preanalisis(video, a, escala, carpeta, preanalisis)


def agregado(vals):
    """Lista de ufloat -> media, σ_est, σ_sis y σ_tot para una magnitud agregada.

    σ_est = desvío entre los valores nominales / √N (ddof=1), como antes. Con N=1
    no hay dispersión: se usa la incerteza del ajuste individual, es decir la suma
    en cuadratura de los componentes NO comunes del ufloat.
    σ_sis = suma en cuadratura de los componentes comunes (etiquetados TAG_COMUN:
    fps, masa y masa del resorte). Se extrae del promedio de los ufloat y NO se
    divide por √N, porque una misma calibración/valor afecta a todos los videos.
    """
    n = len(vals)
    if n == 0:
        raise ValueError("no hay valores para agregar")
    nominales = np.array([v.n for v in vals])
    promedio = sum(vals) / n
    comps = promedio.error_components()

    def comun(var):
        return str(getattr(var, "tag", "") or "").startswith(TAG_COMUN)

    sis = float(np.sqrt(sum(c ** 2 for var, c in comps.items() if comun(var))))
    est_fit = float(np.sqrt(sum(c ** 2 for var, c in comps.items() if not comun(var))))
    if n >= 2:
        dispersion = float(nominales.std(ddof=1))
        est = dispersion / np.sqrt(n)
    else:
        dispersion = None
        est = est_fit
    return dict(
        n=n,
        media=float(promedio.n),
        est=float(est),
        sis=sis,
        tot=float(np.hypot(est, sis)),
        dispersion=dispersion,
    )


def calcular_agregados(res, solo_validos=True):
    """Agrega solo repeticiones aceptables; devuelve None si no queda ninguna."""
    base = [r for r in res if r.get("estado", "revisar") == "aceptable"] if solo_validos else list(res)
    if not base:
        return None
    return {clave: agregado([r[clave] for r in base]) for clave, _, _ in VARIABLES_AGREGADAS}


def _medida_json(valor, unidad):
    """Representa una magnitud con valor, incertidumbre y unidad explícitos."""
    if hasattr(valor, "n") and hasattr(valor, "s"):
        return {"valor": float(valor.n), "incerteza": float(valor.s), "unidad": unidad}
    return {"valor": float(valor), "unidad": unidad}


def resultados_json(res, a=None):
    """Devuelve una estructura legible y versionada para humanos y programas."""
    definiciones = {
        "periodo": ("T", "s"),
        "frecuencia_angular": ("omega", "rad/s"),
        "amortiguamiento": ("gamma", "1/s"),
        "constante_elastica_con_masa_efectiva": ("k", "N/m"),
        "constante_elastica_sin_masa_efectiva": ("k_sin", "N/m"),
        "amplitud": ("A", "m"),
        "posicion_de_equilibrio": ("C", "m"),
        "fase_inicial": ("phi", "rad"),
    }
    videos = []
    for r in res:
        seg = r.get("seguimiento", {})
        total = int(seg.get("cuadros", 0))
        detectados = int(seg.get("detectados", total - round(r["perdidos"] * total)))
        calidad = r.get("estado", estado_video(r))
        perdidos_analisis = float(r.get("perdidos_analisis", r["perdidos"]))
        alertas = []
        invalido = calidad == "invalido"
        if perdidos_analisis > .05: alertas.append("más de 5 % de cuadros sin detección en el tramo analizado")
        if invalido: alertas.append(r.get("motivo", "resultado inválido"))
        if not invalido:
            if r["redchi"] < .3 or r["redchi"] > 3: alertas.append("chi cuadrado reducido fuera del rango orientativo 0.3–3")
            if r["ciclos"] < 5: alertas.append("menos de 5 ciclos observados")
            if r["muestras_T"] < 10: alertas.append("menos de 10 cuadros por período")
            if r["gamma"].n < 2*r["gamma"].s: alertas.append("amortiguamiento compatible con cero")
        resultados = {} if invalido else {nombre: _medida_json(r[clave], unidad)
                      for nombre, (clave, unidad) in definiciones.items()}
        if not invalido:
            resultados["chi_cuadrado_reducido"] = {"valor": float(r["redchi"]), "unidad": ""}
            resultados["chi_cuadrado_sin_piso_de_ruido"] = {"valor": float(r.get("redchi_sin_piso", r["redchi"])), "unidad": ""}
            resultados["rms_residuo"] = {"valor": float(r.get("rms_residuo", 0.0)), "unidad": "m"}
            resultados["maximos"] = {nombre: _medida_json(valor, nombre.rpartition("(")[2].rstrip(")")) for nombre, valor in r["maximos"].items()}
            resultados["energia"] = {nombre: _medida_json(valor, "J") for nombre, valor in r["energia"].items()}
        videos.append({
            "video": r["nombre"],
            "estado": calidad,
            "motivo": r.get("motivo"),
            "alertas": alertas,
            "seguimiento": {
                "metodo": seg.get("metodo", "No informado"),
                "cuadros_totales": total,
                "cuadros_detectados": detectados,
                "cuadros_perdidos": total - detectados,
                "porcentaje_perdido": 100 * float(r["perdidos"]),
                "porcentaje_perdido_analisis": 100 * perdidos_analisis,
                "inicio_analisis_s": float(r.get("inicio_s", 0.0)),
                "inicio_automatico_s": float(r.get("inicio_auto_s", 0.0)),
                "inicio_origen": r.get("inicio_origen", "automático"),
                "fin_analisis_s": float(r.get("fin_s", 0.0)),
                "info_inicio": r.get("inicio_info", {}),
                "punto_inicial_px": r.get("punto_inicial_px"),
                "trayectoria_csv": r.get("trayectoria_csv"),
                "cuadros_rellenados": int(r.get("n_rellenados", 0)),
                "eje_de_oscilacion": r["eje"],
                "cuadros_con_candidatos_multiples": int(seg.get("frames_con_multiples_candidatos", 0)),
                "saltos_descartados": int(seg.get("saltos_descartados", 0)),
                "cuadros_con_flujo": int(seg.get("cuadros_con_flujo", 0)),
                "cuadros_con_plantilla": int(seg.get("cuadros_con_plantilla", 0)),
                "redetecciones": int(seg.get("redetecciones", 0)),
            },
            "ajuste": {
                "ciclos_observados": float(r.get("ciclos", 0)),
                "cuadros_por_periodo": float(r["muestras_T"]),
                "sigma_extra_ruido": float(r.get("sigma_extra", 0.0)),
                "sigma_tracking_px": float(r.get("sigma_tracking_px", 0.0)),
            },
            "fps": {"declarados": float(r["fps_decl"]), "usados": float(r["fps_uso"]),
                    "incerteza": float(r["fps_sigma"]), "origen": r["fps_origen"]},
            "advertencias": list(r.get("advertencias", [])),
            "resultados": resultados,
        })

    advertencias = advertencias_comunes(a) if a is not None else []
    for r in res:
        advertencias.extend(r.get("advertencias", []))
    salida = {
        "version_formato": 2,
        "descripcion": "Análisis de oscilaciones de un resorte. Incertidumbre en las unidades de cada magnitud.",
        "cantidad_videos_analizados": len(res),
        "cantidad_videos_validos": sum(r.get("estado", "revisar") == "aceptable" for r in res),
        "advertencias": advertencias,
        "videos": videos,
    }
    if res:
        agregados = calcular_agregados(res)
        validos = [r for r in res if r.get("estado", "revisar") == "aceptable"]
        if agregados is not None:
            claves = {"periodo": ("T", "s"), "frecuencia_angular": ("omega", "rad/s"),
                      "amortiguamiento": ("gamma", "1/s"),
                      "constante_elastica_con_masa_efectiva": ("k", "N/m"),
                      "constante_elastica_sin_masa_efectiva": ("k_sin", "N/m")}
            salida["resultado_agregado"] = {
                "cantidad_repeticiones": len(validos),
                "repeticiones_excluidas": len(res) - len(validos),
                "magnitudes": {nombre: {
                    "valor": float(agregados[clave]["media"]),
                    "incerteza_estadistica": float(agregados[clave]["est"]),
                    "incerteza_sistematica": float(agregados[clave]["sis"]),
                    "incerteza_total": float(agregados[clave]["tot"]), "unidad": unidad,
                } for nombre, (clave, unidad) in claves.items()},
            }
        else:
            salida["resultado_agregado"] = None
            salida["motivo_sin_agregado"] = (
                "ninguna repetición cumple los criterios de calidad; "
                "no se promedian resultados no confiables"
            )
    return salida


def escribir_informe(res, fallidos, a, escala, k_e, ruta):
    """Escribe primero el resumen útil y luego los detalles para revisar el análisis."""
    if getattr(a, "inicio", None) is not None:
        inicio_txt = f"{a.inicio:.3f} s (manual)"
    elif getattr(a, "recorte_auto", True):
        inicio_txt = "automático (envolvente de la oscilación)"
    else:
        inicio_txt = "sin recorte (desde el primer cuadro)"
    fin_txt = (
        f"{a.fin:.3f} s" if getattr(a, "fin", None) is not None
        else "final del registro"
    )
    L = ["# Análisis del resorte: resultados", "", "## Resumen", "",
         f"- Videos analizados: **{len(res)}** ({sum(r.get('estado') == 'aceptable' for r in res)} válidos para el agregado)",
         f"- Videos con errores: **{len(fallidos)}**",
         f"- Masa colgante: **{fmt(ufloat(a.masa, a.sigma_masa), 'kg')}**",
         f"- Masa del resorte: **{fmt(ufloat(a.masa_resorte, a.sigma_masa_resorte), 'kg')}**",
         f"- Escala espacial: **{fmt(ufloat(*escala), 'px/m')}**",
         f"- Filtro de señal: **{a.ventana} cuadros**",
         f"- Inicio del ajuste: **{inicio_txt}**",
         f"- Fin del ajuste: **{fin_txt}**", ""]
    for aviso in advertencias_comunes(a):
        L.append(f"- **ADVERTENCIA:** {aviso}.")
    L += ["",
          "Los valores se expresan como valor ± incertidumbre. **Revisar** indica que el seguimiento "
          "o el ajuste no cumple al menos uno de los criterios orientativos. El ajuste usa solo "
          "cuadros con detección; la interpolación se reserva para los gráficos.", "", "## Resultados por video", ""]
    if res:
        L += ["| Video | Estado | Período T (s) | Frecuencia angular ω (rad/s) | Amortiguamiento γ (1/s) | k con masa efectiva (N/m) | k sin masa efectiva (N/m) |",
              "|---|---|---:|---:|---:|---:|---:|"]
        for r in res:
            estado = r.get("estado", estado_video(r))
            etiqueta = {"aceptable": "Aceptable", "revisar": "Revisar", "invalido": "Inválido"}.get(estado, estado)
            if estado == "invalido":
                L.append(f"| {r['nombre']} | {etiqueta} | — | — | — | — | — |")
            else:
                L.append(f"| {r['nombre']} | {etiqueta} | {fmt(r['T'])} | {fmt(r['omega'])} | {fmt(r['gamma'])} | {fmt(r['k'])} | {fmt(r['k_sin'])} |")

        L += ["", "## Seguimiento de la pesa", "",
              "El ajuste descarta los cuadros sin detección. Si son muchos, la incertidumbre real "
              "puede ser mayor que la reportada por el ajuste. El inicio automático se estima con "
              "la envolvente de la componente oscilatoria: se busca el primer tramo sostenido que "
              "supera el 15 % de la amplitud final, de modo que un movimiento lento o un reacomodo "
              "no se confunda con la liberación. Si el inicio automático no coincide con la "
              "liberación real, conviene fijarlo con --inicio y el informe deja constancia de ambos.", "",
              "| Video | Método | Cuadros | Detectados | Perdidos | Perdidos (%) | Inicio auto (s) | Inicio usado (s) | Origen | Fin (s) | Perdidos en el tramo (%) | Eje | Varios candidatos | Saltos descartados |",
              "|---|---|---:|---:|---:|---:|---:|---:|---|---:|---:|---|---:|---:|"]
        for r in res:
            if r.get("estado") == "invalido":
                s = r.get("seguimiento", {})
                n = int(s.get("cuadros", 0))
                nd = int(s.get("detectados", n - round(r["perdidos"] * n)))
                info = r.get("inicio_info", {})
                origen = r.get("inicio_origen", "automático")
                razon_inicio = info.get("motivo", "")
                if razon_inicio:
                    origen += f" ({razon_inicio})"
                L.append(
                    f"| {r['nombre']} | {s.get('metodo', 'No informado')} | {n} | {nd} | "
                    f"{n-nd} | {100*r['perdidos']:.1f} % | {r.get('inicio_auto_s', 0.0):.3f} | "
                    f"{r.get('inicio_s', 0.0):.3f} | {origen} | {r.get('fin_s', 0.0):.3f} | "
                    f"{100*r.get('perdidos_analisis', r['perdidos']):.1f} % | {r.get('eje', '—')} | "
                    f"{s.get('frames_con_multiples_candidatos', 0)} | {s.get('saltos_descartados', 0)} |"
                )
                continue
            s = r.get("seguimiento", {})
            n = int(s.get("cuadros", 0))
            nd = int(s.get("detectados", n - round(r["perdidos"] * n)))
            info = r.get("inicio_info", {})
            motivo = info.get("motivo", "")
            motivo = f" ({motivo})" if motivo else ""
            L.append(f"| {r['nombre']} | {s.get('metodo', 'No informado')} | {n} | {nd} | "
                     f"{n-nd} | {100*r['perdidos']:.1f} % | {r.get('inicio_auto_s', 0.0):.3f} | "
                     f"{r.get('inicio_s', 0.0):.3f} | {r.get('inicio_origen', 'automático')}{motivo} | "
                     f"{r.get('fin_s', 0.0):.3f} | "
                     f"{100*r.get('perdidos_analisis', r['perdidos']):.1f} % | {r['eje']} | "
                     f"{s.get('frames_con_multiples_candidatos', 0)} | {s.get('saltos_descartados', 0)} |")

        L += ["", "## Calidad del ajuste", "",
              "| Video | χ² reducido | χ² sin piso de ruido | RMS residual (px) | σ extra (px) | Ciclos observados | Cuadros por período | FPS usado | Origen del FPS |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
        for r in res:
            if r.get("estado") == "invalido":
                L.append(f"| {r['nombre']} | — | — | — | — | {r.get('ciclos', 0):.2f} | — | — | — |")
                continue
            rms_px = float(r.get("rms_residuo", 0.0)) * escala[0]
            sigma_px = float(r.get("sigma_extra", 0.0)) * escala[0]
            L.append(f"| {r['nombre']} | {r['redchi']:.3g} | {r.get('redchi_sin_piso', r['redchi']):.3g} | "
                     f"{rms_px:.3g} | {sigma_px:.3g} | {r['ciclos']:.2f} | {r['muestras_T']:.1f} | "
                     f"{r['fps_uso']:.4g} fps | {r['fps_origen']} |")
        L += ["", "Como guía, el estado aceptable requiere hasta 5 % de cuadros perdidos en el tramo analizado; más de 30 % de pérdidas, menos de 5 ciclos o un ajuste singular da estado Inválido. "
              "χ² reducido entre 0.3 y 3 y al menos 5 ciclos. El χ² usa un piso de ruido estimado del "
              "residual; el valor sin piso se incluye para comparar con el criterio anterior.", "",
              "## Resultado combinado de las repeticiones", "",
              "Solo se promedian las repeticiones con estado aceptable. "
              "σ estadística representa la variación entre repeticiones (o la incertidumbre del ajuste con una repetición). "
              "σ sistemática incluye errores comunes, como masa y FPS. σ total combina ambas.", "",
              "| Magnitud | Media | σ estadística | σ sistemática | σ total |",
              "|---|---:|---:|---:|---:|"]
        agregados = calcular_agregados(res)
        validos = [r for r in res if r.get("estado", "revisar") == "aceptable"]
        if agregados is None:
            L.append("| — | — | — | — | — |")
            L += ["", f"No se calculó un promedio: ninguna de las {len(res)} repeticiones cumple los criterios de calidad."]
        else:
            for clave, nombre, unidad in VARIABLES_AGREGADAS:
                v = agregados[clave]
                L.append(f"| {nombre} ({unidad}) | {v['media']:.6g} | {v['est']:.3g} | {v['sis']:.3g} | {v['tot']:.3g} |")
            if len(validos) < len(res):
                L += ["", f"Se excluyeron {len(res) - len(validos)} repetición(es) por estado Revisar."]
        primer_valido = next((r for r in res if r.get("estado") != "invalido"), None)
        if primer_valido:
            L += ["", "## Otros resultados del primer video válido", "", "### Máximos calculados", ""]
            L.extend(f"- **{nombre}:** {fmt(valor)}" for nombre, valor in primer_valido["maximos"].items())
            L += ["", "### Energías", "", "| Magnitud | Resultado |", "|---|---:|"]
            L.extend(f"| {nombre} | {fmt(valor)} |" for nombre, valor in primer_valido["energia"].items())
        claves = list(primer_valido["comp"]) if primer_valido else []
        L += ["", f"## Señal cruda frente a filtrada (ventana {a.ventana})", "",
              "| Video | " + " | ".join(claves) + " |", "|---|" + "---|" * len(claves)]
        for r in res:
            if r.get("estado") == "invalido":
                continue
            celdas = [fmt(r["comp"][k]) if hasattr(r["comp"][k], "n") else f"{r['comp'][k]:.4f}" for k in claves]
            L.append(f"| {r['nombre']} | " + " | ".join(celdas) + " |")
        if k_e is not None and agregados is not None:
            agg = agregados["T"]
            t_med = ufloat(agg["media"], agg["tot"])
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                chequeo_periodo(k_e, ufloat(a.masa, a.sigma_masa), ufloat(a.masa_resorte, a.sigma_masa_resorte), t_med)
            L += ["", "## Comparación con la medición estática", "",
                  f"Constante elástica estática: **{fmt(k_e, 'N/m')}**", "", "```text", buf.getvalue().rstrip(), "```"]

    limitaciones = []
    for r in res:
        if r.get("estado") == "invalido":
            limitaciones.append(f"{r['nombre']}: estado Inválido; {r.get('motivo', 'no cumple criterios de validez')}.")
            continue
        perdidos_analisis = r.get("perdidos_analisis", r["perdidos"])
        if perdidos_analisis > .05:
            limitaciones.append(
                f"{r['nombre']}: {100*perdidos_analisis:.1f} % de cuadros sin detección en el tramo "
                f"analizado ({100*r['perdidos']:.1f} % en todo el video)."
            )
        if perdidos_analisis > .5:
            limitaciones.append(
                f"{r['nombre']}: se perdió más de la mitad de la trayectoria analizada; "
                "T, k y amortiguamiento no son confiables. Revisar el punto/umbral o descartar esta repetición."
            )
        if r["redchi"] > 3 or r["redchi"] < .3: limitaciones.append(f"{r['nombre']}: χ² reducido {r['redchi']:.2f}; el modelo puede no describir bien los datos.")
        if r["ciclos"] < 5: limitaciones.append(f"{r['nombre']}: solo {r['ciclos']:.1f} ciclos; T y k pueden ser poco precisos.")
        if r["muestras_T"] < 10: limitaciones.append(f"{r['nombre']}: {r['muestras_T']:.1f} cuadros por período; posible submuestreo.")
        if r["gamma"].n < 2*r["gamma"].s: limitaciones.append(f"{r['nombre']}: amortiguamiento compatible con cero dentro de 2 incertidumbres.")
        if r.get("inicio_s", 0.0) > 0:
            limitaciones.append(f"{r['nombre']}: se ajustó desde t = {r['inicio_s']:.3f} s para excluir el tramo estático.")
        auto = float(r.get("inicio_auto_s", 0.0))
        usado = float(r.get("inicio_s", 0.0))
        if str(r.get("inicio_origen", "")).startswith("manual"):
            tolerancia = max(0.5, 0.05 * max(1.0, float(r.get("fin_s", usado)) - auto))
            if abs(usado - auto) > tolerancia:
                limitaciones.append(
                    f"{r['nombre']}: el inicio manual ({usado:.3f} s) difiere del automático "
                    f"({auto:.3f} s). Se usó el manual; revisar si el recorte automático tomó "
                    "un movimiento previo como liberación."
                )
        info = r.get("inicio_info", {})
        if info.get("inicio_en_t0") and len(res) == 1:
            limitaciones.append(
                f"{r['nombre']}: la detección automática no encontró un prefijo quieto "
                f"(inicio = {auto:.3f} s); el tramo previo a la liberación puede estar incluido."
            )
    validos = [r for r in res if r.get("estado", "revisar") == "aceptable"]
    if len(res) < 5: limitaciones.append(f"Se analizaron {len(res)} repeticiones; la receta recomienda entre 5 y 20.")
    if res and not res[0]["fps_sigma"]: limitaciones.append("FPS real no verificado; se usó el FPS del video o el valor ingresado.")
    if getattr(a, "fps_led_aviso", None): limitaciones.append(a.fps_led_aviso)
    if k_e is None: limitaciones.append("No se comparó con una k estática porque no se ingresaron esos datos.")
    elif a.sigma_elongacion is None: limitaciones.append("La incertidumbre de las elongaciones no está incluida en la k estática.")
    if res and len(validos) < len(res):
        limitaciones.append(
            f"{len(res) - len(validos)} repetición(es) quedaron en estado Revisar y no se incluyeron en el promedio."
        )
    for r in res:
        limitaciones.extend(f"{r['nombre']}: {aviso}" for aviso in r.get("advertencias", []))
    limitaciones.extend(f"ADVERTENCIA: {aviso}." for aviso in advertencias_comunes(a))
    limitaciones.extend(f"{nombre}: error durante el análisis: {error}" for nombre, error in fallidos)
    L += ["", "## Observaciones y limitaciones", ""]
    L += [f"- {x}" for x in limitaciones] if limitaciones else ["- No se detectaron limitaciones automáticas."]
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser(description="Agente de análisis de resorte (offline).")
    ap.add_argument("videos", nargs="*")
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
    ap.add_argument("--ventana", type=int, default=11)
    ap.add_argument("--punto", nargs="+", action="append", metavar="VALOR",
                    help="punto inicial por video: --punto NOMBRE X Y (repetible). "
                         "El formato antiguo --punto X Y se aplica a todos y avisa.")
    ap.add_argument("--puntos", help="JSON {video: [x,y]} con un punto inicial por video")
    ap.add_argument("--desde", type=float, default=None,
                    help="instante (s) desde el que empieza el tracking; requiere punto en ese cuadro")
    ap.add_argument("--t-punto", type=float, default=None,
                    help="instante (s) del punto inicial; equivalente a --desde")
    ap.add_argument("--trayectoria", action="append", default=[], metavar="CSV",
                    help="reanalizar un CSV de trayectoria ya guardado (repetible); "
                         "lee el JSON de metadatos que lo acompaña")
    ap.add_argument("--eje", choices=("auto", "x", "y"), default="auto",
                    help="eje de oscilación (default: el de mayor desvío)")
    ap.add_argument("--inicio", type=float,
                    help="segundo desde el cual ajustar; si no se da, se detecta automáticamente")
    ap.add_argument("--fin", type=float,
                    help="último segundo incluido en el ajuste (default: final del registro)")
    ap.add_argument("--sin-recorte", action="store_true",
                    help="no recortar el tramo inicial (ajustar el video completo)")
    ap.add_argument("--ventana-inicio", type=float, default=0.5,
                    help="ventana (s) para detectar el inicio de la oscilación (default 0.5)")
    ap.add_argument("--umbral-inicio", type=float, default=0.15,
                    help="fracción de la amplitud final para detectar el inicio (default 0.15)")
    ap.add_argument("--masas-estaticas", type=float, nargs="+")
    ap.add_argument("--elongaciones", type=float, nargs="+")
    ap.add_argument("--sigma-elongacion", type=float,
                    help="incerteza de cada elongación (m); si no se da, se anota en limitaciones")
    ap.add_argument("--sigma-g", type=float, default=0.01,
                    help="incerteza de g en el k estático (m/s², default 0.01)")
    ap.add_argument("--salidas", default="salidas")
    a = ap.parse_args()
    a.recorte_auto = not a.sin_recorte
    if a.sin_recorte and a.inicio is not None:
        ap.error("--sin-recorte y --inicio son incompatibles")
    if not a.videos and not a.trayectoria:
        ap.error("indicá al menos un video o una --trayectoria CSV")

    if a.px_por_m is None and a.regla_m is None:
        ap.error("dar --px-por-m o --regla-m")
    if not a.videos and a.px_por_m is None:
        ap.error("para reanalizar sólo trayectorias hay que dar --px-por-m "
                 "(no hay video donde marcar la regla)")
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
        _decl = 0.0
        if a.videos:
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

    a.masa_u, a.masa_resorte_u, a.corr_fps = variables_comunes(a)
    for aviso in advertencias_comunes(a):
        print("ADVERTENCIA: " + aviso)

    puntos_nombrados = cargar_puntos_json(a.puntos) if a.puntos else {}
    instantes_nombrados = cargar_instantes_json(a.puntos) if a.puntos else {}
    instante_global = a.desde if a.desde is not None else a.t_punto
    if a.desde is not None and a.t_punto is not None and abs(a.desde-a.t_punto) > 1e-9:
        ap.error("--desde y --t-punto deben indicar el mismo instante")
    punto_global = None
    for grupo in a.punto or []:
        if len(grupo) == 2:
            try:
                punto_global = (float(grupo[0]), float(grupo[1]))
            except ValueError:
                ap.error(f"--punto {grupo}: las coordenadas deben ser números")
        elif len(grupo) == 3:
            try:
                puntos_nombrados[_normalizar_clave(grupo[0])] = (
                    float(grupo[1]), float(grupo[2])
                )
            except ValueError:
                ap.error(f"--punto {grupo}: las coordenadas deben ser números")
        else:
            ap.error("--punto espera NOMBRE X Y (por video) o X Y (global)")
    puntos_video, claves_usadas, advertencias_video = {}, set(), {}
    instantes_video = {}
    for video in a.videos:
        punto, clave = resolver_punto(puntos_nombrados, video)
        if punto is not None:
            puntos_video[video] = punto
            claves_usadas.add(clave)
            instantes_video[video] = instantes_nombrados.get(clave, instante_global or 0.0)
            continue
        if punto_global is not None:
            puntos_video[video] = punto_global
            instantes_video[video] = instante_global or 0.0
            aviso = (
                f"{os.path.basename(video)} no tiene un punto propio; "
                "se usa el --punto global. Verificá que el punto pertenezca a ese video."
            )
            advertencias_video[video] = [aviso]
            print("ADVERTENCIA: " + aviso)
        else:
            puntos_video[video] = None
            instantes_video[video] = 0.0
            aviso = (
                f"{os.path.basename(video)} no tiene punto inicial; "
                "se usará MOG2. Para el seguimiento por punto usá --punto NOMBRE X Y."
            )
            advertencias_video[video] = [aviso]
            print("ADVERTENCIA: " + aviso)
    for clave in set(puntos_nombrados) - claves_usadas:
        print(f"ADVERTENCIA: el punto para {clave!r} no coincide con ningún video analizado.")
    if a.trayectoria and (a.punto or a.puntos):
        print("ADVERTENCIA: --punto/--puntos no se aplica a --trayectoria (ya está guardada).")

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
            resultado = analizar(v, a, escala, a.salidas, punto_inicial=puntos_video.get(v),
                                 desde_s=instantes_video.get(v, 0.0))
            resultado["advertencias"] = advertencias_video.get(v, [])
            res.append(resultado)
            print(f"OK  {v}")
        except Exception as e:
            fallidos.append((os.path.basename(v), str(e)))
            print(f"FALLÓ {v}: {e}")

    for trayectoria in a.trayectoria:
        try:
            preanalisis = cargar_trayectoria(trayectoria)
            nombre_trabajo = preanalisis.get("video") or trayectoria
            res.append(analizar(
                nombre_trabajo, a, escala, a.salidas, preanalisis=preanalisis,
            ))
            print(f"OK  trayectoria {trayectoria}")
        except Exception as e:
            fallidos.append((os.path.basename(trayectoria), str(e)))
            print(f"FALLÓ trayectoria {trayectoria}: {e}")

    escribir_informe(res, fallidos, a, escala, k_e, f"{a.salidas}/informe.md")
    with open(f"{a.salidas}/resultados.json", "w", encoding="utf-8") as f:
        json.dump(resultados_json(res, a), f, indent=2, ensure_ascii=False)
    print(f"Informe: {a.salidas}/informe.md")


if __name__ == "__main__":
    main()
