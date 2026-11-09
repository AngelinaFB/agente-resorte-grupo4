# Informe Etapa 3C.2: corrección y fortalecimiento de controles de evidencia

Fecha: 2026-11-09.

## 1. Resumen ejecutivo

Se endurecieron los controles deterministas que separan recuperación, selección de evidencia y validación de las respuestas. Las citas se comparan con NFC, preservando subíndices, superíndices y símbolos tal como aparecen; `ω` no se equipara con `w` o `v`, y `π` no se equipara con `p`. No se reconstruyen fórmulas.

La energía mecánica requiere ahora evidencia directa en un mismo fragmento para que la cobertura pueda ser completa. También se rechazan fragmentos con fórmulas anunciadas pero ilegibles y citas que se desvían de la pregunta. La suite completa terminó con **56 pruebas aprobadas**.

La evaluación real local mantuvo respaldada la pregunta del período. Las consultas sobre energía y frecuencia angular se abstuvieron. La pregunta de constante elástica también se abstuvo: sus mejores resultados incluyen palabras partidas y extracción degradada. Esa abstención es una regresión de cobertura respecto de 3C.1, pero evita presentar como limpia una cita dañada. No se reconstruyó la bibliografía ni se descargaron modelos o dependencias.

## 2. Archivos inspeccionados y modificados

Inspeccionados:

- `agente-resorte/chatbot/evidence.py`
- `agente-resorte/chatbot/generation.py`
- `agente-resorte/chatbot/evaluation.py`
- `agente-resorte/tests/test_evidence.py`
- `agente-resorte/tests/test_generation.py`
- `INFORME_ETAPA_3C_1.md`

Modificados durante esta etapa:

- `agente-resorte/chatbot/evidence.py`
- `agente-resorte/chatbot/generation.py`
- `agente-resorte/tests/test_evidence.py`
- `INFORME_ETAPA_3C_2.md` (este informe)

No se modificaron `evaluation.py`, la bibliografía, el índice, los embeddings, las dependencias, Streamlit ni el pipeline de medición.

## 3. Controles implementados

### Fidelidad de citas y notación

- La comparación de citas utiliza normalización NFC y no NFKC.
- La comparación conserva los caracteres de subíndice y superíndice. `x²` no es equivalente a `x2`; `Fₖ` no es equivalente a `Fk`.
- No se convierten letras latinas `v`, `w` o `p` en letras griegas.
- Las expresiones con operadores colgantes, símbolos ambiguos para frecuencia angular o una fórmula anunciada sin expresión verificable se descartan sin reparación automática.
- La comprobación de notación revisa el chunk completo para no separar una oración aparentemente limpia de una fórmula dañada en su contexto cercano.

### Tipo de contenido y calidad

- Se rechazan encabezados o instrucciones identificables como ejercicios, ejemplos, procedimientos o resultados cuando la pregunta requiere una explicación conceptual general.
- La palabra «problema» por sí sola no clasifica el fragmento: se evalúan su posición, encabezado e indicadores de instrucción.
- Se conservan los rechazos por marcas de calidad, OCR pendiente, caracteres de reemplazo, símbolos privados no decodificados, texto corto y palabras físicas partidas.
- Los patrones de fórmula y extracción son conservadores. No equivalen a inspeccionar visualmente la página original.

### Cobertura y afirmaciones

- Para declarar completa la cobertura de energía, un mismo fragmento debe relacionar directamente energía mecánica, cinética y potencial; la unión de dos fragmentos parciales no basta.
- `validate_claims` recibe la pregunta original, divide oraciones y cláusulas separadas por punto y coma, y evalúa cada una por separado.
- Cada proposición debe ser pertinente, llevar una referencia entregada al generador y coincidir literalmente con la evidencia citada.
- Las citas fuera de tema o las proposiciones que exceden la pregunta se rechazan. El fallback extractivo pasa por la misma validación.
- Si la evidencia seleccionada solo cubre una parte, el estado sigue siendo `parcial`; sin fragmentos utilizables, el estado es `sin evidencia suficiente`.

## 4. Metodología de pruebas

Primero se ejecutaron las pruebas de evidencia y generación sin cambiar el código. Después de identificar fallos, se aplicaron cambios localizados y se añadieron regresiones deterministas. Las pruebas nuevas usan fixtures y no invocan Qwen ni Ollama.

Una primera ejecución de la suite completa dentro del sandbox falló al crear bases SQLite y directorios temporales, por restricciones de escritura del entorno. Se repitió con permiso de ejecución fuera del sandbox y pasó. Tras el último ajuste se volvió a correr la suite completa con ese permiso.

