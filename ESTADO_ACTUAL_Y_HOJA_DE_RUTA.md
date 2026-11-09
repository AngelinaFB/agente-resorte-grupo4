# Estado actual y hoja de ruta — Grupo 4

**Auditoría documental y técnica:** 9 de noviembre de 2026.  
**Alcance:** inspección del checkout actual. No se modificó código ni se ejecutó una nueva batería de pruebas durante esta auditoría.

> **Advertencia de transferencia:** el checkout local contiene cambios sin commit. El último commit remoto visible es `ac04b16` en `main` (`origin/main`). Varios módulos del chatbot hasta 3C, sus pruebas e informes recientes son archivos modificados o sin seguimiento. Por tanto, un integrante que clone hoy `origin/main` no recibirá el mismo estado que se describe en este documento. Los cambios deben revisarse y compartirse por Git antes de que la guía sea reproducible para el grupo.

### Estado Git observado

- Rama actual: `main`; remoto: `origin` (`https://github.com/AngelinaFB/agente-resorte-grupo4`).
- Último commit: `ac04b16ebd336fb448b39c47d27bac96b0f01f15`, del 8 de noviembre de 2026, `Add: Chatbot entrenado con insumos de la bibliografía de la cátedra [En proceso]`.
- `main` y `origin/main` estaban alineadas en ese commit al momento de la consulta.
- No había cambios staged, pero sí cambios pendientes: modificados `README.md`, `agente-resorte/chatbot/cli.py`, `config.py`, `index.py`, `requirements-chatbot.txt` y `tests/test_index.py`.
- Sin seguimiento estaban los informes recientes, `chatbot/README.md`, `embeddings.py`, `evaluation.py`, `evidence.py`, `generation.py`, `setup-chatbot.ps1` y pruebas nuevas de embeddings/evidencia/generación; también `.audit3c1_eval.err` (vacío). Los dos documentos de transferencia creados en esta tarea también quedan sin seguimiento hasta que el grupo los incorpore.
- Las bases y el corpus están ignorados, por lo que no aparecen como cambios pendientes. Los PDF fuente sí están registrados por Git.

## A. Resumen ejecutivo

El proyecto analiza videos de un resorte oscilante y calcula magnitudes físicas, con una interfaz Streamlit para subir videos y descargar informes. En paralelo se construyó un chatbot académico local que recupera bibliografía con SQLite FTS5 y BGE-M3, y puede generar citas textuales usando Qwen2.5:7b a través de Ollama.

El agente original está implementado en `agente-resorte/` y la interfaz de medición es `app.py`. Los informes históricos documentan pruebas con videos sintéticos, pero no se encontró un video experimental versionado para reproducir una medición real.

El chatbot tiene procesamiento de PDF, índice FTS5, embeddings, búsqueda híbrida y controles de evidencia. No está integrado en Streamlit: su generación y evaluación se ejecutan por CLI. La última evaluación real documentada en `INFORME_ETAPA_3C_2.md` respaldó el período y se abstuvo para energía y frecuencia angular. También se abstuvo para constante elástica porque la extracción recuperada estaba dañada. El propio informe recomienda no considerar estable la Etapa 3C todavía.

En el checkout de auditoría se verificó localmente que el índice informa 35 documentos, 1.688 páginas, 2.531 chunks, 48 páginas con OCR pendiente y 105 páginas con marcas de calidad; `verify --json` informó integridad OK y ningún chunk duplicado u huérfano. Estos datos locales no están incluidos en Git. Las pruebas históricas del informe 3C.2 fueron 56/56 aprobadas; no se repitieron en esta auditoría documental.

### Historial relevante de etapas

