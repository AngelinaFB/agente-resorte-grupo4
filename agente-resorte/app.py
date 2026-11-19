import base64
import io
import json
import re
import tempfile
import unicodedata
import zipfile
from pathlib import Path
from types import SimpleNamespace

import streamlit as st

st.set_page_config(page_title="Análisis de resorte", page_icon="🌀", layout="wide")
with st.spinner("Cargando herramientas del analizador…", show_time=True):
    import cv2
    import numpy as np
    import streamlit.components.v1 as components
    from uncertainties import ufloat

    from calibracion import escala_px_por_m
    from main import (advertencias_comunes, analizar, diagnosticar_trayectoria,
                      preanalizar_video, escribir_informe, resultados_json,
                      variables_comunes)
    from ajuste import k_estatico
    from tracking import trackear

seleccionar_punto_tracking = components.declare_component(
    "selector_punto_tracking",
    path=str(Path(__file__).parent / "selector_punto_tracking"),
)

def alternar_ampliacion_selector(clave):
    st.session_state[clave] = not st.session_state.get(clave, False)


def _leer_medida_chat(mensaje):
    """Lee un valor en g (o kg) y una incertidumbre opcional tras el mensaje."""
    numeros = re.findall(r"(?<![\w.])[+-]?\d+(?:[.,]\d+)?", mensaje)
    if not numeros:
        return None
    valores = [float(valor.replace(",", ".")) for valor in numeros[:2]]
    unidad = "kg" if re.search(r"\bkg\b", mensaje, re.IGNORECASE) else "g"
    factor = 1000.0 if unidad == "kg" else 1.0
    return valores[0] * factor, (valores[1] * factor if len(valores) > 1 else None)


def _leer_longitud_chat(mensaje):
    partes = re.split(r"\s*(?:±|\+/-|\+\-)\s*", mensaje, maxsplit=1)
    numeros_valor = re.findall(r"(?<![\w.])[+-]?\d+(?:[.,]\d+)?", partes[0])
    if not numeros_valor:
        return None
    valor = float(numeros_valor[0].replace(",", "."))

    def factor_metros(texto):
        if re.search(r"\bmm\b", texto, re.IGNORECASE):
            return 0.001
        if re.search(r"\bcm\b", texto, re.IGNORECASE):
            return 0.01
        return 1.0

    unidad_valor = partes[0] if factor_metros(partes[0]) != 1.0 else mensaje
    valor_m = valor * factor_metros(unidad_valor)
    sigma_m = None
    if len(partes) == 2:
        numeros_sigma = re.findall(r"(?<![\w.])[+-]?\d+(?:[.,]\d+)?", partes[1])
        if not numeros_sigma:
            return None
        sigma = float(numeros_sigma[0].replace(",", "."))
        unidad_sigma = partes[1] if factor_metros(partes[1]) != 1.0 else unidad_valor
        sigma_m = sigma * factor_metros(unidad_sigma)
    return valor_m, sigma_m


def _leer_constante_chat(mensaje):
    numeros = re.findall(r"(?<![\w.])[+-]?\d+(?:[.,]\d+)?", mensaje)
    if len(numeros) < 2:
        return None
    valores = [float(valor.replace(",", ".")) for valor in numeros[:2]]
    return valores[0], valores[1]


def _inferir_masa_colgante_chat(k_n_m, sigma_k, masa_resorte_g, sigma_resorte_g, diagnosticos):
    ajustes = [dato for dato in diagnosticos if dato.get("estado") != "invalido"]
    if not ajustes:
        raise ValueError("No hay ajustes válidos para inferir la masa desde k.")
    k = ufloat(k_n_m, sigma_k)
    masa_resorte = ufloat(masa_resorte_g / 1000.0, sigma_resorte_g / 1000.0)
    masas_estimadas = [
        k / (dato["omega"] ** 2 + dato["gamma"] ** 2) - masa_resorte / 3.0
        for dato in ajustes
    ]
    if any(masa.n <= 0 for masa in masas_estimadas):
        raise ValueError(
            "La k ingresada no es compatible con una masa colgante positiva para todos los videos válidos."
        )
    promedio = sum(masas_estimadas) / len(masas_estimadas)
    dispersion = (
        float(np.std([masa.n for masa in masas_estimadas], ddof=1) / np.sqrt(len(masas_estimadas)))
        if len(masas_estimadas) > 1 else 0.0
    )
    estimacion = ufloat(promedio.n, float(np.hypot(promedio.s, dispersion)))
    return estimacion


def _firma_ajuste_chat(videos_actuales):
    metodo = st.session_state.get("metodo_tracking", "Punto marcado · flujo óptico")
    return (
        tuple(_clave_tracking_chat(video, metodo) for video in videos_actuales),
        st.session_state.get("eje_analisis", "auto"),
        int(st.session_state.get("ventana_analisis", 11)),
    )


def _estado_preparacion_chat(videos_actuales):
    """Devuelve los requisitos de análisis que aún no están listos en la interfaz."""
    pendientes = []
    if not videos_actuales:
        return ["Subí al menos un video en el panel del analizador."]

    puntos_regla = st.session_state.get(
        f"puntos_regla_{videos_actuales[0].file_id}", []
    )
    if len(puntos_regla) != 2:
        pendientes.append("marcá los dos extremos de la regla en el cuadro de referencia")
    metodo = st.session_state.get("metodo_tracking", "Punto marcado · flujo óptico")
    if metodo == "Punto marcado · flujo óptico":
        faltan_puntos = [
            video.name for video in videos_actuales
            if not isinstance(st.session_state.get(f"punto_tracking_{video.file_id}"), dict)
        ]
        if faltan_puntos:
            pendientes.append(
                "marcá la masa en cada video: " + ", ".join(faltan_puntos)
            )
    return pendientes


def _vista_tracking_actual(videos_actuales):
    if not videos_actuales:
        return None
    indice = int(st.session_state.get("indice_video_tracking", 0) or 0)
    if not 0 <= indice < len(videos_actuales):
        return None
    video = videos_actuales[indice]
    metodo = st.session_state.get("metodo_tracking", "Punto marcado · flujo óptico")
    punto = st.session_state.get(f"punto_tracking_{video.file_id}")
    punto_inicial = (
        (punto["x"], punto["y"])
        if isinstance(punto, dict) and "x" in punto and "y" in punto
        else None
    )
    desde_s = float(st.session_state.get(f"instante_punto_{video.file_id}", 0.0))
    algoritmo = "punto-inicial-flujo-optico-v6-desde" if metodo == "Punto marcado · flujo óptico" else "mog2-v1"
    firma = tuple((actual.file_id, actual.name) for actual in videos_actuales)
    vista = st.session_state.get("vista_tracking")
    if not vista:
        return None
    coincide = (
        vista.get("firma") == firma
        and vista.get("indice") == indice
        and vista.get("metodo_tracking") == metodo
        and vista.get("algoritmo") == algoritmo
        and vista.get("punto_inicial") == (punto_inicial if metodo == "Punto marcado · flujo óptico" else None)
        and vista.get("instante_punto_s", 0.0) == desde_s
    )
    return vista if coincide else None


def _clave_tracking_chat(video, metodo):
    punto = st.session_state.get(f"punto_tracking_{video.file_id}")
    punto_inicial = (
        (punto["x"], punto["y"])
        if isinstance(punto, dict) and "x" in punto and "y" in punto
        else None
    )
    return (
        video.file_id,
        metodo,
        punto_inicial if metodo == "Punto marcado · flujo óptico" else None,
        float(st.session_state.get(f"instante_punto_{video.file_id}", 0.0)),
    )


def _obtener_diagnosticos_chat(videos_actuales):
    metodo = st.session_state.get("metodo_tracking", "Punto marcado · flujo óptico")
    cache = st.session_state.setdefault("trayectorias_chat", {})
    vista = _vista_tracking_actual(videos_actuales)
    indice_vista = vista.get("indice") if vista else None
    diagnosticos = []
    errores_tracking = []
    ventana = int(st.session_state.get("ventana_analisis", 11))
    eje = st.session_state.get("eje_analisis", "auto")
    clave_diagnostico = (
        tuple(_clave_tracking_chat(video, metodo) for video in videos_actuales),
        eje,
        ventana,
    )
    if st.session_state.get("clave_diagnosticos_chat") == clave_diagnostico:
        return st.session_state.get("diagnosticos_chat", []), []

    for indice, video in enumerate(videos_actuales):
        clave = _clave_tracking_chat(video, metodo)
        guardado = cache.get(video.file_id)
        preanalisis = guardado.get("preanalisis") if guardado and guardado.get("clave") == clave else None
        if preanalisis is None and vista and indice == indice_vista:
            preanalisis = vista.get("preanalisis")
        if preanalisis is None:
            punto = clave[2]
            instante = clave[3]
            try:
                with tempfile.TemporaryDirectory(prefix="resorte-chat-video-") as carpeta:
                    ruta_video = Path(carpeta) / Path(video.name).name
                    ruta_video.write_bytes(video.getvalue())
                    preanalisis = preanalizar_video(
                        str(ruta_video), punto_inicial=punto, desde_s=instante
                    )
            except Exception as exc:
                errores_tracking.append(f"{video.name}: {exc}")
                continue
        cache[video.file_id] = {"clave": clave, "preanalisis": preanalisis}
        try:
            diagnostico = diagnosticar_trayectoria(preanalisis, eje=eje, ventana=ventana)
        except Exception as exc:
            diagnostico = {
                "nombre": video.name,
                "estado": "invalido",
                "motivo": f"{type(exc).__name__}: {exc}",
            }
        diagnosticos.append(diagnostico)
    st.session_state["diagnosticos_chat"] = diagnosticos
    if not errores_tracking:
        st.session_state["clave_diagnosticos_chat"] = clave_diagnostico
    return diagnosticos, errores_tracking


