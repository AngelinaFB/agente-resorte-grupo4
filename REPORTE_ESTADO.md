# REPORTE_ESTADO — auditoría vs consigna (Grupo 4, Línea III, movimiento 3: Resorte)

Auditoría hecha sobre el árbol de trabajo limpio (`git status`: nada para commit) + ejecución
de prueba del pipeline con videos sintéticos en un directorio temporal (fuera del repo, sin tocar código).

## Resumen

1. El pipeline completo existe en código (tracking → calibración → señal → ajuste → informe) y **corre de punta a punta**: lo probé con 2 videos sintéticos y recupera `k_sin_m_ef = 12.000 ± 0.060 N/m` contra el valor verdadero `12.0 N/m` (`generador_sintetico.py`, verdad en `*_verdad.json`).
2. En el repo **no hay ningún resultado ejecutado**: ni videos, ni CSV, ni `salidas/`, ni `informe.md` (los tres directorios están en `.gitignore`), ni link de Drive en el README, pese a que el README mismo pide dejarlo.
3. Faltan ítems enteros de la consigna: **comparación contra el Grupo 8** (no hay datos ni código), **diagramas de cuerpo libre** (no hay ningún archivo de figura), y la **sección de limitaciones** queda como plantilla vacía.
4. La calibración espacial/temporal está *implementada* pero no *ejecutada* en el repo: `fps_real_con_led` funciona (lo verifiqué: 30.0 ± 0.0 fps) pero `main.py` nunca la invoca, y `--sigma-px-por-m` tiene default `0.0`.
5. Cumplimiento global aproximado: ~2 HECHO, ~9 PARCIAL, ~3 FALTA; el principal bloqueo no es de código sino de **datos y evidencia**.

## Tabla de requisitos

