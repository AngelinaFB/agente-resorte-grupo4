# INFORME_ESTADO_13_NOV — Estado actual del analizador de resorte

Fecha: 13 de noviembre de 2026  
Proyecto: Grupo 4, Línea III, movimiento 3 (resorte)  
Código: `agente-resorte/`  
Video real analizado: `Video_R2 (online-video-cutter.com).mp4`

Este informe describe el estado del analizador después de las mejoras de tracking, recorte, ajuste y agregado, y responde si esas mejoras son efectivas. No reemplaza la consigna del curso ni convierte los datos de R2 en una medición final: el video es corto y faltan calibraciones independientes.

---

## 1. Resumen ejecutivo

1. **El analizador mejoró de forma efectiva en robustez y transparencia.** Ahora la CLI puede usar el método de punto (`--punto`), la app permite un punto por video y aplica recorte automático del tramo inicial sin agregar campos nuevos, el ajuste estima un piso de ruido, el `χ²` se reporta con y sin ese piso, y el agregado excluye repeticiones no confiables.
2. **La mejora se ve en R2:** el método de punto siguió la pesa en `130/130` cuadros, sin pérdidas, y dio resultados consistentes al elegir el borde superior o el inferior de la pesa. El MOG2, en cambio, sigue fallando en este video: `28/130` cuadros detectados, `102` perdidos y `94` saltos descartados.
3. **El resultado físico de R2 es preliminar, no final.** El video dura `2.17 s` y contiene `4.77` ciclos, menos que el criterio de 5 ciclos. El estado del analizador es `revisar`, correctamente.
4. **`T` y `k` son los resultados más confiables.** `T = 0.45080 ± 0.00034 s` y `k = 13.85 ± 0.02 N/m` (con masa efectiva del resorte) si el FPS es realmente 60 y la masa es `69.61 g`. La incertidumbre real es mayor que la estadística del ajuste, del orden de 1–2 % por FPS/modelo de masa.
5. **`γ` no está resuelto.** El valor `0.0348 ± 0.0125 1/s` es compatible con cero; solo se puede afirmar que el amortiguamiento es bajo, con una cota superior aproximada de `0.07 1/s`.
6. **`A` depende de la escala.** Con la escala informada `0.000442 m/px`, `A = 2.27 cm`; con la escala estimada a partir del alto de la pesa (`0.000417 m/px`), `A ≈ 2.14 cm`. La diferencia es del 6 %.
7. **Las energías no deben presentarse como definitivas.** Dependen de la escala al cuadrado y de los extremos del registro; su incertidumbre real es mayor que la reportada.
8. **La suite de tests pasa:** `62 tests OK, 1 skipped`. El archivo nuevo `tests/test_agente.py` aporta 6 pruebas de detección de inicio, ajuste robusto y recuperación de `k`.
9. **No se hizo commit.** El árbol de trabajo tiene 5 archivos modificados, y `tests/test_agente.py` e `INFORME_ESTADO_13_NOV.md` sin seguimiento. `generador_sintetico.py` fue revertido y no tiene cambios.

---

## 2. Respuesta directa: ¿ha mejorado efectivamente el analizador?

**Sí, mejoró efectivamente como herramienta de análisis, pero no convierte automáticamente a R2 en un dato final.**

La mejora es clara en estos puntos:

