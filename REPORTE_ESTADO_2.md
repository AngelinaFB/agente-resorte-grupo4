# REPORTE_ESTADO_2 — Auditoría del proyecto (Grupo 4, Línea III, movimiento 3: Resorte)

Auditoría sobre el árbol de trabajo limpio (`git status` inicial: sin cambios) y ejecuciones de prueba
**fuera del repo** (`C:\Users\crowl\AppData\Local\Temp\opencode\audit2`). No se modificó ni borró ningún
archivo de código; este informe es el único archivo nuevo.

## Resumen (5 líneas)

1. El pipeline completo y una interfaz Streamlit nueva existen en código; los 7 `.py` compilan y el flujo
   corre de punta a punta con videos **sintéticos** (horizontal, vertical y LED).
2. **No hay ningún dato real**: 0 videos, 0 CSV/JSON de medición, 0 informes de corrida real, 0 link de
   Drive y 0 datos del Grupo 8 en el repo; todo lo reproducible es sintético.
3. Respecto del estado conocido se agregaron `app.py`, la sección de interfaz del README, la dependencia
   `streamlit`, la conexión del fps con LED a `main.py`, máximos/energías con incerteza y el veredicto del
   chequeo de período; el `REPORTE_ESTADO.md` anterior quedó desactualizado en varios puntos.
4. Casi todos los requisitos de la consigna están implementados, pero se clasifican **PARCIAL** porque
   nunca se ejecutaron con datos reales; **diagramas de cuerpo libre** y **comparación contra el Grupo 8**
   siguen **FALTA**; las limitaciones automáticas existen pero la sección manual queda vacía.
5. Hallazgo crítico nuevo: el **resultado agregado descarta la incerteza sistemática del fps** (con LED,
   cada video da T ± 0.0088 s y k ± 0.28 N/m, pero el agregado de 2 videos da T ± 0.000004 s y k ± 0.00012 N/m),
   además de seguir asumido `SIGMA_PX = 0.29 px`, sin barrido de ventana Savitzky-Golay, sin tests y sin
   versiones fijas en `requirements.txt`.

---

## 1. Inventario del repo (sólo archivos versionados; se excluyen `venv/` y `__pycache__/`)

| Archivo | Qué hace | ¿Nuevo respecto del estado conocido? |
|---|---|---|
| `.gitignore` | Ignora `venv/`, `__pycache__/`, `*.mp4/*.avi/*.mov`, `datos/`, `salidas/`, etc. | No |
| `README.md` | Instalación, uso de la interfaz, receta por archivo, argumentos de incerteza y LED. | Actualizado (interfaz y LED) |
| `Proyectos-Lineas_II_y_III.pdf` | PDF de la consigna de la cátedra (230 KB). No es dato experimental ni informe del grupo. | No |
| `REPORTE_ESTADO.md` | Auditoría anterior. **Contiene afirmaciones que ya no coinciden con el código** (ver problemas). | Documento previo; no es dato |
| `agente-resorte/ajuste.py` | Modelo `x(t)=A e^{-γt}cos(ωt+φ)+C`, ajuste lmfit ponderado, covarianza, `T/γ/k`, k estático, chequeo de período, energías y máximos con incerteza, gráficos. | No (con mejoras) |
| `agente-resorte/app.py` | Interfaz Streamlit: sube videos, escala px/m o regla por coordenadas, masa/eje/color/ventana, FPS opcional, k estático opcional; muestra resultados y descarga informe/JSON/ZIP. | **Sí (nuevo, commit `f189fb2`)** |
| `agente-resorte/calibracion.py` | Escala px/m con σ, fps real con LED, conversión px→m con propagación y corrección de tiempos. | No |
| `agente-resorte/generador_sintetico.py` | Genera video sintético de MAS amortiguado y `*_verdad.json` con la verdad. | No |
| `agente-resorte/main.py` | CLI completo: tracking → calibración → señal → ajuste → agregado → informe Markdown + JSON. | No (con mejoras) |
| `agente-resorte/requirements.txt` | Dependencias: numpy, scipy, opencv-python, lmfit, uncertainties, matplotlib, streamlit. **Sin versiones.** | Sí: se agregó `streamlit` |
| `agente-resorte/RESUMEN_DEMO.md` | Resumen de demo, guion y estado sintético (incluye resultados de una corrida sintética). | **Sí (commit `fdc10aa`, 2026-10-25)** |
| `agente-resorte/señal.py` | Relleno de NaN, derivación por `np.gradient`, Savitzky-Golay, comparación crudo/filtrado, gráfico. | No |
| `agente-resorte/tracking.py` | Tracking HSV por color, contorno mayor, centroide por momentos, tabla `t,x,y,σx,σy`; `SIGMA_PX=0.29`. | No |

