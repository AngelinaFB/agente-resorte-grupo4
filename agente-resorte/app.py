import base64
import io
import json
import tempfile
import zipfile
from pathlib import Path
from types import SimpleNamespace

import streamlit as st

st.set_page_config(page_title="Análisis de resorte", page_icon="🌀", layout="wide")
with st.spinner("Cargando herramientas del analizador…", show_time=True):
    import cv2
    import numpy as np
    import streamlit.components.v1 as components

    from calibracion import escala_px_por_m
    from main import analizar, escribir_informe, resultados_json, variables_comunes
    from ajuste import k_estatico
    from tracking import trackear

seleccionar_punto_tracking = components.declare_component(
    "selector_punto_tracking",
    path=str(Path(__file__).parent / "selector_punto_tracking"),
)

def alternar_ampliacion_selector(clave):
    st.session_state[clave] = not st.session_state.get(clave, False)


def responder_chat_inicial(mensaje):
    texto = mensaje.lower()
    videos_actuales = st.session_state.get("videos_experimento") or []
    if not videos_actuales:
        return (
            "Primero cargá el video desde el panel «Analizador de video». "
            "Cuando lo subas, puedo revisar el estado de los datos del experimento."
        )

    cantidad = len(videos_actuales)
    if any(palabra in texto for palabra in ("falta", "necesito", "dato", "empez", "analiz")):
        metodo = st.session_state.get("metodo_tracking", "Punto marcado · flujo óptico")
        masa = st.session_state.get("masa_analisis", 0.250)
        masa_resorte = st.session_state.get("masa_resorte_analisis", 0.030)
        regla = st.session_state.get("longitud_regla", 0.300)
        pendientes = []
        if metodo == "Punto marcado · flujo óptico":
            indice = st.session_state.get("indice_video_tracking", 0)
            indice = min(max(int(indice or 0), 0), cantidad - 1)
            video = videos_actuales[indice]
            if not st.session_state.get(f"punto_tracking_{video.file_id}"):
                pendientes.append(
                    f"marcar la masa en el primer cuadro de {video.name} para el tracking"
                )

        respuesta = (
            f"Veo {cantidad} video(s). El método seleccionado es «{metodo}». "
            f"El formulario tiene masa colgante = {masa:g} kg, masa del resorte = "
            f"{masa_resorte:g} kg y longitud de regla = {regla:g} m. "
            "Revisá que estos valores coincidan con tus mediciones reales y que las "
            "coordenadas de los extremos de la regla estén bien indicadas."
        )
        if pendientes:
            respuesta += " Para continuar, falta " + " y ".join(pendientes) + "."
        else:
            respuesta += " Con esos datos revisados, podés ejecutar el análisis desde el panel."
        return respuesta

    return (
        "Por ahora puedo revisar el estado de los datos del experimento. Preguntame "
        "«¿qué datos faltan?»; la interpretación de preguntas de física y la edición "
        "de parámetros desde el chat quedan para los siguientes pasos."
    )