- **Etapa 2 / agente original:** `REPORTE_ESTADO_2.md` documenta pipeline de video e interfaz ejecutados con datos sintéticos; no documenta mediciones reales reproducibles. Diagramas de cuerpo libre y comparación con Grupo 8 figuraban pendientes.
- **Etapa 3A:** `REPORTE_ESTADO_5.md` y `INFORME_PARA_EL_GRUPO_ETAPA_3A.md` documentan Ollama/BGE-M3 local, 2.531 embeddings y 13 pruebas de índice/embeddings. También señalan que la pertinencia de algunas búsquedas era mixta y requería revisión humana.
- **Etapa 3B:** `INFORME_VALIDACION_ETAPA_3B.md` documenta Qwen2.5:7b local y cuatro consultas reales. La generación funcionó, pero se detectaron desvíos temáticos, inferencias y fórmulas sin respaldo; se reportaron 28 pruebas aprobadas.
- **Etapa 3C:** `INFORME_ETAPA_3C.md` documenta 44 pruebas y filtros deterministas. Su evaluación real tuvo constante y período respaldados, energía en abstención y frecuencia angular parcial.
- **Auditoría 3C.1:** `INFORME_ETAPA_3C_1.md` reportó riesgos en normalización matemática, tipo de fragmento y cobertura; no hizo cambios de código y recomendó no declarar 3C estable.
- **Corrección 3C.2:** `INFORME_ETAPA_3C_2.md` reporta 56 pruebas aprobadas y evaluación final más conservadora: solo período respaldado; constante, energía y frecuencia angular en abstención. Mantiene la recomendación de no declarar 3C estable hasta resolver extracción y ampliar evaluación.

## B. Arquitectura actual

### Agente de medición

Responsabilidades principales:

- `tracking.py`: localiza y sigue el movimiento del objeto en los cuadros del video.
- `calibracion.py`: escala espacial, conversión a unidades físicas y medición de FPS con LED.
- `señal.py`: relleno de detecciones faltantes, derivación, filtrado y comparación crudo/filtrado.
- `ajuste.py`: ajuste del movimiento amortiguado, magnitudes derivadas, energías y máximos.
- `main.py`: orquesta el procesamiento por CLI y genera informes/archivos de resultados.
- `app.py`: interfaz Streamlit; guarda temporalmente videos subidos, invoca el análisis y ofrece informe, JSON, ZIP y gráficos para descargar.
- `generador_sintetico.py` y `sintetico_verdad.json`: generación/verdad de prueba sintética. `tabla.csv` está versionado y contiene `t_s,x_px,y_px,sx_px,sy_px`, pero su procedencia experimental no se pudo confirmar; no tratarlo como medición real sin aclaración del grupo.

Flujo:

```text
Video(s) + masas + escala/FPS
        ↓
app.py (Streamlit) o main.py (CLI)
        ↓
tracking → calibracion → señal → ajuste
        ↓
resultados por video + agregados + informe Markdown/JSON + gráficos
```

### Chatbot académico local

Responsabilidades actuales:

- `chatbot/pdf_text.py`, `ingest.py`: extraer texto de PDF, marcar calidad y crear chunks con referencias.
- `chatbot/index.py`: construir y consultar SQLite FTS5, exponer páginas y metadatos de calidad.
- `chatbot/embeddings.py`: generar vectores localmente mediante Ollama/BGE-M3 y combinar recuperación semántica y FTS5 mediante RRF.
- `chatbot/evidence.py`: seleccionar fragmentos y validar afirmaciones, citas, referencias, notación y cobertura.
- `chatbot/generation.py`: mandar únicamente evidencia seleccionada a Ollama/Qwen, validar la salida y abstenerse o usar fallback extractivo.
- `chatbot/evaluation.py`: cuatro consultas de evaluación de 3C.
- `chatbot/cli.py`: comandos de ingesta, estadísticas, búsqueda, generación y evaluación.

Flujo actual:

```text
Pregunta
  ↓
recuperación híbrida (FTS5 + BGE-M3)
  ↓
selección determinista (pertinencia, calidad, notación, tipo de contenido)
  ↓
solo evidencia aceptada → Ollama/Qwen2.5:7b (si hay evidencia)
  ↓
validación por proposición, cita textual e ID de referencia
  ↓
respuesta respaldada / parcial / sin evidencia suficiente
```