- Antes, la CLI no podía usar el método de punto; ahora `main.py` acepta `--punto X Y` y lo pasa a `analizar()`.
- Antes, la app usaba un solo punto para todos los videos; ahora guarda un punto por video y avisa si algún video va a usar el punto de otro.
- Antes, el ajuste incluía el tramo estático/acomodo; ahora hay `--inicio`, `--sin-recorte` y detección automática con `detectar_inicio()`.
- La app no agrega campos nuevos: el recorte es automático y el FPS se toma del video. `--inicio`, `--sin-recorte`, `--ventana-inicio` y `--fps-real` son opciones de CLI, no inputs obligatorios de la app.
- Antes, `SIGMA_PX=0.29 px` inflaba el `χ²` por órdenes de magnitud; ahora `ajustar()` estima un piso de ruido por MAD, usa pérdida robusta `soft_l1` y reporta `χ²` estándar, `χ²` sin piso, RMS residual y `σ` extra.
- Antes, se promediaban resultados inválidos; ahora `calcular_agregados()` solo usa repeticiones con estado `aceptable` y devuelve `None` si no queda ninguna.
- Antes, el tracker de punto no se recuperaba si se perdía; ahora combina flujo óptico, plantilla, búsqueda local, actualización de plantilla y re-detección.
- Antes no había tests del agente; ahora hay una suite que pasa y cubre los cambios principales.

Lo que **no** mejoró:

- El MOG2 sigue sin seguir la pesa en R2; el método que funciona es el de punto.
- La CLI todavía usa un solo `--punto` para todos los videos de una corrida. La app sí permite punto por video, pero si el usuario no elige uno, cae al punto del video seleccionado con una advertencia.
- No se re-probaron los videos reales Video2/Video3/Video4 del reporte anterior en este entorno; solo está disponible R2. Por lo tanto, no se puede afirmar que las mejoras resuelvan aquellos casos.
- Siguen pendientes la calibración automática de escala, la comparación con `k` estática, el FPS verificado con LED y la documentación desactualizada.

**Conclusión:** el analizador ahora es más robusto, más honesto con sus incertidumbres y más usable. Para R2, `T` y `k` son resultados preliminares razonables; `γ`, `A` y las energías no deben tratarse como finales.

---

## 3. Cambios implementados desde `REPORTE_ESTADO_4`

| Problema del reporte anterior | Estado actual | Evidencia |
|---|---|---|
| La CLI no podía usar el método de punto | **Corregido** | `main.py` tiene `--punto X Y` y llama `analizar(..., punto_inicial=a.punto)`. |
| La app usaba un punto para todos los videos | **Mejorado** | `app.py` guarda `punto_tracking_<file_id>` por video y advierte si falta uno. |
| No había recorte del tramo estático | **Corregido** | La app detecta el inicio automáticamente; la CLI expone `--inicio`, `--sin-recorte` y `--ventana-inicio`; `detectar_inicio()` en `señal.py`. |
| `SIGMA_PX=0.29 px` inflaba el `χ²` | **Corregido** | `ajustar()` estima `sigma_extra` por MAD, usa `soft_l1` y calcula `redchi_estandar`; el informe muestra ambos `χ²` y el RMS. |
| Se agregaban resultados inválidos | **Corregido** | `calcular_agregados()` filtra por `estado == "aceptable"`; si no hay válidos, no promedia. |
| El tracker de punto no se recuperaba | **Mejorado** | `tracking.py` incorpora plantilla, búsqueda local, actualización y re-detección; reporta `cuadros_con_flujo`, `cuadros_con_plantilla`, `redetecciones`. |
| No había tests | **Corregido parcialmente** | `tests/test_agente.py` con 6 tests; suite total `62 OK, 1 skipped`. |
| El informe no distinguía `χ²` robusto de `χ²` estándar | **Corregido** | Se reportan `chi_cuadrado_reducido`, `chi_cuadrado_sin_piso_de_ruido`, `rms_residuo` y `sigma_extra_ruido`. |
| El ajuste usaba la interpolación de huecos largos | **Corregido** | El ajuste usa solo cuadros con detección; la interpolación queda para los gráficos. |
| El inicio del ajuste no se corregía a `t=0` | **Corregido** | `ajustar(t_fit - inicio, ...)` para que `A` sea la amplitud de liberación. |

La interfaz de la app no incorpora campos nuevos: el tramo inicial se detecta automáticamente y el FPS se toma del video. Las opciones manuales (`--inicio`, `--sin-recorte`, `--ventana-inicio`, `--fps-real`) quedan disponibles solo por CLI y no hay que completarlas para analizar desde la app.

