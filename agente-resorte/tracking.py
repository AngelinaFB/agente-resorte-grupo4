"""Tracking por color con OpenCV: video -> tabla (t, x, y, σx, σy) en píxeles.
Offline, sin dependencias extra."""
import argparse, csv
from collections import deque
import cv2
import numpy as np

# Rangos HSV (OpenCV: H 0-179, S 0-255, V 0-255). Cada color es una lista de rangos.
COLORES = {
    "rojo":     [((0, 120, 80), (10, 255, 255)), ((170, 120, 80), (180, 255, 255))],
    "naranja":  [((10, 120, 80), (25, 255, 255))],
    "amarillo": [((20, 100, 100), (35, 255, 255))],
    "verde":    [((40, 80, 60), (85, 255, 255))],
    "azul":     [((95, 100, 60), (130, 255, 255))],
    "negro":    [((0, 0, 0), (180, 255, 60))],
}

SIGMA_PX = 0.29      # 1/√12 px: incerteza por discretización (conservadora para centroide subpíxel)
AREA_MIN = 30        # px²: objetos más chicos se descartan como ruido

# Seguimiento por continuidad cuando hay MÁS DE UN contorno candidato (p. ej. dos
# marcas del mismo color). El umbral de salto máximo es adaptativo: SALTO_FACTOR
# veces la mediana de los últimos SALTO_N_MEDIANA saltos aceptados, con piso
# SALTO_MIN_PX (8 px ≈ 4 mm a 2000 px/m). Mientras haya menos de
# SALTO_MIN_MUESTRAS saltos se usa SALTO_INICIAL_PX (60 px, para ~2000 px/m y
# 30 fps). Si el
# candidato más cercano supera el umbral, el cuadro queda en NaN. Con un único
# contorno candidato NO se aplica el umbral: se conserva el comportamiento previo.
SALTO_FACTOR = 4.0
SALTO_MIN_PX = 8.0
SALTO_INICIAL_PX = 60.0
SALTO_N_MEDIANA = 15
SALTO_MIN_MUESTRAS = 5


class TablaTracking(np.ndarray):
    """Array (N, 5) del tracking; el resumen queda en el atributo `.resumen`."""


def _contornos_candidatos(frame, color):
    """Contornos de la máscara de color con área >= AREA_MIN."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    m = np.zeros(hsv.shape[:2], np.uint8)
    for lo, hi in COLORES[color]:
        m |= cv2.inRange(hsv, lo, hi)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    contornos, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return [c for c in contornos if cv2.contourArea(c) >= AREA_MIN]


def _centroide(contorno, forma):
    """Centroide del contorno relleno (mismo criterio que el de la tabla)."""
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


def mascara(frame, color):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    m = np.zeros(hsv.shape[:2], np.uint8)
    for lo, hi in COLORES[color]:
        m |= cv2.inRange(hsv, lo, hi)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    # Quedarse solo con el objeto más grande
    contornos, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contornos:
        return None
    grande = max(contornos, key=cv2.contourArea)
    if cv2.contourArea(grande) < AREA_MIN:
        return None
    limpia = np.zeros_like(m)
    cv2.drawContours(limpia, [grande], -1, 255, -1)
    return limpia


def trackear(video, salida="tabla.csv", color="rojo", ver=False):
    """Devuelve array (N, 5): t_s, x_px, y_px, sx_px, sy_px. NaN donde no se detectó.

    Con varias marcas del mismo color sigue una sola por continuidad: primer cuadro
    con detección = mayor área; luego, el candidato cuyo centroide está más cerca
    del último centroide válido. Si el más cercano supera el umbral de salto (ver
    constantes SALTO_*), el cuadro queda en NaN. El resumen se imprime y también
    queda en `trackear.ultimo_resumen` y en el atributo `.resumen` del array
    devuelto, sin cambiar la firma.
    """
    cap = cv2.VideoCapture(video)
    if not cap.isOpened():
        raise RuntimeError(f"No se pudo abrir el video: {video}")
    fps = cap.get(cv2.CAP_PROP_FPS)           # declarado, no necesariamente real
    if not fps or fps <= 0:
        raise RuntimeError("El video no informa fps")

    filas, i = [], 0
    previo = None
    saltos = deque(maxlen=SALTO_N_MEDIANA)
    descartados = 0
    multiples = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        candidatos = _contornos_candidatos(frame, color)
        forma = frame.shape[:2]
        elegido = None

        if len(candidatos) > 1:
            multiples += 1
            centros = [(_centroide(c, forma), c) for c in candidatos]
            centros = [(p, c) for p, c in centros if p is not None]
            if not centros:
                elegido = None
            elif previo is None:
                elegido = max((c for _, c in centros), key=cv2.contourArea)
            else:
                distancias = [np.hypot(p[0] - previo[0], p[1] - previo[1])
                              for p, _ in centros]
                j = int(np.argmin(distancias))
                if distancias[j] > _umbral_salto(saltos):
                    descartados += 1
                    elegido = None
                else:
                    elegido = centros[j][1]
        elif len(candidatos) == 1:
            elegido = candidatos[0]

        if elegido is not None:
            m = np.zeros(forma, np.uint8)
            cv2.drawContours(m, [elegido], -1, 255, -1)
            M = cv2.moments(m, binaryImage=True)
            x, y = M["m10"] / M["m00"], M["m01"] / M["m00"]
            if previo is not None:
                saltos.append(float(np.hypot(x - previo[0], y - previo[1])))
            previo = (x, y)
            filas.append((i / fps, x, y, SIGMA_PX, SIGMA_PX))
            if ver:
                cv2.circle(frame, (int(x), int(y)), 6, (0, 255, 0), 2)
        else:
            filas.append((i / fps, np.nan, np.nan, np.nan, np.nan))
        if ver:
            cv2.imshow("tracking (q para salir)", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                ver = False
                cv2.destroyAllWindows()
        i += 1
    cap.release()
    cv2.destroyAllWindows()

    with open(salida, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t_s", "x_px", "y_px", "sx_px", "sy_px"])
        w.writerows(filas)

    tabla = np.asarray(filas).view(TablaTracking)
    resumen = {
        "cuadros": i,
        "descartados_por_salto": descartados,
        "cuadros_con_multiples": multiples,
        "sin_deteccion": int(np.isnan(tabla[:, 1]).sum()) if tabla.size else 0,
    }
    tabla.resumen = resumen
    trackear.ultimo_resumen = resumen
    print(f"tracking: {resumen['cuadros']} cuadros | "
          f"{descartados} descartados por salto | "
          f"{multiples} con más de un contorno candidato")
    return tabla


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--salida", default="tabla.csv")
    ap.add_argument("--color", choices=list(COLORES), default="rojo")
    ap.add_argument("--ver", action="store_true", help="mostrar el seguimiento en pantalla")
    a = ap.parse_args()
    d = trackear(a.video, a.salida, a.color, a.ver)
    print(f"{len(d)} cuadros, {np.isnan(d[:, 1]).sum()} sin detección -> {a.salida}")