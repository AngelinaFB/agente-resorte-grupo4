# Tareas pendientes

## Objetivo

Reemplazar la pantalla actual por una interfaz conversacional que guíe un análisis completo del resorte: recibe el video, pregunta los datos que falten, ejecuta los cálculos de cinemática, dinámica y energía, y permite consultar la bibliografía y los resultados de esa corrida.

## Plan, de menor a mayor alcance

### 1. Acordar qué puede calcularse

- Definir los resultados prioritarios y sus ecuaciones, unidades e incertidumbres.
- Armar un mapa que distinga datos obtenibles del video, datos que debe aportar el usuario y resultados que pueden derivarse.
- Evitar pedir datos que no hacen falta para el resultado elegido. Si hay más de una opción para completar el análisis, ofrecérselas al usuario.
- Si los datos no determinan una magnitud de forma única, explicar qué dato adicional se necesita.

Ejemplos para revisar con el grupo:

- Video y FPS permiten estimar período, frecuencia y amortiguamiento.
- Para `k` dinámica, el modelo actual también usa las masas. Si el usuario conoce `k` en vez de la masa, se puede evaluar despejar la masa con el mismo ajuste y propagar su incertidumbre.
- Escala espacial hace falta para expresar desplazamientos y magnitudes derivadas en unidades físicas; no debe pedirse automáticamente si el resultado solicitado no la requiere.
- `k` estática requiere datos de fuerza/masa y elongación; decidir si será un cálculo alternativo o una comparación con `k` dinámica.

**Terminado cuando:** el grupo aprueba el mapa de dependencias y los supuestos físicos.

### 2. Hacer que el analizador pida datos progresivamente

Flujo propuesto:

1. El usuario sube uno o más videos y dice qué quiere averiguar, o pide calcular todo lo que sea posible.
2. El analizador solicita lo necesario para poder leer el video: método de seguimiento y, si hace falta, FPS.
3. Hace una primera pasada y estima las magnitudes que dependan del movimiento observado.
4. Presenta qué resultados ya puede calcular y cuáles requieren datos adicionales. Para cada resultado faltante, explica qué dato lo habilita y ofrece opciones cuando existan.
5. El usuario completa los datos que tiene. El sistema calcula lo determinado y señala claramente lo que sigue sin poder inferirse.

La masa, `k`, la calibración espacial y las mediciones estáticas no deben aparecer siempre como un formulario fijo. Se solicitan según el resultado y el mapa aprobado. Las respuestas del usuario se guardan como datos estructurados con unidades e incertidumbres; el modelo no debe inventar valores ni cambiar cálculos por texto libre.

**Terminado cuando:** el flujo puede continuar con datos parciales, pedir solo los datos pertinentes y explicar por qué un cálculo no está disponible.

### 3. Conectar la conversación con el análisis

- Usar el pipeline de análisis existente desde la nueva interfaz, sin duplicar sus cálculos en el chatbot.
- Guardar cada corrida con video, método, parámetros ingresados, valores derivados, incertidumbres, advertencias y resultados.
- Dar al chatbot acceso a los resultados estructurados de la corrida activa.
- Distinguir en las respuestas entre “según la bibliografía” y “en este video/corrida”.
- Mantener la descarga del informe y resultados.
- Completar el informe para que presente resultados cinemáticos, dinámicos y energéticos por repetición y agregados. Actualmente, el Markdown muestra máximos y energías solo del primer video; el JSON los conserva por video, pero el agregado no incluye todas esas magnitudes.
- Acordar si “integrales de movimiento” significa reportar la evolución de las energías `Ec`, `Ep` y `Et` —que el código ya calcula— o agregar cálculos de trabajo/disipación mediante integrales. Implementar lo que pida el análisis de la cátedra y explicitar el efecto del amortiguamiento.

**Terminado cuando:** el informe y la conversación cubren la cinemática, dinámica y energía de cada video y de las repeticiones; las respuestas se basan en resultados guardados, no en valores generados por el modelo.

### 4. Mejorar respuestas y fuentes del chatbot

- Revisar las páginas de la bibliografía cuya extracción dañada provoca abstenciones, especialmente en constante elástica, energía y frecuencia angular.
- Corregir extracción/OCR conservando la referencia exacta a documento y página.
- Evaluar preguntas de física del resorte, preguntas sobre una corrida, consultas ambiguas y preguntas ajenas al tema.
- Mostrar citas para las respuestas teóricas y abstenerse cuando no haya evidencia suficiente.
- Definir el alcance de preguntas permitidas y responder con claridad cuando una pregunta quede fuera de él.

**Terminado cuando:** las respuestas evaluadas se cotejan con sus fuentes, las preguntas fuera de alcance se rechazan y las abstenciones correctas se conservan.

### 5. Validar y preparar para el grupo

- Probar el recorrido completo con videos sintéticos y videos reales autorizados.
- Comparar los resultados con casos de referencia y revisar visualmente el seguimiento.
- Probar fallos de FPS, calibración, tracking, índice bibliográfico y Ollama; la interfaz debe explicar cómo continuar.
- Repetir la instalación en otro equipo y documentar dependencias, modelos e índices locales.
- Actualizar README y guía para compañeros con el flujo final.

**Terminado cuando:** otro integrante puede instalarlo y completar una corrida siguiendo la guía, con resultados y límites documentados.

## Orden para empezar

1. Acordar qué magnitudes debe calcular el analizador y qué datos externos requiere cada una.
2. Implementar el diálogo progresivo de entradas.
3. Conectar el diálogo con el análisis y los resultados de la corrida.
4. Mejorar y evaluar fuentes y respuestas del chatbot.
5. Validar todo el flujo y documentar la instalación.

## Opcional: agregar YOLO

YOLO no forma parte del cambio actual. Si el grupo confirma que lo necesita, queda elegir y validar un modelo, revisar licencia y tamaño de pesos, y definir cómo instalarlo en otros equipos.