| Requisito | Estado | Evidencia | Observaciones |
|---|---|---|---|
| **GLOBALES** ||||
| Todo número con unidad e incerteza | PARCIAL | `main.py:78-105` (informe), `fmt()` `main.py:17-22` | T, γ, k, escala salen con σ y unidad. **Sin σ**: máximos (`main.py:103-105`), energía (`main.py:53-55` usa nominales), `k_estatico` con `g=9.81` exacto y elongaciones sin incerteza (`ajuste.py:51-55`), `verdad.json` sin unidades. |
| Resultado = N mediciones + criterio + referencia | PARCIAL | `main.py:80` (N videos/fallidos), `main.py:94-101` (media ± error estándar, dispersión s), `main.py:86-90` (χ² red. por video) | N y criterio están; **el valor de referencia (Grupo 8) no existe en ninguna parte del repo**, así que no se contrasta contra nada. |
| Sección de limitaciones obligatoria | PARCIAL | `main.py:115-138` | Hay un bloque automático bueno (cuadros perdidos, χ², ciclos, cuadros/período, γ≈0, N<5, fps no verificado, falta k estático, videos fallidos) **más una plantilla vacía** "Qué falló / En qué condición se rompe / Qué quedó sin resolver" sin completar. |
| **PIPELINE** ||||
| 1. Calibración espacial (px/m con incerteza) | PARCIAL | `calibracion.py:30-36` (`escala_px_por_m`, propaga error de click y de la regla), `calibracion.py:6-27` (`marcar_dos_puntos`) | Implementado y con σ, pero: `main.py:152` `--sigma-px-por-m` default `0.0` (si el usuario da sólo `--px-por-m`, la incerteza de escala es 0); la ruta `--regla-m` requiere ventana GUI con clicks (no ejecutable headless, no probada); no hay evidencia de ninguna corrida con regla real. |
| 2. Calibración temporal (fps reales) | PARCIAL | `calibracion.py:39-57` (`fps_real_con_led`), `main.py:35,130-131` | La función **existe y funciona** (test propio: video con LED 10 Hz → 30.0 ± 0.0 fps), pero `main.py` no la invoca: sólo acepta `--fps-real` declarado por el usuario; si no se da, usa el fps del celular y lo anota en limitaciones. σ del fps no se propaga a T. |
| 3. Varias repeticiones (no un video) | PARCIAL | `main.py:180-188` (bucle), `main.py:69-75` (`agregado`), `main.py:128-129` (aviso si N<5) | Código correcto (probado con 2 sintéticos → media ± EEM por variable). **0 videos reales en el repo**; no se puede verificar que se hayan procesado 5-20 repeticiones. |
| 4. Tabla de salida (t, x, y, σx, σy) | PARCIAL | `tracking.py:71-75` (cabecera `t_s,x_px,y_px,sx_px,sy_px`), `calibracion.py:77-80` (pasado a metros) | Estructura correcta y verificada en la corrida de prueba. Pero σx=σy=0.29 px **es una constante asumida** (`tracking.py:17`, "1/√12 px"), no medida; σ es NaN en cuadros sin detección; ninguna tabla quedó versionada (`datos/`, `salidas/` en `.gitignore`). |
| 5. Derivar/limpiar + crudo vs filtrado + ajuste con error | PARCIAL | Receta en `señal.py:34-42` (`procesar`: x→v→a con Savitzky-Golay en cada etapa), comparación crudo/filtrado en `señal.py:52-66` (PNG), ajuste ponderado con covarianza en `ajuste.py:15-26` + `parametros_con_incerteza` `ajuste.py:29-34` | La receta y el ajuste están. **Pero**: (a) la comparación crudo vs filtrado es sólo un gráfico, no una métrica en el informe; (b) `incerteza_cruda` (`señal.py:45-49`) no se usa en el pipeline, sólo en el `__main__` de `señal.py`; (c) el criterio de elección de ventana (barrido 7/11/21/41 vs verdad sintética) sólo está escrito en el README, **no hay código ni resultados de ese barrido**; (d) el `__main__` de `señal.py` falla por `tabla_m.csv` ausente. |
| 6. Cantidades físicas con σ propagada + contraste vs Grupo 8 | PARCIAL | `ajuste.py:29-48` (`correlated_values`, `cantidades`), `main.py:86-101` | Propagación de incerteza real y probada. **Contraste con la referencia: FALTA** (ver fila abajo). |
| **REQUISITOS DEL RESORTE** ||||
| k por elongación en equilibrio vs masa (vertical) | PARCIAL | `ajuste.py:51-55` (`k_estatico`, polyfit con covarianza, ≥3 puntos exigidos en `main.py:176-178`) | Funciona (test: k = 11.847 ± 0.061 N/m con los datos de ejemplo del README). **Los datos reales no están en el repo**, `g` sin incerteza, elongaciones sin σ. |
| x(t), v(t), a(t) con máximos y su posición | PARCIAL | Gráficos `señal.py:52-66`; máximos `ajuste.py:75-82`; salida en `main.py:103-105` | Existe, con unidades en las etiquetas. Problemas: **sin incerteza**; y al hacer `.strip()` (`main.py:105`) las claves `"  en x (m)"` y `"  en x (m) "` colisionan: el informe muestra dos líneas idénticas "en x (m)" / "en t (s)" sin decir si es de v_max o de a_max (verificado en la corrida de prueba). |
| Diagrama de cuerpo libre (vertical y horizontal) | FALTA | — | No hay ninguna figura, plantilla ni código que genere un DCL en todo el repo (sólo hay 7 archivos `.py`, 1 `requirements.txt` y el README en la raíz). |
| Energía cinética y elástica a lo largo de una oscilación | PARCIAL | `ajuste.py:68-72` (`energias`), gráfico `ajuste.py:93-94` (Ec, Ep, Et) | Se calcula y se grafica por video. **Con valores nominales** (`main.py:53-55`: `k_con_mef.nominal_value`, `m_ef.nominal_value`) → sin incerteza; no entra al informe; no se analiza conservación ni su decaimiento por amortiguamiento. |
| Amortiguamiento si es visible | PARCIAL | γ con σ en informe (`main.py:86-90`), chequeo automático `main.py:126-127` ("γ compatible con 0"), modelo amortiguado `ajuste.py:10-12` | Detectado por un solo método (ajuste). Sin segunda estimación independiente (decrecimiento logarítmico de envolvente) para cross-check. |
| Chequeo físico: masa efectiva y período con/sin m_ef | PARCIAL | `ajuste.py:41` (`m_ef = m + m_r/3`), `ajuste.py:58-65` (`chequeo_periodo`), volcado al informe `main.py:107-113` | Probado y funciona: imprime T sin/con m_ef, diferencia con T medido en σ para cada caso. **No dice explícitamente cuál de los dos coincide** (sólo lista ambas diferencias), y requiere `k_e` independiente que no está en el repo (el informe lo avisa). |
| **Comparación explícita contra Grupo 8** | **FALTA** | — | Cero menciones a "Grupo 8", "Tracker", "referencia" en todo el código y en el README. No hay archivo de datos del grupo, ni campo en el informe para la comparación, ni siquiera el link de Drive que el propio README pide dejar. |

