import cv2, csv
import numpy as np
from scipy.signal import find_peaks


def marcar_dos_puntos(video):
    """Abre el primer cuadro; click en los dos extremos de la regla. Devuelve [(x1,y1),(x2,y2)]."""
    cap = cv2.VideoCapture(video)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise RuntimeError("No se pudo leer el video")
    puntos = []

    def click(evento, x, y, *_):
        if evento == cv2.EVENT_LBUTTONDOWN and len(puntos) < 2:
            puntos.append((x, y))
            cv2.circle(frame, (x, y), 4, (0, 255, 0), -1)

    cv2.namedWindow("Regla: 2 clicks, Enter para terminar")
    cv2.setMouseCallback("Regla: 2 clicks, Enter para terminar", click)
    while True:
        cv2.imshow("Regla: 2 clicks, Enter para terminar", frame)
        if cv2.waitKey(20) == 13 and len(puntos) == 2:
            break
    cv2.destroyAllWindows()
    return puntos


def escala_px_por_m(p1, p2, largo_m, sigma_punto_px=1.0, sigma_largo_m=0.0005):
    """px/m y su incerteza a partir de dos puntos sobre una regla de largo conocido."""
    d = float(np.hypot(p2[0] - p1[0], p2[1] - p1[1]))
    sigma_d = np.sqrt(2) * sigma_punto_px          # dos extremos, error de click en cada uno
    s = d / largo_m
    sigma_s = s * np.sqrt((sigma_d / d) ** 2 + (sigma_largo_m / largo_m) ** 2)
    return s, sigma_s


def fps_real_con_led(video, roi, f_led_hz):
    """fps real filmando un LED que parpadea a f_led_hz. roi=(x, y, w, h). Devuelve (fps, incerteza)."""
    cap = cv2.VideoCapture(video)
    x, y, w, h = roi
    brillo = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        brillo.append(frame[y:y + h, x:x + w].mean())
    cap.release()
    b = np.array(brillo)
    picos, _ = find_peaks(b, distance=2, prominence=0.3 * (b.max() - b.min()))
    if len(picos) < 4:
        raise RuntimeError("Muy pocos picos detectados: revisar ROI o frecuencia del LED")
    periodos = np.diff(picos)                      # cuadros entre parpadeos
    fps = f_led_hz * periodos.mean()
    sigma = f_led_hz * periodos.std(ddof=1) / np.sqrt(len(periodos))
    return fps, sigma


def a_metros(csv_entrada, csv_salida, px_por_m, sigma_px_por_m, x0_px=None, y0_px=None, fps_real=None):
    """Convierte la tabla (t, x, y, sx, sy) de px a m, con incerteza propagada.
    Origen: x0/y0 (equilibrio); si no se da, la media de la señal.
    Si se da fps_real, reescala t = t_declarado * fps_declarado / fps_real."""
    d = np.genfromtxt(csv_entrada, delimiter=",", names=True)
    t, x, y, sx, sy = d["t_s"], d["x_px"], d["y_px"], d["sx_px"], d["sy_px"]
    x0 = np.nanmean(x) if x0_px is None else x0_px
    y0 = np.nanmean(y) if y0_px is None else y0_px
    s, ss = px_por_m, sigma_px_por_m
    xm, ym = (x - x0) / s, -(y - y0) / s           # y hacia arriba
    sxm = np.sqrt((sx / s) ** 2 + ((x - x0) * ss / s ** 2) ** 2)
    sym = np.sqrt((sy / s) ** 2 + ((y - y0) * ss / s ** 2) ** 2)
    if fps_real is not None:
        cap = cv2.VideoCapture(csv_entrada.replace(".csv", ".mp4"))
        fps_decl = cap.get(cv2.CAP_PROP_FPS)
        cap.release()
        t = t * fps_decl / fps_real
    with open(csv_salida, "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["t_s", "x_m", "y_m", "sx_m", "sy_m"])
        wr.writerows(zip(t, xm, ym, sxm, sym))
    return t, xm, ym, sxm, sym


if __name__ == "__main__":
    # Video sintético: px/m conocido = 2000 (sin regla en la imagen)
    t, x, y, sx, sy = a_metros("tabla.csv", "tabla_m.csv", px_por_m=2000, sigma_px_por_m=2)
    print(f"Amplitud ≈ {np.nanmax(np.abs(x)):.4f} m (real: 0.0500 m)")