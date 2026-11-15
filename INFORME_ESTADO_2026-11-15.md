# Estado del analizador de resorte — 15/11/2026

**Proyecto:** Grupo 4, Línea III, movimiento 3 (resorte)  
**Repositorio:** `C:\Users\crowl\agente-resorte-grupo4`  
**Commit de referencia:** `03463ed` (`fix: calidad.py; main.py (nuevos flags); Nuevos tests y artefactos de verificación`)  
**Alcance:** estado verificable del analizador de video y de los resultados disponibles. No se modificó código, no se hizo commit y no se volvieron a rastrear videos.  
**Convenciones:** `[C]` confirmado en un archivo del repo; `[NV]` no verificado en esta sesión; `[S]` supuesto o dato provisional. No se pudo releer el PDF de la consigna en este entorno; la tabla de requisitos se basa en `REPORTE_ESTADO_2.md`, `REPORTE_ESTADO_4.md` y la documentación del repo.

## 1. Resumen ejecutivo

1. El pipeline actual analiza videos con un punto elegido sobre la masa, recorte automático del tramo previo, ajuste amortiguado robusto y un módulo nuevo de calidad; la app permite un punto y un instante de clic por video. `[C]` en `main.py`, `app.py`, `calidad.py`.
2. La corrida real corregida usa `m = 64.55 ± 0.014 g`, `m_r = 9.73 ± 0.01 g` y escala `2262 ± 20 px/m`; da `T = 0.642066 ± 0.000463 s` y `k = 6.49217 ± 0.00946 N/m` para `N = 3`. `[C]` en `agente-resorte/salidas/verificacion/mejoras/reales/`.
3. Los tres videos quedan `Aceptable` con la regla nueva: pérdidas en el tramo `0.00 %`, ciclos `18.70–38.39` y `RMS/A = 0.92–4.19 %`. `[C]`.
4. La corrida anterior con `0.3090 kg`, `0.09730 kg` y `6397 ± 12 px/m` no es una medición física válida: `T` coincide, pero `k` queda ≈5.04 veces mayor y `A` no es comparable. `[C]` en `resultado_3videos/informe.md`.
5. El punto antiguo de Video4, `(860,421)`, cae sobre el resorte y produce 63.96 % de pérdidas y un ajuste no interpretable; la corrida final usa `(875,675)` y comienza en `37.001 s`. `[C]` en `REPORTE_VERIFICACION.md` y en los metadatos de tracking.
6. La validación sintética recupera la verdad cuando los parámetros son físicos, pero los casos con masas ×10 quedan `Aceptable` con solo advertencias, aunque la extensión esperada sea `97.6 cm` o `467.0 cm`. `[C]` en `sintetico_10x/` y `sintetico_10x_error/`.
7. No hay una calibración independiente de escala, FPS verificado con LED, `k` estática, comparación externa con el Grupo 8, DCL ni 5–20 repeticiones. `[NV]`/`FALTA`.
8. `salidas/verificacion/masas_varias/` no existe: el estudio `T²` vs masa no se ejecutó. No se inventan valores en este informe. `[C]`.

## 2. Qué se hizo y cómo funciona

### 2.1 Pipeline, una línea por etapa

| Etapa | Archivo | Qué hace | Evidencia / salida |
|---|---|---|---|
| Rastreo | `agente-resorte/tracking.py` | Sigue un punto elegido sobre la masa con flujo óptico, plantilla y re-detección; guarda trayectoria, `t`, `x`, `y`, `σx`, `σy` y metadatos. | `*_px.csv`, `*_px_tracking.json`; Video2/3/4 con 0 %, 16.38 % y 0 % de pérdidas totales. `[C]` |
| Calibración | `agente-resorte/calibracion.py` | Convierte px a metros con escala conocida o dos puntos de una regla; mide FPS con LED. | `escala_px_por_m()`, `a_metros()`, `fps_real_con_led()`; no se usó LED real. `[C]`/`[NV]` |
| Señal | `agente-resorte/señal.py` | Detecta el inicio de la oscilación por envolvente, rellena solo para gráficos, deriva y filtra con Savitzky-Golay. | Inicios `8.571`, `6.470` y `37.001 s`; ventana usada `11` cuadros. `[C]` |
| Ajuste | `agente-resorte/ajuste.py` | Ajusta `x(t) = A e^{-γt} cos(ωt+φ) + C` con `soft_l1`; estima un piso de ruido por MAD y calcula covarianza. | `T`, `γ`, `k`, `A`, `χ²`, RMS y máximos. `[C]` |
| Calidad | `agente-resorte/calidad.py` | Convierte masas, avisa valores implausibles, calcula `x_eq = mg/k`, período por cruces, energías analíticas, criterios e IC95. | `criterios_calidad()`, `periodo_por_cruces()`, `ic95_media_t()`. `[C]` |
| Orquestación | `agente-resorte/main.py` | Recibe videos o trayectorias, aplica puntos por video, recorte, ajuste, agregado, informe Markdown/JSON y metadatos. | `--punto`, `--puntos`, `--desde`, `--trayectoria`; `informe.md` y `resultados.json`. `[C]` |
| Interfaz | `agente-resorte/app.py` | Streamlit: subida múltiple, punto e instante por video, masas en gramos, escala, ventana, eje, chequeo estático y descargas. | No se ejecutó una corrida completa de UI en esta sesión. `[C]`/`[NV]` |
| Pruebas | `agente-resorte/tests/` | Pruebas del agente, calidad, chatbot, índice, embeddings y generación. | `82/82` OK; `test_calidad` `20/20`. `[C]` |