Además hay un `agente-resorte/venv/` local **ignorado por git** que sólo contiene `pip` (las dependencias
del proyecto no están instaladas ahí), y `__pycache__/` ignorado. No hay carpetas `datos/`, `salidas/`,
`tests/`, `assets/`, notebooks ni imágenes versionadas.

---

## 2. Requisitos de la consigna

Criterio aplicado: **no se marca HECHO si no hay una ejecución con datos reales**. Todo lo ejecutado en esta
auditoría es sintético y se indica así.

| Requisito | Estado | Evidencia (archivo:función/línea) | Observaciones |
|---|---|---|---|
| Todo número con unidad e incerteza | PARCIAL | `main.py:17-22` (`fmt`), informe `main.py:101-207` | T, γ, k, escala, masa, máximos, energías y ΔEt salen con σ y unidad. **Sin σ**: RMS crudo/filtrado (`main.py:158,165-166`), `χ² red.` y, si no hay LED, el fps sale como “sin incerteza estimada”. |
| Resultado = N mediciones + criterio + referencia | PARCIAL | N y fallidos `main.py:103`; media ± EEM y dispersión `main.py:92-98,131-136` | N y criterio (media ± error estándar, dispersión) están. **La referencia (Grupo 8) no existe** en el repo ni en el informe. |
| Limitaciones obligatorias | PARCIAL | Automáticas `main.py:179-205`; plantilla manual vacía `main.py:206-207` | Detecta cuadros perdidos, χ², ciclos, muestras/período, γ≈0, N<5, fps no verificado, falta k estático y fallidos. “Qué falló / en qué condición se rompe / qué quedó sin resolver” queda **sin completar**. |
| Calibración espacial (px/m con σ) | PARCIAL | `calibracion.py:6-36` (`marcar_dos_puntos`, `escala_px_por_m`); CLI `main.py:220-223,277-282`; app `app.py:42-98,156-163` | Implementada y con propagación. Se ejecutó sólo con escala conocida (2000 px/m, σ=2) sobre sintético. La ruta `--regla-m` usa GUI (`cv2.imshow` + clicks, `calibracion.py:20-26`), no se puede probar headless; la app ofrece coordenadas manuales. `sigma_largo_m=0.0005 m` y `sigma_punto_px=1.0` son fijos, no configurables. **Sin corrida real.** |
| Calibración temporal (fps reales con σ) | PARCIAL | `calibracion.py:39-71` (`fps_real_con_led`); prioridad y propagación `main.py:36-44,60-66,224-273` | Funciona: LED sintético a 10 Hz → **30.0000 ± 0.3269 fps**; σ se propaga a ω, γ, k, Ec/Et y RMS. No se ejecutó con LED real; `f_led` se toma exacto (sin σ) y la componente sistemática no entra al agregado (ver problemas). |
| Repeticiones (5–20 videos) | PARCIAL | Bucle y agregado `main.py:92-98,291-303`; aviso N<5 `main.py:192-193` | Código correcto y probado con 2 sintéticos (horizontal) y 1 vertical. **No hay evidencia de 5–20 repeticiones reales**; el límite se avisa automáticamente. |
| Tabla `t, x, y, σx, σy` | PARCIAL | `tracking.py:39-75` (px), `calibracion.py:74-95` (m) | Se generan `*_px.csv` y `*_m.csv` en la corrida sintética (columnas `t_s,x_px,y_px,sx_px,sy_px` y `t_s,x_m,y_m,sx_m,sy_m`). **σx=σy=0.29 px asumidos** (`tracking.py:17`), no medidos; NaN donde no hay detección. Ninguna tabla real quedó versionada. |
| Derivar y filtrar + comparación crudo/filtrado + ajuste con error | PARCIAL | `señal.py:23-66` (`derivar`, `filtrar`, `procesar`, `comparar_crudo_filtrado`); `ajuste.py:15-34`; informe `main.py:149-169` | Receta x→v→a con Savitzky-Golay y ajuste ponderado con covarianza. La comparación crudo/filtrado ahora es una tabla numérica (RMS x/v/a y RMS a/a_max), no sólo PNG. **No hay barrido 7/11/21/41 ni criterio registrado**; sólo el default 11 (`main.py:230`) y la receta del README. El RMS no lleva σ. |
| k estático y k dinámico | PARCIAL | Dinámico `ajuste.py:37-48`; estático `ajuste.py:51-69`; CLI `main.py:284-289` | Ambos calculados con incerteza. En sintético: k estático **11.847 ± 0.062 N/m**; dinámico sin m_ef **12.000 ± 0.060 N/m** (verdad 12). No hay datos reales de masas/elongaciones; `σg=0.01` por default y `σ_elongación` opcional (si falta, se anota en limitaciones). |
| Máximos (x, v, a) con instante/posición | PARCIAL | `ajuste.py:126-170` (`maximos`); `main.py:80,140-142` | Analíticos sobre el ajuste, con covarianza y etiquetas inequívocas (`x_max`, `v_max`, `a_max` y sus `posición`/`t`). En sintético: x_max = 0.046784 ± 0.000041 m; v_max = 0.37384 ± 0.00035 m/s; a_max = 2.8090 ± 0.0025 m/s². Se reportan sólo del primer video. **Sin real.** |
| Energías cinética/elástica/total | PARCIAL | `ajuste.py:110-123` (`energias`); `main.py:69-77,144-147` | Ec, Ep, Et con k, m_ef, C y corrección por σ_fps como ufloats. En sintético: Ec_max = 0.013767 ± 0.000066 J; Ep_max = 0.015681 ± 0.000075 J; ΔEt = −0.013118 ± 0.000063 J. No se analiza conservación/decaimiento más allá del ΔEt; sólo primer video. **Sin real.** |
| Amortiguamiento | PARCIAL | Modelo y ajuste `ajuste.py:10-12,15-26`; salida `main.py:84,126`; aviso γ≈0 `main.py:190-191` | γ = 0.151576 ± 0.000014 1/s en sintético (verdad 0.15). Sólo se estima por el ajuste; no hay contraste independiente por decrecimiento logarítmico de la envolvente. **Sin real.** |
| Masa efectiva y chequeo de período | PARCIAL | `ajuste.py:41` (`m_ef=m+m_r/3`), `ajuste.py:72-107` (`chequeo_periodo`); `main.py:171-177` | Con `m_resorte=0.03 kg` el chequeo distingue: “T medido compatible con el cálculo sin m_ef (1.7 σ)”, “con m_ef no coincide (8.5 σ)”. Con `m_r=0` avisa que el chequeo no es informativo. **No hay masa real del resorte.** El veredicto “dudoso” se cuenta como compatible en la conclusión (`ajuste.py:97-107`). |
| Diagramas de cuerpo libre (vertical y horizontal) | **FALTA** | — | No hay figura, plantilla, script ni imagen de DCL en el repo. El único PDF es la consigna. |
| Comparación contra el Grupo 8 | **FALTA** | — | No hay datos, CSV, JSON, campo del informe, argumento CLI ni link de Drive. La única mención es `README.md:37` (“El Grupo 8 debería hacerlo”), sin comparación. |
| Sección de limitaciones completa | PARCIAL | `main.py:179-207` | Bloque automático útil y poblado en la corrida sintética (“Solo 2 repeticiones…”, “fps real no verificado…”), pero la sección manual exigida queda como plantilla vacía. |