## Problemas detectados

1. **Sin resultados ni datos versionados**: `datos/`, `salidas/` y `*.mp4` están en `.gitignore`; el repo no contiene CSV, gráficos, `informe.md`, `resultados.json` ni videos. Todo lo que se afirme sobre "anduvo bien" es **no verificable desde el repo**.
2. **Referencia (Grupo 8) ausente**: no hay datos, archivo de comparación ni link en el README (`README.md:13-14` sólo explica la política de no subir videos, sin dejar URL).
3. **`--sigma-px-por-m` default 0.0** (`main.py:152`): si se entrega `--px-por-m` sin σ, la incerteza de escala se ignora y σx, σy quedan subestimadas.
4. **σx, σy constantes y asumidas** (`tracking.py:17`, `SIGMA_PX = 0.29`): no se estima empíricamente (p. ej. dispersión del centroide sobre un objeto estático). Efecto visible: χ² red. = 1.57 en el sintético, es decir las σ del ajuste no están calibradas.
5. **fps real no forma parte del pipeline**: `fps_real_con_led` está desconectado de `main.py` (sólo se puede pasar `--fps-real` a mano); la σ del fps no se propaga a T ni a k.
6. **Máximos sin incerteza y con etiquetas ambiguas** (`main.py:103-105` + `ajuste.py:75-82`): tras `.strip()` las etiquetas de v_max y de a_max quedan iguales.
7. **Energía sin incerteza** (`main.py:53-55`): usa nominales de k y m_ef, violando la regla "todo número con incerteza".
8. **`k_estatico` con `g = 9.81` exacto y elongaciones sin σ** (`ajuste.py:51`): la incerteza de k estático queda sólo del scatter de la recta.
9. **`--masa-resorte` default 0.0** (`main.py:149`): si no se informa, `k_con_mef` y `k_sin_m_ef` son idénticos y el chequeo de masa efectiva pierde sentido (además de asumir resorte uniforme, m/3, sin verificarlo).
10. **Sección de limitaciones sin completar** (`main.py:137-138`): plantilla vacía en todo informe generado.
11. **`requirements.txt` sin versiones** (`requirements.txt:1-6`), pese a que el README dice "En Requirements.txt fijamos versiones" (`README.md:4`). Además el `venv/` del repo tiene **sólo pip**: las dependencias no están instaladas ahí.
12. **Sin tests, CI ni notebooks**: cero archivos de test en el repo; la única validación posible (vs `verdad.json` del generador sintético) no está automatizada.
13. **`señal.py` se importa por nombre con "ñ"** (`main.py:12`): funciona en este entorno (UTF-8), pero es fricción para clonar en otros sistemas/CI.
14. **`a_metros` con `fps_real` deriva el video con `csv_entrada.replace(".csv", ".mp4")`** (`calibracion.py:73-76`): frágil (rompe con `.csv` en medio del nombre o con otra extensión); además está duplicado respecto de la corrección que hace `main.py:38`.
15. **Escala calculada una sola vez con el primer video** y aplicada a todos (`main.py:167-172`): asume mismo setup/cámara sin verificar.
16. **`resultados.json` sin unidades ni metadatos** (`main.py:190-192`): sólo pares (valor, error); no registra escala, fps, versión del código ni commit → reproducibilidad limitada.
17. **Criterio de ventana Savitzky-Golay no implementado**: el README pide barrer 7/11/21/41 y elegir con criterio explícito (`README.md:28-31`); no hay script ni resultado de ese barrido, sólo el default `--ventana 11` (`main.py:156`).
18. **Ruta `--regla-m` exige GUI** (`calibracion.py:20-26`, `cv2.imshow` + clicks): no funciona en headless ni en CI; no hay fallback para marcar puntos por archivo.

## Pendientes priorizados

