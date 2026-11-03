"""Seguimiento visual de la masa: video -> tabla en pixeles."""
import argparse, csv
from collections import deque
import cv2
import numpy as np

SIGMA_PX = 0.29
AREA_MIN_MOV = 80
AREA_MAX_MOV = 600000
SALTO_FACTOR = 4.0
SALTO_MIN_PX = 8.0
SALTO_INICIAL_PX = 60.0
SALTO_N_MEDIANA = 15
SALTO_MIN_MUESTRAS = 5


class TablaTracking(np.ndarray):
    """Array (N, 5) del tracking; el resumen queda en el atributo `.resumen`."""


def _contornos_movimiento(frame, bgsub):
    """Contornos del movimiento con área entre AREA_MIN_MOV y AREA_MAX_MOV."""
    fg = bgsub.apply(frame)
    kernel = np.ones((5, 5), np.uint8)
    fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, kernel)
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, kernel)
    contornos, _ = cv2.findContours(fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return [c for c in contornos
            if AREA_MIN_MOV <= cv2.contourArea(c) <= AREA_MAX_MOV]


def _centroide(contorno, forma):
    """Centroide del contorno relleno, o None si no tiene área."""
    mascara = np.zeros(forma, np.uint8)
    cv2.drawContours(mascara, [contorno], -1, 255, -1)
    momentos = cv2.moments(mascara, binaryImage=True)
    if momentos["m00"] == 0:
        return None
    return momentos["m10"] / momentos["m00"], momentos["m01"] / momentos["m00"]


def _puntos_opticos(gray, punto, radio=18):
    """Inicializa puntos visuales cercanos al clic para seguir la misma zona."""
    x, y = punto
    mascara = np.zeros_like(gray)
    cv2.circle(mascara, (int(round(x)), int(round(y))), radio, 255, -1)
    encontrados = cv2.goodFeaturesToTrack(
        gray,
        maxCorners=40,
        qualityLevel=0.005,
        minDistance=3,
        mask=mascara,
        blockSize=5,
    )
    ancla = np.array([[[x, y]]], dtype=np.float32)
    if encontrados is None:
        return ancla
    return np.concatenate((ancla, encontrados.astype(np.float32)), axis=0)


def _flujo_local(gray_anterior, gray_actual, puntos):
    """Estima el desplazamiento robusto de los rasgos alrededor del punto elegido."""
    siguientes, estado, error = cv2.calcOpticalFlowPyrLK(
        gray_anterior, gray_actual, puntos, None,
        winSize=(31, 31), maxLevel=3,
        criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01),
    )
    if siguientes is None or estado is None:
        return None

    anteriores, estado_vuelta, _ = cv2.calcOpticalFlowPyrLK(
        gray_actual, gray_anterior, siguientes, None,
        winSize=(31, 31), maxLevel=3,
        criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01),
    )
    if anteriores is None or estado_vuelta is None:
        return None

    ida = siguientes.reshape(-1, 2)
    vuelta = anteriores.reshape(-1, 2)
    origen = puntos.reshape(-1, 2)
    valido = (
        estado.reshape(-1).astype(bool)
        & estado_vuelta.reshape(-1).astype(bool)
        & (np.linalg.norm(vuelta - origen, axis=1) <= 2.0)
    )
    if error is not None:
        valido &= error.reshape(-1) <= 40.0
    alto, ancho = gray_actual.shape
    valido &= (
        (ida[:, 0] >= 0) & (ida[:, 0] < ancho)
        & (ida[:, 1] >= 0) & (ida[:, 1] < alto)
    )
    if not np.any(valido):
        return None

    desplazamientos = ida[valido] - origen[valido]
    desplazamiento = np.median(desplazamientos, axis=0)
    desviaciones = np.linalg.norm(desplazamientos - desplazamiento, axis=1)
    limite = max(2.5, 3.0 * float(np.median(desviaciones)))
    consistentes = desviaciones <= limite
    if np.any(consistentes):
        desplazamiento = np.median(desplazamientos[consistentes], axis=0)
    puntos_consistentes = ida[valido][consistentes]
    puntos_siguientes = puntos_consistentes.reshape(-1, 1, 2).astype(np.float32)
    return desplazamiento, puntos_siguientes


def _umbral_salto(saltos):
    """Umbral adaptativo en px a partir de los saltos ya aceptados."""
    if len(saltos) < SALTO_MIN_MUESTRAS:
        return SALTO_INICIAL_PX
    return max(SALTO_MIN_PX, SALTO_FACTOR * float(np.median(saltos)))


