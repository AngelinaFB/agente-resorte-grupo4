"""Genera un video sintético de un resorte (MAS amortiguado) y guarda la verdad en verdad.json."""
import argparse, json
import cv2
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--k", type=float, default=12.0)        # N/m
ap.add_argument("--m", type=float, default=0.200)       # kg
ap.add_argument("--gamma", type=float, default=0.15)    # 1/s
ap.add_argument("--A", type=float, default=0.05)        # m
ap.add_argument("--fps", type=float, default=30)
ap.add_argument("--dur", type=float, default=8)         # s
ap.add_argument("--px-por-m", type=float, default=2000)
ap.add_argument("--ruido", type=float, default=4.0)     # desvío del ruido gaussiano (niveles de gris)
ap.add_argument("--blur", type=int, default=5)          # tamaño del kernel (impar)
ap.add_argument("--vertical", action="store_true")      # oscila en y en vez de x
ap.add_argument("--semilla", type=int, default=0)
ap.add_argument("--salida", default="sintetico.mp4")
a = ap.parse_args()

W, H = 640, 480
omega0 = np.sqrt(a.k / a.m)
omega = np.sqrt(omega0**2 - a.gamma**2)
rng = np.random.default_rng(a.semilla)

out = cv2.VideoWriter(a.salida, cv2.VideoWriter_fourcc(*"mp4v"), a.fps, (W, H))
for i in range(int(a.fps * a.dur)):
    t = i / a.fps
    x = a.A * np.exp(-a.gamma * t) * np.cos(omega * t)
    frame = np.full((H, W, 3), 230, np.uint8)
    d = int(x * a.px_por_m)
    cx, cy = (W // 2, H // 2 + d) if a.vertical else (W // 2 + d, H // 2)
    cv2.circle(frame, (cx, cy), 25, (0, 0, 200), -1)
    if a.blur > 1:
        frame = cv2.GaussianBlur(frame, (a.blur, a.blur), 0)
    frame = np.clip(frame + rng.normal(0, a.ruido, frame.shape), 0, 255).astype(np.uint8)
    out.write(frame)
out.release()

verdad = dict(k=a.k, m=a.m, gamma=a.gamma, A=a.A, omega=omega, T=2 * np.pi / omega,
              fps=a.fps, px_por_m=a.px_por_m, ruido=a.ruido, blur=a.blur)
with open(a.salida.rsplit(".", 1)[0] + "_verdad.json", "w") as f:
    json.dump(verdad, f, indent=2)
print(f"Video: {a.salida} | T verdadero = {verdad['T']:.4f} s")