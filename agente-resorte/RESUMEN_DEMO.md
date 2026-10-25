# RESUMEN_DEMO - Grupo 4 (Línea III, Resorte)

## 1) ¿Qué hace el agente? (≤10 líneas)
El agente automatiza el análisis video→físico del MAS amortiguado.  
Lee un/varios videos `.mp4` con el oscilador, sigue el objeto por color con OpenCV.  
Calibra la escala espacial (px/m) con regla o valor dado, y puede corregir el FPS con LED.  
Convierte a metros, filtra/interpola detecciones faltantes, deriva (velocidad/aceleración) con Savitzky–Golay.  
Ajusta `x(t)=A e^{-γt}cos(ωt+φ)+C` por mínimos cuadrados ponderados (lmfit).  
Calcula T, γ, k con/sin masa efectiva del resorte (considerando m_resorte/3), máximos, energías y sus incertezas.  
Hace chequeo físico con k estático si se proveen datos; genera informe `.md`, `resultados.json` y figuras.

## 2) ¿Cómo funciona cada etapa? (archivo:función / técnica)

| Etapa | Archivo | Función(es) | Detalle según código |
|---|---|---|---|
| **Tracking** | `tracking.py` | `mascara()`, `trackear()` | **Técnica:** Segmentación por **color en espacio HSV (OpenCV clásico)**, no YOLO. Se construyen máscaras por rangos HSV (`COLORES`), morfología `MORPH_OPEN`, se toma **únicamente el contorno de mayor área** (`cv2.findContours` RETR_EXTERNAL), se descartan áreas < `AREA_MIN` (30 px²). Centroide por **momentos binarios** (`cv2.moments`), incertidumbre asignada `SIGMA_PX=1/√12 px` (discretización). Genera tabla `(t_s, x_px, y_px, sx_px, sy_px)` con NaN si no hay detección. Usa `cv2.VideoCapture`, toma `fps` declarado. |
| **Calibración espacial** | `calibracion.py` | `marcar_dos_puntos()`, `escala_px_por_m()` | Click en dos extremos de una regla en el primer frame. Distancia euclídea en px `d=hypot`. Incertidumbre de puntos `sigma_punto_px` (default 1.0) → `sigma_d = sqrt(2)*sigma_punto_px`. Escala `s = d/largo_m`, propagación `sigma_s = s*sqrt((sigma_d/d)^2 + (sigma_largo_m/largo_m)^2)`. |
| **Calibración temporal (LED)** | `calibracion.py` | `fps_real_con_led()` | Detecta parpadeos con `scipy.signal.find_peaks` sobre brillo (ROI opcional o frame completo). Requiere `f_led_hz`. Verifica periodos entre picos ~constantes (lanza error si `std(ddof=1)>1.0`); exige >=4 picos. `fps = f_led_hz * periodos.mean()`. Incertidumbre: `sigma_disp = f_led_hz*std/sqrt(n)` + `sigma_cuant = f_led_hz/sqrt(12*n)` (periodos enteros en cuadros) combinadas por `hypot`. En `main.py` tiene **prioridad** sobre `--fps-real` sobre fps declarado. Si difiere >10% avisa. |
| **Conversión a metros / corrección fps** | `calibracion.py`, `main.py` | `a_metros()`, `analizar()` | Origen `(x0,y0)`: media de señal si no se pasa (equilibrio). `xm=(x-x0)/s`, `ym=-(y-y0)/s` (y hacia arriba). Propagación incluye término por incertidumbre de escala. Si hay `fps_real`, reescala `t = t_declarado * fps_decl / fps_real`. En `main.py` se usa `fps_uso` (LED>--fps-real>declarado) y se aplica la corrección `t = t * fps_decl / fps_uso`. |
| **Derivación y filtrado** | `señal.py` | `derivar()`, `filtrar()`, `procesar()`, `comparar_crudo_filtrado()` | `derivar = np.gradient(y,t)` (diferencias finitas centrales). `filtrar = scipy.signal.savgol_filter(y, ventana_impar, orden)` (ventana ajustada si imparidad/longitud). `procesar()` hace dos caminos: crudo `v_c,a_c` por derivadas directas; filtrado `x_f`, luego `v_f = filtrar(derivar(t,x_f),...)`, luego `a_f = filtrar(derivar(t,v_f),...)` (receta tipo "filtrar x, derivar a v, filtrar v, derivar a a, filtrar a"). `incerteza_cruda`: `sv=sqrt(2)*sx/(2*dt)`, `sa=sqrt(2)*sv/(2*dt)`. `comparar_crudo_filtrado` reporta RMS(crudo-filtrado); si hay `corr_v` (por fps) escala RMS_v por `corr_v`, RMS_a por `corr_v^2`. |
| **Ajuste** | `ajuste.py` | `ajustar()`, `parametros_con_incerteza()`, `cantidades()` | Modelo `x(t)=A e^{-γt}cos(ωt+φ)+C` (lmfit `Model`). Semilla ω0 desde pico de FFT de `(x-mean)`. Pesos `1/sx`. Parámetros como `ufloat` con correlaciones via `correlated_values` desde covarianza de lmfit. `ω0^2 = ω^2 + γ^2`, `m_ef = m + m_r/3`. `T=2π/ω`, `k_con_mef = m_ef*ω0^2`, `k_sin_mef = m*ω0^2`. |
| **Máximos** | `ajuste.py` | `maximos()` | Analítico sobre solución ajustada con parámetros correlacionados. Encuentra primer máximo con `t>=0` resolviendo `θ = base + nπ ≡ φ mod π`. Calcula envolvente `A e^{-γt}`, `R=sqrt(ω^2+γ^2)`, `S=ω^2+γ^2`, fases `atan2(ω,γ)`, `atan2(2γω, γ^2-ω^2)`. Devuelve |x|,|v|,|a| máximos con instante/posición y propagación de covarianzas. |
| **Energías** | `ajuste.py` | `energias()` | `Ec = 0.5*m_ef*v_f^2`, `Ep = 0.5*k*(x_f - C)^2`, `Et=Ec+Ep`. Si hay `corr_v` (incerteza fps), escala `v_f *= corr_v` (Ec se escala; Ep no se duplica). Todo con `ufloat`. |
| **k estático / chequeo** | `ajuste.py`, `main.py` | `k_estatico()`, `chequeo_periodo()` | Regresión lineal `F = m g vs elongación` con `np.polyfit(cov=True)`. Propaga `sigma_g` como `δk = (k/g)σg` (común). Si se da `sigma_elongacion`, propaga por derivadas parciales sobre puntos (`dk/de_j`). `chequeo_periodo()` compara T con/sin m_ef vs T medido con z-score; veredicto <2σ coincide, 2-3 dudoso, >=3 no coincide. |