La evaluación real se ejecutó de forma local con `qwen2.5:7b`, BGE-M3 y el índice existente, con límite de 20 candidatos por pregunta. No se accedió a Internet ni se descargó contenido. Para las consultas sin evidencia aceptada, el sistema no llamó a Qwen.

## 5. Resultados por auditoría

### A. Notación matemática

**Aprobado en pruebas deterministas.** Sears p.468, «La frecuencia angular v es 2 p veces la frecuencia», se descarta como ambigua tanto al seleccionar evidencia como al validar una cita suministrada manualmente. También se rechazan `x²` frente a `x2`, `Fₖ` frente a `Fk`, fórmulas incompletas y fórmulas anunciadas sin expresión legible.

**Evaluación real:** la consulta de frecuencia angular se abstuvo; no usó la cita dudosa de Sears p.468 ni la extracción incompleta de Ochoa p.2.

### B. Tipo de contenido

**Aprobado en pruebas deterministas.** Un «Problema 4» que incluye “representa”, “rigidez” y “proporcional” no se acepta como definición general. Un ejemplo con vocabulario definitorio tampoco se generaliza. Un patrón de palabra física partida no se acepta.

La clasificación se basa en señales explícitas. No puede determinar automáticamente todos los casos mixtos donde una misma extracción junta prosa teórica, problemas y respuestas.

### C. Cobertura de relaciones

**Aprobado en pruebas deterministas.** Dos fragmentos, uno sobre energía mecánica/cinética y otro sobre energía mecánica/potencial, quedan en `parcial`; no se consideran prueba de una relación conjunta entre las tres.

**Evaluación real:** la consulta de energía mecánica se abstuvo. El mejor candidato, `libroejercicios.pdf`, p.227, contiene una fórmula anunciada pero ilegible (`La fórmula ... es: La E m ...`). El control lo descartó; no llegó a Qwen.

### D. Validación contextual de afirmaciones

**Aprobado en pruebas deterministas.** En una cita que combina una definición del período y una frase sobre la masa de la Luna, la definición pertinente se verifica y la segunda proposición se rechaza; el resultado queda `parcial`. Las referencias inexistentes y las afirmaciones sin cita continúan rechazándose.

**Evaluación real:** Qwen produjo para el período tres citas textuales pertinentes, validadas con referencias a Ochoa, p.2, y Sears, p.443.

### E. Calidad de extracción

**Aprobado en regresiones incluidas.** El texto con `de sarro lla`, un carácter de reemplazo, marcas de calidad o una fórmula no verificable se descarta. No se reconstruyen símbolos a partir del contexto físico.

La evaluación real de constante elástica se abstuvo: el candidato mejor clasificado, Meriam p.163, incluye `de sarro lla`; otro candidato destacado, libroejercicios p.66, también tiene extracción fragmentada. La consulta de energía rechazó el caso de la fórmula ilegible de p.227. La abstención evita que el match de palabras convierta esos fragmentos en evidencia confiable.

## 6. Pruebas automatizadas

Se agregaron 12 pruebas nuevas en `test_evidence.py`, cubriendo:

1. Sears p.468 con `v/p` ambiguos.
2. Distinción entre superíndice y carácter plano.
3. Distinción entre subíndice y carácter plano.
4. Fórmula incompleta.
5. Fórmula anunciada pero ilegible.
6. Ejercicio con vocabulario definitorio.
7. Ejemplo con vocabulario definitorio.
8. Unión insuficiente de fragmentos parciales de energía.
9. Cláusula textual fuera de tema.
10. Palabra física partida no cubierta por el patrón previo.
11. Conservación de evidencia limpia para constante y período.
12. Abstención de frecuencia angular ante notación ambigua.

La batería completa ejecutada al cierre: `py -3.14 -m unittest discover -s tests -v` — **56 pruebas; OK**. Esto incluye las 44 pruebas existentes antes de 3C.2 y las 12 nuevas. No se añadieron dependencias.

## 7. Comparación de las cuatro consultas reales