La respuesta generativa es CLI (`ask`); no hay chatbot conversacional ni interfaz Streamlit conectados.

## C. Estado de desarrollo por componente

| Componente | Estado | Implementación y pruebas | Limitaciones / verificación |
| --- | --- | --- | --- |
| Seguimiento de video | Implementado en código | `tracking.py`; sin suite automatizada específica en `tests/` | Los informes históricos reportan validación sintética. No se encontró video de medición real versionado para repetirla. |
| Calibración | Implementado en código | `calibracion.py`; sin suite automatizada específica | Requiere datos correctos de regla/escala, masa y FPS; la detección automática de regla sigue pendiente según historial. |
| Señal y ajuste | Implementado en código | `señal.py`, `ajuste.py`; sin suite automatizada específica | Hay validación sintética en informes anteriores; el desempeño con datos del grupo no está verificado en este checkout. |
| Interfaz del agente | Implementada | `app.py`, Streamlit; instrucciones en `README.md` | No es la interfaz del chatbot. No se inició Streamlit durante esta auditoría. |
| Extracción e indexación de PDF | Implementada | `chatbot/pdf_text.py`, `ingest.py`, `index.py`; `test_pdf_text.py`, `test_index.py` | La extracción puede romper palabras, símbolos y fórmulas. Los índices locales no están versionados. |
| Recuperación semántica e híbrida | Implementada en este checkout | `chatbot/embeddings.py`; `test_embeddings.py` | Depende de Ollama/BGE-M3 y del archivo local `embeddings.sqlite`; pertinencia evaluada solo con consultas de muestra. |
| Selección/validación de evidencia | Implementada, en fortalecimiento | `chatbot/evidence.py`; `test_evidence.py` | Heurísticas conservadoras; 3C.2 documenta abstención en constante, energía y frecuencia angular por problemas de fuente. No se recomienda declarar estable. |
| Generación local | Implementada por CLI | `chatbot/generation.py`; `test_generation.py`; Ollama local | No hay interfaz. Las pruebas con dobles no garantizan obediencia de Qwen. La evaluación real 3C.2 invocó Qwen solo para período. |
| Integración de informes experimentales | Pendiente | No hay módulo de ingestión de resultados experimentales en el chatbot | Requiere acordar formato, procedencia y calidad de informes antes de indexarlos. |
| Chatbot en Streamlit | Pendiente | `app.py` implementa solo el flujo de videos | No modificar/integrar hasta acordar interfaz y criterio de evidencia estable. |

## D. Bibliografía e indexación

### Fuentes observadas

En `agente-resorte/Bibliografía/` se encontraron y Git tiene registrados cuatro PDF fuente —Sears, Meriam, `libroejercicios.pdf` y `coordenadas intrinsecas y polares.pdf`— y `Ochoa.rar`. El archivo comprimido contiene 31 PDF que se extraen localmente a `data/corpus/raw/ochoa/`; de ahí resultan los 35 documentos del índice. Los PDF fuente y el RAR sí están en Git; los PDF extraídos no.

### Artefactos locales observados

`agente-resorte/data/index/bibliografia/` contiene en este equipo:

- `bibliografia.sqlite` (aprox. 24,3 MiB): índice y datos FTS5.
- `embeddings.sqlite` (aprox. 11,3 MiB): embeddings locales separados.
- `pages.jsonl`, `chunks.jsonl`, `manifest.json`: extracción, fragmentos y metadatos.

Esta carpeta está ignorada por `agente-resorte/.gitignore`; un clon limpio no la recibirá. `data/corpus/` también está ignorada.

### Conteos y calidad verificados

La lectura local de `stats --json` y `verify --json` informó:

- 35 documentos; 1.688 páginas PDF; 1.671 páginas con texto.
- 2.531 chunks y 2.531 filas FTS.
- 48 páginas requieren OCR; 105 presentan marcas de calidad.
- `integrity_check: ok`; 0 chunks huérfanos, duplicados o vacíos.