---

## 3. Cambios desde el estado conocido

1. **Nuevo `agente-resorte/app.py`** (306 líneas, commit `f189fb2`): interfaz Streamlit que reutiliza
   `analizar()` y `escribir_informe()` de `main.py`, procesa los videos en una carpeta temporal y permite
   descargar informe, JSON y ZIP. Agrega `streamlit` a `requirements.txt` y una sección de interfaz al README.
2. **El fps con LED ya está conectado a `main.py`** (`--video-led`, `--f-led`, `--roi`; `main.py:224-273`).
   Esto **contradice al `REPORTE_ESTADO.md` anterior**, que dice que `main.py` nunca invocaba
   `fps_real_con_led`; el código actual sí lo hace y propaga σ a T/γ/k.
3. **`--sigma-px-por-m` pasó a ser obligatorio** cuando se usa `--px-por-m` (`main.py:243-246`). Es un
   cambio de comportamiento intencional: comandos viejos sin `--sigma-px-por-m` ahora abortan.
4. **Máximos y energías con incerteza**: `ajuste.maximos` devuelve ufloats con covarianza y claves
   desambiguadas; `energias` usa k/m_ef/C y `corr_v` para no duplicar σ_fps. Antes (según el reporte previo)
   los máximos no tenían σ y las etiquetas colisionaban por `.strip()`.