| Consulta | Etapa 3C.1 | Etapa 3C.2 final | Evidencia/razón principal |
| --- | --- | --- | --- |
| Constante elástica | Respaldada, Meriam p.163 | **Sin evidencia suficiente**; 20 descartados; Qwen no invocado | El fragmento contiene `de sarro lla`; otro resultado de libroejercicios también está dañado. No se relajó el control para conservar una respuesta. |
| Período de oscilación | Respaldada | **Respaldada**; 2 aceptados, 18 descartados; generación local | Ochoa, `21-OscilaLibres`, p.2, y Sears, p.443. Las tres proposiciones presentadas fueron citas verificadas. |
| Energía mecánica, cinética y potencial | Sin evidencia suficiente | **Sin evidencia suficiente**; 20 descartados; Qwen no invocado | No hay evidencia conjunta confiable en los candidatos. El pasaje de libroejercicios p.227 con fórmula ilegible fue descartado. |
| Frecuencia angular | Parcial (en la corrida de 3C.1) | **Sin evidencia suficiente**; 20 descartados; Qwen no invocado | Sears p.468 contiene `v/p` dudosos y Ochoa p.2 presenta notación extraída incompleta. |

### Tiempos observados en la evaluación final

| Consulta | Recuperación | Generación | Validación | Total |
| --- | ---: | ---: | ---: | ---: |
| Constante elástica | 1,097 s | 0 s | 0 s | 1,097 s |
| Período | 0,665 s | 2,155 s | 0,003 s | 2,822 s |
| Energía | 0,626 s | 0 s | 0 s | 0,626 s |
| Frecuencia angular | 0,887 s | 0 s | 0 s | 0,887 s |

En la consulta de período, la respuesta completa generada y presentada fue:

> Período. [F1] Es el tiempo al cabo del cual las magnitudes que caracterizan el estado de un sistema toman nuevamente los mismos valores. [F1] El periodo, T, es el tiempo que tarda un ciclo, y siempre es positivo. [F2]

Referencias: Ochoa, `21-OscilaLibres 058-066`, p.2 (F1); Sears, *Física Universitaria*, p.443 (F2). Qwen generó dos citas, y la segmentación determinista presentó la etiqueta “Período.” como una proposición adicional respaldada por el mismo fragmento.

## 8. Problemas corregidos y cambios de comportamiento

- Se corrigió la equivalencia accidental que permitía validar notación matemática normalizada de forma demasiado agresiva.
- Se bloqueó la aceptación de `v/p` ambiguos como si fueran omega/pi.
- Se bloqueó la cobertura de energía obtenida uniendo fragmentos parciales.
- Se añadió validación por pregunta y por proposición, incluyendo citas textuales fuera de tema.
- Se amplió la detección de contenido instructivo/ejercicios, palabras partidas y fórmulas ilegibles.
- La consulta real de constante elástica pasó de respaldada a abstención debido a la detección del daño en la extracción. Se considera un resultado más seguro, aunque reduce la cobertura disponible.

## 9. Limitaciones y riesgos pendientes

- La evaluación automática de tipo documental y calidad es heurística; no sustituye la inspección visual de cada página PDF ni un OCR corregido.
- Las pruebas deterministas verifican el validador y los fixtures, no garantizan que Qwen obedezca en futuras ejecuciones. En esta corrida, Qwen solo fue llamado para la pregunta del período.
- Los perfiles especializados cubren los cuatro temas evaluados; las preguntas abiertas requieren más pruebas antes de considerar fiable su selección temática.
- La verificación literal puede abstenerse ante una paráfrasis correcta. Este comportamiento es deliberado mientras no haya un verificador semántico determinista con garantías.
- Para la constante elástica, los primeros 20 resultados actuales no contienen un fragmento suficientemente limpio. Se requiere mejorar extracción/OCR de la bibliografía antes de recuperar esa cobertura; no se corrigió ni reconstruyó el índice en esta etapa.
- Una fórmula tipográficamente correcta en el PDF fuente puede seguir siendo ilegible en la extracción de texto. El sistema no puede demostrar fidelidad al original sin revisar la página renderizada.
- No se midieron RAM ni uso de GPU en esta evaluación; se registraron tiempos de las cuatro consultas. La única inferencia real fue Qwen en la consulta del período.

## 10. Recomendación técnica

Los controles deterministas mejoraron en los riesgos auditados y la evaluación ya no presenta la notación dudosa de frecuencia angular ni la relación incompleta de energía como respuesta respaldada. Aun así, **no recomiendo declarar estable toda la Etapa 3C**: queda pendiente resolver la extracción documental degradada, especialmente para la constante elástica, y ampliar la evaluación de consultas no cubiertas por perfiles. La implementación debe conservar la abstención en esos casos.

Se completa 3C.2 y se detiene aquí. No se integraron informes experimentales ni interfaz.