### 2.2 Cambios relevantes desde `7251ffa`

| Cambio | Archivo(s) | Estado verificado |
|---|---|---|
| Método de punto, re-detección y metadatos de trayectoria | `tracking.py` | Usado en los tres videos; Video2 y Video4 sin pérdidas, Video3 con 306/1868 cuadros perdidos fuera del tramo ajustado. `[C]` |
| Un punto por video, reanálisis de CSV y `--desde` | `main.py`, `app.py` | La corrida final reanalizó tres CSV; Video4 se rastreó desde `37.001 s`. `[C]` |
| Recorte automático del prefijo y ajuste solo con detecciones | `señal.py`, `main.py` | Inicios automáticos `[C]`; la interpolación queda para gráficos. `[C]` |
| Ajuste robusto con piso de ruido | `ajuste.py` | `χ²` con piso `0.636–1.012`; sin piso `4.99–117`. `[C]` |
| Módulo de calidad, masas y extensión estática | `calidad.py` | `x_eq` esperada, avisos de masa, cruces, criterios e IC95. `[C]` |
| Interfaz en gramos y con instante de clic por video | `app.py` | Código y defaults `64.55 g` / `9.73 g`; no se validó el flujo completo con uploads. `[C]`/`[NV]` |
| Suite de pruebas | `tests/test_calidad.py` y resto | `82/82` OK; `test_calidad` `20/20`. `[C]` |
| Chatbot bibliográfico | `chatbot/` | Existe por CLI, no está integrado al analizador; la evaluación 3C.2 no lo declara estable. `[C]`/`[NV]` |

### 2.3 Interfaz y argumentos que importan

- La app pide masa colgante y masa del resorte en gramos, escala, punto e instante por video, ventana `7/11/21/41`, eje y datos estáticos opcionales. `[C]` en `app.py`.
- CLI: `--masa`/`--masa-g`, `--masa-resorte`/`--masa-resorte-g`, `--px-por-m` + `--sigma-px-por-m` obligatorio, `--punto`, `--puntos`, `--trayectoria`, `--desde`, `--inicio`, `--fin`, `--sin-recorte`, `--ventana`, `--eje`, `--residuo-max-pct`, `--video-led`/`--f-led` y `--salidas`. `[C]` en `main.py --help`.
- Defaults relevantes: ventana `11`, eje `auto`, residuo máximo `8 %`, inicio automático y fin del registro. `[C]`.
- `--desde` mueve el comienzo del rastreo; `--inicio` solo recorta el tramo que se ajusta después de rastrear. No son intercambiables. `[C]` en `REGRESION_Y_DIAGNOSTICOS.md`.

## 3. Resultados reales

### 3.1 Entradas y procedencia

| Dato | Valor usado | Origen / estado |
|---|---:|---|
| Masa colgante | `64.55 ± 0.014 g` = `0.06455 ± 0.000014 kg` | Metadatos de la corrida `reales`; atribuida a R1+P1. `[C]`/`[S]` |
| Masa del resorte | `9.73 ± 0.01 g` = `0.00973 ± 0.00001 kg` | Metadatos de la corrida `reales`; sin hoja externa que lo confirme. `[C]`/`[S]` |
| Escala | `2262 ± 20 px/m` | Argumento `--px-por-m`; no es calibración independiente. `[C]`/`[S]` |
| FPS | `59.9709–59.9713 fps` | Declarado por el video, `σ = 0`; no verificado con LED. `[C]`/`[NV]` |
| Puntos | Video2 `(850,700)`; Video3 `(840,708)`; Video4 `(875,675)` | Metadatos de tracking; no se revisó visualmente cada punto. `[C]`/`[NV]` |
| Tramos | Video2 `8.571–20.610`; Video3 `6.470–31.132`; Video4 `37.001–55.693 s` | Recorte automático. `[C]` |