chat_col, analizador_col = st.columns([1, 3], gap="large")
with chat_col:
    st.subheader("Chat del análisis")
    st.caption("Panel conversacional del experimento")
    st.session_state.setdefault(
        "conversacion_analisis",
        [{
            "role": "assistant",
            "content": (
                "Hola. Cargá el video en el analizador y preguntame «¿qué datos faltan?». "
                "Voy a revisar los valores actuales y señalarte qué revisar antes de correrlo."
            ),
        }],
    )
    with st.container(height=560, border=True):
        for mensaje in st.session_state.conversacion_analisis:
            with st.chat_message(mensaje["role"]):
                st.write(mensaje["content"])

    entrada_chat = st.chat_input(
        "Escribí sobre este análisis…",
        key="entrada_chat_analisis",
    )
    if entrada_chat:
        st.session_state.conversacion_analisis.append(
            {"role": "user", "content": entrada_chat}
        )
        respuesta = responder_chat_inicial(entrada_chat)
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


    def crear_video_tracking(contenido, nombre, punto_inicial, progreso=None):
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
            "punto-inicial-flujo-optico-v5" if usar_punto_tracking else "mog2-v1"
        )
        col_video, col_boton = st.columns([3, 1])
        indice_tracking = col_video.selectbox(
            "Video para revisar",
            options=range(len(videos)),
            format_func=lambda indice: videos[indice].name,
            key="indice_video_tracking",
        )
        video_seleccionado = videos[indice_tracking]
        cuadro_tracking, tamano_tracking = primer_cuadro_video(
            video_seleccionado.getvalue(), video_seleccionado.name
        )
        clave_punto = f"punto_tracking_{video_seleccionado.file_id}"
        if cuadro_tracking is None or tamano_tracking is None:
            st.error("No se pudo leer el primer cuadro del video para preparar el seguimiento.")
        elif usar_punto_tracking:
            st.caption(
                "Hacé clic en el punto exacto de la masa en el primer cuadro. "
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
                video.name for video in videos
                if not isinstance(st.session_state.get(f"punto_tracking_{video.file_id}"), dict)
            ]
            if sin_punto_propio:
                st.warning(
                    "Estos videos no tienen un punto propio y usarán el punto del video seleccionado: "
                    + ", ".join(sin_punto_propio)
                    + ". Para mejorar la precisión, elegí el punto de la masa en cada video."
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
                    )
                st.session_state["vista_tracking"] = {
                    "firma": firma_videos,
                    "indice": indice_tracking,
                    "formato": "mp4",
                    "algoritmo": algoritmo_tracking,
                    "metodo_tracking": metodo_tracking,
                    "punto_inicial": punto_tracking if usar_punto_tracking else None,
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
    masa = c_masa.number_input(
        "Masa colgante (kg)", min_value=0.000001, value=0.250, step=0.010,
        key="masa_analisis",
        help="Masa total que cuelga del resorte, incluido el portapesas.",
    )
    sigma_masa = c_sigma.number_input(
        "Incerteza de masa (kg)", min_value=0.0, value=0.001, step=0.001,
        help="Incerteza de la masa colgante según la resolución de la balanza o la medición usada.",
    )
    masa_resorte = c_resorte.number_input(
        "Masa del resorte (kg)", min_value=0.0, value=0.030, step=0.001,
        key="masa_resorte_analisis",
        help="Se considera con factor 1/3 en la masa efectiva.",
    )
    sigma_masa_resorte = c_sigma_resorte.number_input(
        "Incerteza del resorte (kg)", min_value=0.0, value=0.0001, step=0.0001, format="%.4f",
        help="Incerteza de la masa del resorte según la resolución de la balanza o la medición usada.",
    )
    st.caption(f"Masa colgante: {masa*1000.0:.1f} g")

    with st.form("parametros_analisis"):
        with st.container(border=True):
            st.markdown("**Calibración con regla**")
            puntos = None
            if frame_size:
                c_largo, c_ventana, _ = st.columns(
                    [1.2, 1.4, 5], vertical_alignment="bottom"
                )
                regla_m = c_largo.number_input(
                    "Longitud (m)", min_value=0.000001, value=0.300, step=0.010,
                    key="longitud_regla",
                    help="Distancia real, en metros, entre las dos marcas que seleccionaste en el cuadro.",
                )
                ventana = c_ventana.selectbox(
                    "Ventana (cuadros)", [7, 11, 21, 41], index=1,
                    help="Cantidad de cuadros que se usan para suavizar la posición, velocidad y aceleración. Valores grandes suavizan más, pero pueden borrar detalles.",
                )
                puntos = (
                    tuple((punto["x"], punto["y"]) for punto in puntos_regla)
                    if len(puntos_regla) == 2
                    else None
                )
                if puntos is None:
                    st.info("Marcá los dos extremos de la regla en el cuadro de referencia.")
            else:
                c_largo, c_ventana, _ = st.columns(
                    [1.2, 1.4, 5], vertical_alignment="bottom"
                )
                regla_m = c_largo.number_input(
                    "Longitud (m)", min_value=0.000001, value=0.300, step=0.010,
                    key="longitud_regla",
                )
                ventana = c_ventana.selectbox(
                    "Ventana (cuadros)", [7, 11, 21, 41], index=1,
                    help="Ventana de Savitzky-Golay para filtrar posición, velocidad y aceleración.",
                )
        with st.expander("Chequeo estático opcional"):
            st.caption("Opcional. Solo sirve para calcular k por F = kx. NO es necesario para obtener k dinámico con el ajuste x(t).")
            masas_texto = st.text_input("Masas estáticas (kg, separadas por comas)")
            elongaciones_texto = st.text_input("Elongaciones (m, separadas por comas)")
            usar_sigma_elongacion = st.checkbox("Indicar incerteza de elongación")
            sigma_elongacion = st.number_input(
                "Incerteza de cada elongación (m)",
                min_value=0.0,
                value=0.001,
                step=0.001,
                disabled=not usar_sigma_elongacion,
                help="Incerteza de cada elongación medida, por ejemplo la resolución de la regla. Se usa para calcular la incerteza de la constante elástica estática.",
            )

        ejecutar = st.form_submit_button(
            "Analizando…" if st.session_state.analisis_ocupado else "Analizar videos",
            type="primary",
            disabled=(
                not videos
                or len(puntos_regla) != 2
                or (usar_punto_tracking and punto_tracking is None)
                or st.session_state.analisis_ocupado
            ),
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
        ventana,
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
                escala = escala_px_por_m(puntos[0], puntos[1], regla_m)
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

                args = SimpleNamespace(
                    masa=masa,
                    sigma_masa=sigma_masa,
                    masa_resorte=masa_resorte,
                    sigma_masa_resorte=sigma_masa_resorte,
                    fps_led=None,
                    fps_sigma=0.0,
                    f_led=None,
                    fps_real=None,
                    ventana=ventana,
                    inicio=None,
                    recorte_auto=True,
                    ventana_inicio=0.5,
                    sigma_g=0.01,
                    sigma_elongacion=sigma_elongacion if usar_sigma_elongacion else None,
                    masas_estaticas=masas_estaticas,
                    elongaciones=elongaciones,
                    fps_led_aviso=None,
                )
                args.masa_u, args.masa_resorte_u, args.corr_fps = variables_comunes(args)
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
                        if not usar_punto_tracking:
                            punto_video = None
                        elif isinstance(guardado, dict):
                            punto_video = (guardado["x"], guardado["y"])
                        else:
                            punto_video = punto_tracking

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
                            preanalisis = None
                            vista_actual = st.session_state.get("vista_tracking")
                            if (
                                vista_actual
                                and vista_actual.get("firma") == firma_videos
                                and vista_actual.get("indice") == index
                                and vista_actual.get("algoritmo") == algoritmo_tracking
                                and vista_actual.get("metodo_tracking") == metodo_tracking
                                and vista_actual.get("punto_inicial") == punto_video
                            ):
                                preanalisis = vista_actual.get("preanalisis")
                            resultados.append(analizar(
                                ruta,
                                args,
                                escala,
                                str(salidas_dir),
                                progreso=actualizar_progreso,
                                punto_inicial=punto_video,
                                preanalisis=preanalisis,
                            ))
                        except Exception as exc:
                            fallidos.append((Path(ruta).name, str(exc)))
                        porcentaje_video = int(95 * (index + 1) / len(rutas))
                        barra.progress(porcentaje_video, text=f"{porcentaje_video}% · Videos procesados: {index + 1}/{len(rutas)}")

                    estado_progreso.info("Generando informe y archivos descargables…")

                    informe_path = salidas_dir / "informe.md"
                    escribir_informe(resultados, fallidos, args, escala, k_e, str(informe_path))
                    json_path = salidas_dir / "resultados.json"
                    json_path.write_text(
                        json.dumps(resultados_json(resultados), indent=2, ensure_ascii=False),
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

                def mostrar(nombre):
                    m = r[nombre]
                    valor = f"{m['valor']:.5g}"
                    if "incerteza" in m:
                        valor += f" ± {m['incerteza']:.2g}"
                    return f"{valor} {m.get('unidad', '')}".strip()

                filas_resumen.append({
                    "Video": video["video"],
                    "Estado": "Revisar" if video["estado"] == "revisar" else "Aceptable",
                    "Método": seg.get("metodo", "No informado"),
                    "Seguimiento": f"{seg['cuadros_detectados']}/{seg['cuadros_totales']} cuadros",
                    "Período T": mostrar("periodo"),
                    "Frecuencia angular ω": mostrar("frecuencia_angular"),
                    "Amortiguamiento γ": mostrar("amortiguamiento"),
                    "Amplitud": mostrar("amplitud"),
                    "k con masa efectiva": mostrar("constante_elastica_con_masa_efectiva"),
                })
            if filas_resumen:
                st.dataframe(filas_resumen, hide_index=True, use_container_width=True)
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