5. **k estático** ahora acepta `--sigma-g` y `--sigma-elongacion`; **chequeo de período** imprime un
   veredicto y una conclusión explícita (`ajuste.py:72-107`).
6. **README actualizado** con la interfaz y los argumentos de LED/σ. Sigue **sin link de datos** y sin
   versiones; la promesa de “fijamos versiones” que citaba el reporte anterior ya no aparece en el README.
7. **`REPORTE_ESTADO.md` quedó desactualizado** (dice que el LED no está conectado, que `--sigma-px-por-m`
   tiene default 0, que la comparación crudo/filtrado es sólo gráfico y que los máximos no tienen σ; todo
   eso cambió o directamente es falso con el código actual).
8. **Sin cambios** en los puntos abiertos: `SIGMA_PX=0.29` asumido, sin barrido de ventana, sin tests, sin
   versiones fijas, sin datos reales, sin DCL y sin comparación con el Grupo 8.
9. **`py_compile`**: los 7 `.py` compilan sin errores con Python 3.14.8
   (`main.py`, `app.py`, `tracking.py`, `calibracion.py`, `ajuste.py`, `generador_sintetico.py`, `señal.py`).
10. **No se rompió sintaxis ni el flujo principal**. Sí persisten entrypoints de demostración que fallan en
    un clon limpio: `señal.py`, `calibracion.py` y `ajuste.py` en modo `__main__` buscan
    `tabla_m.csv`/`tabla.csv` que no están versionados.

---

## 4. Datos reales

**No apareció ningún dato real.** Conteo explícito:

- Videos reales (`*.mp4`, `*.avi`, `*.mov`, `*.mkv`): **0**.
- CSV de medición: **0**.
- JSON de medición/informe: **0**.
- Imágenes/figuras (DCL, gráficos, capturas): **0**.
- Links a Drive/Grupo 8: **0**.
- Informes de corrida real: **0**. Los únicos `.md` son README, auditorías y el resumen de demo.
- PDF: **1** (`Proyectos-Lineas_II_y_III.pdf`, consigna de la cátedra, commit del 2026-10-08), **no es dato**.

Las únicas cifras numéricas del repo están en `RESUMEN_DEMO.md`, `REPORTE_ESTADO.md` y en este informe, y
todas provienen de corridas **sintéticas** o de ejemplos del README. Las carpetas `datos/` y `salidas/`
están en `.gitignore`, y no existen siquiera localmente en el repo.

---

## 5. Pruebas ejecutadas (siempre fuera del repo; resultados SINTÉTICOS)

Directorio: `C:\Users\crowl\AppData\Local\Temp\opencode\audit2`. Python del sistema 3.14.8
(numpy 2.5.3, scipy 1.18.1, cv2 5.0.0, lmfit 1.3.4, uncertainties 3.2.3, matplotlib 3.11.2, streamlit 1.66.1).
El `venv/` del repo sólo tiene `pip`; no se usó.