Cambios que **no** se hicieron:

- No se modificó `generador_sintetico.py`; fue revertido y no tiene diff.
- No se actualizaron `README.md`, `RESUMEN_DEMO.md` ni el texto del selector de punto.
- No se fijaron versiones en `requirements.txt`.
- No se implementó calibración automática de la regla.
- No se agregó comparación automática con `k` estática si no se ingresan datos.

---

## 4. Verificación automática

### 4.1 Tests

Comando:

```powershell
cd agente-resorte
python -m unittest discover -s tests -q
```

Resultado:

```text
Ran 62 tests in 1.608s

OK (skipped=1)
```

El archivo `tests/test_agente.py` contiene 6 pruebas:

- `detectar_inicio()` sin prefijo empieza en cero.
- `detectar_inicio()` con prefijo estático de 2 s detecta entre 1.9 y 2.2 s.
- `detectar_inicio()` con ruido no adelanta el inicio.
- `ajustar()` recupera `T` y `γ` en una oscilación sintética.
- `ajustar()` tolera outliers con la pérdida robusta.
- `cantidades()` recupera `k` dentro de 0.1 N/m.

### 4.2 Validación sintética registrada

Verdad sintética: `T=0.811308 s`, `k=12 N/m`, `γ=0.15 1/s`, `A=0.05 m`.

| Caso | Inicio usado | T (s) | γ (1/s) | k (N/m) | A (m) | χ² |
|---|---:|---:|---:|---:|---:|---:|
| Sin prefijo | 0 | 0.811477 | 0.152647 | 11.995146 | 0.049556 | 0.757 |
| Prefijo estático de 2 s | 2.067 (automático) | 0.811835 | 0.151551 | 11.984509 | 0.049388 | 0.693 |
| Dos repeticiones | — | 0.811535 | — | — | — | — |

Lectura: el ajuste recupera la verdad sintética con errores menores al 0.1 % en `T` y `k`, y el recorte automático encuentra el inicio de la oscilación. Esto valida la lógica, no los datos reales.

---

## 5. Video real R2

### 5.1 Datos del video

| Dato | Valor |
|---|---:|
| Archivo | `Video_R2 (online-video-cutter.com).mp4` |
| Resolución | `1920 × 1080` |
| FPS declarado | `60 fps` |
| Cuadros | `130` |
| Duración | `2.1667 s` |
| PTS | `16.667 ms` entre cuadros; sin cuadros duplicados exactos |
| Masa colgante | `69.61 g = 0.06961 kg`; error `0.01 g` |
| Masa del resorte | `5.06 g = 0.00506 kg`; error `0.01 g` |
| Escala informada | `0.000442 m/px`; equivale a `2262.44 px/m` |
| Tamaño del recipiente | `13.425 cm ± 0.005 cm` |
| Distancia celular-resorte | `78.5 cm ± 0.5 cm` |

### 5.2 Punto de tracking

Las coordenadas aportadas por el usuario, `(653,341)` y `(658,570)`, corresponden a una vista escalada del video; en el archivo nativo `1920×1080` esas posiciones son fondo estático. Mapeadas con el factor aproximado de una vista `~1366×768`, equivalen a:

- borde superior de la pesa: `(918,480)`;
- borde inferior de la pesa: `(925,802)`.

El usuario confirmó que esos puntos eran el borde superior e inferior de la pesa en el primer cuadro. El alto nativo de la pesa es entonces `802 − 480 = 322 px`. Con `13.425 cm`, la escala estimada por el alto es:

```text
0.13425 m / 322 px ≈ 0.000417 m/px
```

Esa escala es un 6 % menor que `0.000442 m/px`. La diferencia es razonable para coordenadas aproximadas y no afecta `T` ni `k`; solo afecta `A` y las energías.

### 5.3 Resultados con el método de punto

Punto usado: `(925,802)` (borde inferior de la pesa). El mismo resultado se obtiene con `(918,480)` y con otros puntos sobre la pesa.