def _resumen_ajuste_chat(diagnosticos):
    lineas = []
    for dato in diagnosticos:
        if dato.get("estado") == "invalido":
            motivo = str(dato.get("motivo", "")).lower()
            detalle = "covarianza singular" if "covarianza" in motivo else "ajuste no confiable"
            lineas.append(f"- **{dato['nombre']}:** {detalle}.")
            continue
        T, omega, gamma = dato["T"], dato["omega"], dato["gamma"]
        lineas.append(
            f"- **{dato['nombre']}:** $T={T.n:.4g}\\pm{T.s:.2g}\\,\\mathrm{{s}}$; "
            f"$\\gamma={gamma.n:.4g}\\pm{gamma.s:.2g}\\,\\mathrm{{s}}^{{-1}}$."
        )
    return "\n".join(lineas)


def _explicar_datos_derivables(vista, diagnosticos=()):
    lineas = [
        "**Del video obtengo:** posición, velocidad, aceleración, amplitud, período y amortiguamiento."
    ]
    if diagnosticos:
        lineas.append("**Ajuste preliminar:**\n" + _resumen_ajuste_chat(diagnosticos))
    elif vista:
        resumen = vista.get("resumen", {})
        detectados = resumen.get("detectados")
        cuadros = resumen.get("cuadros")
        if detectados is not None and cuadros:
            lineas.append(f"**Seguimiento:** {detectados}/{cuadros} cuadros detectados.")
    return "\n\n".join(lineas)


def _normalizar_texto_chat(texto):
    normalizado = unicodedata.normalize("NFD", texto.lower())
    return "".join(caracter for caracter in normalizado if unicodedata.category(caracter) != "Mn")


def _es_pedido_analisis(mensaje):
    texto = _normalizar_texto_chat(mensaje).strip(" ¿?¡!.,")
    comandos = {
        "analizar", "analizar video", "analizar videos", "iniciar analisis",
        "empezar analisis", "continuar analisis", "que datos faltan",
        "que necesito para analizar",
    }
    if texto in comandos:
        return True
    interrogativo = texto.startswith(("como ", "que es ", "por que ", "cual es ", "explicame "))
    if interrogativo:
        return False
    return (
        "analizar" in texto and any(palabra in texto for palabra in ("video", "analisis", "informe"))
        or "datos" in texto and ("falta" in texto or "necesito" in texto)
        and any(palabra in texto for palabra in ("video", "analisis", "analizar"))
    )


def _es_pregunta_bibliografica(mensaje):
    texto = _normalizar_texto_chat(mensaje).strip()
    return "?" in mensaje or texto.startswith(
        ("que ", "como ", "por que ", "cual ", "cuando ", "explicame ", "defini ")
    )


def _es_consulta_fisica_chat(mensaje):
    palabras = re.findall(r"[a-z0-9]+", _normalizar_texto_chat(mensaje))
    temas = (
        "fisic", "mecanic", "resort", "muell", "oscil", "movim", "cinematic",
        "dinamic", "fuerz", "masa", "peso", "gravedad", "gravit", "newton",
        "hooke", "rozamiento", "friccion", "equilibr", "inerc", "impuls",
        "choque", "colision", "trayector", "desplaz", "posicion", "veloc",
        "aceler", "rapidez", "amplitud", "period", "frecuenc", "amortigu",
        "energi", "trabaj", "potenci", "elast", "derivad", "integral",
        "conservacion", "caida", "rotacion", "torque", "momento",
    )
    return any(palabra.startswith(tema) for palabra in palabras for tema in temas) or bool(
        re.search(r"(?<!\w)k(?!\w)", _normalizar_texto_chat(mensaje))
    )


def _respuesta_social_chat(mensaje):
    texto = _normalizar_texto_chat(mensaje).strip(" .,!¿?¡")
    saludos = {
        "hola", "holi", "buenas", "buen dia", "buenos dias", "buenas tardes",
        "buenas noches", "hey", "que tal", "como estas",
    }
    cortesias = {"gracias", "muchas gracias", "ok", "dale", "listo", "genial"}
    if texto in saludos:
        return "¡Hola! Soy un asistente de **física mecánica** y análisis de videos de resortes. ¿Qué necesitás?"
    if texto in cortesias:
        return "¡De nada! Puedo ayudarte con **física mecánica** o con el análisis de tus videos."
    return None


def _es_respuesta_dato_chat(mensaje, paso):
    if paso == "regla":
        return _leer_longitud_chat(mensaje) is not None
    if paso == "k":
        return _leer_constante_chat(mensaje) is not None
    if paso in ("masa", "masa_resorte", "masa_resorte_k"):
        texto = _normalizar_texto_chat(mensaje).strip(" .,!¿?")
        return _leer_medida_chat(mensaje) is not None or texto in {
            "no la se", "la desconozco", "desconozco", "no tengo ese dato",
            "masa despreciable", "aproximar como despreciable",
        }
    return False


def _mensaje_fuera_de_alcance():
    return (
        "Puedo ayudar con **física mecánica** y el **análisis de videos de resortes**. "
        "Preguntame sobre movimiento, fuerzas, energía o tus resultados."
    )


def _analisis_vigente_chat(videos_actuales):
    """Devuelve solo resultados que coinciden con los datos visibles de la corrida."""
    analisis = st.session_state.get("ultimo_analisis")
    firma = analisis.get("firma") if analisis else None
    if not videos_actuales or not isinstance(firma, tuple) or len(firma) < 16:
        return None

    identidad_videos = tuple((video.file_id, video.name) for video in videos_actuales)
    puntos_tracking = tuple(
        (video.file_id, st.session_state.get(f"punto_tracking_{video.file_id}"))
        for video in videos_actuales
    )
    puntos_regla_guardados = st.session_state.get(
        f"puntos_regla_{videos_actuales[0].file_id}", []
    )
    puntos_regla = (
        tuple((punto["x"], punto["y"]) for punto in puntos_regla_guardados)
        if len(puntos_regla_guardados) == 2 else None
    )
    usar_sigma_elongacion = bool(st.session_state.get("usar_sigma_elongacion", False))
    firma_actual = (
        identidad_videos,
        st.session_state.get("metodo_tracking"),
        puntos_tracking,
        float(st.session_state.get("masa_analisis_g", 64.55)) / 1000.0,
        float(st.session_state.get("sigma_masa_analisis_g", 0.014)) / 1000.0,
        float(st.session_state.get("masa_resorte_analisis_g", 9.73)) / 1000.0,
        float(st.session_state.get("sigma_masa_resorte_analisis_g", 0.010)) / 1000.0,
        puntos_regla,
        float(st.session_state.get("longitud_regla", 0.300)),
        float(st.session_state.get("sigma_longitud_regla_m", 0.0005)),
        int(st.session_state.get("ventana_analisis", 11)),
        st.session_state.get("eje_analisis", "auto"),
        st.session_state.get("masas_estaticas_texto", ""),
        st.session_state.get("elongaciones_estaticas_texto", ""),
        usar_sigma_elongacion,
        (
            float(st.session_state.get("sigma_elongacion_m", 0.001))
            if usar_sigma_elongacion else None
        ),
    )
    return analisis if firma[:16] == firma_actual else None


def _es_consulta_resultado_chat(mensaje):
    texto = _normalizar_texto_chat(mensaje).strip(" ¿?¡!.,")
    if texto.startswith(("que es ", "como se calcula ", "como se define ", "por que ", "explicame ")):
        return False
    magnitudes = (
        "periodo", "frecuencia", "amortiguamiento", "constante elastica", "valor de k",
        "amplitud", "posicion", "velocidad", "aceleracion", "energia", "energia cinetica",
        "energia potencial", "energia total", "seguimiento", "tracking", "maximo",
        "trabajo", "disipacion", "disipativo",
    )
    pide_valor = any(palabra in texto for palabra in (
        "cuanto", "cuanta", "cual", "que valor", "resultado", "me dio", "dio ",
        "obtuvo", "tuvo", "fue", "salio", "mi analisis", "mi video", "la corrida", "repeticion",
    ))
    menciona_magnitud = (
        any(magnitud in texto for magnitud in magnitudes)
        or bool(re.search(r"\bk\b", texto))
        or bool(re.search(r"\bet\b", texto))
        or "δet" in texto
    )
    return menciona_magnitud and (pide_valor or "video" in texto or "corrida" in texto)