La mayoría de los problemas marcados se concentra en `libroejercicios.pdf` (26 páginas con OCR pendiente y 54 con flags), Sears (8 y 37) y Meriam (14 y 14). Los conteos se solapan según los metadatos y no deben sumarse como páginas distintas. Los archivos marcados incluyen páginas sin texto, texto insuficiente y posible OCR. Ejemplos que afectan consultas actuales: Meriam p.163 (`de sarro lla`), libroejercicios pp.66 y 227, Sears p.468 (símbolos `v/p` ambiguos en la extracción), Ochoa `21-OscilaLibres` p.2 (fórmula incompleta en parte del texto).

No se instaló Tesseract ni se corrigió la extracción. No se deben tratar las marcas del índice como evidencia de que el texto está visualmente correcto.

### Construcción y verificación

Desde `agente-resorte/`, con el entorno activado:

```powershell
python -m chatbot.cli stats --json
python -m chatbot.cli verify --json
```

Si el índice no existe y están disponibles las fuentes:

```powershell
python -m chatbot.cli ingest
python -m chatbot.cli verify --json
```

La generación de embeddings es una operación independiente y llama a Ollama/BGE-M3:

```powershell
python -m chatbot.cli embed-build --model bge-m3 --ollama-url http://127.0.0.1:11434
python -m chatbot.cli embed-stats --json
```

No reconstruir si basta con verificar; la ingesta reescribe el índice local. Para acceder a búsqueda FTS basta el índice bibliográfico; para semántica/híbrida también hacen falta el servicio Ollama, BGE-M3 y `embeddings.sqlite`.

La última medición documentada para generar embeddings de 2.531 chunks fue 449,85 segundos (7 min 30 s) en un equipo concreto. No es una garantía para otra computadora; no se midió rendimiento cruzado.

## E. Modelos y funcionamiento local

### Modelos y servicios

- `bge-m3`: embeddings de consultas y fragmentos para búsqueda semántica. El backend por defecto está configurado como `ollama` en `chatbot/config.py`.
- `qwen2.5:7b`: generación de citas/respuestas a partir de la evidencia seleccionada.
- Ollama: servicio local HTTP en `http://127.0.0.1:11434`; no es un servicio en la nube. Los modelos viven en el perfil de cada usuario, fuera del repositorio.

En el equipo de esta auditoría se comprobó `Ollama 0.40.15` y estaban disponibles `qwen2.5:7b` (ID `845dbda0ea48`, tamaño listado 4,7 GB) y `bge-m3:latest` (ID `790764642607`, tamaño listado 1,2 GB). Esto describe solo esta computadora.

Para comprobarlos en otra máquina:

```powershell
ollama --version
ollama list
```

Si `ollama` no está en PATH en Windows, probar la instalación por usuario:

```powershell
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" --version
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" list
```

El servicio debe estar activo para las consultas semánticas y de generación. En esta auditoría la CLI de `ollama` no estaba en PATH, aunque se pudo ejecutar desde la ruta habitual; la evaluación local anterior ya había comprobado el servicio.

### Instalación y hardware observados

Los informes 3A/3B documentan una máquina Windows 11 con Ryzen 5 5600H (6 núcleos/12 hilos), aproximadamente 15,86 GB de RAM y Radeon RX 6600M. En una ejecución previa Ollama reportó uso GPU para Qwen y BGE-M3; también se registró un mínimo de RAM libre cercano a 0,99 GB. Eso no constituye un requisito mínimo ni predice el desempeño en equipos de otros integrantes. Los informes previos mencionan además un equipo de referencia distinto, Ryzen 7 5700U con 24 GB y Radeon integrada.

El acceso WMI para leer hardware fue denegado en esta auditoría; no se hizo una medición nueva de RAM/VRAM ni una prueba de carga. La aceleración AMD depende del equipo y del entorno. No se debe prometer GPU ni un tiempo de respuesta. El almacenamiento necesario para los modelos es local al usuario; el tamaño de descarga observado en `ollama list` no es una medición de memoria pico.

