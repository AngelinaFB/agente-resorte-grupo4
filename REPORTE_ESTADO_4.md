# REPORTE_ESTADO_4 — Auditoría del estado actual (Grupo 4, Línea III, movimiento 3: resorte)

Actualización al 8 de noviembre de 2026. Este reporte audita el estado del repositorio después del commit `1b3be24` y separa lo verificado de lo que sigue pendiente. No reemplaza la consigna del curso ni afirma validación con datos reales del Grupo 8.

## Resumen ejecutivo

1. El árbol de trabajo estaba limpio y `HEAD` es `1b3be24` (“fix: tracking corregido funciona correctamente al hacer click sobre la masa”). Es el único commit nuevo desde `7251ffa`; `REPORTE_ESTADO_3.md` quedó intacto.
2. El último commit agregó un segundo método de seguimiento: flujo óptico a partir de un punto inicial (`punto_inicial`) y un selector de punto en la interfaz. MOG2 sigue siendo el método por defecto y el único disponible desde la CLI.
3. En la validación sintética, el método de punto recupera la verdad (`T=0.811299 s`, `k=12.0003 N/m`, `γ=0.1500 1/s`, `χ²r≈1.03`, 0 % de cuadros perdidos). MOG2 sigue el período y la constante con error pequeño, pero falla los criterios de calidad: 7.5–27.1 % de cuadros perdidos, `χ²r` 850–2255 y saltos máximos de 54–67 px.
4. En los tres videos reales, la corrida CLI por defecto (MOG2) analiza 3/3 videos pero produce resultados inválidos: 97.4 %, 94.6 % y 68.5 % de cuadros perdidos; `T=2.085`, `24.97` y `47.73 s`; `k=6.196`, `0.0318` y `0.00729 N/m`; los tres quedan marcados “Revisar”. El agregado (`T=24.93±13.2 s`) no tiene significado físico.
5. Con el método de punto y semillas derivadas en esta auditoría, Video2 recupera un tramo estable con `T≈0.6429 s` y `k≈32.61 N/m` solo al recortar el inicio; Video3 ya encuentra `T≈0.6420 s` y `k≈32.71 N/m` en el video completo, pero el recorte baja `χ²r` de `1.46×10⁴` a `359`. Video4 pierde 64 % de los cuadros y su ajuste estable es mucho menos confiable.
6. El ajuste actual usa el video completo, incluido el tramo previo a la liberación. Video2 tiene unos 4–6 s estáticos y Video4 unos 40 s de acomodo; sin `--inicio` ni recorte automático, el ajuste de Video2 y Video4 se “engancha” a la deriva y devuelve períodos de 9.26 s y 7.7×10⁶ s, respectivamente.
7. La app usa un único punto para todos los videos de la corrida. Con el punto de Video2 `(850,700)`, Video3 falla con `RuntimeError: el ajuste no tiene matriz de covarianza (¿no se detecta oscilación?)` y Video4 devuelve `T=21.51 s` con 72.4 % de cuadros perdidos.
8. El `χ²r` real es enorme porque `SIGMA_PX=0.29 px` es demasiado optimista: el residual RMS real es de aproximadamente 3.7–5 px. Si se reescala la incertidumbre al residual, el `χ²r` baja a valores del orden de 1; el período y `k` del tramo estable siguen siendo consistentes.
9. El período real robusto es `T≈0.641–0.643 s` en los ajustes estables (≈1.56 Hz); el mapa periódico independiente da `0.636–0.645 s`. Es independiente de la escala y de la masa. `k≈32.6–32.8 N/m` depende linealmente de la masa efectiva asumida; con los valores por defecto de la app (`m=0.250 kg`, `m_r=0.030 kg`) daría aproximadamente `24.8–25.0 N/m`.
10. No hay datos del Grupo 8, ni escala real, ni masa real, ni LED real. `C:\Users\crowl\Downloads\resultados.json` es de un video externo (“0_Traditional Experiment on mass spring system”), no del Grupo 8. La documentación (`README.md`, `RESUMEN_DEMO.md`) y el texto del selector siguen desactualizados; `requirements.txt` no tiene versiones; no hay tests; `diag_tracking.py` es un placeholder.

## 1. Alcance y método