### 3.2 Seguimiento y ajuste por video

| Video | Tramo (s) | Detectados / totales | Perdidos totales | Perdidos en el tramo | Ciclos | `T ± σ` (s) | `γ ± σ` (1/s) | `k_ef ± σ` (N/m) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Video2_R1_P1 | 8.571–20.610 | 1237 / 1237 | 0 (0.00 %) | 0.00 % | 18.70 | 0.642883 ± 0.000033 | 0.01337 ± 0.00051 | 6.4757 ± 0.0015 |
| Video3_R1_P1 | 6.470–31.132 | 1562 / 1868 | 306 (16.38 %) | 0.00 % | 38.39 | 0.642034 ± 0.000023 | 0.01136 ± 0.00034 | 6.4928 ± 0.0015 |
| Video4_R1_P1 | 37.001–55.693 | 1122 / 1122 | 0 (0.00 %) | 0.00 % | 29.15 | 0.6412800 ± 0.0000070 | 0.00673 ± 0.00011 | 6.5081 ± 0.0014 |

`k_ef` usa `m_ef = m + m_r/3`. Los pérdidas de Video3 son anteriores al tramo ajustado; dentro del tramo, el ajuste usa solo cuadros detectados. `[C]`.

### 3.3 Amplitud, extensión esperada y chequeos independientes

| Video | `k_sin m_ef ± σ` (N/m) | `A ± σ_fit` (m) | `x_eq` esperada (cm) | `RMS/A` (%) | `T` por cruces (s) | `ΔT/T` (%) | Estado |
|---|---:|---:|---:|---:|---:|---:|---|
| Video2_R1_P1 | 6.1658 ± 0.0015 | 0.067461 ± 0.000233 | 9.779 ± 0.010 | 2.55 | 0.642792 | −0.0142 | Aceptable |
| Video3_R1_P1 | 6.1822 ± 0.0014 | 0.058470 ± 0.000257 | 9.753 ± 0.010 | 4.19 | 0.641489 | −0.0847 | Aceptable |
| Video4_R1_P1 | 6.1967 ± 0.0014 | 0.069831 ± 0.000076 | 9.7300 ± 0.0099 | 0.92 | 0.641353 | +0.0114 | Aceptable |

- `A` se obtuvo con escala `2262 ± 20 px/m`; la incertidumbre de la tabla es solo la del ajuste. La escala aporta un 0.884 % relativo adicional: aproximadamente `0.00060`, `0.00052` y `0.00062 m` para Video2/3/4. `[C]`
- `x_eq` es la extensión **esperada** `m g/k`, no una elongación medida. `[C]`/`[S]`
- `RMS/A` es el RMS residual dividido por la amplitud; el criterio nuevo exige `≤ 8 %`. `[C]`
- `T` por cruces y `ΔT/T` son chequeos relativamente independientes del ajuste sinusoidal. `[C]`

### 3.4 Agregado de las tres repeticiones

N = 3; repeticiones excluidas = 0. Se usa la media y el IC95 % de la media con `t(2) = 4.303`. `[C]`

| Magnitud | Media ± σ_total | IC95 % de la media |
|---|---:|---|
| `T` (s) | 0.642066 ± 0.000463 | [0.640073, 0.644058] |
| `ω` (rad/s) | 9.7859 ± 0.00706 | [9.75554, 9.81627] |
| `γ` (1/s) | 0.010485 ± 0.001964 | [0.002036, 0.018933] |
| `k` con `m_ef` (N/m) | 6.49217 ± 0.00946 | [6.45189, 6.53245] |
| `k` sin `m_ef` (N/m) | 6.18157 ± 0.00901 | [6.14322, 6.21992] |
| `x_eq` esperada global (cm) | 9.754 ± 0.010 | — |

Para `k` con `m_ef`, `σ_est = 0.00936 N/m` y `σ_sis = 0.00138 N/m`; la total es la combinación en cuadratura. La dispersión muestral de `T` es `0.000802 s`, mayor que el error estándar del ajuste. `[C]`

### 3.5 `T²` vs masa: no ejecutado

`agente-resorte/salidas/verificacion/masas_varias/` **no existe**. No se ejecutó el barrido de masas, no hay tabla `T²` vs `m`, no hay ajuste de `k` vs masa y no se contrastó `m_resorte/3`. No se agregan valores. `[C]`

## 4. Validación sintética

Casos de `agente-resorte/salidas/verificacion/mejoras/`. La verdad del generador es `k = 6.49 N/m`; el caso correcto tiene `T` esperado `≈ 0.64217 s`. `[C]`