| Prueba | Resultado | Lectura |
|---|---|---|
| `py -m py_compile` de todos los `.py` | **OK** | Sintaxis correcta. |
| `main.py` con 2 videos sintéticos horizontales (k=12 N/m, m=0.2 kg, γ=0.15 1/s, A=0.05 m, 30 fps, 2000 px/m; seeds 1 y 2) | T = 0.8113245 ± 0.0000040 s; γ = 0.151576 ± 0.000014 1/s; k sin m_ef = 11.99960 ± 0.00012 N/m; χ² red. = 1.65/1.66 | El ajuste recupera la verdad sintética. **No es medición real.** |
| Mismo caso con `m_resorte=0.03 kg` | k con m_ef = 12.59958 ± 0.00012 N/m; k sin m_ef = 11.99960 ± 0.00012 N/m | Diferencia esperada por `m_ef=m+m_r/3`. |
| k estático con los datos de ejemplo del README | 11.847 ± 0.062 N/m | Sólo ejemplo sintético/README. |
| Chequeo de período | “T medido compatible con el cálculo sin m_ef (1.7 σ)”; “con m_ef no coincide (8.5 σ)” | Funciona el veredicto; depende de un k estático que no es real. |
| Video sintético vertical (`--vertical`, `--eje y`, m_r=0) | T = 0.811320 ± 0.000038 s; k = 12.000 ± 0.060 N/m | El eje y también funciona en sintético. |
| LED sintético (10 Hz, 30 fps, 240 cuadros) | fps = **30.0000 ± 0.3269 fps** | La calibración temporal funciona en sintético. |
| 2 videos + LED | Por video: T = 0.811328 ± 0.008840 s, k = 12.599 ± 0.281 N/m. **Agregado: T = 0.8113245 ± 0.0000040 s, k = 12.59958 ± 0.00012 N/m** | **Defecto crítico**: el agregado ignora la σ del fps (ver problemas). |
| Interfaz `app.py` vía `streamlit.testing.v1.AppTest`, subiendo los 2 sintéticos y eligiendo eje x | 0 excepciones, 2 resultados, ZIP de 773802 bytes con informe/JSON/CSV/PNG | El flujo de la interfaz funciona; **no se probó en navegador real ni con video real**. |
| `streamlit` en ejecución | Aviso de deprecación: `use_container_width` será reemplazado (`app.py:303`) | Sólo advertencia en 1.66.1; deuda técnica. |
| `señal.py`, `calibracion.py`, `ajuste.py` en modo `__main__` en directorio vacío | **FALLAN** por `FileNotFoundError` (`tabla_m.csv`/`tabla.csv`) | Entrypoints de demo no reproducibles sin archivos intermedios. |

**Distinción explícita**: todos los valores de esta sección son de **validación sintética**, no de medición
real. La interfaz también se probó con esos mismos sintéticos.

---

## 6. Problemas detectados

1. **El agregado descarta la incerteza del fps (crítico).** `agregado()` (`main.py:92-98`) calcula
   media ± dispersión/√N usando sólo los valores nominales de cada video e ignora las σ individuales. Con LED,
   la misma σ de fps afecta a todos los videos de forma correlacionada; el agregado debería incluirla
   linealmente (o como systematic común), no dividirla por √N. Evidencia numérica: T por video ±0.008840 s
   → agregado ±0.0000040 s; k por video ±0.281 N/m → agregado ±0.00012 N/m.
2. **No hay datos reales ni referencia del Grupo 8.** Sin videos/CSV reales no se puede cumplir “N mediciones,
   criterio y contra qué referencia”; la comparación con el Grupo 8 no existe en código ni en datos.
3. **No hay diagramas de cuerpo libre.** Ni figuras ni generador de figuras.
4. **Limitaciones manuales vacías.** La sección obligatoria queda como plantilla
   (“Qué falló / En qué condición se rompe / Qué quedó sin resolver”, `main.py:206-207`).
5. **`SIGMA_PX = 0.29 px` asumido** (`tracking.py:17`), no estimado empíricamente. El χ² reducido sintético
   ≈1.65–1.66 (debería ser ≈1 si las σ fueran correctas) sugiere que la σ del tracking está subestimada
   al menos en ese setup.
6. **RMS crudo/filtrado sin incerteza** (`main.py:158,165-166`): son números “pelados”, en tensión con
   “todo número con unidad e incerteza”. El resto del informe sí lleva σ.
7. **Sin barrido de ventana Savitzky-Golay.** El README pide probar 7/11/21/41 con un criterio explícito
   (`README.md:46`), pero no hay script, tabla ni criterio registrado; sólo el default 11.
8. **`requirements.txt` sin versiones** (`requirements.txt:1-7`), sin Python fijado y sin lock. El `venv/`
   local no tiene las dependencias instaladas (sólo `pip`).