- Repositorio auditado: `C:\Users\crowl\agente-resorte-grupo4`; código en `agente-resorte\`.
- Estado de Git: rama `main`, `HEAD 1b3be24`, árbol limpio antes de crear este reporte. El commit anterior de referencia es `7251ffa`.
- No se modificó ni se borró ningún archivo existente. Los scripts, JSON, CSV y cuadros de esta auditoría viven en `C:\Users\crowl\AppData\Local\Temp\opencode\audit4`.
- Se ejecutaron: `git status`, `git diff`, `git show`, `py_compile` de todos los `.py`, `main.py --help`, una corrida CLI real con `--salidas`, una corrida equivalente a la app con `analizar(..., punto_inicial=...)`, una prueba inicial de Streamlit `AppTest`, y scripts de análisis sintético/real.
- Los cuadros anotados se generaron, pero **no se pudieron inspeccionar visualmente** en este entorno. La validación visual queda pendiente; lo que sí se verificó es que el punto trackeado es más oscuro que el anillo, de forma programática (ver §7).

## 2. Cambios desde `7251ffa`

| Área | Cambio | Evidencia |
|---|---|---|
| `tracking.py` | Se agregó el modo de flujo óptico con `punto_inicial`: `_puntos_opticos`, `_flujo_local`, seguimiento acumulado y criterio de consistencia. MOG2 sigue siendo el modo por defecto. | Diff `7251ffa..HEAD`; el docstring actual dice “Tracking por movimiento con MOG2… Sin color/ROI”. |
| `app.py` | Se agregó el selector de punto sobre el primer cuadro y la vista previa del tracking por punto. El análisis pasa ese punto a `analizar`. | +192 líneas; componente `selector_punto_tracking`. |
| `main.py` | `analizar()` acepta `punto_inicial=None` y lo pasa a `trackear()`. **La función `main()` de la CLI no lo pasa**: la CLI nunca usa el método de punto. | Diff de 6 líneas en `main.py`. |
| Archivos nuevos | `agente-resorte/selector_punto_tracking/index.html`, `agente-resorte/sintetico_verdad.json`, `agente-resorte/tabla.csv`. | Inventario del commit. |
| Lo que no cambió | MOG2 por defecto; no hay `--punto`, `--inicio`, `--eje`, `--color`, `--hsv-min/--hsv-max`; no hay recorte automático; no hay re-detección si el punto se pierde. | `main.py --help` y lectura de `tracking.py`. |

El cambio de MOG2 ya venía del trabajo anterior (Reporte 3): la versión con HSV/ROI es histórica y no es la que está en `7251ffa`. Por eso el `README.md` y `RESUMEN_DEMO.md`, que todavía hablan de color/HSV/eje, están desactualizados respecto del código actual.

## 3. Inventario y estado de archivos

| Archivo / ruta | Tamaño / estado | Rol y observación |
|---|---|---|
| `agente-resorte/tracking.py` | Presente | MOG2 + flujo óptico opcional; constantes `SIGMA_PX=0.29`, `SALTO_FACTOR=4.0`, `SALTO_MIN_PX=8.0`, `SALTO_INICIAL_PX=60.0`, `SALTO_N_MEDIANA=15`, `SALTO_MIN_MUESTRAS=5`. |
| `agente-resorte/main.py` | Presente | Pipeline CLI, JSON e informe Markdown; `analizar(..., punto_inicial=None)`, pero `main()` no pasa punto. |
| `agente-resorte/app.py` | Presente | Streamlit; selector de punto; aplica el mismo punto a todos los videos. |
| `agente-resorte/ajuste.py` | Presente | `ajustar` con semilla FFT, `cantidades`, `χ²r`; `SIGMA_PX=0.29` se define en `tracking.py` y se usa en la tabla de tracking. |
| `agente-resorte/calibracion.py` | Presente | `a_metros`, `escala_px_por_m`, `fps_real_con_led`; la calibración espacial sigue siendo manual. |
| `agente-resorte/señal.py` | Presente | `rellenar_nan`, `procesar`; el rellenado interpola huecos, incluso huecos largos. |
| `agente-resorte/generador_sintetico.py` | Presente | Genera el video sintético y `sintetico_verdad.json`; no genera LED, dos marcas ni mancha de fondo (esas variantes se generaron en `audit4`). |
| `agente-resorte/diag_tracking.py` | 11 B | Placeholder; no es un diagnóstico funcional. |
| `agente-resorte/selector_punto_tracking/index.html` | 3137 B | Componente de click; el texto dice “Hacé clic sobre el punto rojo de la masa”, incoherente con el método sin color. |
| `agente-resorte/requirements.txt` | 72 B | Dependencias sin versiones; no hay lockfile. |
| `agente-resorte/tabla.csv` | 13309 B | Muestra sintética 640×480, 30 fps, 8 s; encabezado `t_s,x_px,y_px,sx_px,sy_px`. No es dato real. |
| `agente-resorte/sintetico_verdad.json` | Presente | Verdad sintética: `k=12`, `m=0.2`, `γ=0.15`, `A=0.05`, `ω=7.7445`, `T=0.8113079`, 30 fps, 2000 px/m, ruido 4, blur 5. |
| `README.md` y `agente-resorte/RESUMEN_DEMO.md` | Presentes | Desactualizados: describen tracking por color/HSV, `--eje`, ROI y una versión anterior del flujo. |
| `REPORTE_ESTADO_3.md` | 7061 B | Intacto. |
| `REPORTE_ESTADO_4.md` | Creado por esta auditoría | Este archivo. |
| `tests/`, `pyproject.toml`, `setup.cfg` | Ausentes | No hay suite de tests ni metadatos de empaquetado. |
| `agente-resorte/elegir_marca.py`, `dcl.py`, `assets/`, PDF de la consigna | Ausentes | No están en el repo; no se pudieron auditar. |

## 4. Cómo funciona el tracking actual

### 4.1 MOG2 (por defecto)

- `trackear()` crea `cv2.createBackgroundSubtractorMOG2` y procesa el cuadro completo; no hay ROI ni color.
- Aplica morfología, filtra componentes por área, elige el candidato más cercano al centroide anterior y descarta saltos mayores que un umbral adaptativo.
- Si no hay candidato, deja `NaN`; el pipeline luego interpola. No hay re-detección ni “modo perdido”.
- El umbral de salto se adapta con la mediana de los últimos 15 saltos; los primeros cuadros usan `SALTO_INICIAL_PX=60`.
- El primer cuadro elige el contorno de mayor área (no necesariamente la masa) y luego sigue el más cercano.

### 4.2 Punto / flujo óptico (opcional)

- Solo se activa si se pasa `punto_inicial=(x,y)`. En la app se activa con el click; en la CLI no hay forma de pasarlo.
- `_puntos_opticos` toma hasta 40 features en un radio de 18 px alrededor del punto inicial; `_flujo_local` usa Lucas–Kanade con verificación forward–backward y toma la mediana del desplazamiento de los features consistentes.
- Acumula el desplazamiento cuadro a cuadro. No vuelve a detectar la masa ni corrige deriva; si la mediana se contamina con fondo, el punto se va.
- El método es sensible al punto inicial. En la app, un mismo punto se usa para todos los videos de la corrida.

### 4.3 CLI vs. app

| Capacidad | CLI (`main.py`) | App (`app.py`) |
|---|---|---|
| MOG2 | Sí, por defecto | Sí |
| Punto inicial | **No** (no hay argumento) | Sí, con click |
| Punto por video | No | **No**: un punto para toda la corrida |
| Recorte de inicio | No | No |
| Elección de eje | Automática | Automática |
| ROI/HSV/color | No | No |
| LED/fps | `--roi` solo para LED | Campos de LED |

## 5. Validación sintética

### 5.1 Escenarios

Se generaron en `audit4\sint` con el mismo modelo del generador oficial (`k=12 N/m`, `m=0.2 kg`, `γ=0.15 1/s`, `A=0.05 m`, 30 fps, 8 s, 2000 px/m, ruido 4, blur 5):

- `a1`–`a4`: una marca roja + LED de 10 Hz en la esquina.
- `b`: dos marcas rojas del mismo color, separadas 60 px.
- `c`: una mancha roja estática de radio 45 px en el fondo, más grande que la masa (radio 25 px).
- El punto inicial del método de punto es el centro exacto de la masa en `t=0` (oráculo); en la app eso lo aporta el click humano.

### 5.2 Resultados

Verdad: `T=0.8113079 s`, `k=12 N/m`, `γ=0.15 1/s`.

| Video | Método | T (s) | k (N/m) | γ (1/s) | χ²r | Perdidos | Salto máx (px) | FFT T (s) | Multi |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| a1 | MOG2 | 0.81283 | 11.956 | 0.1665 | 2255 | 27.1 % | 66.1 | 0.8333 | 168 |
| a1 | punto | 0.811299 | 12.0003 | 0.15002 | 1.03 | 0.0 % | 25.0 | 0.8000 | 0 |
| a2 | MOG2 | 0.81245 | 11.965 | 0.1330 | 1096 | 19.6 % | 67.5 | 0.8042 | 177 |
| a2 | punto | 0.811297 | 12.0003 | 0.15003 | 1.02 | 0.0 % | 25.0 | 0.8000 | 0 |
| a3 | MOG2 | 0.81236 | 11.968 | 0.1345 | 1114 | 21.7 % | 67.1 | 0.7833 | 172 |
| a3 | punto | 0.811300 | 12.0002 | 0.15000 | 1.03 | 0.0 % | 25.0 | 0.8000 | 0 |
| a4 | MOG2 | 0.81254 | 11.963 | 0.1327 | 999 | 17.5 % | 59.0 | 0.7333 | 172 |
| a4 | punto | 0.811299 | 12.0003 | 0.15001 | 1.03 | 0.0 % | 25.0 | 0.8000 | 0 |
| b | MOG2 | 0.81232 | 11.968 | 0.1129 | 850 | 7.5 % | 54.3 | 0.8222 | 225 |
| b | punto | 0.811300 | 12.0002 | 0.15001 | 1.03 | 0.0 % | 25.0 | 0.8000 | 0 |
| c | MOG2 | 0.81254 | 11.962 | 0.1190 | 950 | 15.4 % | 67.0 | 0.7519 | 166 |
| c | punto | 0.811298 | 12.0003 | 0.15003 | 1.03 | 0.0 % | 25.0 | 0.8000 | 0 |

Lectura:

- El método de punto reproduce la verdad dentro de la incertidumbre y cumple `χ²r≈1`, 0 % perdidos y saltos coherentes con el movimiento real (≈25 px).
- MOG2 aproxima bien `T` y `k` (error <1 %), pero no cumple los criterios de calidad: muchos cuadros perdidos, `χ²r` de 850–2255 y saltos de 54–67 px. En `b` y `c` se confunde con la segunda marca o con la mancha de fondo, aunque el período no se degrada tanto.
- La ventaja del punto es la robustez ante candidatos múltiples/fondo; su debilidad es que necesita un punto inicial correcto y no se recupera si se pierde.

### 5.3 LED y agregado

- LED de 10 Hz en `a1`: `fps=30.0±0.327` tanto con ROI `(20,20,40,40)` como con el cuadro completo. Pasa el criterio.
- Agregado con los 4 videos de punto (misma masa/incertidumbres compartidas):
  - `T=0.8112989±6.35×10⁻⁷ s`.
  - `k=12.000265±0.060035 N/m`; la componente sistemática (`0.060035`) no se divide por `√N`, la estadística sí: `1.915×10⁻⁵` para N=4 frente a `2.711×10⁻⁵` para N=2.
  - `γ=0.1500120±0.0000066` (sin componente sistemática; la incertidumbre es la estadística del ajuste agregado).
- El agregado es correcto en su matemática; el problema es que en datos reales se está agregando ruido/deriva, no repeticiones comparables.

## 6. Videos reales

### 6.1 Datos disponibles

| Video | Resolución | FPS | Cuadros | Duración | Observación |
|---|---|---:|---:|---:|---|
| `Video2_R1_P1.MOV` | 1920×1080 | 59.9709 | 1237 | 20.61 s | Liberación/aprox. 5.5–6 s; oscilación clara. |
| `Video3_R1_P1.MOV` | 1920×1080 | 59.9711 | 1868 | 31.15 s | Oscilación clara desde ≈6 s; el punto tiene un hueco de detección de ≈2 a 6 s. |
| `Video4_R1_P1.MOV` | 1920×1080 | 59.9713 | 3341 | 55.72 s | Acomodo largo; oscilación clara recién después de ≈40 s. |

- No hay videos del Grupo 8 en el repo ni en las rutas auditadas. `C:\Users\crowl\Downloads\resultados.json` corresponde a un video externo, no al Grupo 8.
- No hay escala real, masa real ni LED real. Para esta auditoría se usaron valores provisorios: `m=0.3090±0.0010 kg`, `m_r=0.09730±0.00010 kg` (masa efectiva `0.34143 kg`) y `escala=2000±2 px/m`. **No son mediciones del Grupo 8.**
- `T` no depende de la escala ni de la masa. `k` sí depende linealmente de `m_ef`: con `m_ef=0.34143 kg` da `≈32.6–32.8 N/m`; con los defaults de la app (`m=0.250`, `m_r=0.030`, `m_ef=0.260`) daría `≈24.8–25.0 N/m`. Ninguno de los dos debe presentarse como resultado final.

### 6.2 Corrida CLI por defecto (MOG2)

Comando equivalente al de la app, sin punto inicial, con `--salidas audit4\cli_real`. Resultado: 3/3 videos analizados, 0 errores, **3/3 “Revisar”**.

| Video | Eje | T (s) | k con m_ef (N/m) | γ (1/s) | χ²r | Perdidos | Ciclos | Cuadros/T |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Video2 | x | 2.085±0.012 | 6.196±0.095 | 3.011±0.043 | 29.6 | 97.4 % | 9.89 | 125.0 |
| Video3 | y | 24.97±0.57 | 0.0318±0.0018 | 0.173±0.010 | 7.44×10³ | 94.6 % | 1.25 | 1497.7 |
| Video4 | y | 47.73±0.46 | 0.00729±0.00017 | 0.0635±0.0023 | 6.87×10⁴ | 68.5 % | 1.17 | 2862.2 |

Un reajuste posterior con otro eje/umbral dio valores compatibles en la conclusión: `T=2.08/24.32/47.30 s`, `k=6.20/0.0327/0.00744 N/m`, `χ²r=30/9139/90490`. La diferencia fina no cambia el diagnóstico: el MOG2 por defecto no sigue la masa en estos videos.

Agregado de la corrida CLI: `T=24.93±13.2 s`, `k=2.078±2.06 N/m`, `γ=1.082±0.965 1/s`. Es un promedio de resultados inválidos; no debe usarse.

### 6.3 Método de punto con semillas de auditoría

Semillas correctas en el primer cuadro: Video2 `(850,700)`, Video3 `(840,708)`, Video4 `(860,421)`. La semilla `(848,704)` para Video4, que había aparecido como máximo del diff, **no** es la masa: falla con 67.9 % de cuadros perdidos y un salto máximo de 163 px. MOG2 detecta la masa de Video4 por primera vez en `(859.8,421.0)`.

| Video | Semilla | Detectados | Perdidos | Salto máx (px) | Ajuste completo | Tramo estable | FFT del tramo |
|---|---|---:|---:|---:|---|---|---:|
| Video2 | `(850,700)` | 1237/1237 | 0.0 % | 25.4 | `T=9.258±0.228 s`, `k=0.159±0.008`, `χ²r=8.81×10⁴` | `t≥8.5 s`: `T=0.642906±0.000027 s`, `k=32.6115±0.0956`, `γ=0.01283±0.00041`, `χ²r=176`, `A=0.08485 m` | 0.6380 s |
| Video3 | `(840,708)` | 1562/1868 | 16.4 % | 22.1 | `T=0.64204±0.00009 s`, `k=32.699±0.096`, `χ²r=1.46×10⁴` | `t≥6.5 s`: `T=0.641978±0.000016 s`, `k=32.7059±0.0959`, `γ=0.01122±0.00025`, `χ²r=359`, `A=0.07106 m` | 0.6486 s |
| Video4 | `(860,421)` | 1204/3341 | 64.0 % | 28.1 | `T=7.7×10⁶ s` (basura), `k=0.00196`, `χ²r=8.03×10⁴` | `t≥44.5 s`: `T=0.640840±0.000682 s`, `k=32.822±0.119`, `γ≈0`, `χ²r=4.61×10⁴`, `A=0.0503±0.0264 m` | 0.6591 s |

Notas:

- El tramo estable de Video2 y Video3 da `T≈0.642 s` y `k≈32.6–32.7 N/m` con `m_ef=0.34143 kg`. Es el resultado más consistente de la auditoría. Video2 depende del recorte (`t≥8.5 s`); Video3 ya da `T/k` correctos en el video completo, pero el recorte baja `χ²r` de `1.46×10⁴` a `359`. Ambos dependen de la masa provisoria.
- Video4 es el caso problemático: 64 % de cuadros perdidos y un ajuste estable con `χ²r=4.6×10⁴`. En el tramo `t≥44.5 s` el punto solo tiene 93/672 cuadros detectados (13.8 %); el ajuste estable está dominado por interpolación. El período `0.6408 s` coincide con los otros videos, pero no se puede afirmar que el tracking sea confiable. El ajuste descartando `NaN` falla con `Input must be 1- or 2-d.`.
- MOG2 sobre Video4 después de `t=40 s` sí detecta 83.5 % (787/942) y 95.5 % después de `t=44.5 s` (642/672), y da `T=0.64136 s`, `k=32.77 N/m`, `χ²r=2.57×10⁴`. Es decir, el video contiene la oscilación, pero el pipeline actual no recorta ni cambia de método.
- El período también se verificó de forma independiente con un mapa periódico por regiones, sin usar el tracker: Video2 `T=0.64458 s` en `(856,960)`; Video3 `T=0.63568 s` en `(872,992)`; Video4 `T=0.64034 s` en `(888,960)`, además de una componente lenta `T=2.65 s` en la zona de la persona/cámara. La componente de ≈0.64 s es real y consistente.

### 6.4 Prueba equivalente a la app (un punto para todos)

Se usó el punto `(850,700)` de Video2 para los tres videos, como hace la app al aplicar el mismo punto a toda la corrida.

| Video | Resultado | T (s) | k con m_ef (N/m) | χ²r | Perdidos |
|---|---|---:|---:|---:|---:|
| Video2 | “OK”, pero mal ajuste | 9.38±0.25 | 0.1548±0.0082 | 7.42×10⁴ | 0.0 % |
| Video3 | **Falla** | — | — | — | 228/1868 (12.2 %) |
| Video4 | “OK”, pero mal ajuste | 21.51±0.16 | 0.02936±0.00043 | 3.57×10⁴ | 72.4 % |

Error de Video3: `RuntimeError: el ajuste no tiene matriz de covarianza (¿no se detecta oscilación?)`. El informe de la app marca “Videos analizados correctamente: 2” y “Videos con errores: 1”; el agregado de los dos que sí terminan es `T=15.45±6.07 s`, también sin significado.

### 6.5 Sobre el `χ²r` real

- `SIGMA_PX=0.29 px` es la incertidumbre asumida para cada centroide. En los videos reales el residual RMS del ajuste es de ≈3.7–5 px (depende del tramo y del método).
- Con `σ=0.29 px`, cualquier imperfección de tracking produce `χ²r` de cientos a decenas de miles. No es que el modelo físico esté mal: es que la incertidumbre declarada es demasiado chica.
- Si se reescala `σ` al RMS residual, el `χ²r` del tramo estable baja a valores del orden de 1. El período y `k` no cambian sustancialmente. La conclusión práctica: **no usar `χ²r` con `σ=0.29` como único criterio de aceptación en datos reales**; estimar `σ` del tracking o reportar el RMS residual.
- El criterio de la app (“hasta 5 % perdidos, `χ²r` 0.3–3, ≥5 ciclos”) es razonable como guía, pero con el `σ` actual ningún video real puede cumplirlo aunque el período sea correcto.

## 7. Evidencia visual generada

- Para cada video y método se generaron 12 PNG en `audit4\cuadros_reales\`:
  - `Video2_punto`, `Video2_mog2`, `Video3_punto`, `Video3_mog2`, `Video4_punto`, `Video4_mog2`.
  - 8 cuadros equiespaciados + 4 de mayor salto (pueden solaparse); la selección está en `seleccion.txt`.
- En el método de punto: círculo/cruz verde en el centroide, cruz azul en el punto inicial y puntos azules en los features del flujo óptico en el primer cuadro; texto rojo si el cuadro se perdió.
- En MOG2: contornos grises, contorno elegido en verde y centroide en rojo; texto rojo si no hubo detección.
- **No se pudieron revisar visualmente las imágenes.** Lo verificado programáticamente es que el punto trackeado es más oscuro que el anillo: diferencia BGR aproximada de `−80/−82/−87` en Video2, `−21/−25/−27` en Video3 y `−6.8/−4.8/−5.5` en Video4. Eso es consistente con una masa oscura y explica el bajo contraste de Video4. No se afirma nada más sobre el contenido visual.

## 8. Requisitos y criterios de aceptación

| Requisito / criterio | Estado | Evidencia |
|---|---|---|
| Funcionar sin internet | Cumplido | OpenCV clásico; no hay descargas ni servicios en la nube en el flujo. |
| Seguir la masa varios ciclos y no saltar a mano/objeto | **Parcial / falla en real** | Sintético punto: 0 % perdidos; real MOG2: 68–97 % perdidos; real punto: Video2/3 aceptable con recorte, Video4 64 % perdidos. |
| Informar cuadros perdidos o baja confianza | Cumplido | `perdidos_pct`, `saltos_descartados`, `frames_con_multiples_candidatos`, estado “Revisar”. |
| Calibración espacial automática de la regla | **No implementado** | `calibracion.py` requiere longitud y coordenadas de extremos; el Reporte 3 ya lo marcaba pendiente. |
| Recuperar la verdad sintética | Punto: cumple; MOG2: parcial | Punto `χ²r≈1.03`, 0 % perdidos; MOG2 `χ²r` 850–2255, 7.5–27.1 % perdidos. |
| Medir FPS con LED | Cumplido en sintético | `30.0±0.327` con ROI y full frame. |
| Propagación de incertidumbres y agregado | Cumplido en la matemática | `σ_sis` no se divide por `√N`; `σ_est` sí. |
| Informe/JSON versionado y legible | Cumplido | `main.py` genera informe Markdown y JSON con unidades/alertas. |
| Tests automatizados | **Ausente** | No hay `tests/`, `pytest` ni CI. |
| Reproducibilidad de dependencias | **Parcial** | `requirements.txt` sin versiones; no hay lockfile. |
| No usar IA preentrenada | Cumplido | Visión clásica OpenCV. |
| Validación con videos reales del Grupo 8 | **No realizado** | No hay datos del Grupo 8; los videos auditados son `Video2/3/4_R1_P1.MOV` y no hay escala/masa reales. |
| Interfaz sin pasos manuales de color/ROI | Cumplido | No hay selector de color/ROI; sí hay click de punto. |
| Un punto por video | **No cumplido** | La app usa el mismo punto para toda la corrida. |
| Recorte del tramo previo a la liberación | **No implementado** | No hay `--inicio` ni detección automática. |

## 9. Problemas y limitaciones (ordenados por impacto)

1. **La CLI no puede usar el método de punto.** `main()` no pasa `punto_inicial`; la corrida por defecto es MOG2 y falla en los tres videos reales. Es el problema más grave para reproducir el análisis desde línea de comandos.
2. **La app aplica un solo punto a todos los videos.** Con el punto de Video2, Video3 falla y Video4 da un resultado incorrecto. El punto debería elegirse por video (o detectarse automáticamente).
3. **No hay recorte de inicio.** El ajuste completo incluye el tramo estático/acomodo. Video2 y Video4 se “enganchan” a la deriva; Video3 tiene suerte y encuentra el período, pero con `χ²r` enorme. Falta `--inicio` o detección de liberación.
4. **`SIGMA_PX=0.29 px` no representa el error real.** El `χ²r` queda inflado por 2–4 órdenes de magnitud. Hay que estimar `σ` del tracking o usar el RMS residual.
5. **El método de punto no se recupera si se pierde.** No hay re-detección, búsqueda local por plantilla ni combinación con MOG2. En Video4 pierde 64 % de los cuadros; la mediana de features puede seguir fondo.
6. **Video4 necesita un tratamiento específico.** La masa está en `(860,421)`, no en `(848,704)`. La oscilación útil empieza después de ≈40 s. MOG2 post-40 funciona mejor que el punto, pero el pipeline no lo hace.
7. **Documentación desactualizada.** `README.md` y `RESUMEN_DEMO.md` describen HSV/color/ROI/`--eje`, que ya no existen. El texto del selector dice “punto rojo”, incoherente con el método actual.
8. **Sin tests, sin versiones fijas, sin diagnóstico.** `requirements.txt` no fija versiones; `diag_tracking.py` es un placeholder; no hay tests de tracking/ajuste/agregado.
9. **Sin datos reales del Grupo 8.** No se puede validar la escala, la masa, el LED ni comparar `k` dinámica con `k` estática. Los valores `0.309/0.0973/2000` son provisorios.
10. **`tabla.csv` y `sintetico_verdad.json` son muestras sintéticas.** No deben presentarse como datos reales.
11. **El agregado de resultados inválidos no se bloquea.** La app/CLI marca “Revisar”, pero igual calcula y muestra un promedio (por ejemplo `T=24.93±13.2 s`). Convendría no agregar videos con estado inválido o marcarlo explícitamente.
12. **El botón de análisis requiere un punto.** Sin click, “Analizar videos” queda deshabilitado. Es esperable, pero debe documentarse; además el click es sobre el primer cuadro y no se reutiliza por video.

## 10. Pendientes y recomendaciones

### 10.1 Corto plazo (para que el flujo sea usable)

- Agregar `--punto X Y` (idealmente repetible o por nombre de video) a `main.py` y pasarlo a `analizar()`. Mientras tanto, documentar que la CLI solo hace MOG2.
- En la app, permitir un punto por video (o reutilizar el punto solo si el usuario lo confirma). No aplicar el punto de Video2 a Video3/Video4.
- Agregar `--inicio` y/o detección automática de liberación; ajustar solo el tramo oscilatorio. Para Video2/3, `t≥6.5–8.5 s`; para Video4, `t≥40–44.5 s`.
- Estimar `σ` del tracking (o usar el RMS residual) y no hardcodear `0.29 px` para datos reales. Reportar `χ²r` con la incertidumbre usada y el RMS.
- Para Video4, usar MOG2 después de `t≈40 s` o el punto `(860,421)` con re-detección. No usar `(848,704)`.

### 10.2 Mediano plazo (robustez)

- Mejorar el punto: re-detección por plantilla/contorno cuando la confianza baja, búsqueda en una ventana del tamaño de la masa, combinación MOG2+punto, o un tracker de una sola hipótesis con validación.
- Validar el tracker con una etiqueta manual de unos cientos de cuadros en Video2/3/4; medir error de centroide y porcentaje de deriva.
- Implementar la calibración automática de la regla con confianza e incertidumbre; hasta entonces, no describirla como automática.
- Agregar tests: `pytest` para `ajustar`/`cantidades`, `rellenar_nan`, `agregado`, tracking sintético y un end-to-end con un video sintético. Incluir un test que verifique que `main()` no acepta punto (o, mejor, que lo acepta cuando se implemente).
- Fijar versiones en `requirements.txt` o agregar un lockfile; documentar la versión de Python/OpenCV usada.
- Actualizar `README.md`, `RESUMEN_DEMO.md` y el texto de `selector_punto_tracking/index.html`; eliminar referencias a HSV/color/ROI/`--eje`.
- Completar o eliminar `diag_tracking.py`; si se elimina, dejar el diagnóstico en un script de `tools/` o en la documentación.

### 10.3 Datos reales

- Conseguir los videos del Grupo 8, la escala real (regla), la masa real y el LED; repetir la corrida y comparar `k` dinámica con `k` estática.
- Mientras no haya datos del Grupo 8, presentar `T≈0.642 s` como el resultado robusto y `k≈32.6 N/m` solo como estimación condicionada a `m_ef=0.34143 kg`; aclarar que con los defaults de la app daría `≈24.8–25.0 N/m`.
- No usar `C:\Users\crowl\Downloads\resultados.json` como dato del Grupo 8: es un video externo.

## 11. Lo que no se pudo verificar

- **Inspección visual** de los 72 PNG generados. No hay visión de imágenes en este entorno; solo se verificó el contraste del punto de forma programática.
- **Click humano real** en el navegador. Se ejecutó `AppTest` inicial (renderiza, no lanza excepción, botón deshabilitado), pero no se subieron videos ni se hizo click en el componente.
- **Corrida completa de la app** con videos subidos. La prueba “equivalente a la app” usó `analizar(..., punto_inicial=...)` directamente, no la UI.
- **Escala, masa, LED y videos del Grupo 8.** No están disponibles.
- **Calibración automática de la regla.** No está implementada.
- **Reproducción del video anotado** con `cv2.VideoWriter`/`avc1` en el entorno real de Streamlit. No se ejercitó.
- **Suite de tests.** No existe; no se pudo correr `pytest` ni un lint/typecheck del proyecto.
- **Comportamiento de `main.py` con `--roi` y LED reales.** El `--roi` existe solo para LED/fps; no se probó con un LED real.

## 12. Anexo: comandos, rutas y reproducibilidad

### 12.1 Comandos usados

```powershell
git status --short
git log --oneline -5
git diff 7251ffa..HEAD --stat
git diff 7251ffa..HEAD -- agente-resorte/main.py
git show 7251ffa:agente-resorte/tracking.py
.\venv\Scripts\python.exe -m py_compile ajuste.py app.py calibracion.py diag_tracking.py generador_sintetico.py main.py señal.py tracking.py
.\venv\Scripts\python.exe main.py --help
.\venv\Scripts\python.exe main.py <videos> --masa 0.309 --sigma-masa 0.001 --masa-resorte 0.0973 --sigma-masa-resorte 0.0001 --escala 2000 --sigma-escala 2 --salidas <audit4>\cli_real
.\venv\Scripts\python.exe <audit4>\run_sint.py
.\venv\Scripts\python.exe <audit4>\run_real.py
.\venv\Scripts\python.exe <audit4>\run_app_equiv.py
.\venv\Scripts\python.exe <audit4>\run_visual.py
```

### 12.2 Archivos de respaldo de la auditoría

En `C:\Users\crowl\AppData\Local\Temp\opencode\audit4`:

- `sint_resultados.json`: tabla sintética completa (a1–a4, b, c, MOG2/punto, LED, agregados N=2/N=4).
- `real_table.json`: tabla real completa (MOG2, punto, tramos estables, drop-NaN, Video4 post-40).
- `reales_punto.json`, `reales_mog2.json`, `seed_search_v2.json`, `frame0_mass.json`.
- `cli_real\informe.md`, `app_equiv\informe.md`, `app_equiv\resultados.json`.
- `periodic_maps.json`, `motion_maps.json`: mapas periódicos/de movimiento por regiones.
- `cuadros_reales\<Video>_<metodo>\`: 12 PNG por combinación + `seleccion.txt`.
- `sint\`: videos sintéticos y verdades; `salidas_sint\`: CSV/informes por escenario.
- `gen_sint.py`, `run_sint.py`, `run_real.py`, `run_app_equiv.py`, `run_visual.py`: scripts reproducibles.

### 12.3 Entorno

- Windows, PowerShell 5.1; Python 3.14.8 en `agente-resorte\venv`; OpenCV, NumPy, SciPy, `uncertainties`, Streamlit (versiones no fijadas en `requirements.txt`).
- Videos reales: `C:\Users\crowl\Downloads\resorte\Video2_R1_P1.MOV`, `Video3_R1_P1.MOV`, `Video4_R1_P1.MOV`.
- `git status` final: solo `REPORTE_ESTADO_4.md` como archivo nuevo; ningún archivo existente modificado.

### 12.4 Conclusión operativa

- **Resultado robusto:** `T≈0.641–0.643 s` (≈1.56 Hz) en los tres videos, confirmado por el método de punto en tramos estables y por el mapa periódico independiente.
- **Resultado condicionado:** `k≈32.6–32.8 N/m` solo si se acepta `m_ef=0.34143 kg` y la escala provisoria; no es un resultado final del Grupo 8.
- **Lo que no está listo:** la corrida CLI por defecto, la app con un punto para todos, el recorte automático, la calibración real y la validación con datos del Grupo 8.
- **Próximo paso mínimo:** implementar punto por video + `--inicio`/recorte y estimación de `σ`; después, repetir la corrida real y comparar `k` dinámica con `k` estática.