| Magnitud | Resultado |
|---|---:|
| Estado | `revisar` |
| Cuadros analizados | `130/130` |
| Cuadros perdidos | `0` |
| Inicio del ajuste | `0.000 s` (el video ya empieza oscilando) |
| Eje | `y` |
| Ciclos observados | `4.77` |
| Cuadros por período | `27.0` |
| Período `T` | `0.45080 ± 0.00034 s` |
| Frecuencia angular `ω` | `13.938 ± 0.010 rad/s` |
| Amortiguamiento `γ` | `0.0348 ± 0.0125 1/s` |
| `k` con masa efectiva | `13.850 ± 0.021 N/m` |
| `k` sin masa efectiva | `13.523 ± 0.020 N/m` |
| Amplitud `A` | `0.02269 ± 0.00031 m` con escala `0.000442` |
| `A` con escala del alto de la pesa | `≈0.0214 m` |
| `χ²` reducido con piso de ruido | `0.907` |
| `χ²` sin piso de ruido | `24.74` |
| RMS residual | `0.000916 m ≈ 2.07 px` |
| `σ` extra de ruido | `0.000961 m ≈ 2.17 px` |
| `σ` de tracking | `0.400 px` |
| FPS usado | `60 fps` declarado, no verificado con reloj externo |

Consistencia entre puntos:

| Punto | T (s) | k con masa efectiva (N/m) | A (m) | Estado |
|---|---:|---:|---:|---|
| `(925,802)` borde inferior | 0.45080 | 13.850 | 0.02269 | revisar |
| `(918,480)` borde superior | 0.45008 | 13.895 | 0.02210 | revisar |
| `(933,800)` | 0.45076 | 13.853 | 0.02268 | revisar |
| `(933,840)` | 0.45091 | 13.843 | 0.02259 | revisar |

La dispersión entre puntos es pequeña (`T` varía ~0.0008 s, `k` ~0.05 N/m), lo que indica que el punto está sobre un cuerpo rígido y que el tracking es estable.

### 5.4 MOG2 en el mismo video

La corrida con MOG2 (método por defecto) dio:

```text
130 cuadros | 28 detectados | 102 perdidos | 94 saltos descartados
```

Es decir, MOG2 sigue sin seguir la pesa en R2. La mejora del analizador no proviene de MOG2, sino del método de punto y de las correcciones del ajuste.

---

## 6. Confiabilidad de los resultados de R2

| Resultado | Confiabilidad | Comentario |
|---|---|---|
| Tracking | Alta | `130/130`, sin pérdidas; consistente entre puntos. |
| `T` | Alta | Intervalos entre picos de `0.450 s`; incertidumbre estadística ~0.1 %, sistemática por registro corto ~0.5 %. |
| `k` | Media-alta | Depende de la masa y del FPS. Si el FPS es 60 y la masa es correcta, `13.85 N/m`; la incertidumbre real es ~1–2 % (0.1–0.3 N/m), no solo `0.021 N/m`. |
| `γ` | Baja | Compatible con cero; solo se puede dar una cota superior ~`0.07 1/s`. |
| `A` | Media | Depende de la escala; `2.27 cm` con `0.000442`, `2.14 cm` con la escala del alto. Error ~6–10 %. |
| Energías | Baja | Dependen de la escala al cuadrado y de los extremos; no usar como resultado final. |
| Estado `revisar` | Correcto | El video tiene menos de 5 ciclos. |

### 6.1 Por qué `T` y `k` son razonables

- Los picos de `y` ocurren en `t = 0.15, 0.60, 1.05, 1.50, 1.95 s`; los intervalos son todos `0.450 s`.
- Los mínimos ocurren en `t = 0.367, 0.817, 1.267, 1.717 s`; los intervalos son `0.450 s`.
- El ajuste da `T = 0.45080 s`, consistente con los picos.
- Con `m_ef = m + m_r/3 = 0.06961 + 0.00506/3 = 0.07130 kg`, `k = m_ef ω² ≈ 13.85 N/m`.
- Sin corrección de masa del resorte, `k = m ω² ≈ 13.52 N/m`. La diferencia entre ambas convenciones es 2.4 %.