def responder_chat_resultados(mensaje, analisis):
    """Contesta con valores literales del JSON de la corrida actual, no de la bibliografía."""
    datos = analisis.get("resultados") or {}
    videos = datos.get("videos") or []
    texto = _normalizar_texto_chat(mensaje)
    if not videos:
        return "**Resultados de tu análisis**\nLa corrida actual no tiene resultados por video. Escribí «analizar» para generarlos."

    seleccionado = None
    numero_video = re.search(r"\bvideo\s*(\d+)\b", texto)
    if numero_video:
        indice = int(numero_video.group(1)) - 1
        if 0 <= indice < len(videos):
            seleccionado = [videos[indice]]
    if seleccionado is None:
        for video in videos:
            nombre = _normalizar_texto_chat(str(video.get("video", "")))
            if nombre and nombre in texto:
                seleccionado = [video]
                break
    if seleccionado is None:
        seleccionado = videos if len(videos) > 1 else [videos[0]]

    def medida(valor):
        if not isinstance(valor, dict) or "valor" not in valor:
            return "sin dato"
        salida = f"{valor['valor']:.5g}"
        if "incerteza" in valor:
            salida += f" ± {valor['incerteza']:.2g}"
        unidad = valor.get("unidad", "")
        return f"{salida} {unidad}".strip()

    respuestas = []
    for video in seleccionado:
        resultado = video.get("resultados") or {}
        estado = video.get("estado", "sin estado")
        if estado == "invalido":
            detalle = video.get("motivo") or "el ajuste no produjo valores confiables"
            respuestas.append(f"**{video.get('video', 'Video')} · Inválido:** {detalle}.")
            continue

        metricas = [
            ("periodo", "Período T"),
            ("frecuencia_angular", "Frecuencia angular ω"),
            ("amortiguamiento", "Amortiguamiento γ"),
            ("constante_elastica_con_masa_efectiva", "Constante elástica k"),
            ("amplitud", "Amplitud"),
        ]
        lineas = []
        if "periodo" in texto:
            metricas = [metricas[0]]
        elif "frecuencia" in texto or "omega" in texto or "ω" in mensaje:
            metricas = [metricas[1]]
        elif "amortiguamiento" in texto or "gamma" in texto or "γ" in mensaje:
            metricas = [metricas[2]]
        elif "constante elastica" in texto or re.search(r"\bk\b", texto):
            metricas = [metricas[3]]
        elif "amplitud" in texto:
            metricas = [metricas[4]]
        elif "energia" in texto or re.search(r"\bet\b", texto) or "δet" in texto:
            metricas = []
        elif "velocidad" in texto or "aceleracion" in texto or "maximo" in texto or "posicion" in texto:
            metricas = []

        for clave, etiqueta in metricas:
            if clave in resultado:
                lineas.append(f"- {etiqueta}: {medida(resultado[clave])}")

        maximos = resultado.get("maximos") or {}
        maxima_medida = []
        if "posicion" in texto or "maximo" in texto:
            maxima_medida.extend((clave, etiqueta) for clave, etiqueta in maximos.items()
                                 if "x_max" in clave or "posici" in clave)
        if "velocidad" in texto or "maximo" in texto:
            maxima_medida.extend((clave, etiqueta) for clave, etiqueta in maximos.items()
                                 if "v_max" in clave)
        if "aceleracion" in texto or "maximo" in texto:
            maxima_medida.extend((clave, etiqueta) for clave, etiqueta in maximos.items()
                                 if "a_max" in clave)
        for clave, etiqueta in maxima_medida:
            lineas.append(f"- {etiqueta}: {medida(maximos[clave])}")

        energia = resultado.get("energia") or {}
        consulta_trabajo = any(palabra in texto for palabra in ("trabajo", "disipacion", "disipativo"))
        if consulta_trabajo:
            delta = next((clave for clave in energia if "ΔEt" in clave), None)
            lineas.append(
                "- El informe no integra el trabajo explícitamente; informa el cambio de energía mecánica."
                + (f" ΔEt: {medida(energia[delta])}." if delta else "")
            )
        if "energia" in texto or re.search(r"\bet\b", texto) or "δet" in texto:
            terminos_energia = []
            if "cinetica" in texto:
                terminos_energia = [clave for clave in energia if "Ec_max" in clave]
            elif "potencial" in texto:
                terminos_energia = [clave for clave in energia if "Ep_max" in clave]
            elif "perdid" in texto or "disipad" in texto or "delta" in texto or "Δet" in mensaje.lower():
                terminos_energia = [clave for clave in energia if "ΔEt" in clave]
            elif "total" in texto or "mecanica" in texto or re.search(r"\bet\b", texto):
                terminos_energia = [clave for clave in energia if "Et " in clave or "ΔEt" in clave]
            else:
                terminos_energia = list(energia)
            lineas.extend(f"- {clave}: {medida(energia[clave])}" for clave in terminos_energia)

        alertas = video.get("alertas") or []
        if "seguimiento" in texto or "tracking" in texto:
            seguimiento = video.get("seguimiento") or {}
            lineas.append(
                f"- Seguimiento: {seguimiento.get('cuadros_detectados', '?')}/"
                f"{seguimiento.get('cuadros_totales', '?')} cuadros detectados; estado {estado}."
            )
        if alertas:
            lineas.append("- Alertas del informe: " + "; ".join(str(alerta) for alerta in alertas))
        if not lineas:
            lineas = [f"- Estado: {estado}"]
            lineas.extend(f"- {etiqueta}: {medida(resultado[clave])}" for clave, etiqueta in metricas if clave in resultado)
        respuestas.append(f"**{video.get('video', 'Video')} · {estado}:**\n" + "\n".join(lineas))
    return "**Resultados de tu análisis (datos del informe, no bibliografía)**\n\n" + "\n\n".join(respuestas)


def responder_chat_bibliografia(pregunta):
    try:
        from chatbot.generation import answer_question

        resultado = answer_question(pregunta, limit=8)
    except (ImportError, ModuleNotFoundError):
        return (
            "**Bibliografía de la cátedra**\nNo se pudieron cargar sus dependencias. "
            "Desde la carpeta `agente-resorte`, ejecutá "
            "`python -m pip install -r requirements-chatbot.txt`."
        )
    except FileNotFoundError:
        return (
            "**Bibliografía de la cátedra**\nEl índice bibliográfico local todavía no está preparado. "
            "Desde PowerShell, en `agente-resorte`, ejecutá el script `setup-chatbot.ps1` y asegurate "
            "de tener disponibles los PDF de la bibliografía."
        )
    except (RuntimeError, ValueError) as exc:
        return f"**Bibliografía de la cátedra**\nNo pude completar la consulta: {exc}"
    except Exception as exc:
        return f"**Bibliografía de la cátedra**\nFalló la consulta ({type(exc).__name__}): {exc}"

    estados = {
        "respaldada": "respuesta respaldada",
        "parcial": "respuesta parcial",
        "sin evidencia suficiente": "evidencia insuficiente",
    }
    partes = [
        f"**Bibliografía de la cátedra · {estados.get(resultado.get('status'), resultado.get('status'))}**",
        resultado.get("answer", "No se obtuvo una respuesta."),
    ]
    referencias = resultado.get("references", [])
    if referencias:
        partes.extend(["", "**Fuentes:**"])
        for referencia in referencias:
            documento = referencia.get("document") or referencia.get("source_path") or "Documento sin título"
            pagina = referencia.get("page")
            detalle_pagina = f"p. {pagina}" if pagina is not None else "página no indicada"
            partes.append(f"- [{referencia.get('id', '?')}] {documento}, {detalle_pagina}.")
    if resultado.get("generation_error") and resultado.get("references"):
        partes.extend([
            "",
            "No se pudo usar Ollama; se muestra únicamente una cita textual recuperada y verificada.",
        ])
    return "\n".join(partes)


