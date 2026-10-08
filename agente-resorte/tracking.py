"""Tracking por color con OpenCV: video -> tabla (t, x, y, σx, σy) en píxeles.
Offline, sin dependencias extra."""
import argparse, csv
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
    """Devuelve array (N, 5): t_s, x_px, y_px, sx_px, sy_px. NaN donde no se detectó."""
    cap = cv2.VideoCapture(video)
    if not cap.isOpened():
        raise RuntimeError(f"No se pudo abrir el video: {video}")
    fps = cap.get(cv2.CAP_PROP_FPS)           # declarado, no necesariamente real
    if not fps or fps <= 0:
        raise RuntimeError("El video no informa fps")

    filas, i = [], 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        m = mascara(frame, color)
        if m is not None:
            M = cv2.moments(m, binaryImage=True)
            x, y = M["m10"] / M["m00"], M["m01"] / M["m00"]
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
    return np.array(filas)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--salida", default="tabla.csv")
    ap.add_argument("--color", choices=list(COLORES), default="rojo")
    ap.add_argument("--ver", action="store_true", help="mostrar el seguimiento en pantalla")
    a = ap.parse_args()
    d = trackear(a.video, a.salida, a.color, a.ver)
    print(f"{len(d)} cuadros, {np.isnan(d[:, 1]).sum()} sin detección -> {a.salida}")