def trackear(
    video,
    salida="tabla.csv",
    ver=False,
    progreso=None,
    frame_callback=None,
    punto_inicial=None,
):
    """Devuelve (N, 5): t_s, x_px, y_px, sx_px, sy_px; NaN donde no se detectó.

    Si se pasa `frame_callback`, recibe cada cuadro con el resultado del tracking
    superpuesto, sin abrir una ventana interactiva.
    """
    cap = cv2.VideoCapture(video)
    if not cap.isOpened():
        raise RuntimeError(f"No se pudo abrir el video: {video}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 0:
        raise RuntimeError("El video no informa fps")
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    intervalo_progreso = max(1, total_frames // 100) if total_frames > 0 else 30
    punto_inicial = None if punto_inicial is None else tuple(map(float, punto_inicial))

    filas, i = [], 0
    previo = None
    frame_gris_previo = None
    puntos_opticos = None
    bgsub = None if punto_inicial is not None else cv2.createBackgroundSubtractorMOG2(
        history=250, varThreshold=16, detectShadows=False
    )
    saltos = deque(maxlen=SALTO_N_MEDIANA)
    descartados = 0
    multiples = 0
    detectados = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        gris = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        x_y = None
        if punto_inicial is not None and i == 0:
            alto, ancho = gris.shape
            x_inicial, y_inicial = punto_inicial
            if not (0 <= x_inicial < ancho and 0 <= y_inicial < alto):
                cap.release()
                raise ValueError(
                    f"El clic inicial {punto_inicial} queda fuera del cuadro "
                    f"de {ancho}x{alto}."
                )
            x_y = punto_inicial
            puntos_opticos = _puntos_opticos(gris, punto_inicial)
            frame_gris_previo = gris
        elif punto_inicial is not None:
            resultado = _flujo_local(frame_gris_previo, gris, puntos_opticos)
            if resultado is not None:
                desplazamiento, puntos_opticos = resultado
                x_y = (
                    previo[0] + float(desplazamiento[0]),
                    previo[1] + float(desplazamiento[1]),
                )
                frame_gris_previo = gris
        else:
            contornos = _contornos_movimiento(frame, bgsub)
            if len(contornos) > 1:
                multiples += 1
            if contornos:
                mayores = sorted(
                    contornos, key=cv2.contourArea, reverse=True
                )[:5]
                centros = [
                    _centroide(c, gris.shape) for c in mayores
                ]
                centros = [p for p in centros if p is not None]
                if previo is None:
                    x_y = centros[0] if centros else None
                elif centros:
                    candidato = min(
                        centros,
                        key=lambda p: np.hypot(
                            p[0] - previo[0], p[1] - previo[1]
                        ),
                    )
                    salto = float(np.hypot(
                        candidato[0] - previo[0], candidato[1] - previo[1]
                    ))
                    if salto <= _umbral_salto(saltos):
                        x_y = candidato
                    else:
                        descartados += 1

        if x_y is not None:
            x, y = x_y
            if previo is not None:
                saltos.append(float(np.hypot(x - previo[0], y - previo[1])))
            previo = (x, y)
            filas.append((i / fps, x, y, SIGMA_PX, SIGMA_PX))
            detectados += 1
        else:
            filas.append((i / fps, np.nan, np.nan, np.nan, np.nan))
        if ver or frame_callback is not None:
            if x_y is None:
                cv2.putText(
                    frame, "Punto no seguido", (12, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2,
                )
            else:
                cv2.circle(frame, (int(x), int(y)), 6, (0, 255, 0), 2)
        if frame_callback is not None:
            frame_callback(frame)
        if ver:
            cv2.imshow("tracking (q para salir)", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                ver = False
                cv2.destroyAllWindows()
        i += 1
        if progreso is not None and (i % intervalo_progreso == 0 or (total_frames > 0 and i >= total_frames)):
            progreso(i, total_frames if total_frames > 0 else None)
    cap.release()
    cv2.destroyAllWindows()

    with open(salida, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t_s", "x_px", "y_px", "sx_px", "sy_px"])
        w.writerows(filas)

    tabla = np.asarray(filas, dtype=float).reshape(-1, 5).view(TablaTracking)
    resumen = {
        "cuadros": i,
        "detectados": detectados,
        "perdidos": i - detectados,
        "saltos_descartados": descartados,
        "frames_con_multiples_candidatos": multiples,
        "metodo": (
            "punto seleccionado (flujo optico)"
            if punto_inicial is not None else "movimiento"
        ),
    }
    tabla.resumen = resumen
    trackear.ultimo_resumen = resumen
    if progreso is not None and (total_frames <= 0 or i % intervalo_progreso != 0):
        progreso(i, total_frames if total_frames > 0 else None)
    print(f"tracking: {resumen['cuadros']} cuadros | "
          f"{detectados} detectados | {resumen['perdidos']} perdidos | "
          f"{descartados} descartados por salto | {resumen['metodo']}")
    return tabla


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--salida", default="tabla.csv")
    ap.add_argument("--ver", action="store_true", help="mostrar el seguimiento en pantalla")
    a = ap.parse_args()
    d = trackear(a.video, a.salida, a.ver)
    print(f"{len(d)} cuadros, {np.isnan(d[:, 1]).sum()} sin detección -> {a.salida}")