| # | Pendiente | Prioridad | Esfuerzo | Archivo a crear/tocar |
|---|---|---|---|---|
| 1 | **Traer los datos del Grupo 8** (`datos/referencia_g8.csv` o similar: T, x(t), σ) y agregar bloque "Comparación vs medición humana" en el informe con diferencia en σ | Crítica | Grande (depende de datos ajenos) | crear `datos/referencia_g8.*`; tocar `main.escribir_informe` + nuevo arg `--referencia` |
| 2 | **Ejecutar el pipeline con 5-20 videos reales** y versionar la evidencia (`salidas/informe.md`, CSV) o dejar el link de Drive en el README | Crítica | Grande | `README.md` (link), carpeta `salidas/` o `docs/` con outputs |
| 3 | **Completar la sección de limitaciones** a mano en el informe final (qué falló, en qué condición se rompe, qué quedó sin resolver) | Crítica | Chico | `main.py:137-138` (o el `informe.md` final) |
| 4 | **Diagramas de cuerpo libre** vertical y horizontal (imagen generada o dibujada) | Alta | Chico | crear `dcl.py` o `assets/dcl_*.png` |
| 5 | **Máximos con incerteza** y etiquetas desambiguadas (v_max vs a_max) | Alta | Chico | `ajuste.maximos` (`ajuste.py:75-82`), `main.py:103-105` |
| 6 | **Energía con incerteza propagada** (ufloat de k y m_ef) y volcado al informe, no sólo al PNG | Alta | Chico | `main.py:53-55`, `ajuste.energias`, `main.escribir_informe` |
| 7 | **Hacer obligatorio `--sigma-px-por-m`** (o estimarlo) y dar σ a `g` y a las elongaciones en `k_estatico` | Media | Chico | `main.py:152,163-164`, `ajuste.py:51-55` |
| 8 | **Conectar `fps_real_con_led` a `main.py`** (`--video-led`) y propagar σ_fps a T/k | Media | Chico | `main.py` (args + `analizar`) |
| 9 | **Barrido de ventana Savitzky-Golay vs verdad sintética** (7/11/21/41) y criterio registrado en el informe | Media | Medio | crear `ventana_check.py`; tocar `main.escribir_informe` |
| 10 | **Comparación crudo vs filtrado cuantificada** en el informe (RMS de a_c vs a_f, error vs ajuste), no sólo el PNG | Media | Chico | `señal.procesar`/`main.escribir_informe` |
| 11 | **Decir explícitamente** en el chequeo de período cuál T (con/sin m_ef) es el compatible | Media | Chico | `ajuste.chequeo_periodo` (`ajuste.py:58-65`) |
| 12 | **Fijar versiones en `requirements.txt`** (el README lo promete) | Baja | Chico | `requirements.txt` |
| 13 | **Tests automatizados** con el generador sintético: |k_rec − k_true| < 3σ, T < 3σ, N cuadros, fps | Baja | Medio | crear `test_pipeline.py` |
| 14 | **Metadatos en `resultados.json`** (escala, fps, commit, unidades) | Baja | Chico | `main.py:190-192` |

## Qué no se puede verificar desde el repo

- **Datos/videos del Grupo 8**: no existen aquí, ni link en el README. No se puede contrastar nada.
- **Videos reales del experimento** (horizontal y vertical): ninguno (política de no subir videos); tampoco hay evidencia de que se hayan procesado.
- **Resultados ejecutados**: `salidas/` y `datos/` están ignorados por git → no hay forma de saber si el pipeline corrió con datos reales, con qué N, o con qué escala.
- **fps real del celular**: no hay registro de medición con LED/cronómetro.
- **Masa real del resorte y sus incertezas**: sólo defaults en CLI (`0.0 kg`).
- **Si la calibración con regla se usó**: el `--regla-m` no tiene salida persistente (no guarda los puntos ni el σ de la corrida).
- Corridas de auditoría (realizadas por mí en `Temp\opencode\audit`, fuera del repo): `generador_sintetico` → `main.py` con 2 videos OK; chequeo de período con k estático OK; `fps_real_con_led` OK; `señal.py.__main__` y `calibracion.py.__main__` **fallan** por falta de `tabla_m.csv`/`tabla.csv`.

## Preguntas abiertas para el equipo

1. ¿Dónde están los datos/videos del Grupo 8? ¿Se puede dejar el link de Drive en el README?
2. ¿Se alcanzaron las 5-20 repeticiones pedidas? ¿En qué máquina/carpetas quedaron los `informe.md`/CSV generados?
3. ¿Se midió el fps real (LED/cronómetro) en los videos reales? ¿Con qué valor y σ?
4. ¿Cuál es la masa del resorte y su incerteza? (para que `k_con_m_ef` ≠ `k_sin_m_ef`)
5. ¿Quién completa la plantilla de limitaciones del informe, y en qué archivo final queda?
6. ¿El DCL se entrega como figura aparte (informe PDF) o debe generarlo el agente?
7. ¿Los videos de resorte horizontal y vertical se procesan en corridas separadas con distinto `--eje`, o hay que automatizar esa detección?
8. ¿`requirements.txt` debe llevar versiones fijas efectivamente? (el README lo afirma y no lo es)