## 3) Estado de los datos (reales vs sintéticos)
**Búsqueda realizada:** se revisaron `agente-resorte/`, subcarpetas y `__pycache__`. Se buscaron `*.mp4,*.avi,*.mov,*.csv,*.json, tabla*, informe*, datos/, salidas/`.  
**Encontrado:** Solo archivos `.py`, `requirements.txt`, entorno `venv/` (dependencias del sistema en Python global para pruebas). **No hay** `datos/`, `salidas/`, videos reales, CSVs reales ni informes de corridas reales en el repo o carpetas locales visibles.  
**Videos reales:** 0. **CSV reales:** 0. **Fechas:** Ninguna.  
**Conclusión:** **No existen datos reales en el repo.** Todo lo verificable es **generación sintética**.

## 4) Resultados (reales o sintéticos)
**Prueba verificada fuera del repo (temporal):** Generado `sintetico.mp4` con `generador_sintetico.py` (k=12 N/m, m=0.2 kg, γ=0.15 1/s, A=0.05 m, fps=30, px/m=2000) → `T verdadero = 0.8113 s`. Ejecutado `main.py` sobre ese video.

**Salida (informe.md):**
| Métrica | Valor (con incerteza) | Notas |
|---|---|---|
| T | 0.811328 ± 0.000038 s | Muy cerca del verdadero (0.8113) |
| γ | 0.15159 ± 0.00037 1/s | Muy cerca de 0.15 |
| k con m_ef | 11.999 ± 0.060 N/m | m_resorte=0 → idéntico a sin m_ef |
| k sin m_ef | 11.999 ± 0.060 N/m |  |
| χ² red. | 1.65 | Cerca de 1 |
| fps usado | 30.0000 fps (declarado, sin verificar) | Sin incerteza |
| N videos | 1 (repeticiones) | < 5 (marcado en limitaciones) |

Energías/máximos y crudo vs filtrado según tabla del informe (verificado).  