| Caso | Masas (g) | `T` (s) | `k` (N/m) | `x_eq` esperada (cm) | Avisos | Estado |
|---|---:|---:|---:|---:|---:|---|
| `sintetico_correcto` | 64.55 / 9.73 | 0.6421715 ± 0.0000001 | 6.49001 ± 0.00138 | 9.757 ± 0.010 | 0 | Aceptable (antes Revisar) |
| `sintetico_10x` | 645.5 / 97.3 | 2.0307245 ± 0.0000004 | 6.49007 ± 0.00138 | 97.57 ± 0.10 | 1 | Aceptable |
| `sintetico_10x_error` | 3090 / 973 | 4.5573324 ± 0.0000018 | 6.49033 ± 0.00190 | 467.05 ± 0.48 | 2 | Aceptable |

- En el caso correcto, el ajuste recupera `T`, `k` y `x_eq`; el cambio de estado de `Revisar` a `Aceptable` se debe a la regla nueva, no a una mejora de los datos. `[C]`
- En los casos ×10, `T` y `k` son coherentes con las masas ingresadas, pero `x_eq` es físicamente implausible. El estado sigue `Aceptable`: las masas solo generan advertencias, no bloquean el resultado. `[C]`
- No se corrieron en esta sesión casos nuevos de ruido, dos marcas, fondo, outliers ni videos sintéticos largos. `[NV]`

## 5. Hallazgos, correcciones y efectos

1. **Error de masas y escala corregido.** La corrida previa usó `0.3090 kg`, `0.09730 kg` y `6397 ± 12 px/m`; el nuevo análisis usa `0.06455 kg`, `0.00973 kg` y `2262 ± 20 px/m`. `0.3090 kg` coincide numéricamente con `30.9 g × 10` (R1), no con R1+P1; `0.09730 kg` es `9.73 g × 10`. `[C]` en `resultado_3videos/informe.md` y `reales/resultados.json`.
2. **`T` no depende de la escala; `k` sí depende de la masa.** Las dos corridas dan `T ≈ 0.642 s`, pero `k` pasa de `≈32.7` a `≈6.49 N/m` (factor `5.04`) y `A` cambia con la escala. No usar `k = 32.7 N/m` como resultado físico. `[C]`
3. **Video4 tenía un punto inválido.** `(860,421)` cae sobre el resorte; la corrida vieja perdió `63.96 %`, dio `T = 5181 ± 27 743 122 s` y `A = 79.44 m`, valores no interpretables. La corrida final usa `(875,675)` y `--desde 37.001`; logra `0 %` de pérdidas y un ajuste Aceptable. `[C]`/`[NV]` para la inspección visual.
4. **El estado nuevo no bloquea masas absurdas.** `sintetico_10x` y `sintetico_10x_error` quedan `Aceptable` con extensiones esperadas de `97.6` y `467.0 cm`. Falta que la plausibilidad de masa/extensión cambie el estado, no solo el texto de advertencia. `[C]`
5. **`χ²` cercano a 1 no es una validación independiente.** `ajuste.py` estima el ruido extra de los residuos del mismo ajuste; por eso el `χ²` con piso queda `0.636–1.012`, mientras que sin piso va de `4.99` a `117`. `[C]` en `SENSIBILIDAD_CLIC.md`.
6. **El clic sobre la masa es sensible en Video3.** En 12 perturbaciones, 9 conservan `T ≈ 0.642 s`; 3 fallan: `(+0,−10)` pierde `70.24 %` y da `T = 6.3158 s`, `(+0,−20)` da `T = 881.25 s` y `(−20,+0)` pierde `85.44 %` con ajuste singular. `[C]` en `SENSIBILIDAD_CLIC.md`.
7. **Energías y borde.** El último `0.5 s` de Video3 tiene un máximo relativo de `28.35 %` en `Et`; con exclusión de 5 cuadros en cada extremo, el sesgo baja a `−3.98 %` al final. Las energías dependen de `A²` y de la escala; no sirven como resultado final. `[C]`
8. **Tiempos de cuadro.** Las marcas están cuantizadas a `1/600 s`; `dt` mediana `16.667 ms`, mínimo `15.000 ms`, máximo `18.333 ms`. Usar tiempos reales cambia `T` menos de `0.004 %`. `[C]` en `amplitud/tiempos_cuadro_resumen.csv`.
9. **Período vs amplitud.** Las pendientes `T(A)` por ventanas son `0.123 ± 0.081 s/m` (Video2), `0.478 ± 0.029 s/m` (Video3) y `−0.011 ± 0.022 s/m` (Video4); la pendiente común se rechaza con `p ≈ 0`, pero Video3 tiene `χ²/dof = 81.3` y una sola corrida. No se interpreta como no linealidad física. `[C]` en `amplitud/resumen_pendientes.txt`.

