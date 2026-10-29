"""Tracking por movimiento con MOG2: video -> tabla (t,x,y,sx,sy) en pixeles. Sin color/ROI."""
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
    m = np.zeros(forma, np.uint8)
    cv2.drawContours(m, [contorno], -1, 255, -1)
    M = cv2.moments(m, binaryImage=True)
    if M["m00"] == 0:
        return None
    return M["m10"] / M["m00"], M["m01"] / M["m00"]


def _umbral_salto(saltos):
    """Umbral adaptativo en px a partir de los saltos ya aceptados."""
    if len(saltos) < SALTO_MIN_MUESTRAS:
        return SALTO_INICIAL_PX
    return max(SALTO_MIN_PX, SALTO_FACTOR * float(np.median(saltos)))


def trackear(video, salida="tabla.csv", ver=False, progreso=None):
    """Devuelve array (N, 5): t_s, x_px, y_px, sx_px, sy_px. NaN donde no se detectó."""
    cap = cv2.VideoCapture(video)
    if not cap.isOpened():
        raise RuntimeError(f"No se pudo abrir el video: {video}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 0:
        raise RuntimeError("El video no informa fps")
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    intervalo_progreso = max(1, total_frames // 100) if total_frames > 0 else 30

    bgsub = cv2.createBackgroundSubtractorMOG2(
        history=250, varThreshold=16, detectShadows=False)

    filas, i = [], 0
    previo = None
    saltos = deque(maxlen=SALTO_N_MEDIANA)
    descartados = 0
    multiples = 0
    detectados = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        forma = frame.shape[:2]
        candidatos = _contornos_movimiento(frame, bgsub)
        if len(candidatos) > 1:
            multiples += 1

        elegido = None
        if candidatos:
            centros = [(p, c) for p, c in
                       ((_centroide(c, forma), c) for c in candidatos)
                       if p is not None]
            if centros:
                if previo is None:
                    elegido = max((c for _, c in centros), key=cv2.contourArea)
                else:
                    distancias = [np.hypot(p[0] - previo[0], p[1] - previo[1])
                                  for p, _ in centros]
                    j = int(np.argmin(distancias))
                    if len(centros) > 1 and distancias[j] > _umbral_salto(saltos):
                        descartados += 1
                    else:
                        elegido = centros[j][1]

        if elegido is not None:
            x, y = _centroide(elegido, forma)
            if previo is not None:
                saltos.append(float(np.hypot(x - previo[0], y - previo[1])))
            previo = (x, y)
            filas.append((i / fps, x, y, SIGMA_PX, SIGMA_PX))
            detectados += 1
            if ver:
                cv2.circle(frame, (int(x), int(y)), 6, (0, 255, 0), 2)
                cv2.drawContours(frame, [elegido], -1, (0, 255, 0), 2)
        else:
            filas.append((i / fps, np.nan, np.nan, np.nan, np.nan))
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
    }
    tabla.resumen = resumen
    trackear.ultimo_resumen = resumen
    if progreso is not None and (total_frames <= 0 or i % intervalo_progreso != 0):
        progreso(i, total_frames if total_frames > 0 else None)
    print(f"tracking: {resumen['cuadros']} cuadros | "
          f"{detectados} detectados | {resumen['perdidos']} perdidos | "
          f"{descartados} descartados por salto | "
          f"{multiples} con más de un candidato")
    return tabla


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--salida", default="tabla.csv")
    ap.add_argument("--ver", action="store_true", help="mostrar el seguimiento en pantalla")
    a = ap.parse_args()
    d = trackear(a.video, a.salida, a.ver)
    print(f"{len(d)} cuadros, {np.isnan(d[:, 1]).sum()} sin detección -> {a.salida}")