El proyecto está pensado para uso posterior offline, pero preparar una máquina nueva requiere obtener Python wheels y los modelos. No hay un procedimiento versionado para transportar el almacén de modelos de Ollama entre usuarios sin red.

## F. Pruebas y confiabilidad

Comando en el checkout completo:

```powershell
python -m unittest discover -s tests -v
```

Hay 56 métodos `test_*` en el checkout actual: 5 de índice, 8 de embeddings, 6 de extracción PDF, 9 de generación y 28 de evidencia. El último resultado registrado en `INFORME_ETAPA_3C_2.md` fue 56 aprobadas. **No se ejecutó de nuevo durante esta auditoría.** Además, esos módulos de chatbot no están todos compartidos en `origin/main` todavía.

Las pruebas cubren extracción/chunking, integridad/consultas SQLite, embeddings y búsqueda con dobles, selección y estados de evidencia, validación literal, referencias, fallos de Ollama/modelo y fixtures de generación. No validan exhaustivamente el significado de todos los textos, la fidelidad visual de fórmulas, todas las consultas abiertas ni la futura obediencia de Qwen.

La última evaluación real documentada en 3C.2 usó los modelos locales y 20 candidatos por consulta. Período quedó respaldado; constante, energía y frecuencia angular se abstuvieron. El hecho de que pasen las pruebas no convierte 3C en estable: el informe 3C.2 lo desaconseja mientras persistan problemas de extracción y cobertura.

## G. Problemas y limitaciones pendientes

1. **Transferencia Git incompleta:** varios módulos, pruebas y reportes de 3A–3C están sin commit. Un clon de `origin/main` no tiene el estado documentado aquí.
2. **Índice local:** SQLite, JSONL y corpus extraído se ignoran. Cada integrante los debe generar en su equipo desde los PDF fuente o recibirlos por un medio que el grupo acuerde.
3. **Extracción matemática:** fórmulas y símbolos se dañan en los PDF. No hay OCR correctivo ni verificación visual sistemática; la validación literal no prueba que el texto extraído coincida con el PDF.
4. **Cobertura:** con los controles actuales, tres de las cuatro consultas reales de 3C.2 se abstuvieron; el objetivo académico exige conservar estas abstenciones si falta evidencia.
5. **Modelo y recursos:** no hay requisito de hardware validado para todos. Rendimiento y aceleración AMD no están garantizados.
6. **Dependencias:** `requirements.txt` no fija versiones y no hay `pyproject.toml`, lockfile o archivo Conda verificado. La reproducibilidad entre equipos es limitada.
7. **Agente original:** la operación con datos reales de integrantes no está verificada con videos versionados. Los informes previos diferencian resultados sintéticos de mediciones reales.
8. **Integraciones pendientes:** ni los informes experimentales son fuentes del chatbot ni existe interfaz conversacional en Streamlit.
9. **Preparación automática:** `setup-chatbot.ps1` instala dependencias, puede instalar Ollama mediante `winget`, ejecuta `ollama pull bge-m3` y crea índices si faltan. No es un instalador offline ni una simple verificación.

## H. Hoja de ruta propuesta

### 1. Antes de integrar el chatbot

| Prioridad y tarea | Objetivo / motivo | Componentes | Dependencias | Criterio verificable |
| --- | --- | --- | --- | --- |
| P0. Compartir el estado de código por Git | Alinear el clon de cada integrante con lo documentado | `chatbot/`, `tests/`, README, informes 3A–3C | Revisión del grupo y estrategia de commits | Un clon limpio contiene los módulos y pruebas; `git status` limpio tras checkout. |
| P1. Mejorar y auditar extracción | Recuperar definiciones sin confiar en símbolos dañados | `pdf_text.py`, fuentes PDF, marcas del manifest | Revisar páginas fuente; decidir si se autoriza OCR o revisión manual | Casos de constante, período, energía y frecuencia muestran el texto fuente cotejado con página PDF; flags no borrados sin fundamento. |
| P1. Repetir evaluación 3C en otro equipo | Comprobar instalación local y reproducibilidad | setup, BGE/Qwen, `evaluate-3c`, evidencia | Código compartido y modelos disponibles | Registrar aceptados/descartados, salida, estado, referencias, tiempos y recursos; revisión humana de citas. |
| P2. Ampliar casos de pertinencia | Evitar afirmaciones completas desde evidencia parcial o fuera de tema | `evidence.py`, pruebas | Evaluación documental de bibliografía | Casos acordados por el grupo tienen resultados reproducibles; abstención se conserva ante duda. |

