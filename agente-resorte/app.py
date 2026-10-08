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
from main import analizar, escribir_informe
from tracking import COLORES
from ajuste import k_estatico


st.set_page_config(page_title="Análisis de resorte", page_icon="🌀", layout="wide")
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


videos = st.file_uploader(
    "Videos del experimento",
    type=["mp4", "avi", "mov", "mkv"],
    accept_multiple_files=True,
    help="Podés subir varias repeticiones filmadas con la misma configuración.",
)

modo_escala = st.radio(
    "¿Cómo vas a indicar la escala espacial?",
    ["Conozco los píxeles por metro", "Medir una regla en el primer video"],
    horizontal=True,
)

frame_size = None
if videos and modo_escala == "Medir una regla en el primer video":
    with tempfile.TemporaryDirectory(prefix="resorte-vista-") as temp_dir:
        sample_path = Path(temp_dir) / Path(videos[0].name).name
        sample_path.write_bytes(videos[0].getvalue())
        capture = cv2.VideoCapture(str(sample_path))
        ok, frame = capture.read()
        capture.release()
        if not ok:
            st.error("No se pudo leer el primer cuadro del video para mostrar la regla.")
        else:
            frame_size = (frame.shape[1], frame.shape[0])
            st.caption(
                f"Primer cuadro del video ({frame_size[0]} × {frame_size[1]} px). "
                "Anotá las coordenadas de los dos extremos de la regla."
            )
            st.image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

with st.form("parametros_analisis"):
    st.subheader("Datos del experimento")
    col1, col2 = st.columns(2)
    masa = col1.number_input("Masa colgante (kg)", min_value=0.000001, value=0.250, step=0.010)
    sigma_masa = col2.number_input("Incerteza de la masa (kg)", min_value=0.0, value=0.001, step=0.001)
    masa_resorte = col1.number_input("Masa del resorte (kg)", min_value=0.0, value=0.030, step=0.001)
    sigma_masa_resorte = col2.number_input(
        "Incerteza de la masa del resorte (kg)", min_value=0.0, value=0.0001, step=0.0001, format="%.4f"
    )

    st.subheader("Calibración")
    if modo_escala == "Conozco los píxeles por metro":
        col1, col2 = st.columns(2)
        px_por_m = col1.number_input("Escala (px/m)", min_value=0.000001, value=2000.0, step=10.0)
        sigma_px_por_m = col2.number_input(
            "Incerteza de la escala (px/m)", min_value=0.0, value=2.0, step=0.5
        )
        regla_m = None
        puntos = None
    else:
        regla_m = st.number_input("Longitud real de la regla (m)", min_value=0.000001, value=0.300, step=0.010)
        px_por_m = None
        sigma_px_por_m = None
        puntos = None
        if frame_size:
            width, height = frame_size
            st.caption("Ingresá las coordenadas de los extremos sobre la imagen (origen arriba a la izquierda).")
            c1, c2, c3, c4 = st.columns(4)
            x1 = c1.number_input("x₁ (px)", min_value=0, max_value=width - 1, value=0, key="x1")
            y1 = c2.number_input("y₁ (px)", min_value=0, max_value=height - 1, value=0, key="y1")
            x2 = c3.number_input("x₂ (px)", min_value=0, max_value=width - 1, value=width - 1, key="x2")
            y2 = c4.number_input("y₂ (px)", min_value=0, max_value=height - 1, value=0, key="y2")
            puntos = ((x1, y1), (x2, y2))

    col1, col2, col3 = st.columns(3)
    eje = col1.selectbox("Eje de oscilación", ["y", "x"], format_func=lambda v: "Vertical (y)" if v == "y" else "Horizontal (x)")
    color = col2.selectbox("Color de la marca", list(COLORES), index=list(COLORES).index("rojo"))
    ventana = col3.selectbox("Ventana de filtrado (cuadros)", [7, 11, 21, 41], index=1)

    st.subheader("Opciones")
    usar_fps = st.checkbox("Ingresar FPS real medido")
    fps_real = st.number_input(
        "FPS real",
        min_value=0.000001,
        value=30.0,
        step=0.1,
        disabled=not usar_fps,
    )
    with st.expander("Chequeo estático opcional"):
        masas_texto = st.text_input("Masas estáticas (kg, separadas por comas)")
        elongaciones_texto = st.text_input("Elongaciones (m, separadas por comas)")
        usar_sigma_elongacion = st.checkbox("Indicar incerteza de elongación")
        sigma_elongacion = st.number_input(
            "Incerteza de cada elongación (m)",
            min_value=0.0,
            value=0.001,
            step=0.001,
            disabled=not usar_sigma_elongacion,
        )

    ejecutar = st.form_submit_button("Analizar videos", type="primary", disabled=not videos)

firma = (
    tuple((video.file_id, video.name) for video in videos) if videos else (),
    modo_escala,
    masa,
    sigma_masa,
    masa_resorte,
    sigma_masa_resorte,
    px_por_m if modo_escala == "Conozco los píxeles por metro" else puntos,
    sigma_px_por_m,
    regla_m,
    eje,
    color,
    ventana,
    usar_fps,
    fps_real if usar_fps else None,
    masas_texto,
    elongaciones_texto,
    usar_sigma_elongacion,
    sigma_elongacion if usar_sigma_elongacion else None,
)

if ejecutar:
    if not videos:
        st.error("Cargá al menos un video.")
    elif modo_escala == "Medir una regla en el primer video" and not frame_size:
        st.error("No se pudo obtener un cuadro del video. Revisá el archivo e intentá de nuevo.")
    else:
        try:
            if puntos is not None:
                if puntos[0] == puntos[1]:
                    raise ValueError("Los dos extremos de la regla deben ser puntos distintos.")
                escala = escala_px_por_m(puntos[0], puntos[1], regla_m)
            else:
                escala = (px_por_m, sigma_px_por_m)
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
                color=color,
                fps_led=None,
                fps_sigma=0.0,
                f_led=None,
                fps_real=fps_real if usar_fps else None,
                eje=eje,
                ventana=ventana,
                sigma_g=0.01,
                sigma_elongacion=sigma_elongacion if usar_sigma_elongacion else None,
                masas_estaticas=masas_estaticas,
                elongaciones=elongaciones,
                fps_led_aviso=None,
            )
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

            with st.spinner("Procesando video(s)…"):
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
                    for ruta in rutas:
                        try:
                            resultados.append(analizar(ruta, args, escala, str(salidas_dir)))
                        except Exception as exc:
                            fallidos.append((Path(ruta).name, str(exc)))

                    informe_path = salidas_dir / "informe.md"
                    escribir_informe(resultados, fallidos, args, escala, k_e, str(informe_path))
                    json_path = salidas_dir / "resultados.json"
                    json_path.write_text(
                        json.dumps(
                            [
                                {
                                    clave: (resultado[clave].n, resultado[clave].s)
                                    for clave in ("T", "gamma", "k", "k_sin")
                                }
                                | {"video": resultado["nombre"]}
                                for resultado in resultados
                            ],
                            indent=2,
                        ),
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
        except (ValueError, RuntimeError) as exc:
            st.error(str(exc))
        except Exception as exc:
            st.exception(exc)

analisis = st.session_state.get("ultimo_analisis")
if analisis and analisis["firma"] == firma:
    st.subheader("Resultados")
    if analisis["resultados"]:
        st.json(analisis["resultados"])
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