def responder_chat_inicial(mensaje):
    texto = mensaje.strip().lower()
    videos_actuales = st.session_state.get("videos_experimento") or []
    firma_videos_chat = tuple(video.file_id for video in videos_actuales)
    if st.session_state.get("firma_masas_chat") != firma_videos_chat:
        st.session_state["firma_masas_chat"] = firma_videos_chat
        st.session_state["paso_datos_chat"] = None
        st.session_state["masas_confirmadas_chat"] = False
        st.session_state["longitud_confirmada_chat"] = False
        st.session_state["modo_datos_dinamica_chat"] = None
        st.session_state["k_dinamica_chat"] = None
        st.session_state.pop("masa_origen_chat", None)
        st.session_state.pop("k_dinamica_ingresada_chat", None)
        st.session_state.pop("masa_inferida_chat_g", None)
        st.session_state["masa_resorte_aproximada_chat"] = False

    firma_masa_inferida = st.session_state.get("firma_masa_inferida_chat")
    if (
        st.session_state.get("masa_origen_chat") == "inferida desde k dinámica medida"
        and firma_masa_inferida is not None
        and firma_masa_inferida != _firma_ajuste_chat(videos_actuales)
    ):
        st.session_state["masas_confirmadas_chat"] = False
        st.session_state["paso_datos_chat"] = None
        st.session_state["modo_datos_dinamica_chat"] = None
        st.session_state["k_dinamica_chat"] = None
        st.session_state.pop("masa_origen_chat", None)
        st.session_state.pop("k_dinamica_ingresada_chat", None)
        st.session_state.pop("masa_inferida_chat_g", None)

    firma_regla = None
    if videos_actuales:
        puntos_regla = st.session_state.get(
            f"puntos_regla_{videos_actuales[0].file_id}", []
        )
        firma_regla = (
            videos_actuales[0].file_id,
            tuple(
                (punto.get("x"), punto.get("y"))
                for punto in puntos_regla if isinstance(punto, dict)
            ),
        )
    firma_regla_confirmada = st.session_state.get("firma_regla_confirmada_chat")
    if firma_regla_confirmada is not None and firma_regla_confirmada != firma_regla:
        st.session_state["longitud_confirmada_chat"] = False
        if st.session_state.get("paso_datos_chat") in (
            "fuente_dinamica", "masa", "k", "masa_resorte", "masa_resorte_k"
        ):
            st.session_state["paso_datos_chat"] = None

    paso = st.session_state.get("paso_datos_chat")
    respuesta_social = _respuesta_social_chat(mensaje)
    if respuesta_social:
        return respuesta_social
    if paso and any(palabra in texto for palabra in ("cancel", "después", "despues")):
        st.session_state["paso_datos_chat"] = None
        return "Dejé el análisis en pausa. Cuando quieras continuar, escribí «analizar»."
    if (
        paso
        and not _es_consulta_fisica_chat(mensaje)
        and not _es_respuesta_dato_chat(mensaje, paso)
    ):
        return _mensaje_fuera_de_alcance()
    if _es_consulta_resultado_chat(mensaje):
        analisis_actual = _analisis_vigente_chat(videos_actuales)
        if analisis_actual is None:
            return (
                "**Resultados de tu análisis**\nNo encuentro una corrida vigente con los datos "
                "actuales. Escribí «analizar» para generar el informe y después preguntame por "
                "el período, la amplitud, k o las energías."
            )
        return responder_chat_resultados(mensaje, analisis_actual)

    if paso and _es_pregunta_bibliografica(mensaje):
        if _es_consulta_fisica_chat(mensaje):
            return responder_chat_bibliografia(mensaje)
        return _mensaje_fuera_de_alcance()

    if paso == "regla":
        medida_longitud = _leer_longitud_chat(mensaje)
        if medida_longitud is None:
            return "No pude leer la longitud. Indicá la distancia en m o cm; podés agregar su incertidumbre, por ejemplo: 30 ± 0,1 cm."
        longitud_m, sigma_longitud_m = medida_longitud
        if longitud_m <= 0 or (sigma_longitud_m is not None and sigma_longitud_m < 0):
            return "La longitud debe ser positiva y su incertidumbre no puede ser negativa."
        st.session_state["longitud_regla"] = longitud_m
        if sigma_longitud_m is not None:
            st.session_state["sigma_longitud_regla_m"] = sigma_longitud_m
        st.session_state["longitud_confirmada_chat"] = True
        st.session_state["firma_regla_confirmada_chat"] = firma_regla
        if st.session_state.get("masas_confirmadas_chat"):
            st.session_state["paso_datos_chat"] = None
            st.session_state["analisis_ocupado"] = True
            return "Anoté la longitud actualizada. Voy a regenerar el informe con la trayectoria guardada, sin volver a seguir el video."
        st.session_state["paso_datos_chat"] = "fuente_dinamica"
        ajuste = _resumen_ajuste_chat(st.session_state.get("diagnosticos_chat", []))
        incertidumbre = (
            f" (± {sigma_longitud_m:g} m)" if sigma_longitud_m is not None else ""
        )
        respuesta = f"Anoté **ℓ = {longitud_m:g} m{incertidumbre}**."
        if ajuste:
            respuesta += f"\n\n**Ajuste preliminar:**\n{ajuste}"
        respuesta += (
            "\n\n**Dato que falta:** masa colgante o una k medida independientemente. "
            "Respondé **masa** o **k**."
        )
        return respuesta

    if paso == "fuente_dinamica":
        if "masa" in texto and "resorte" not in texto:
            st.session_state["modo_datos_dinamica_chat"] = "masa"
            st.session_state["paso_datos_chat"] = "masa"
            return "Indicá la masa colgante en g o kg; podés agregar su incertidumbre. Ej.: **64,5 ± 0,1 g**."
        if re.search(r"\bk\b", texto) or "constante" in texto or "elastica" in texto or "elástica" in texto:
            st.session_state["modo_datos_dinamica_chat"] = "k"
            st.session_state["paso_datos_chat"] = "k"
            return "Indicá la constante medida en N/m con su incertidumbre. Ej.: **k = 12,4 ± 0,3 N/m**."
        return "Respondé **masa** o **k**, según el dato que tengas."

    if paso == "k":
        constante = _leer_constante_chat(mensaje)
        if constante is None or constante[0] <= 0 or constante[1] < 0:
            return "No pude leer k. Usá el formato **k = 12,4 ± 0,3 N/m**."
        st.session_state["k_dinamica_chat"] = constante
        st.session_state["paso_datos_chat"] = "masa_resorte_k"
        return "Anoté **k**. Indicá la masa del resorte en g o kg; si no la conocés, respondé **desconozco** y la aproximaré a cero."

    if paso in ("masa", "masa_resorte", "masa_resorte_k"):
        texto_normalizado = _normalizar_texto_chat(mensaje).strip(" .,!¿?")
        omitir_masa_resorte = (
            paso in ("masa_resorte", "masa_resorte_k")
            and texto_normalizado in {
                "no la se", "la desconozco", "desconozco", "no tengo ese dato",
                "masa despreciable", "aproximar como despreciable",
            }
        )
        medida = (0.0, 0.0) if omitir_masa_resorte else _leer_medida_chat(mensaje)
        if (
            medida is None or medida[0] < 0
            or (paso == "masa" and medida[0] == 0)
            or (medida[1] is not None and medida[1] < 0)
        ):
            nombre = "masa colgante" if paso == "masa" else "masa del resorte"
            return f"No pude leerlo. Indicá la **{nombre}** en g o kg (ej.: **9,7 ± 0,1 g**)."
        valor_g, sigma_g = medida
        if paso == "masa":
            st.session_state["masa_analisis_g"] = valor_g
            if sigma_g is not None:
                st.session_state["sigma_masa_analisis_g"] = sigma_g
            st.session_state["paso_datos_chat"] = "masa_resorte"
            return "Anoté la masa colgante. ¿Cuánto pesa el resorte? Podés responder **desconozco** si querés aproximarlo a cero."

        st.session_state["masa_resorte_analisis_g"] = valor_g
        if sigma_g is not None:
            st.session_state["sigma_masa_resorte_analisis_g"] = sigma_g
        st.session_state["masa_resorte_aproximada_chat"] = omitir_masa_resorte
        if paso == "masa_resorte_k":
            k_n_m, sigma_k = st.session_state["k_dinamica_chat"]
            sigma_resorte = (
                sigma_g if sigma_g is not None
                else st.session_state.get("sigma_masa_resorte_analisis_g", 0.010)
            )
            try:
                masa_inferida = _inferir_masa_colgante_chat(
                    k_n_m, sigma_k, valor_g, sigma_resorte,
                    st.session_state.get("diagnosticos_chat", []),
                )
            except ValueError as exc:
                return f"No puedo inferir una masa válida: {exc} Revisá k y las masas, o elegí ingresar la masa colgante."
            st.session_state["masa_analisis_g"] = masa_inferida.n * 1000.0
            st.session_state["sigma_masa_analisis_g"] = masa_inferida.s * 1000.0
            st.session_state["masa_inferida_chat_g"] = (
                masa_inferida.n * 1000.0, masa_inferida.s * 1000.0
            )
            st.session_state["masa_origen_chat"] = "inferida desde k dinámica medida"
            st.session_state["firma_masa_inferida_chat"] = _firma_ajuste_chat(videos_actuales)
            st.session_state["k_dinamica_ingresada_chat"] = {
                "valor": k_n_m, "incerteza": sigma_k, "unidad": "N/m"
            }
            resultado_masa = (
                f"Con k y los ajustes del video, la masa colgante estimada es "
                f"{masa_inferida.n * 1000:.4g} ± {masa_inferida.s * 1000:.2g} g. "
            )
        else:
            st.session_state["masa_origen_chat"] = "ingresada como medición"
            st.session_state.pop("k_dinamica_ingresada_chat", None)
            resultado_masa = ""
        st.session_state["paso_datos_chat"] = None
        st.session_state["masas_confirmadas_chat"] = True
        st.session_state["analisis_ocupado"] = True
        if omitir_masa_resorte:
            resultado_masa += (
                "Tomé la masa del resorte como cero (aproximación). "
            )
        return resultado_masa + "Listo, genero el informe con las trayectorias guardadas."

    if not _es_pedido_analisis(mensaje):
        if _es_consulta_fisica_chat(mensaje):
            return responder_chat_bibliografia(mensaje)
        return _mensaje_fuera_de_alcance()

    pendientes = _estado_preparacion_chat(videos_actuales)
    vista_tracking = _vista_tracking_actual(videos_actuales)
    if pendientes:
        explicacion = _explicar_datos_derivables(vista_tracking)
        faltantes = "\n".join(f"- {pendiente.capitalize()}" for pendiente in pendientes)
        return f"{explicacion}\n\n**Antes de seguir:**\n{faltantes}\nDespués, escribí **analizar**."

    diagnosticos, errores_tracking = _obtener_diagnosticos_chat(videos_actuales)
    if errores_tracking:
        return "No pude obtener la trayectoria de todos los videos: " + "; ".join(errores_tracking) + ". Corregí esos puntos o el método de seguimiento y volvé a escribir «analizar»."
    explicacion = _explicar_datos_derivables(vista_tracking, diagnosticos)

    if not st.session_state.get("longitud_confirmada_chat"):
        st.session_state["paso_datos_chat"] = "regla"
        return (
            explicacion
            + "\n\n**Me falta la longitud real de la regla.** ¿Cuánto mide entre las marcas? "
            "Ej.: **30 cm**."
        )

    if not st.session_state.get("masas_confirmadas_chat"):
        st.session_state["paso_datos_chat"] = "fuente_dinamica"
        return (
            explicacion
            + "\n\n**Para calcular dinámica y energía**, necesito la masa colgante "
            "o una k medida. ¿Cuál tenés: **masa** o **k**?"
        )

    st.session_state["analisis_ocupado"] = True
    return "Los datos requeridos están cargados. Voy a generar el informe; cada video se seguirá una sola vez y se reutilizará cualquier trayectoria ya guardada."