9. **Sin tests automatizados** ni CI. La única validación contra `*_verdad.json` no está automatizada.
10. **Calibración espacial con regla sólo por GUI** (`calibracion.py:20-26`), no ejecutable headless; la app
    ofrece coordenadas manuales, pero no se probó con una regla real. `sigma_largo_m=0.0005 m` y
    `sigma_punto_px=1.0` son fijos.
11. **fps LED con `f_led` exacto** y sin término sistemático separado; además la comparación con el fps
    declarado avisa sólo si difiere >10 % (`main.py:264-271`).
12. **La interfaz no expone la calibración con LED** (`fps_led=None` fijo en `app.py:180`), ni `sigma_g`
    (fijo 0.01 en `app.py:186`), ni ROI. El eje por defecto de la app es vertical (`y`) y el del CLI es
    horizontal (`x`): inconsistencia menor. No se probó en navegador real.
13. **Documentación desactualizada/incompleta.** `REPORTE_ESTADO.md` contradice el código actual; el README
    no documenta todos los argumentos (`--ventana`, `--color`, `--salidas`, `--eje`, `--masa-resorte`,
    `--sigma-masa`) y no tiene link de Drive ni versión de Python.
14. **Entrypoints `__main__` de `señal.py`, `calibracion.py` y `ajuste.py` fallan** en un clon limpio por
    archivos CSV intermedios ausentes.
15. **`a_metros` conserva una rama fps muerta/frágil** (`calibracion.py:86-90`, `.replace(".csv",".mp4")`);
    `main.py` corrige el tiempo después, así que esa rama no se usa y podría duplicar la corrección si se
    activara.
16. **El chequeo de período cuenta “dudoso” como compatible** en la conclusión (`ajuste.py:97-107`), lo que
    puede sobreafirmar compatibilidad.
17. **Máximos y energías se informan sólo del primer video**, no por repetición ni agregados.
18. **`app.py` usa `use_container_width`** (`app.py:303`), deprecado en Streamlit 1.66.1 (aviso; se eliminaría
    después de 2025-12-31 según el mensaje).

---

## 7. Pendientes priorizados

| # | Pendiente | Prioridad | Esfuerzo | Archivo a tocar/crear |
|---|---|---|---|---|
| 1 | Incorporar la σ del fps (y cualquier systematic común) al resultado agregado, sin dividirla por √N | **Crítica** | Medio | `main.py:92-98` (`agregado`, `escribir_informe`) |
| 2 | Conseguir y versionar/ubicar los datos del Grupo 8 (T, x(t), σ) y agregar el bloque de comparación en el informe | **Crítica** | Grande (depende de terceros) | crear `datos/referencia_g8.*`; tocar `main.escribir_informe` + arg `--referencia` |
| 3 | Procesar 5–20 videos reales y dejar evidencia versionada o link de Drive en el README | **Crítica** | Grande | `README.md`; `datos/` o `docs/salidas` (o link) |
| 4 | Completar a mano la sección de limitaciones en el informe final (qué falló, cuándo se rompe, qué quedó) | **Crítica** | Chico | `main.py:206-207` o informe final |
| 5 | Diagramas de cuerpo libre vertical y horizontal (figura o script generador) | **Alta** | Chico | crear `dcl.py` o `assets/dcl_*.png` |
| 6 | Estimar empíricamente `SIGMA_PX` (objeto estático, dispersión del centroide) y justificarlo | **Alta** | Medio | `tracking.py:17`; nuevo script/validación |
| 7 | Barrido de ventana SG 7/11/21/41 contra la verdad sintética, con criterio y tabla en el informe | **Alta** | Medio | crear `ventana_check.py`; tocar `main.escribir_informe` |
| 8 | Agregar σ a los RMS crudo/filtrado (o declararlos como indicadores sin σ de forma explícita) | **Alta** | Chico | `main.py:158,165-166`; `señal.comparar_crudo_filtrado` |
| 9 | Conectar LED/ROI/σg a la interfaz o documentar claramente que sólo están en CLI; unificar eje por defecto | **Media** | Medio | `app.py:100-124,174-191`; `README.md` |
| 10 | Fijar versiones en `requirements.txt` y documentar versión de Python | **Media** | Chico | `requirements.txt`, `README.md` |
| 11 | Tests automatizados con el generador sintético (`|k_rec−k_true|<3σ`, T, N, fps) | **Media** | Medio | crear `tests/test_pipeline.py`; agregar pytest a requirements |
| 12 | Exponer/usar σ de `f_led` y `sigma_largo_m`/`sigma_punto_px` como argumentos | **Media** | Chico | `calibracion.py:30-39`; `main.py` |
| 13 | Corregir documentación: actualizar `REPORTE_ESTADO.md` o retirarlo, y completar argumentos en README | **Media** | Chico | `README.md`, `REPORTE_ESTADO.md` |
| 14 | Reportar máximos/energías por video o agregados, no sólo el primero | **Baja** | Chico | `main.escribir_informe` |
| 15 | Sacar rama fps muerta de `a_metros` y unificar la corrección temporal en un solo lugar | **Baja** | Chico | `calibracion.py:86-90`; `main.py:47` |
| 16 | Cambiar `use_container_width` por `width` y revisar compatibilidad con Streamlit futuro | **Baja** | Chico | `app.py:303` |
| 17 | Añadir contraste independiente de amortiguamiento (decrecimiento logarítmico) | **Baja** | Medio | `ajuste.py`; nuevo cálculo en `main.py` |