### 6.2 Por qué `γ` no es confiable

- El ajuste da `γ = 0.0348 ± 0.0125 1/s`; el intervalo de 2σ incluye cero.
- La envolvente de máximos da `γ ≈ 0.057 1/s`; la de mínimos da `γ ≈ 0`; el promedio es ~0.03.
- En `4.77` ciclos, un amortiguamiento de `0.03 1/s` produce una caída de amplitud de solo `e^{-0.03·2.17} ≈ 0.94`; es indistinguible del ruido y de la deriva.
- Conclusión: reportar “amortiguamiento bajo, compatible con cero” y no un valor preciso.

### 6.3 Por qué `A` y las energías dependen de la escala

- `A` se mide en píxeles y se convierte con la escala. La escala informada y la estimada por el alto de la pesa difieren 6 %, por lo que `A` difiere 6 %.
- Las energías dependen de `k` y de `A²`; un 6 % en `A` produce ~12 % en energía.
- Los valores de `Et` al inicio y al final son sensibles a la fase y al filtrado; no son una medida robusta de la disipación. Para amortiguamiento, usar `γ` o la envolvente de amplitudes, no `ΔEt`.

---

## 7. Problemas que siguen abiertos

1. **Video R2 demasiado corto.** `2.17 s` y `4.77` ciclos; no cumple el criterio de 5 ciclos. `T` y `k` son preliminares; `γ` no se resuelve.
2. **FPS no verificado.** Se usa el FPS declarado por el video (`60 fps`). Los PTS son coherentes (`16.667 ms`) y no hay cuadros duplicados exactos, pero no se comparó con un reloj externo. `k` escala con el FPS al cuadrado; un error de 1 % en FPS produce ~2 % en `k`.
3. **Escala aproximada.** La escala informada `0.000442 m/px` y la estimada por el alto de la pesa `0.000417 m/px` difieren 6 %. `T` y `k` no dependen de la escala; `A` y energías sí.
4. **Sin `k` estática.** No hay comparación dinámica vs estática. La extensión estática esperada con `m = 69.61 g` y `k = 13.85 N/m` es `x = mg/k ≈ 4.93 cm`; si se mide el estiramiento del resorte con esa masa, se puede validar `k`.
5. **MOG2 sigue fallando en R2.** `28/130` detectados y `102` perdidos. El método por defecto no es adecuado para este video; el método de punto sí.
6. **La CLI usa un solo punto para todos los videos.** `--punto` se aplica a toda la corrida. Para varios videos con masas/posiciones distintas, usar la app con punto por video o correr un video por vez.
7. **No se re-probaron Video2/3/4.** En este entorno solo está R2. No se puede afirmar que la re-detección y el recorte automático resuelvan los casos del reporte anterior.
8. **El recorte automático solo se validó en sintético.** En R2 detectó `0.0 s` porque el video ya empieza oscilando. Falta probarlo en un video real con un prefijo estático largo.
9. **Documentación y dependencias.** `README.md`, `RESUMEN_DEMO.md` y el texto del selector siguen desactualizados; `requirements.txt` no fija versiones; `diag_tracking.py` sigue siendo un placeholder.
10. **Sin datos del Grupo 8.** No hay escala, masa, LED ni `k` estática del Grupo 8. R2 es un video real, pero no reemplaza una campaña de repeticiones.

---

## 8. Recomendaciones

### 8.1 Para cerrar el resultado de R2

- Reportar `T = 0.451 s` y `k ≈ 13.8 N/m` como **preliminares**, aclarando que dependen de `m = 69.61 g`, `m_r = 5.06 g` y FPS `60`.
- Reportar `γ` solo como cota superior (`γ < 0.07 1/s` aproximadamente), no como valor medido.
- Reportar `A ≈ 2.2 cm` con la escala usada y aclarar la incertidumbre de escala (~6–10 %).
- No reportar las energías como definitivas.
- Medir el estiramiento estático del resorte con la misma masa; si da `≈4.9 cm`, `k` dinámica y estática son consistentes.

