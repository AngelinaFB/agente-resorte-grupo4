import io
import json
import tempfile
import zipfile
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import streamlit as st

from calibracion import escala_px_por_m
from main import analizar, escribir_informe, resultados_json, variables_comunes
from ajuste import k_estatico


st.set_page_config(page_title="Análisis de resorte", page_icon="🌀", layout="wide")
if "analisis_ocupado" not in st.session_state:
    st.session_state.analisis_ocupado = False
st.markdown(
    """
    <style>
    .block-container { max-width: 1200px !important; padding-left: 2rem; padding-right: 2rem; }
    div[data-testid="stNumberInput"] { max-width: 170px !important; }
    div[data-testid="stSelectbox"] { max-width: 230px !important; }
    div[data-testid="stTextInput"] { max-width: 320px !important; }
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("Análisis de movimiento de un resorte")
st.write(
    "Subí uno o varios videos del experimento, completá los datos y ejecutá el análisis. "
    "Los videos se procesan en una carpeta temporal y no se guardan en el repositorio."
)


def leer_lista(texto, nombre):
    if not texto.strip():
        return None
    try:
        return [float(valor.strip()) for valor in texto.split(",") if valor.strip()]
    except ValueError as exc:
        raise ValueError(f"{nombre}: ingresá números separados por comas.") from exc


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


videos = st.file_uploader(
    "Videos del experimento",
    type=["mp4", "avi", "mov", "mkv"],
    accept_multiple_files=True,
    help="Subí uno o varios videos del mismo setup/cámara. Si subís varias repeticiones se van a agregar automáticamente.",
)

frame_size = None
if videos:
    frame_preview, frame_size = primer_cuadro_video(videos[0].getvalue(), videos[0].name)
    if frame_preview is None:
        st.error("No se pudo leer el primer cuadro del video para mostrar la regla.")
    else:
        st.caption(f"Cuadro de referencia ({frame_size[0]} × {frame_size[1]} px)")
        st.image(frame_preview, width=520)

st.subheader("Datos del experimento")
c_masa, c_sigma, c_resorte, c_sigma_resorte, _ = st.columns([1.1, 1.1, 1.1, 1.1, 2.5])
masa = c_masa.number_input(
    "Masa colgante (kg)", min_value=0.000001, value=0.250, step=0.010,
    help="Masa total que cuelga del resorte, incluido el portapesas.",
)
sigma_masa = c_sigma.number_input(
    "Incerteza de masa (kg)", min_value=0.0, value=0.001, step=0.001,
    help="Incerteza de la masa colgante según la resolución de la balanza o la medición usada.",
)
masa_resorte = c_resorte.number_input(
    "Masa del resorte (kg)", min_value=0.0, value=0.030, step=0.001,
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
            width, height = frame_size
            c_largo, c_ventana, _ = st.columns([1.2, 1.4, 5])
            regla_m = c_largo.number_input(
                "Longitud (m)", min_value=0.000001, value=0.300, step=0.010,
                key="longitud_regla",
                help="Longitud física, en metros, del tramo de la regla cuyos dos extremos vas a indicar debajo.",
            )
            ventana = c_ventana.selectbox(
                "Ventana de filtrado (cuadros)", [7, 11, 21, 41], index=1,
                help="Cantidad de cuadros que se usan para suavizar la posición, velocidad y aceleración. Valores grandes suavizan más, pero pueden borrar detalles.",
            )
            st.caption(
                "Coordenadas de los dos extremos de la regla en el cuadro de arriba. "
                "El origen está arriba a la izquierda: x crece hacia la derecha e y hacia abajo."
            )
            c_x1, c_y1, c_x2, c_y2, _ = st.columns([1.1, 1.1, 1.1, 1.1, 2.5])
            ayuda_x1 = "Posición horizontal en píxeles del primer extremo de la regla, mirando el cuadro de referencia."
            ayuda_y1 = "Posición vertical en píxeles del primer extremo de la regla. El valor aumenta hacia abajo."
            ayuda_x2 = "Posición horizontal en píxeles del otro extremo de la regla."
            ayuda_y2 = "Posición vertical en píxeles del otro extremo de la regla. El valor aumenta hacia abajo."
            x1 = c_x1.number_input("Extremo 1 · x (px)", min_value=0, max_value=width - 1, value=0, key="x1", help=ayuda_x1)
            y1 = c_y1.number_input("Extremo 1 · y (px)", min_value=0, max_value=height - 1, value=0, key="y1", help=ayuda_y1)
            x2 = c_x2.number_input("Extremo 2 · x (px)", min_value=0, max_value=width - 1, value=width - 1, key="x2", help=ayuda_x2)
            y2 = c_y2.number_input("Extremo 2 · y (px)", min_value=0, max_value=height - 1, value=0, key="y2", help=ayuda_y2)
            puntos = ((x1, y1), (x2, y2))
        else:
            c_largo, c_ventana, _ = st.columns([1.2, 1.4, 5])
            regla_m = c_largo.number_input(
                "Longitud de la regla (m)", min_value=0.000001, value=0.300, step=0.010,
                key="longitud_regla",
            )
            ventana = c_ventana.selectbox(
                "Ventana de filtrado (cuadros)", [7, 11, 21, 41], index=1,
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
        type="primary", disabled=not videos or st.session_state.analisis_ocupado,
    )

firma = (
    tuple((video.file_id, video.name) for video in videos) if videos else (),
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
)

if ejecutar and not st.session_state.analisis_ocupado:
    st.session_state.analisis_ocupado = True
    st.session_state.pop("error_analisis", None)
    st.rerun()

if st.session_state.analisis_ocupado:
    if not videos:
        st.session_state["error_analisis"] = "Cargá al menos un video."
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
                        resultados.append(analizar(
                            ruta, args, escala, str(salidas_dir), progreso=actualizar_progreso
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