### 2. Integrar informes experimentales

| Tarea | Objetivo / motivo | Componentes | Dependencias | Criterio verificable |
| --- | --- | --- | --- | --- |
| Definir contrato de informe | Distinguir dato medido, configuración, incerteza y procedencia | JSON generado por `main.py`, esquema/versionado | Validación de agentes y responsables de informe | Informe identifica video, parámetros, fecha, magnitudes/unidades, incertidumbre y alertas. |
| Diseñar acceso separado de teoría | No confundir un resultado experimental particular con ley general | Nuevos módulos de fuente experimental, permisos/filtros | Contrato aprobado y controles de evidencia estables | Consulta puede citar informe y corrida específicos; nunca generaliza un único ensayo. |
| Pruebas de procedencia y calidad | Evitar responder desde resultado fallido o de baja calidad | tests de ingesta y selección | Integración local | Fixtures de informe válido, incompleto, fallido y contradictorio producen decisiones documentadas. |

### 3. Desarrollar interfaz

| Tarea | Objetivo / motivo | Componentes | Dependencias | Criterio verificable |
| --- | --- | --- | --- | --- |
| Diseñar flujo de chat con el grupo | Mantener claras pregunta, evidencia y abstención | Nueva UI aislada; no confundir con `app.py` del analizador | Etapa 3C aceptada y requisitos acordados | Prototipo permite preguntar, ver estado y desplegar fuente/página/contexto; no cambia flujo de medición. |
| Manejar errores y operación offline | Informar Ollama/modelo ausente y preservar uso del agente | UI y cliente de generación | UI aprobada | Si el chatbot no está listo, el análisis de video sigue funcionando; errores de modelo no aparecen como respuestas. |

### 4. Validación final

- Ejecutar las suites del chatbot y del agente desde clon limpio, con versiones registradas.
- Verificar comandos FTS, semántico, híbrido, `ask` y evaluación local; comprobar explícitamente que ninguna API externa sea llamada.
- Repetir las cuatro consultas reales y agregar preguntas nuevas aprobadas por el grupo; conservar las abstenciones pertinentes.
- Probar el agente con videos reales autorizados por el grupo, documentando entradas, parámetros, incertezas y revisión visual.
- Confirmar en un segundo equipo la instalación y el rendimiento antes de anunciar disponibilidad para todos.
- Considerar 3C estable solo tras cerrar los riesgos de extracción y demostrar resultados aceptables en evaluación independiente; 56 pruebas solas no bastan.

## Fuentes inspeccionadas

`README.md`; `Proyectos-Lineas_II_y_III.pdf`; `agente-resorte/chatbot/README.md`; `requirements.txt`; `requirements-chatbot.txt`; ambos `.gitignore`; `setup-chatbot.ps1`; `chatbot/config.py`, `cli.py`, `pdf_text.py`, `ingest.py`, `index.py`, `embeddings.py`, `evidence.py`, `generation.py`, `evaluation.py`; `main.py`, `app.py`, `tracking.py`, `calibracion.py`, `señal.py`, `ajuste.py`; `selector_punto_tracking/index.html`; pruebas en `tests/`; `REPORTE_ESTADO.md` a `REPORTE_ESTADO_5.md`; informes 3A, 3B, 3C, 3C.1 y 3C.2; estructura local de `Bibliografía`, `data/corpus` y `data/index`; estado de Git, último commit, remoto, versión local de Ollama y lista de modelos.