**Clasificación:** **Resultados son de VALIDACIÓN SINTÉTICA, NO MEDICIÓN REAL.** No se mezclaron datos reales (no existen).

## 5) Estado contra la consigna (HECHO/PARCIAL/FALTA)

| Requisito | Estado | Evidencia / Comentario |
|---|---|---|
| **Calibración espacial (regla px/m)** | HECHO | `calibracion.py:marcar_dos_puntos`, `escala_px_por_m` con propagación de incertidumbre. Requiere `--sigma-px-por-m` si se da `--px-por-m`. |
| **Calibración temporal (LED)** | HECHO | `calibracion.py:fps_real_con_led` con detección de picos, verificación de constancia, incertidumbre cuantización+dispersión, prioridad en `main.py`. |
| **Repeticiones (múltiples videos)** | PARCIAL | `main.py` acepta múltiples videos y agrega (media ± SEM + dispersión). Sin datos reales, solo probado con 1. |
| **Tabla t,x,y,σx,σy** | HECHO | `tracking.py` genera `*_px.csv` con esas columnas; `a_metros` genera `*_m.csv` con `t_s,x_m,y_m,sx_m,sy_m`. |
| **Derivar y filtrar (receta)** | HECHO | `señal.py:procesar` sigue la receta; `savgol_filter`; incertidumbre cruda; comparación crudo/filtrado. |
| **k (con/sin m_ef)** | HECHO | `ajuste.py:cantidades` calcula ambos con `m_ef = m + m_r/3`. |
| **Máximos** | HECHO | `ajuste.py:maximos` analíticos con incerteza/covarianzas. |
| **Energías** | HECHO | `ajuste.py:energias` Ec,Ep,Et con propagación y corrección por fps si aplica. |
| **Amortiguamiento (γ)** | HECHO | Ajuste incluye γ, propagado e incluido en energías/cálculos. |
| **Masa efectiva** | HECHO | Implementado (m_resorte/3). Funciona aunque m_resorte=0. |
| **Diagramas de cuerpo libre** | FALTA | No hay archivos de diagramas (no encontrados). No generado por código. |
| **Comparación contra Grupo 8** | FALTA | No hay código/archivos para comparación con otro grupo. |
| **Limitaciones** | HECHO/PARCIAL | `main.py:escribir_informe` auto-genera limitaciones (pérdidas, χ², ciclos, muestras/T, γ~0, repeticiones<5, fps sin verificar, falta k estático, etc.). |

## 6) Guion de demo (5 min, PowerShell/Windows)

**Prerrequisitos:** Dependencias instaladas (sistema tiene opencv-python/scipy/lmfit/uncertainties/numpy/matplotlib). Código en repo, **no modificarlo**.

### Comandos probados fuera del repo (verificados)
```powershell
# Crear directorio temporal FUERA del repo
$tmp = "C:\Users\crowl\AppData\Local\Temp\opencode\demo4"
New-Item -ItemType Directory -Force -Path $tmp | Out-Null
$env:PYTHONPATH = "C:\Users\crowl\agente-resorte-grupo4\agente-resorte"
Set-Location $tmp

# 1) Generar video sintético (validación)
py "C:\Users\crowl\agente-resorte-grupo4\agente-resorte\generador_sintetico.py" --salida sintetico.mp4 --fps 30 --dur 6 --k 12 --m 0.2 --gamma 0.15 --A 0.05 --px-por-m 2000
# Esperado: "Video: sintetico.mp4 | T verdadero = 0.8113 s"

# 2) Analizarlo (demo completo)
py "C:\Users\crowl\agente-resorte-grupo4\agente-resorte\main.py" sintetico.mp4 --masa 0.2 --px-por-m 2000 --sigma-px-por-m 2 --salidas .
# Esperado: "OK  sintetico.mp4" y "Informe: ./informe.md"

# 3) Revisar informe
Get-Content .\informe.md | Select-Object -First 60
```

**Si hay video REAL (cuando exista):**
```powershell
$tmp = "C:\Users\crowl\AppData\Local\Temp\opencode\demo_real"
New-Item -ItemType Directory -Force -Path $tmp | Out-Null
$env:PYTHONPATH = "C:\Users\crowl\agente-resorte-grupo4\agente-resorte"
Set-Location $tmp
# Copiar video real ahí (fuera del repo) o pasar ruta
py "C:\Users\crowl\agente-resorte-grupo4\agente-resorte\main.py" "ruta\al\video_real.mp4" --masa <kg> --sigma-masa <kg> --masa-resorte <kg> --sigma-masa-resorte <kg> --regla-m <m> --salidas .
# O con escala conocida: --px-por-m <val> --sigma-px-por-m <val>
# O con calibración LED: agregar --video-led led.mp4 --f-led <Hz> [--roi x y w h]
```