## 6. Estado frente a la consigna

| Requisito | Estado | Evidencia | Observaciones |
|---|---|---|---|
| Seguir la masa varios ciclos sin saltar a mano/objeto | PARCIAL | `tracking.py`; pérdidas `0/0/16.38 %` totales y `0 %` en el tramo | Video3 depende del clic; Video4 necesita punto y arranque en `37 s`. |
| Informar pérdidas y baja confianza | HECHO | `*_px_tracking.json`; `perdidos_pct`, saltos, candidatos, estado | Incluye advertencias y criterios. |
| Calibración espacial `px/m` con σ | PARCIAL | `calibracion.py`; `2262 ± 20 px/m` | Es argumento, no calibración independiente; la app permite regla de dos puntos. |
| Calibración temporal con LED y σ | PARCIAL | `fps_real_con_led()`; FPS declarado `σ = 0` | No se usó LED real; `k` escala con `fps²`. |
| Tabla `t, x, y, σx, σy` | HECHO | `*_px.csv`, `*_m.csv` | Generadas para los tres videos. |
| Derivar/filtrar, comparación crudo/filtrado y ajuste con error | PARCIAL | `señal.py`, `ajuste.py`; ventana `11` | La app ofrece `7/11/21/41`, pero no hay barrido con criterio registrado. |
| `k` dinámica y `k` estática | PARCIAL | `ajuste.py:cantidades`, `k_estatico` | La estática no se midió; no hay contraste real. |
| Máximos `x`, `v`, `a` con instante/posición | HECHO | `ajuste.py:maximos`; `reales/informe.md` | Calculados sobre el ajuste; no son mediciones independientes. |
| Energías cinética, elástica y total | PARCIAL | `ajuste.py:energias`; `energia_borde` | Dependen de `A²`, escala y borde; Video3 con sesgo de `28.35 %`. |
| Amortiguamiento `γ` | PARCIAL | `ajuste.py`, `calidad.py` | Solo por ajuste; no se contrastó con decrecimiento logarítmico de la envolvente. |
| Masa efectiva y chequeo de período | HECHO | `m_ef = m + m_r/3`; `chequeo_periodo()` | Verifica consistencia, pero no reemplaza una `k` estática. |
| N repeticiones, criterio y referencia | PARCIAL | N = 3; IC95 `t(2)`; `reales/resultados.json` | La receta pide 5–20; no hay referencia externa del Grupo 8. |
| Todo número con unidad e incerteza | PARCIAL | `informe.md`, `resultados.json` | FPS declarado sin σ; `A` sin sistemática de escala; RMS y `χ²` adimensionales. |
| Limitaciones obligatorias | HECHO | Este informe, sección 7 | Incluye qué falló, condiciones de falla y pendientes. |
| Diagramas de cuerpo libre | FALTA | No hay archivo, figura ni script de DCL | No se generó en esta etapa. |
| Comparación contra el Grupo 8 | FALTA | No hay `k` ni resultados independientes del G8 | Se usan videos/masas atribuidos al G8, pero no una comparación externa. |
| Un punto por video y recorte automático | HECHO | `app.py`, `main.py`, `señal.py`; puntos y tramos de la tabla 3.1 | `--desde` y `--inicio` tienen funciones distintas. |
| Funcionar sin internet en la medición | HECHO | OpenCV clásico; no hay servicios en el pipeline | El chatbot es un componente aparte. |
| Pruebas automatizadas | HECHO | `82/82`; `test_calidad` `20/20` | No hay lint/typecheck configurado. |
| Dependencias reproducibles | PARCIAL | `requirements.txt` sin versiones; no hay lockfile | Versiones observadas en la sección 9. |
| Informe/JSON versionados | PARCIAL | `informe.md`, `resultados.json` | `salidas/` y videos están ignorados por Git. |
| No usar IA preentrenada en la medición | HECHO | `tracking.py` y `ajuste.py` no usan modelos generativos | El chatbot bibliográfico usa Ollama/Qwen por CLI, fuera de la medición. |

## 7. Limitaciones

### 7.1 Qué falló o puede fallar