### 8.2 Para mejorar la medición

- Grabar un video más largo: al menos 10 ciclos (idealmente 20–30 s), para resolver `γ` y reducir la sistemática de `T`.
- Repetir 5–20 veces la liberación con la misma masa y el mismo resorte.
- Verificar el FPS con un LED de frecuencia conocida o un cronómetro en el mismo video.
- Calibrar la escala con un objeto de tamaño conocido en el mismo plano y en el mismo video (la pesa de `13.425 cm` sirve si se mide su alto o ancho con precisión).
- Elegir el punto sobre la pesa en cada video; no reutilizar el punto de otro video.
- Usar el método de punto, no MOG2, para videos con fondo/candidatos múltiples.
- Mantener el estado `revisar` cuando no se cumplan los criterios; no forzar el agregado.

---

## 9. Reproducibilidad

### 9.1 Comandos

```powershell
cd agente-resorte

# Tests
python -m unittest discover -s tests -q

# Ayuda de la CLI
python main.py --help

# Análisis de R2 con el punto del borde inferior de la pesa
python main.py "..\Video_R2 (online-video-cutter.com).mp4" `
  --masa 0.06961 --sigma-masa 0.00001 `
  --masa-resorte 0.00506 --sigma-masa-resorte 0.00001 `
  --px-por-m 2262.4434 --sigma-px-por-m 15 `
  --punto 925 802 `
  --salidas "C:\Users\angel\AppData\Local\Temp\opencode\video_r2\salidas_r2_925_802"
```

### 9.2 Archivos generados

- Informe del análisis: `C:\Users\angel\AppData\Local\Temp\opencode\video_r2\salidas_r2_925_802\informe.md`
- JSON: `C:\Users\angel\AppData\Local\Temp\opencode\video_r2\salidas_r2_925_802\resultados.json`
- CSV en píxeles: `C:\Users\angel\AppData\Local\Temp\opencode\video_r2\salidas_r2_925_802\Video_R2 (online-video-cutter.com)_px.csv`
- CSV en metros: `C:\Users\angel\AppData\Local\Temp\opencode\video_r2\salidas_r2_925_802\Video_R2 (online-video-cutter.com)_m.csv`
- Gráficos: `...\Video_R2 (online-video-cutter.com)_senal.png` y `..._ajuste.png`

### 9.3 Estado de Git

```text
 M agente-resorte/ajuste.py
 M agente-resorte/app.py
 M agente-resorte/main.py
 M agente-resorte/señal.py
 M agente-resorte/tracking.py
?? agente-resorte/tests/test_agente.py
?? INFORME_ESTADO_13_NOV.md
```

No se hizo commit. `generador_sintetico.py` no tiene cambios. Tanto el test nuevo como este informe están sin seguimiento.

---

## 10. Conclusión

El analizador **sí mejoró efectivamente**: ahora puede usar el punto desde la CLI, permite punto por video en la app, recorta automáticamente el tramo inicial sin pedir campos nuevos, ajusta con un piso de ruido realista, reporta la calidad con más transparencia y no promedia resultados inválidos. La suite de tests pasa y el método de punto sigue la pesa de R2 sin pérdidas.

Para R2, el resultado preliminar es:

- `T ≈ 0.451 s`;
- `k ≈ 13.8 N/m` con masa efectiva (o `13.5 N/m` sin corrección de masa del resorte);
- `γ` bajo, compatible con cero;
- `A ≈ 2.2 cm` con la escala informada;
- estado `revisar` por tener menos de 5 ciclos.

La mejora es del **analizador**, no una validación física definitiva del video. Para convertir estos números en un resultado final hacen falta un video más largo, FPS verificado, escala calibrada, varias repeticiones y, si es posible, una medición estática de `k`.