**Qué mostrar en pantalla:**
1. Generador crea video + `sintetico_verdad.json` (valores verdaderos). 
2. Tracking + conversión a metros (tablas `_px.csv`, `_m.csv` generadas en salida). 
3. Ajuste MAS amortiguado, parámetros con incerteza, χ² reducido. 
4. Máximos, energías con propagación. 
5. `informe.md` con tabla agregada, crudo vs filtrado, limitaciones auto-detectadas.

**Verificación de comandos:** Ambos comandos probados fuera del repo; **funcionaron** con Python del sistema (py). `generador_sintetico.py` corre directamente con `argparse` (no depende de main). Si `cv2` faltara en algún entorno, fallaría al importar (verificado: en entorno con deps ok).

## 7) Preguntas probables del asistente + respuestas honestas

| Pregunta | Respuesta (basada en código) |
|---|---|
| **¿Por qué esa técnica de tracking?** | HSV + contornos externos + mayor área + momentos. Es simple, offline, sin pesos extra; apropiado para objeto de color uniforme sobre fondo. No usa YOLO (no hay rastreo por red neuronal). |
| **¿Cómo se obtiene la incerteza?** | Tracking: `SIGMA_PX=1/√12 px`. Escala: propagación desde distancia entre dos puntos + incertezas. FPS LED: dispersión de periodos / sqrt(n) + cuantización 1/√12 cuadro. Ajuste: lmfit covarianza → `correlated_values`. k estático: dispersión de recta + σg + opcional σ_elongación. Energías/máximos propagados con `uncertainties`. |
| **¿Qué pasa si el fps declarado es falso?** | Si no se calibra con LED ni se pasa `--fps-real`, `main.py` usa fps declarado y lo marca "sin verificar". Cuando se corrige, `t = t_decl * fps_decl / fps_uso` afecta T, γ, k (se escalan por factor relacionado al fps) y se propaga `sigma_fps/fps_uso`. Si hay gran diferencia (>10%) con LED se avisa. |
| **¿Qué limitaciones tiene?** | Solo objeto más grande por color (puede fallar con oclusiones/múltiples objetos). Si no detecta, interpola linealmente. FFT para semilla puede fallar si señal rara. Requiere >=4 ciclos para buen ajuste; <10 muestras/T o pocos ciclos baja precisión. Sin k estático no hay chequeo físico. Sin fps verificado incertidumbre subestimada. |
| **¿Cómo sabe que es MAS amortiguado?** | Ajusta modelo explícito `A exp(-γt)cos(ωt+φ)+C`. Calcula ω0² = ω²+γ², obtiene k con m_ef. Chequeo de periodo con/sin m_ef si hay k estático. |
| **¿Por qué m_resorte/3?** | En `cantidades()` se usa `m_ef = m + m_r/3` (corrección teórica estándar para resorte distribuido). |
| **¿Qué significa χ² reducido?** | Reportado por lmfit (`res.redchi`); ~1 indica pesos consistentes con incertidumbres del tracking. Valores muy distintos activan limitación. |

## 8) Lista de lo que no pude verificar
- **Videos reales:** Ninguno encontrado en repo/carpetas locales. No hay evidencia de corridas reales.
- **CSV/informes reales:** No encontrados.
- **Diagramas de cuerpo libre:** No existen archivos.
- **Comparación Grupo 8:** No hay código ni datos.
- **Entorno venv:** Las dependencias del proyecto no están instaladas en `venv` local; pruebas exitosas con Python del sistema que sí las tiene.
- **Comportamiento con video real complejo:** No verificado (ruido, iluminación variable, oclusiones) - solo sintético probado.
- **Exactitud de `SIGMA_PX` en setup real:** Asignado conservadoramente (1/√12); puede no reflejar setup experimental.

## Verificación final
```powershell
git -C "C:\Users\crowl\agente-resorte-grupo4\agente-resorte" status
```
**Resultado:** `On branch main`, `Your branch is up to date with 'origin/main'.` Solo se creó `RESUMEN_DEMO.md` en la raíz del repo. **No se modificó ni borró ningún archivo existente.**