if not st.session_state.get("interfaz_cargada", False):
    skeleton_interfaz = st.empty()
    with skeleton_interfaz.container():
        st.markdown(
            """
            <style>
            .resorte-skeleton-screen {
                position: fixed;
                inset: 0;
                z-index: 999999;
                display: flex;
                justify-content: center;
                overflow-y: auto;
                padding: 2rem;
                background: var(--background-color);
            }
            .resorte-skeleton-layout {
                display: grid !important;
                grid-template-columns: minmax(220px, 1fr) minmax(0, 3fr) !important;
                gap: 2rem;
                width: 100%;
                max-width: 1800px;
                margin: auto;
                align-items: start;
            }
            .resorte-skeleton-panel {
                min-width: 0;
                width: 100%;
                text-align: left;
            }
            .resorte-skeleton-block,
            .resorte-skeleton-box,
            .resorte-skeleton-input {
                background: var(--secondary-background-color);
                border: 1px solid var(--border-color);
                border-radius: 0.55rem;
                animation: resorte-pulse 1.25s ease-in-out infinite alternate;
            }
            .resorte-skeleton-block { height: 0.9rem; margin: 0.8rem 0; }
            .resorte-skeleton-block.title { height: 1.45rem; width: 72%; }
            .resorte-skeleton-block.section-title { height: 1.15rem; width: 42%; margin-top: 1.5rem; }
            .resorte-skeleton-block.short { width: 48%; }
            .resorte-skeleton-box { box-sizing: border-box; width: 100%; padding: 1rem; }
            .resorte-skeleton-history { height: min(560px, 62vh); }
            .resorte-skeleton-bubble { height: 3.3rem; margin: 0.8rem 0; border-radius: 0.8rem; }
            .resorte-skeleton-bubble.short { width: 72%; }
            .resorte-skeleton-input { height: 2.7rem; margin-top: 0.9rem; }
            .resorte-skeleton-upload { height: 5rem; }
            .resorte-skeleton-preview { height: min(22rem, 38vh); margin: 0.8rem 0; }
            .resorte-skeleton-control { height: 3rem; margin: 0.5rem 0; }
            .resorte-skeleton-input-row {
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 0.8rem;
            }
            .resorte-skeleton-input-row .resorte-skeleton-input { margin-top: 0; }
            .resorte-skeleton-button { width: 11rem; height: 2.8rem; margin: 1rem 0; }
            @keyframes resorte-pulse {
                from { opacity: 0.42; }
                to { opacity: 0.9; }
            }
            @media (max-width: 700px) {
                .resorte-skeleton-layout { grid-template-columns: 1fr !important; gap: 1rem; }
                .resorte-skeleton-screen { padding: 1rem; }
                .resorte-skeleton-history { height: 10rem; }
                .resorte-skeleton-input-row { grid-template-columns: 1fr; }
            }
            @media (prefers-reduced-motion: reduce) {
                .resorte-skeleton-block,
                .resorte-skeleton-box,
                .resorte-skeleton-input { animation: none; opacity: 0.65; }
            }
            </style>
            <div class="resorte-skeleton-screen" aria-hidden="true">
              <div class="resorte-skeleton-layout">
                <section class="resorte-skeleton-panel">
                  <div class="resorte-skeleton-block title"></div>
                  <div class="resorte-skeleton-block short"></div>
                  <div class="resorte-skeleton-box resorte-skeleton-history">
                    <div class="resorte-skeleton-bubble short resorte-skeleton-box"></div>
                    <div class="resorte-skeleton-bubble resorte-skeleton-box"></div>
                    <div class="resorte-skeleton-bubble short resorte-skeleton-box"></div>
                  </div>
                  <div class="resorte-skeleton-input"></div>
                </section>
                <section class="resorte-skeleton-panel">
                  <div class="resorte-skeleton-block title"></div>
                  <div class="resorte-skeleton-block short"></div>
                  <div class="resorte-skeleton-box resorte-skeleton-upload"></div>
                  <div class="resorte-skeleton-block section-title"></div>
                  <div class="resorte-skeleton-block short"></div>
                  <div class="resorte-skeleton-box resorte-skeleton-preview"></div>
                  <div class="resorte-skeleton-box resorte-skeleton-control"></div>
                  <div class="resorte-skeleton-block section-title"></div>
                  <div class="resorte-skeleton-control"></div>
                  <div class="resorte-skeleton-box resorte-skeleton-preview"></div>
                  <div class="resorte-skeleton-block section-title"></div>
                  <div class="resorte-skeleton-input-row">
                    <div class="resorte-skeleton-input"></div>
                    <div class="resorte-skeleton-input"></div>
                    <div class="resorte-skeleton-input"></div>
                  </div>
                  <div class="resorte-skeleton-box resorte-skeleton-control"></div>
                  <div class="resorte-skeleton-button resorte-skeleton-input"></div>
                </section>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

chat_col, analizador_col = st.columns([1, 3], gap="large")
with chat_col:
    st.subheader("Chat del análisis")
    st.caption("Física mecánica y análisis de tus videos")
    bienvenida_chat = (
        "Hola. Podés preguntarme sobre física mecánica o pedirme que analice tus videos. "
        "Para empezar, subí los videos, marcá la regla y el punto de seguimiento, "
        "y escribí «analizar»."
    )
    st.session_state.setdefault(
        "conversacion_analisis",
        [{
            "role": "assistant",
            "content": bienvenida_chat,
        }],
    )
    if st.session_state.conversacion_analisis and st.session_state.conversacion_analisis[0].get("role") == "assistant":
        st.session_state.conversacion_analisis[0]["content"] = bienvenida_chat
    historial_chat = st.container(height=560, border=True)
    with historial_chat:
        for mensaje in st.session_state.conversacion_analisis:
            with st.chat_message(mensaje["role"]):
                st.write(mensaje["content"])

    entrada_chat = st.chat_input(
        "Escribí tu mensaje",
        key="entrada_chat_analisis",
    )
    if entrada_chat:
        st.session_state.conversacion_analisis.append(
            {"role": "user", "content": entrada_chat}
        )
        with historial_chat:
            with st.chat_message("user"):
                st.write(entrada_chat)
            with st.chat_message("assistant"):
                with st.spinner("Buscando respuesta…"):
                    respuesta = responder_chat_inicial(entrada_chat)
                st.write(respuesta)
        st.session_state.conversacion_analisis.append(
            {"role": "assistant", "content": respuesta}
        )
        st.rerun()

with analizador_col:
    st.title("Análisis de movimiento de un resorte")
    st.write(
        "Subí uno o varios videos del experimento y completá los datos para generar "
        "el informe. Los videos se procesan en una carpeta temporal y no se guardan "
        "en el repositorio."
    )

    if "analisis_ocupado" not in st.session_state:
        st.session_state.analisis_ocupado = False
    st.markdown(
        """
        <style>
        .block-container { max-width: 1800px !important; padding-left: 2rem; padding-right: 2rem; }
        div[data-testid="stNumberInput"] { max-width: 170px !important; }
        div[data-testid="stSelectbox"] { max-width: 230px !important; }
        div[data-testid="stTextInput"] { max-width: 320px !important; }
        /* Elimina el espacio muerto donde se perdia el foco del textarea. */
        .st-key-entrada_chat_analisis div:has(> div > textarea) { column-gap: 0; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    def leer_lista(texto, nombre):
        if not texto.strip():
            return None
        try:
            return [float(valor.strip()) for valor in texto.split(",") if valor.strip()]
        except ValueError as exc:
            raise ValueError(f"{nombre}: ingresá números separados por comas.") from exc


    METODO_PUNTO = "Punto marcado · flujo óptico"
    METODO_MOG2 = "MOG2 · detección de movimiento"


    @st.cache_data(show_spinner=False)
    def primer_cuadro_video(contenido, nombre):
        """Decodifica una sola vez el cuadro de vista previa por archivo subido."""
        with tempfile.TemporaryDirectory(prefix="resorte-vista-") as temp_dir:
            ruta = Path(temp_dir) / Path(nombre).name
            ruta.write_bytes(contenido)
            captura = cv2.VideoCapture(str(ruta))
            ok, cuadro = captura.read()
            captura.release()
            if not ok:
                return None, None
            alto, ancho = cuadro.shape[:2]
            return cv2.cvtColor(cuadro, cv2.COLOR_BGR2RGB), (ancho, alto)


    @st.cache_data(show_spinner=False)
    def cuadro_video_en_t(contenido, nombre, instante_s):
        with tempfile.TemporaryDirectory(prefix="resorte-vista-t-") as temp_dir:
            ruta = Path(temp_dir) / Path(nombre).name
            ruta.write_bytes(contenido)
            captura = cv2.VideoCapture(str(ruta))
            captura.set(cv2.CAP_PROP_POS_MSEC, max(0.0, float(instante_s)) * 1000)
            ok, cuadro = captura.read()
            ancho = int(captura.get(cv2.CAP_PROP_FRAME_WIDTH))
            alto = int(captura.get(cv2.CAP_PROP_FRAME_HEIGHT))
            captura.release()
            if not ok:
                return None, None
            return cv2.cvtColor(cuadro, cv2.COLOR_BGR2RGB), (ancho, alto)


    def crear_video_tracking(contenido, nombre, punto_inicial, progreso=None, desde_s=0.0):
        """Genera una previsualización mp4 del seguimiento elegido."""
        with tempfile.TemporaryDirectory(prefix="resorte-tracking-") as temp_dir:
            ruta_video = Path(temp_dir) / Path(nombre).name
            ruta_salida = Path(temp_dir) / "tracking.mp4"
            ruta_video.write_bytes(contenido)

            captura = cv2.VideoCapture(str(ruta_video))
            fps = captura.get(cv2.CAP_PROP_FPS)
            ancho = int(captura.get(cv2.CAP_PROP_FRAME_WIDTH))
            alto = int(captura.get(cv2.CAP_PROP_FRAME_HEIGHT))
            captura.release()
            if fps <= 0 or ancho <= 0 or alto <= 0:
                raise RuntimeError("No se pudieron leer los datos del video para previsualizar el tracking.")

            escritor = cv2.VideoWriter(
                str(ruta_salida),
                cv2.VideoWriter_fourcc(*"avc1"),
                fps,
                (ancho, alto),
            )
            if not escritor.isOpened():
                escritor.release()
                raise RuntimeError("No se pudo crear el video de previsualización del tracking.")
            try:
                tabla = trackear(
                    str(ruta_video),
                    str(Path(temp_dir) / "tracking.csv"),
                    progreso=progreso,
                    frame_callback=escritor.write,
                    punto_inicial=punto_inicial,
                    desde_s=desde_s,
                )
            finally:
                escritor.release()

            if not ruta_salida.is_file() or ruta_salida.stat().st_size == 0:
                raise RuntimeError("El video de previsualización del tracking quedó vacío.")
            verificador = cv2.VideoCapture(str(ruta_salida))
            video_valido, _ = verificador.read()
            verificador.release()
            if not video_valido:
                raise RuntimeError("No se pudo verificar el video de previsualización del tracking.")
            preanalisis = {
                "filas": np.asarray(tabla).copy(),
                "seguimiento": dict(tabla.resumen),
                "metadatos": dict(getattr(tabla, "metadatos", {})),
                "nombre": Path(nombre).stem,
                "video": str(ruta_video),
            }
            return ruta_salida.read_bytes(), preanalisis


    videos = st.file_uploader(
        "Videos del experimento",
        type=["mp4", "avi", "mov", "mkv"],
        accept_multiple_files=True,
        key="videos_experimento",
        help="Subí uno o varios videos del mismo setup/cámara. Si subís varias repeticiones se van a agregar automáticamente.",
    )

    frame_size = None
    punto_tracking = None
    puntos_regla = []
    metodo_tracking = None
    usar_punto_tracking = False
    if videos:
        frame_preview, frame_size = primer_cuadro_video(videos[0].getvalue(), videos[0].name)
        if frame_preview is None:
            st.error("No se pudo leer el primer cuadro del video para mostrar la regla.")
        else:
            st.caption(f"Cuadro de referencia ({frame_size[0]} × {frame_size[1]} px)")
            st.caption(
                "Calibración: hacé clic en dos marcas de la regla cuya distancia real "
                "conozcas. Un tercer clic empieza de nuevo."
            )
            ok, imagen_regla = cv2.imencode(
                ".jpg", cv2.cvtColor(frame_preview, cv2.COLOR_RGB2BGR)
            )
            if not ok:
                raise RuntimeError("No se pudo preparar el cuadro para calibrar la regla.")
            imagen_regla_data = "data:image/jpeg;base64," + base64.b64encode(
                imagen_regla.tobytes()
            ).decode("ascii")
            clave_puntos_regla = f"puntos_regla_{videos[0].file_id}"
            clave_expandir_regla = f"expandir_selector_regla_{videos[0].file_id}"
            st.session_state.setdefault(clave_expandir_regla, False)
            with st.container(horizontal=True, horizontal_alignment="left"):
                st.button(
                    ":material/close_fullscreen:"
                    if st.session_state[clave_expandir_regla]
                    else ":material/open_in_full:",
                    key=f"boton_{clave_expandir_regla}",
                    help="Volver al tamaño normal"
                    if st.session_state[clave_expandir_regla]
                    else "Ampliar selector",
                    on_click=alternar_ampliacion_selector,
                    args=(clave_expandir_regla,),
                )
            expandir_regla = st.session_state[clave_expandir_regla]
            seleccion_regla = seleccionar_punto_tracking(
                image_data=imagen_regla_data,
                image_width=frame_size[0],
                image_height=frame_size[1],
                selection_mode="two_points",
                selected_points=st.session_state.get(clave_puntos_regla, []),
                selected_point=None,
                display_width="100%" if expandir_regla else 760,
                key=f"selector_regla_{videos[0].file_id}",
            )
            if isinstance(seleccion_regla, list) and len(seleccion_regla) <= 2:
                if all(
                    isinstance(punto, dict)
                    and isinstance(punto.get("x"), int)
                    and isinstance(punto.get("y"), int)
                    and 0 <= punto["x"] < frame_size[0]
                    and 0 <= punto["y"] < frame_size[1]
                    for punto in seleccion_regla
                ):
                    st.session_state[clave_puntos_regla] = seleccion_regla
            puntos_regla = st.session_state.get(clave_puntos_regla, [])
            if len(puntos_regla) == 1:
                st.info(
                    f"Extremo 1 seleccionado: ({puntos_regla[0]['x']}, "
                    f"{puntos_regla[0]['y']}) px. Ahora marcá el otro extremo."
                )
            elif len(puntos_regla) == 2:
                st.success(
                    f"Extremos seleccionados: ({puntos_regla[0]['x']}, {puntos_regla[0]['y']}) "
                    f"y ({puntos_regla[1]['x']}, {puntos_regla[1]['y']}) px."
                )

    sin_punto_propio = []
    if videos:
        firma_videos = tuple((video.file_id, video.name) for video in videos)
        metodo_tracking = st.segmented_control(
            "Método de seguimiento",
            options=[METODO_PUNTO, METODO_MOG2],
            default=METODO_PUNTO,
            required=True,
            key="metodo_tracking",
            help="El punto marcado sigue rasgos alrededor del clic. MOG2 detecta movimiento en el cuadro completo.",
        )
        usar_punto_tracking = metodo_tracking == METODO_PUNTO
        algoritmo_tracking = (
            "punto-inicial-flujo-optico-v6-desde" if usar_punto_tracking else "mog2-v1"
        )
        col_video, col_boton = st.columns([3, 1])
        indice_tracking = col_video.selectbox(
            "Video para revisar",
            options=range(len(videos)),
            format_func=lambda indice: videos[indice].name,
            key="indice_video_tracking",
        )
        video_seleccionado = videos[indice_tracking]
        clave_t_punto = f"instante_punto_{video_seleccionado.file_id}"
        clave_punto = f"punto_tracking_{video_seleccionado.file_id}"
        instante_punto = st.number_input("Instante del clic (s)", min_value=0.0, value=0.0,
                                         step=0.1, key=clave_t_punto,
                                         on_change=lambda k=clave_punto: st.session_state.pop(k, None))
        cuadro_tracking, tamano_tracking = cuadro_video_en_t(
            video_seleccionado.getvalue(), video_seleccionado.name, instante_punto
        )
        if cuadro_tracking is None or tamano_tracking is None:
            st.error(f"No se pudo leer el cuadro de t={instante_punto:g} s para preparar el seguimiento.")
        elif usar_punto_tracking:
            st.caption(
                f"Hacé clic en el punto exacto de la masa en el cuadro de t = {instante_punto:g} s. "
                "El seguimiento arranca en ese píxel y continúa por flujo óptico, sin buscar el color rojo."
            )
            ok, imagen_jpeg = cv2.imencode(
                ".jpg", cv2.cvtColor(cuadro_tracking, cv2.COLOR_RGB2BGR)
            )
            if not ok:
                raise RuntimeError("No se pudo preparar el cuadro para seleccionar el punto de tracking.")
            imagen_data = "data:image/jpeg;base64," + base64.b64encode(
                imagen_jpeg.tobytes()
            ).decode("ascii")
            clave_expandir_punto = f"expandir_selector_punto_{video_seleccionado.file_id}"
            st.session_state.setdefault(clave_expandir_punto, False)
            with st.container(horizontal=True, horizontal_alignment="left"):
                st.button(
                    ":material/close_fullscreen:"
                    if st.session_state[clave_expandir_punto]
                    else ":material/open_in_full:",
                    key=f"boton_{clave_expandir_punto}",
                    help="Volver al tamaño normal"
                    if st.session_state[clave_expandir_punto]
                    else "Ampliar selector",
                    on_click=alternar_ampliacion_selector,
                    args=(clave_expandir_punto,),
                )
            expandir_punto = st.session_state[clave_expandir_punto]
            punto_seleccionado = seleccionar_punto_tracking(
                image_data=imagen_data,
                image_width=tamano_tracking[0],
                image_height=tamano_tracking[1],
                selected_point=st.session_state.get(clave_punto),
                display_width="100%" if expandir_punto else 760,
                default=None,
                key=f"selector_{video_seleccionado.file_id}",
            )
            if isinstance(punto_seleccionado, dict):
                try:
                    x = int(punto_seleccionado["x"])
                    y = int(punto_seleccionado["y"])
                except (KeyError, TypeError, ValueError):
                    st.session_state.pop(clave_punto, None)
                else:
                    if 0 <= x < tamano_tracking[0] and 0 <= y < tamano_tracking[1]:
                        st.session_state[clave_punto] = {"x": x, "y": y}
            punto_guardado = st.session_state.get(clave_punto)
            if isinstance(punto_guardado, dict):
                punto_tracking = (punto_guardado["x"], punto_guardado["y"])
            if punto_tracking is not None:
                st.success(
                    f"Punto inicial seleccionado: ({punto_tracking[0]}, {punto_tracking[1]}) px. "
                    "Podés volver a hacer clic para cambiarlo."
                )
            else:
                st.info("Seleccioná el punto inicial de la masa para habilitar el tracking.")
        else:
            st.caption(
                "MOG2 detecta las regiones que se mueven en el cuadro completo. "
                "No hace falta marcar la masa."
            )

        if usar_punto_tracking:
            sin_punto_propio = [
                f"{video.name} (t={float(st.session_state.get('instante_punto_' + video.file_id, 0.0)):g} s)"
                for video in videos
                if not isinstance(st.session_state.get(f"punto_tracking_{video.file_id}"), dict)
            ]
            if sin_punto_propio:
                st.warning(
                    "Falta marcar la masa en el instante elegido de: "
                    + ", ".join(sin_punto_propio)
                    + ". Cada video debe tener su propio punto; no se reutiliza el punto de otro video."
                )

        if col_boton.button(
            "Ver seguimiento",
            type="secondary",
            disabled=usar_punto_tracking and punto_tracking is None,
        ):
            barra_tracking = st.progress(0, text="Preparando la vista del tracking…")

            def actualizar_progreso_tracking(actual, total):
                if total:
                    porcentaje = min(int(100 * actual / total), 99)
                    barra_tracking.progress(
                        porcentaje,
                        text=f"Procesando cuadro {actual:,} de {total:,} ({porcentaje}%)",
                    )
                else:
                    barra_tracking.progress(
                        0, text=f"Procesando cuadro {actual:,}… (duración no informada)"
                    )

            try:
                with st.spinner("Siguiendo la masa y preparando la vista…"):
                    video_tracking, preanalisis_tracking = crear_video_tracking(
                        video_seleccionado.getvalue(),
                        video_seleccionado.name,
                        punto_inicial=(punto_tracking if usar_punto_tracking else None),
                        progreso=actualizar_progreso_tracking,
                        desde_s=instante_punto,
                    )
                st.session_state["vista_tracking"] = {
                    "firma": firma_videos,
                    "indice": indice_tracking,
                    "formato": "mp4",
                    "algoritmo": algoritmo_tracking,
                    "metodo_tracking": metodo_tracking,
                    "punto_inicial": punto_tracking if usar_punto_tracking else None,
                    "instante_punto_s": float(instante_punto),
                    "video": video_tracking,
                    "resumen": preanalisis_tracking["seguimiento"],
                    "preanalisis": preanalisis_tracking,
                }
                barra_tracking.progress(100, text="Vista de tracking lista")
            except Exception as exc:
                barra_tracking.empty()
                st.error(f"No se pudo generar la vista de tracking: {type(exc).__name__}: {exc}")

        vista_tracking = st.session_state.get("vista_tracking")
        if (
            vista_tracking
            and vista_tracking["firma"] == firma_videos
            and vista_tracking["indice"] == indice_tracking
            and vista_tracking.get("algoritmo") == algoritmo_tracking
            and vista_tracking.get("metodo_tracking") == metodo_tracking
            and vista_tracking.get("punto_inicial") == (punto_tracking if usar_punto_tracking else None)
            and vista_tracking.get("instante_punto_s", 0.0) == float(instante_punto)
        ):
            resumen = vista_tracking["resumen"]
            if vista_tracking.get("video"):
                st.video(vista_tracking["video"], format="video/mp4")
            else:
                st.info(
                    "El seguimiento se calculó, pero este equipo no pudo codificar el video "
                    "de vista previa. El análisis puede continuar con los datos guardados."
                )
            st.caption(
                f"Método: {metodo_tracking} · "
                f"Detecciones: {resumen['detectados']}/{resumen['cuadros']} cuadros · "
                f"Sin detección: {resumen['perdidos']} · "
                f"Saltos descartados: {resumen['saltos_descartados']}. "
                "El círculo verde marca la posición seguida; rojo indica un cuadro perdido."
            )
            if resumen["cuadros"] and resumen["perdidos"] / resumen["cuadros"] > 0.05:
                st.warning(
                    "Se perdió más del 5 % del seguimiento. Revisá el método elegido, "
                    "la visibilidad de la masa y posibles oclusiones."
                )

    st.subheader("Datos del experimento")
    c_masa, c_sigma, c_resorte, c_sigma_resorte, _ = st.columns([1.1, 1.1, 1.1, 1.1, 2.5])
    masa_g = c_masa.number_input(
        "Masa colgante (g)", min_value=0.001, value=64.55, step=0.01, format="%.3f",
        key="masa_analisis_g",
        help="Masa total que cuelga del resorte, incluido el portapesas, en gramos.",
    )
    sigma_masa_g = c_sigma.number_input(
        "Incerteza de masa (g)", min_value=0.0, value=0.014, step=0.001, format="%.3f",
        key="sigma_masa_analisis_g",
        help="Incerteza de la masa colgante en gramos, según la balanza o la medición usada.",
    )
    masa_resorte_g = c_resorte.number_input(
        "Masa del resorte (g)", min_value=0.0, value=9.73, step=0.01, format="%.3f",
        key="masa_resorte_analisis_g",
        help="Masa del resorte en gramos. Se considera con factor 1/3 en la masa efectiva.",
    )
    sigma_masa_resorte_g = c_sigma_resorte.number_input(
        "Incerteza del resorte (g)", min_value=0.0, value=0.010, step=0.001, format="%.3f",
        key="sigma_masa_resorte_analisis_g",
        help="Incerteza de la masa del resorte en gramos, según la balanza o la medición usada.",
    )
    masa = masa_g / 1000.0
    sigma_masa = sigma_masa_g / 1000.0
    masa_resorte = masa_resorte_g / 1000.0
    sigma_masa_resorte = sigma_masa_resorte_g / 1000.0
    st.caption(
        f"Masa colgante: {masa_g:.3f} g = {masa:.6f} kg · "
        f"Resorte: {masa_resorte_g:.3f} g = {masa_resorte:.6f} kg"
    )

    with st.form("parametros_analisis"):
        with st.container(border=True):
            st.markdown("**Calibración con regla**")
            puntos = None
            if frame_size:
                c_largo, c_ventana, c_eje, _ = st.columns(
                    [1.2, 1.4, 1.0, 4], vertical_alignment="bottom"
                )
                regla_m = c_largo.number_input(
                    "Longitud (m)", min_value=0.000001, value=0.300, step=0.010,
                    key="longitud_regla",
                    help="Distancia real, en metros, entre las dos marcas que seleccionaste en el cuadro.",
                )
                sigma_regla_m = c_largo.number_input(
                    "Incerteza longitud (m)", min_value=0.0, value=0.0005, step=0.0001,
                    format="%.4f", key="sigma_longitud_regla_m",
                    help="Incerteza de la distancia real ingresada. También podés indicarla en el chat, por ejemplo: 30 ± 0,1 cm.",
                )
                ventana = c_ventana.selectbox(
                    "Ventana (cuadros)", [7, 11, 21, 41], index=1,
                    key="ventana_analisis",
                    help="Cantidad de cuadros que se usan para suavizar la posición, velocidad y aceleración. Valores grandes suavizan más, pero pueden borrar detalles.",
                )
                eje = c_eje.selectbox(
                    "Eje", ["auto", "x", "y"], index=0, key="eje_analisis",
                    help="Eje de oscilación. Auto usa el de mayor desvío; elegí x o y si el movimiento es conocido.",
                )
                puntos = (
                    tuple((punto["x"], punto["y"]) for punto in puntos_regla)
                    if len(puntos_regla) == 2
                    else None
                )
                if puntos is None:
                    st.info("Marcá los dos extremos de la regla en el cuadro de referencia.")
            else:
                c_largo, c_ventana, c_eje, _ = st.columns(
                    [1.2, 1.4, 1.0, 4], vertical_alignment="bottom"
                )
                regla_m = c_largo.number_input(
                    "Longitud (m)", min_value=0.000001, value=0.300, step=0.010,
                    key="longitud_regla",
                )
                sigma_regla_m = c_largo.number_input(
                    "Incerteza longitud (m)", min_value=0.0, value=0.0005, step=0.0001,
                    format="%.4f", key="sigma_longitud_regla_m",
                    help="Incerteza de la distancia real ingresada. También podés indicarla en el chat, por ejemplo: 30 ± 0,1 cm.",
                )
                ventana = c_ventana.selectbox(
                    "Ventana (cuadros)", [7, 11, 21, 41], index=1,
                    key="ventana_analisis",
                    help="Ventana de Savitzky-Golay para filtrar posición, velocidad y aceleración.",
                )
                eje = c_eje.selectbox(
                    "Eje", ["auto", "x", "y"], index=0, key="eje_analisis",
                    help="Eje de oscilación. Auto usa el de mayor desvío.",
                )
        with st.expander("Chequeo estático opcional"):
            st.caption("Opcional. Solo sirve para calcular k por F = kx. NO es necesario para obtener k dinámico con el ajuste x(t).")
            masas_texto = st.text_input(
                "Masas estáticas (kg, separadas por comas)", key="masas_estaticas_texto"
            )
            elongaciones_texto = st.text_input(
                "Elongaciones (m, separadas por comas)", key="elongaciones_estaticas_texto"
            )
            usar_sigma_elongacion = st.checkbox(
                "Indicar incerteza de elongación", key="usar_sigma_elongacion"
            )
            sigma_elongacion = st.number_input(
                "Incerteza de cada elongación (m)",
                min_value=0.0,
                value=0.001,
                step=0.001,
                key="sigma_elongacion_m",
                disabled=not usar_sigma_elongacion,
                help="Incerteza de cada elongación medida, por ejemplo la resolución de la regla. Se usa para calcular la incerteza de la constante elástica estática.",
            )

        ejecutar = st.form_submit_button(
            "Analizando…" if st.session_state.analisis_ocupado else "Analizar videos",
            type="secondary" if st.session_state.analisis_ocupado else "primary",
            disabled=(
                not videos
                or len(puntos_regla) != 2
                or (usar_punto_tracking and (punto_tracking is None or bool(sin_punto_propio)))
                or st.session_state.analisis_ocupado
            ),
            key="boton_analizar_videos",
        )

    firma = (
        tuple((video.file_id, video.name) for video in videos) if videos else (),
        metodo_tracking if videos else None,
        tuple(
            (video.file_id, st.session_state.get(f"punto_tracking_{video.file_id}"))
            for video in videos
        ) if videos else (),
        masa,
        sigma_masa,
        masa_resorte,
        sigma_masa_resorte,
        puntos,
        regla_m,
        sigma_regla_m,
        ventana,
        eje,
        masas_texto,
        elongaciones_texto,
        usar_sigma_elongacion,
        sigma_elongacion if usar_sigma_elongacion else None,
        punto_tracking if usar_punto_tracking and sin_punto_propio else None,
    )

    if ejecutar and not st.session_state.analisis_ocupado:
        st.session_state.analisis_ocupado = True
        st.session_state.pop("error_analisis", None)
        st.rerun()

    if st.session_state.analisis_ocupado:
        if not videos:
            st.session_state["error_analisis"] = "Cargá al menos un video."
        elif usar_punto_tracking and punto_tracking is None:
            st.session_state["error_analisis"] = "Hacé clic en el punto de la masa antes de analizar."
        elif not frame_size or puntos is None:
            st.session_state["error_analisis"] = "No se pudo leer el primer cuadro para calibrar la regla. Revisá el video."
        else:
            try:
                if puntos[0] == puntos[1]:
                    raise ValueError("Los dos extremos de la regla deben ser puntos distintos.")
                escala = escala_px_por_m(
                    puntos[0], puntos[1], regla_m,
                    sigma_largo_m=sigma_regla_m,
                )
                if escala[0] <= 0:
                    raise ValueError("La escala debe ser mayor que cero.")

                masas_estaticas = leer_lista(masas_texto, "Masas estáticas")
                elongaciones = leer_lista(elongaciones_texto, "Elongaciones")
                if bool(masas_estaticas) != bool(elongaciones):
                    raise ValueError("Para el chequeo estático, completá tanto las masas como las elongaciones.")
                if masas_estaticas and (
                    len(masas_estaticas) != len(elongaciones) or len(masas_estaticas) < 3
                ):
                    raise ValueError("El chequeo estático requiere la misma cantidad de datos y al menos 3 puntos.")

                masa_origen = st.session_state.get("masa_origen_chat")
                k_dinamica_ingresada = st.session_state.get("k_dinamica_ingresada_chat")
                masa_inferida_chat = st.session_state.get("masa_inferida_chat_g")
                if k_dinamica_ingresada and masa_inferida_chat:
                    coincide_masa = np.isclose(masa_g, masa_inferida_chat[0]) and np.isclose(
                        sigma_masa_g, masa_inferida_chat[1]
                    )
                    if not coincide_masa:
                        masa_origen = "ingresada como medición"
                        k_dinamica_ingresada = None

                args = SimpleNamespace(
                    masa=masa,
                    sigma_masa=sigma_masa,
                    masa_origen=masa_origen,
                    k_dinamica_ingresada=k_dinamica_ingresada,
                    masa_resorte=masa_resorte,
                    sigma_masa_resorte=sigma_masa_resorte,
                    fps_led=None,
                    fps_sigma=0.0,
                    f_led=None,
                    fps_real=None,
                    ventana=ventana,
                    eje=eje,
                    inicio=None,
                    fin=None,
                    recorte_auto=True,
                    ventana_inicio=0.5,
                    umbral_inicio=0.15,
                    sigma_g=0.01,
                    sigma_elongacion=sigma_elongacion if usar_sigma_elongacion else None,
                    masas_estaticas=masas_estaticas,
                    elongaciones=elongaciones,
                    fps_led_aviso=None,
                    residuo_max_pct=8.0,
                    escala=escala,
                    escala_origen="regla marcada con clics",
                )
                args.masa_u, args.masa_resorte_u, args.corr_fps = variables_comunes(args)
                for aviso in advertencias_comunes(args):
                    print("ADVERTENCIA: " + aviso)
                    st.warning(aviso)
                k_e = (
                    k_estatico(
                        masas_estaticas,
                        elongaciones,
                        sigma_g=args.sigma_g,
                        sigma_elongacion=args.sigma_elongacion,
                    )
                    if masas_estaticas and elongaciones
                    else None
                )

                barra = st.progress(0, text="Preparando análisis…")
                estado_progreso = st.empty()
                with tempfile.TemporaryDirectory(prefix="analisis-resorte-") as temp_dir:
                    videos_dir = Path(temp_dir) / "videos"
                    salidas_dir = Path(temp_dir) / "salidas"
                    videos_dir.mkdir()
                    salidas_dir.mkdir()
                    rutas = []
                    for index, video in enumerate(videos):
                        ruta = videos_dir / f"{index}_{Path(video.name).name}"
                        ruta.write_bytes(video.getvalue())
                        rutas.append(str(ruta))

                    resultados = []
                    fallidos = []
                    for index, ruta in enumerate(rutas):
                        estado_progreso.info(f"Analizando video {index + 1} de {len(rutas)}: {Path(ruta).name}")
                        video_actual = videos[index]
                        guardado = st.session_state.get(f"punto_tracking_{video_actual.file_id}")
                        instante_video = float(st.session_state.get(f"instante_punto_{video_actual.file_id}", 0.0))
                        if not usar_punto_tracking:
                            punto_video = None
                        elif isinstance(guardado, dict):
                            punto_video = (guardado["x"], guardado["y"])
                        else:
                            punto_video = None

                        def actualizar_progreso(actual, total, indice=index, cantidad=len(rutas)):
                            if total:
                                fraccion = min(actual / total, 1.0)
                                texto = f"Video {indice + 1}/{cantidad}: cuadro {actual:,} de {total:,}"
                            else:
                                fraccion = 0.0
                                texto = f"Video {indice + 1}/{cantidad}: procesando cuadro {actual:,}"
                            porcentaje = int(95 * (indice + fraccion) / cantidad)
                            barra.progress(porcentaje, text=f"{porcentaje}% · {texto}")

                        try:
                            if usar_punto_tracking and punto_video is None:
                                raise ValueError(
                                    f"{video_actual.name}: falta marcar la masa en el cuadro de t={instante_video:g} s; "
                                    "cada video debe tener su propio punto de tracking."
                                )
                            preanalisis = None
                            guardado_chat = st.session_state.get("trayectorias_chat", {}).get(
                                video_actual.file_id
                            )
                            if (
                                guardado_chat
                                and guardado_chat.get("clave")
                                == _clave_tracking_chat(video_actual, metodo_tracking)
                            ):
                                preanalisis = guardado_chat.get("preanalisis")
                            vista_actual = st.session_state.get("vista_tracking")
                            if (
                                preanalisis is None
                                and vista_actual
                                and vista_actual.get("firma") == firma_videos
                                and vista_actual.get("indice") == index
                                and vista_actual.get("algoritmo") == algoritmo_tracking
                                and vista_actual.get("metodo_tracking") == metodo_tracking
                                and vista_actual.get("punto_inicial") == punto_video
                                and vista_actual.get("instante_punto_s", 0.0) == instante_video
                            ):
                                preanalisis = vista_actual.get("preanalisis")
                            resultado = analizar(
                                ruta,
                                args,
                                escala,
                                str(salidas_dir),
                                progreso=actualizar_progreso,
                                punto_inicial=punto_video,
                                preanalisis=preanalisis,
                                desde_s=instante_video,
                            )
                            for aviso in resultado.get("advertencias", []):
                                print("ADVERTENCIA: " + aviso)
                            resultados.append(resultado)
                        except Exception as exc:
                            fallidos.append((Path(ruta).name, str(exc)))
                        porcentaje_video = int(95 * (index + 1) / len(rutas))
                        barra.progress(porcentaje_video, text=f"{porcentaje_video}% · Videos procesados: {index + 1}/{len(rutas)}")

                    estado_progreso.info("Generando informe y archivos descargables…")

                    informe_path = salidas_dir / "informe.md"
                    escribir_informe(resultados, fallidos, args, escala, k_e, str(informe_path))
                    json_path = salidas_dir / "resultados.json"
                    json_path.write_text(
                        json.dumps(resultados_json(resultados, args, escala), indent=2, ensure_ascii=False),
                        encoding="utf-8",
                    )
                    archivos = {
                        path.relative_to(salidas_dir).as_posix(): path.read_bytes()
                        for path in salidas_dir.rglob("*")
                        if path.is_file()
                    }
                    informe = informe_path.read_text(encoding="utf-8")
                    paquete = io.BytesIO()
                    with zipfile.ZipFile(paquete, "w", zipfile.ZIP_DEFLATED) as archivo_zip:
                        for nombre, contenido in archivos.items():
                            archivo_zip.writestr(nombre, contenido)
                    st.session_state["ultimo_analisis"] = {
                        "firma": firma,
                        "informe": informe,
                        "resultados": json.loads(json_path.read_text(encoding="utf-8")),
                        "archivos": archivos,
                        "zip": paquete.getvalue(),
                        "fallidos": fallidos,
                    }
                    barra.progress(100, text="Análisis completo")
            except (ValueError, RuntimeError) as exc:
                st.session_state["error_analisis"] = str(exc)
            except Exception as exc:
                st.session_state["error_analisis"] = f"{type(exc).__name__}: {exc}"
        st.session_state.analisis_ocupado = False
        st.rerun()

    if st.session_state.get("error_analisis"):
        st.error(st.session_state.pop("error_analisis"))

    analisis = st.session_state.get("ultimo_analisis")
    if analisis and analisis["firma"] == firma:
        st.subheader("Resultados")
        if analisis["resultados"]:
            datos = analisis["resultados"]
            filas_resumen = []
            for video in datos.get("videos", []):
                r = video["resultados"]
                seg = video["seguimiento"]

                def mostrar_medida(medida):
                    if not medida:
                        return "—"
                    valor = f"{medida['valor']:.5g}"
                    if "incerteza" in medida:
                        valor += f" ± {medida['incerteza']:.2g}"
                    return f"{valor} {medida.get('unidad', '')}".strip()

                def mostrar(nombre):
                    return mostrar_medida(r.get(nombre))

                etiquetas_estado = {
                    "aceptable": "Aceptable", "revisar": "Revisar", "invalido": "Inválido"
                }
                ajuste = video.get("ajuste", {})
                t_cruces = ajuste.get("T_cruces_s")
                rms_pct = ajuste.get("rms_residuo_pct_amplitud")
                filas_resumen.append({
                    "Video": video["video"],
                    "Estado": etiquetas_estado.get(video["estado"], video["estado"]),
                    "Estado anterior": etiquetas_estado.get(video.get("estado_anterior"), video.get("estado_anterior")),
                    "Método": seg.get("metodo", "No informado"),
                    "Seguimiento": f"{seg['cuadros_detectados']}/{seg['cuadros_totales']} cuadros",
                    "Período T": mostrar("periodo"),
                    "T cruces (s)": "—" if t_cruces is None else f"{t_cruces:.6f}",
                    "RMS/A (%)": "—" if rms_pct is None else f"{rms_pct:.2f}",
                    "Frecuencia angular ω": mostrar("frecuencia_angular"),
                    "Amortiguamiento γ": mostrar("amortiguamiento"),
                    "Amplitud": mostrar("amplitud"),
                    "x_eq esperada": mostrar_medida(video.get("extension_estatica_esperada")),
                    "k con masa efectiva": mostrar("constante_elastica_con_masa_efectiva"),
                })
            if filas_resumen:
                st.dataframe(filas_resumen, hide_index=True, use_container_width=True)
            escala_json = datos.get("escala")
            if escala_json:
                st.caption(
                    f"Escala: {escala_json['valor']:.6g} ± {escala_json['sigma']:.3g} px/m "
                    f"(origen: {escala_json['origen']})."
                )
            for aviso in datos.get("advertencias", []):
                st.warning(aviso)
            for video in datos.get("videos", []):
                if video.get("alertas"):
                    st.warning(f"{video['video']}: " + "; ".join(video["alertas"]))
            agregado = datos.get("resultado_agregado")
            if agregado:
                st.markdown("**Promedio de las repeticiones**")
                filas_agregado = []
                for nombre, medida in agregado["magnitudes"].items():
                    filas_agregado.append({
                        "Magnitud": nombre.replace("_", " "),
                        "Media": f"{medida['valor']:.5g} {medida['unidad']}",
                        "Incerteza estadística": f"{medida['incerteza_estadistica']:.2g} {medida['unidad']}",
                        "Incerteza sistemática": f"{medida['incerteza_sistematica']:.2g} {medida['unidad']}",
                        "Incerteza total": f"{medida['incerteza_total']:.2g} {medida['unidad']}",
                    })
                st.dataframe(filas_agregado, hide_index=True, use_container_width=True)
            with st.expander("Ver JSON completo"):
                st.json(datos)
        else:
            st.warning("No se pudo analizar ninguno de los videos. Revisá los errores en el informe.")
        for nombre, error in analisis["fallidos"]:
            st.warning(f"{nombre}: {error}")

        columnas = st.columns([1, 1, 2])
        columnas[0].download_button(
            "Descargar informe",
            data=analisis["informe"],
            file_name="informe.md",
            mime="text/markdown",
        )
        columnas[1].download_button(
            "Descargar resultados JSON",
            data=json.dumps(analisis["resultados"], indent=2),
            file_name="resultados.json",
            mime="application/json",
        )
        columnas[2].download_button(
            "Descargar todos los resultados (ZIP)",
            data=analisis["zip"],
            file_name="resultados_resorte.zip",
            mime="application/zip",
        )

        imagenes = [
            (nombre, contenido)
            for nombre, contenido in analisis["archivos"].items()
            if nombre.lower().endswith(".png")
        ]
        if imagenes:
            st.subheader("Gráficos")
            columnas = st.columns(min(2, len(imagenes)))
            for indice, (nombre, contenido) in enumerate(imagenes):
                with columnas[indice % len(columnas)]:
                    st.image(contenido, caption=nombre, use_container_width=True)

        with st.expander("Informe completo"):
            st.markdown(analisis["informe"])

if not st.session_state.get("interfaz_cargada", False):
    skeleton_interfaz.empty()
    st.session_state["interfaz_cargada"] = True