- **Escala no independiente.** `2262 ± 20 px/m` es un argumento. Un error de `0.884 %` en escala produce `0.884 %` en `A` y `1.77 %` en energía; no afecta `T` ni `k` dinámica. `[C]`
- **FPS no verificado.** Se usa el FPS declarado (`59.97 fps`, `σ = 0`). Si el FPS real difiere `1 %`, `k` cambia `≈2 %` porque `k ∝ fps²`. `[C]`/`[NV]`
- **Masas atribuidas.** No hay hoja de medición que confirme R1+P1 = `64.55 g` y resorte = `9.73 g`; una masa incorrecta cambia `k` y `x_eq`. `[S]`
- **Clic en Video3.** Desplazamientos de `10–20 px` pueden perder `70–85 %` de los cuadros, cambiar el inicio automático y producir `T` sin sentido. `[C]`
- **Video4.** El punto `(860,421)` es inválido; el punto final `(875,675)` no se revisó visualmente en esta sesión. `[C]`/`[NV]`
- **Regla de calidad de masas.** Las masas ×10 de los sintéticos quedan `Aceptable`; no hay bloqueo por `x_eq` fuera de rango. `[C]`
- **`χ²`.** El piso de ruido se estima del mismo ajuste; un `χ² ≈ 1` no demuestra que el modelo sea correcto. `[C]`
- **Energías.** El borde del filtro Savitzky-Golay sesga `Et` al inicio/final; Video3 tiene un máximo de `28.35 %` en el último `0.5 s`. `[C]`
- **N = 3.** El IC95 con `t(2)` es ancho; no se alcanzan 5–20 repeticiones. `[C]`

### 7.2 Condiciones en las que se rompe

- El tracker se rompe si el clic cae sobre el resorte, el fondo o una mano que ocluye la masa; Video4 viejo y Video3 con `−20 px` lo muestran. `[C]`
- El detector de inicio puede marcar `t = 0` si la oscilación ya está presente en el primer cuadro o si la trayectoria interpolada tiene huecos; no distingue una liberación real de un reacomodo. `[C]`
- El ajuste puede dar parámetros no interpretables si quedan pocos cuadros válidos o si la matriz es singular; el estado debe ser `Revisar`/`Inválido`, no un resultado físico. `[C]`
- La comparación `T` vs amplitud se rompe si se mezclan ventanas con deriva, clics distintos o cambios de escala; Video3 lo evidencia con `χ²/dof = 81.3`. `[C]`

### 7.3 Sin resolver

- No hay `k` estática ni `x_eq` medida para comparar con `9.754 ± 0.010 cm`. `[NV]`
- No hay FPS con LED, escala por regla independiente, ni hoja de masas firmada. `[NV]`
- No hay 5–20 repeticiones ni videos nuevos; no hay grabación con varias amplitudes controladas. `[NV]`
- No se ejecutó `masas_varias`; no hay `T²` vs masa. `[C]`
- No se analizó `Video Project 3.mp4`; no se ubicó un punto válido. `[NV]`
- No hay DCL ni comparación externa con el Grupo 8. `[NV]`
- No se validó la app completa con uploads reales; solo se revisó el código y los resultados del pipeline. `[NV]`
- El chatbot 3C sigue sin integración y no se declara estable. `[C]`/`[NV]`

## 8. Pendientes priorizados

| Prioridad | Tarea | Esfuerzo | Archivo / responsable |
|---|---|---|---|
| P0 | Confirmar masas R1, P1 y resorte; conseguir la hoja de medición | 0.5 h | Datos del G8; `main.py` no cambia |
| P0 | Calibrar escala con regla u objeto de `13.425 ± 0.005 cm` | 0.5–1 h | `calibracion.py`; datos nuevos |
| P0 | Medir `k` estática y `x_eq` con la misma masa | 1 h | `ajuste.py:k_estatico`; informe |
| P0 | Verificar FPS con LED o cronómetro | 1 h | `calibracion.py:fps_real_con_led` |
| P1 | Hacer que masas/extensión implausibles cambien el estado, no solo el aviso | 1–2 h | `calidad.py`, `main.py`, `tests/test_calidad.py` |
| P1 | Repetir 5–20 liberaciones con la misma masa | 2–4 h | `main.py`; datos nuevos |
| P1 | Revisar visualmente los puntos de Video3/Video4 y documentar el clic | 1 h | `tracking.py`; metadatos |
| P1 | Completar DCL vertical y horizontal | 2–3 h | Informe/figuras; no hay archivo actual |
| P2 | Automatizar la calibración de la regla | 4–8 h | `calibracion.py`, `app.py` |
| P2 | Contraste independiente de `γ` por envolvente/log-decremento | 2–3 h | `calidad.py`/`ajuste.py` |
| P2 | Repetir `T` vs `A` con amplitudes controladas | 2 h | Datos nuevos; `amplitud/` |
| P2 | Fijar versiones o agregar lockfile | 1 h | `requirements.txt` |
| P3 | Actualizar README y retirar estados superados de reportes viejos | 1 h | `README.md`, reportes |

## 9. Reproducibilidad

### 9.1 Versiones observadas