---

## 8. Lo que no se pudo verificar y preguntas abiertas

### No verificado

- **Datos reales**: no hay videos, CSV ni informes de corrida real; no se puede verificar N, escala, fps ni
  condiciones experimentales.
- **Grupo 8**: no hay datos, archivo ni link; no se puede comparar nada.
- **DCL**: no existe ningún archivo.
- **Calibración con regla real**: `marcar_dos_puntos` requiere GUI y no se ejecutó; la ruta por coordenadas de
  la app no se probó con una regla real.
- **Calibración LED real**: sólo se probó con un LED sintético; no hay `f_led` real ni su incerteza.
- **Robustez del tracking con video real**: iluminación, oclusiones, objetos del mismo color, motion blur;
  sólo se probó con sintéticos.
- **Interfaz en navegador real**: se ejecutó con `AppTest` (sin excepciones), no con `streamlit run` +
  navegador ni con archivos subidos desde disco.
- **Masa real del resorte y su σ**: no hay dato; el ejemplo usa 0.03 kg.
- **k estático real**: sólo se ejecutó el ejemplo del README (masas/elongaciones de ejemplo).
- **Entorno del equipo**: el `venv/` local sólo tiene `pip`; no se sabe qué versiones usa cada integrante.
- **Fecha/origen de los datos**: no hay datos, por lo tanto no hay fechas que reportar.

### Preguntas para el equipo

1. ¿Dónde están los videos reales y los datos del Grupo 8? ¿Se puede dejar el link de Drive en el README?
2. ¿Cuántas repeticiones reales se hicieron y en qué carpeta/equipo quedaron los `informe.md`/CSV?
3. ¿Se midió el fps real con LED en los videos del experimento? ¿Con qué `f_led`, ROI y σ?
4. ¿Cuál es la masa del resorte y su incerteza? Sin ese dato el chequeo con/sin masa efectiva pierde sentido.
5. ¿El DCL se entrega como figura en el informe PDF o debe generarlo el agente?
6. ¿La comparación con el Grupo 8 debe ser de T/k, de x(t) completa, o de ambas? ¿En qué formato están sus datos?
7. ¿Quién completa la sección manual de limitaciones y en qué archivo final queda?
8. ¿Se exige que `requirements.txt` tenga versiones fijas y una versión de Python declarada?
9. ¿Los videos horizontales y verticales se procesan en corridas separadas con `--eje` o se espera detección
   automática del eje?
10. ¿La interfaz debe permitir calibrar con LED (hoy sólo el CLI lo hace) o alcanza con el FPS numérico?

---

## Verificación final

Al cierre de este informe se ejecutó `git status`: el árbol estaba limpio antes de crear este archivo y lo
único nuevo sin trackear es `REPORTE_ESTADO_2.md`. No se modificó, renombró ni borró ningún archivo de código
ni de datos. Las pruebas se hicieron en `C:\Users\crowl\AppData\Local\Temp\opencode\audit2`, fuera del repo.