| Componente | Versión |
|---|---|
| Python | 3.14.8 |
| Sistema | Windows 11, `10.0.26200` |
| numpy | 2.5.4 |
| scipy | 1.18.1 |
| pandas | 3.1.0 |
| opencv-python | 5.0.0.93 |
| lmfit | 1.3.4 |
| uncertainties | 3.2.3 |
| matplotlib | 3.11.2 |
| streamlit | 1.66.1 |

`requirements.txt` no fija versiones. No hay `pyproject.toml`, lockfile ni lint/typecheck. `[C]`

### 9.2 Comandos

Reanálisis exacto que reproduce la corrida `reales` (desde `agente-resorte/`):

```powershell
.\venv\Scripts\python.exe main.py `
  --trayectoria salidas\resultado_masas_g8\Video2_R1_P1_px.csv `
  --trayectoria salidas\resultado_masas_g8\Video3_R1_P1_px.csv `
  --trayectoria salidas\resultado_masas_g8\Video4_R1_P1_px.csv `
  --masa-g 64.55 --sigma-masa 0.000014 `
  --masa-resorte-g 9.73 --sigma-masa-resorte 0.00001 `
  --px-por-m 2262 --sigma-px-por-m 20 `
  --ventana 11 --eje y `
  --salidas salidas\verificacion\mejoras\reales
```

Ruta para volver a rastrear desde los videos (no reejecutada en esta sesión): usar `--punto` y, solo en Video4, `--desde 37.001`; no aplicar `--desde 37.001` a Video2/3. `[NV]`

```powershell
# Video2 y Video3: --desde 0 por defecto
.\venv\Scripts\python.exe main.py datos\Video2_R1_P1.MOV --punto 850 700 `
  --masa-g 64.55 --sigma-masa 0.000014 --masa-resorte-g 9.73 --sigma-masa-resorte 0.00001 `
  --px-por-m 2262 --sigma-px-por-m 20 --eje y --ventana 11 --salidas salidas\repro\Video2

.\venv\Scripts\python.exe main.py datos\Video3_R1_P1.MOV --punto 840 708 `
  --masa-g 64.55 --sigma-masa 0.000014 --masa-resorte-g 9.73 --sigma-masa-resorte 0.00001 `
  --px-por-m 2262 --sigma-px-por-m 20 --eje y --ventana 11 --salidas salidas\repro\Video3

.\venv\Scripts\python.exe main.py datos\Video4_R1_P1.MOV --punto 875 675 --desde 37.001 `
  --masa-g 64.55 --sigma-masa 0.000014 --masa-resorte-g 9.73 --sigma-masa-resorte 0.00001 `
  --px-por-m 2262 --sigma-px-por-m 20 --eje y --ventana 11 --salidas salidas\repro\Video4
```

Pruebas:

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -q
.\venv\Scripts\python.exe -m unittest tests.test_calidad -q
.\venv\Scripts\python.exe -m py_compile calidad.py main.py app.py
```

Resultados verificados: suite `82/82` OK; `test_calidad` `20/20`; `py_compile` sin errores. `[C]`

### 9.3 Artefactos y Git

- La corrida `reales` deja `informe.md`, `resultados.json`, `*_px.csv`, `*_m.csv`, `*_px_tracking.json`, `*_senal.png` y `*_ajuste.png` en `agente-resorte/salidas/verificacion/mejoras/reales/`. `[C]`
- `resultado_masas_g8/` conserva la corrida con las masas corregidas, pero su `informe.md` no incluye todos los campos nuevos; la relectura `reales` sí los incluye. `[C]`
- `salidas/`, `datos/` y los videos están ignorados por `.gitignore`; un clon limpio no recibe la evidencia. `[C]`
- El JSON de `reales` registra `commit_git = 90f7f71`, porque se generó con los cambios todavía sin commit; el código final quedó en `03463ed`. `[C]`
- El informe `resultado_3videos` y el `REPORTE_VERIFICACION.md` contienen estados y amplitudes de corridas anteriores; no deben mezclarse con la tabla 3.3. `[C]`

## 10. Preguntas abiertas y no verificado

1. ¿La masa colgante es exactamente `R1 + P1 = 30.9 + 33.65 g = 64.55 g`, o P1 tiene otra masa? `[S]`
2. ¿Los `9.73 g` del resorte son la masa total y corresponden al factor `m_r/3`? `[S]`
3. ¿Cuál es el origen de `2262 ± 20 px/m` y qué objeto mide `13.425 ± 0.005 cm`? `[NV]`
4. ¿El FPS real coincide con `59.97 fps`? ¿Hay LED o cronómetro disponible? `[NV]`
5. ¿El Grupo 8 midió `k` estática o `x_eq`? ¿Con qué masa y escala? `[NV]`
6. ¿Se pueden conseguir 5–20 repeticiones y varias amplitudes controladas? `[NV]`
7. ¿`Video Project 3.mp4` es un recorte de Video2 y de dónde sale la escala `6397 px/m`? `[NV]`
8. ¿La comparación con el Grupo 8 exige `k` estática, o alcanza con contrastar `T` y `k` dinámica? `[NV]`

## Discrepancias encontradas

1. **`resultado_3videos` no es la corrida correcta.** Usa `0.3090 kg` y `0.09730 kg`; el valor `0.3090 kg` coincide con R1 `30.9 g` con la coma corrida, no con R1+P1 `64.55 g`. Usa escala `6397 ± 12 px/m`, factor `2.828` respecto de `2262`. `T` coincide, pero `k` y `A` no. `[C]`
2. **Video4 antiguo.** `(860,421)` cae sobre el resorte: `63.96 %` de pérdidas, `T = 5181 ± 27 743 122 s`, `A = 79.44 m`; no es un resultado físico. La corrida final usa `(875,675)` y `37.001 s`, con `0 %` de pérdidas. `[C]`
3. **Tabla de sensibilidad al clic.** La tabla antigua marca `OK` en Video3 con `70.24 %` de pérdidas y `T = 6.3158 s`; la regla nueva no debería aceptar ese caso. Los 3 casos que fallan son `(+0,−10)`, `(+0,−20)` y `(−20,+0)`. `[C]`
4. **Masas ×10.** `sintetico_10x` y `sintetico_10x_error` quedan `Aceptable` con `x_eq` de `97.57` y `467.05 cm`; el estado no bloquea la incoherencia física. `[C]`
5. **`χ²`.** El `χ²` con piso (`0.636–1.012`) se obtiene sumando un ruido estimado de los mismos residuos; no es una prueba independiente. `[C]`
6. **Amplitudes mezcladas.** `REPORTE_VERIFICACION.md` informa `0.07636` y `0.06614 m` con escala provisional `2000 px/m`; no son comparables con `A` de la tabla 3.3, calculada con `2262 px/m`. `[C]`
7. **Campos faltantes en el informe viejo del G8.** `resultado_masas_g8/informe.md` no muestra `A`, `x_eq`, cruces ni bordes; la relectura `reales` sí. Los `T`/`k` coinciden. `[C]`
8. **Metadatos de corrida.** El JSON `reales` declara `commit_git = 90f7f71`, anterior a `03463ed`; se generó antes del commit con los archivos que luego se commitearon. `[C]`
9. **Documentación superada.** `REPORTE_ESTADO_2.md`, `REPORTE_ESTADO_4.md`, `REPORTE_ESTADO_6.md` y `INFORME_ESTADO_13_NOV.md` describen estados anteriores (por ejemplo, ausencia de tests o de punto por video). Este informe reemplaza esas afirmaciones para el estado del 15/11/2026. `[C]`
10. **Sin datos de `masas_varias`.** No existe la carpeta y no se ejecutó el estudio; cualquier conclusión sobre `k(m)` o `m_resorte/3` sería inventada. `[C]`

## Fuentes consultadas

- `agente-resorte/main.py`, `app.py`, `calidad.py`, `ajuste.py`, `señal.py`, `tracking.py`, `calibracion.py`.
- `agente-resorte/tests/test_calidad.py`, `tests/test_agente.py` y resto de `tests/`.
- `agente-resorte/salidas/verificacion/mejoras/reales/{informe.md,resultados.json}` y metadatos de tracking.
- `agente-resorte/salidas/verificacion/mejoras/sintetico_{correcto,10x,10x_error}/resultados.json`.
- `agente-resorte/salidas/verificacion/{SENSIBILIDAD_CLIC.md,REPORTE_VERIFICACION.md,REGRESION_Y_DIAGNOSTICOS.md}`.
- `agente-resorte/salidas/verificacion/amplitud/{tiempos_cuadro_resumen.csv,global_por_video.csv,ventanas_periodo_amplitud.csv,resumen_pendientes.txt}`.
- `agente-resorte/salidas/resultado_masas_g8/{informe.md,resultados.json,*_px_tracking.json}`.
- `agente-resorte/salidas/resultado_3videos/{informe.md,resultados.json}`.
- `README.md`, `TAREAS_PENDIENTES.md`, `REPORTE_ESTADO_2.md`, `REPORTE_ESTADO_4.md`, `REPORTE_ESTADO_6.md`, `INFORME_ESTADO_13_NOV.md`, `ESTADO_ACTUAL_Y_HOJA_DE_RUTA.md`.
- `git log`, `git diff --stat`, `git status --short`; `python --version` y `pip list` del entorno local.
