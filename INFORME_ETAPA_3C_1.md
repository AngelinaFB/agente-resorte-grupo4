# Informe de auditoria Etapa 3C.1: controles de evidencia

Fecha: 2026-11-08.

## 1. Resumen ejecutivo

- Se audito el comportamiento actual sin modificar codigo, pruebas ni configuraciones. Solo se creo este informe.
- La bateria automatizada existente ejecuto 44 pruebas y termino en OK.
- Las consultas de constante elastica y periodo conservaron el resultado respaldado; la consulta de energia se abstuvo como antes.
- La consulta de frecuencia angular cambio con respecto al informe 3C: antes fue parcial porque se rechazo una formula reformulada; en esta corrida Qwen copio la formula dudosa y la frase de Sears literalmente, y la salida quedo respaldada.
- Las pruebas ad hoc detectaron fallos reproducibles: Sears p.468 acepta v/p ambiguos; NFKC equipara algunos sub/superindices con texto plano; ejemplos y problemas con palabras definitorias pasan; grupos de energia de dos fuentes pueden sumar cobertura completa; una afirmacion fuera de tema dentro de una cita exacta pasa.
- **Recomendacion: no considerar estable la Etapa 3C.** La coincidencia exacta es util para citas, pero no demuestra que la notacion matematica sea fiel o no ambigua ni que toda la cita responda a la pregunta.

## 2. Archivos inspeccionados

- `agente-resorte/chatbot/evidence.py` ? perfiles, calidad, seleccion, segmentacion y validacion extractiva.
- `agente-resorte/chatbot/generation.py` ? contexto que llega a Ollama, validacion, estados y respuesta presentada.
- `agente-resorte/chatbot/evaluation.py` ? conjunto reproducible de cuatro preguntas.
- `agente-resorte/chatbot/pdf_text.py` ? extractor PDF local; su docstring indica que no reconstruye formulas, tablas ni layout complejo.
- `agente-resorte/tests/test_evidence.py`, `agente-resorte/tests/test_generation.py` ? cobertura automatizada existente.
- `INFORME_ETAPA_3C.md` ? resultados de referencia de la Etapa 3C.
- La evaluacion uso la bibliografia y los indices locales en modo lectura. No se reconstruyo ni modifico el indice.

## 3. Funcionamiento actual de los controles

- La recuperacion hibrida propone candidatos; el score no es criterio de aceptacion.
- `select_evidence` aplica perfiles tematicos para constante elastica, periodo, energia mecanica y frecuencia angular. Para energia, cada candidato se acepta si cubre energia mecanica, una relacion y al menos uno entre energia cinetica/potencial; luego la cobertura se agrega entre todos los aceptados.
- La calidad rechaza marcas de OCR/calidad, texto corto, U+FFFD, caracteres de uso privado, signos de reemplazo densos y algunos patrones prefijados de palabras partidas. No hay un analizador general de integridad matematica.
- Ollama recibe solo los fragmentos aceptados. Si no hay candidatos aceptados, no se invoca Qwen.
- `validate_claims` exige referencias F disponibles y una cita que coincida con el texto aceptado. `_exact_quote` aplica NFKC antes de comparar. La funcion no recibe la pregunta ni verifica si cada clausula responde a ella.
- Los estados finales combinan grupos tematicos cubiertos y afirmaciones literales verificadas; no comprueban la validez cientifica de la extraccion.

## 4. Metodologia y pruebas realizadas

1. Inspeccion estatica de los modulos y pruebas indicados arriba.
2. Ejecucion de la suite existente antes de cualquier cambio: `py -3.14 -m unittest discover -s tests -v`.
3. Ejecucion de probes deterministas en memoria que llamaron `select_evidence`, `validate_claims` y `answer_question` con candidatos y dobles locales. No se escribieron casos de regresion al repositorio porque el flujo pedido requiere proponer los cambios antes de implementarlos.
4. Repeticion local de `evaluate-3c --model qwen2.5:7b --limit 20 --json` con BGE-M3 y Qwen ya instalados. Sin Internet, servicios externos, descargas ni reconstruccion de indice.
5. Repeticion supervisada por memoria; no se detuvo ninguna consulta.

La suite registro **44 tests, OK, 2.006 s**. Este resultado valida la bateria actual, no los nuevos probes ad hoc ni la obediencia estable de Qwen.

## 5. Resultados por auditoria

### 5.1 Simbolos, notacion y formulas

| Caso determinista | Resultado actual | Evaluacion |
| --- | --- | --- |
| Sears, pag. 468: cita literal `La frecuencia angular v es 2 p veces la frecuencia.` | La seleccion acepta el fragmento; la validacion acepta la misma cita literal. | **Falla.** No distingue si `v` y `p` son los simbolos escritos o sustituciones de omega/pi. No los reinterpreta, pero los presenta como evidencia suficiente. |
| Evidencia `omega=2pi/T`; respuesta cambia a `v=2p/T`. | Rechaza la respuesta porque ya no coincide literalmente. | Pasa este cambio de variable exacto; no cubre la ambiguedad que ya existe en la fuente. |
| Evidencia `x` + U+00B2 (superindice 2); respuesta `x2` plano. | Acepta como respaldada. | **Falla.** NFKC colapsa superindices a caracteres ordinarios. |
| Evidencia `F` + U+2096 (subindice k); respuesta `Fk` plano. | Acepta como respaldada. | **Falla.** NFKC colapsa subindices. |
| `1/2` frente a una fraccion con U+2044; parentesis distintos. | Rechaza las variantes de la prueba. | Pasa los casos concretos; no implica cobertura de toda la notacion matematica. |
| Fragmento con `w=2pn por lo tanto T 2p w.` y sin caracteres de reemplazo. | Selecciona y valida la cita como respaldada. | **Falla.** Una expresion incompleta/ambigua que no activa las marcas de calidad puede pasar por cita literal. |
| Caracteres griegos U+03C9/U+03C0 frente a Latin `v`/`p` en la afirmacion. | Rechaza el cambio de glifos. | Pasa sustitucion textual; el caso Sears demuestra que no detecta una fuente que ya trae letras ambiguas. |

La extraccion de Sears p.468 no muestra U+FFFD, marca OCR ni marca de calidad. No se reinterpretaron sus caracteres. No habia un renderizador PDF local disponible entre las herramientas consultadas para contrastar visualmente ese glifo con la pagina; no se instalo ninguno.

### 5.2 Definiciones, ejercicios, ejemplos y procedimientos

- Entrada: `Problema: la constante elastica k representa la rigidez del resorte; la fuerza es proporcional a su deformacion. Determine el resultado solicitado...`
- Resultado de `select_evidence`: **aceptado** como evidencia respaldada. El detector solo invalida un marcador de ejercicio cuando el mismo pasaje no contiene palabras de definicion; `representa` y `es proporcional` permiten pasar.
- Entrada con prefijo `Ejemplo:` y palabras `constante elastica`, `rigidez`, `fuerza proporcional`, `deformacion`: **aceptada** para constante elastica. El bloqueo de ejemplos esta limitado a energia mecanica.
- Procedimientos/resultados no se distinguen de forma general: los marcadores cubren un conjunto pequeno (`problema`, `ejercicio`, `calcule`, etc.) y no hay categoria determinista independiente para resultado de ejercicio.
- **Falla:** la compatibilidad del tipo de fuente no esta garantizada por la coincidencia de senales definitorias.

### 5.3 Cobertura parcial y alcance de afirmaciones

- Para la pregunta sobre energia, se dieron dos fragmentos parciales: uno relacionaba energia mecanica con cinetica y otro relacionaba energia mecanica con potencial. Cada uno paso el criterio por separado; la union cubrio todos los grupos y la seleccion dio `respaldada`.
- Un doble local de generacion cito literalmente ambos fragmentos y `answer_question` presento estado **respaldada**. Ningun fragmento demostraba la relacion conjunta entre las tres formas de energia.
- Una cita literal del periodo que incluia tambien `la masa de la Luna es 7.3e22 kg` dentro de la misma oracion fue aceptada y presentada como **respaldada**. La validacion no compara el alcance de cada clausula con la pregunta.
- Si una afirmacion separada no coincide, el sistema puede marcar parcial; sin embargo, no separa todas las clausulas internas de una oracion compuesta.
- Referencias inventadas y afirmaciones sin referencia se rechazan en las pruebas existentes. Las referencias aceptadas deben estar en el mapa F entregado al modelo.
- **Falla:** la union de temas y la cita literal no prueban que la evidencia completa cubra la relacion preguntada ni que cada parte de una oracion sea pertinente.

### 5.4 Extraccion defectuosa y calidad documental

- Los probes con U+FFFD y marcas `quality_flags` se rechazaron; esa proteccion funciona para esos casos.
- El detector de palabras fragmentadas cubre patrones prefijados, pero la respuesta actual para constante acepto Meriam p.163 con `de sarro lla` en el texto citado. Ese defecto no coincide con la lista de patrones.
- La notacion `w=2pn ... T 2p w=` de Ochoa p.2 y `v ... 2 p` de Sears p.468 no tiene marcas, caracteres privados o secuencias que activen los filtros. Ambas se aceptaron.
- La documentacion del extractor advierte que no reconstruye formulas/layout. Sin OCR ni contraste visual, los filtros actuales no detectan todas las confusiones de letras, sub/superindices o expresiones truncadas.
- **Falla:** las reglas detectan algunos defectos, no una extraccion matematica confiable en general.

### 5.5 Regresion y consultas reales de Etapa 3C

| Pregunta | Resultado anterior (`INFORME_ETAPA_3C.md`) | Resultado actual | Aceptados / descartados |
| --- | --- | --- | ---: |
| ¿Qué representa la constante elástica de un resorte? | respaldada | respaldada | 1 / 19 |
| ¿Cómo se define el período de oscilación? | respaldada | respaldada | 2 / 18 |
| ¿Qué relación existe entre la energía mecánica, cinética y potencial? | sin evidencia suficiente | sin evidencia suficiente | 0 / 20 |
| ¿Qué es la frecuencia angular? | parcial | respaldada | 2 / 18 |

La recuperacion y la generacion se midieron en segundos:

| Pregunta | Recuperacion | Generacion | Validacion | Total |
| --- | ---: | ---: | ---: | ---: |
| ¿Qué representa la constante elástica de un resorte? | 5.945 | 14.014 | 0.0013 | 19.961 |
| ¿Cómo se define el período de oscilación? | 0.655 | 3.151 | 0.0002 | 3.807 |
| ¿Qué relación existe entre la energía mecánica, cinética y potencial? | 0.621 | 0.000 | 0.0000 | 0.621 |
| ¿Qué es la frecuencia angular? | 0.874 | 4.000 | 0.0002 | 4.875 |

#### Consulta 1: ¿Qué representa la constante elástica de un resorte?

**Resultado:** respaldada. Recuperados: 20; aceptados: 1; descartados: 19.
**Respuesta presentada:**

```text
Supondremos aquí que el resorte es del tipo lineal común de constante recuperadora o rigidez k, de tal modo que la fuerza F que de sarro lla, de tracción o compresión, es proporcional a su deformación x, es decir , F = kx. [F1]
```

**Respuesta bruta de Qwen:**

```text
Supondremos aquí que el resorte es del tipo lineal común de constante recuperadora o rigidez k, de tal modo que la fuerza F que de sarro lla, de tracción o compresión, es proporcional a su deformación x, es decir , F = kx. [F1]
```

**Afirmaciones verificadas:**
- `Supondremos aquí que el resorte es del tipo lineal común de constante recuperadora o rigidez k, de tal modo que la fuerza F que de sarro lla, de tracción o compresión, es proporcional a su deformación x, es decir , F = kx. [F1]` ? F: F1.

**Afirmaciones rechazadas:**
- Ninguna.

**Referencias presentadas:**
- [F1] `Mecanica para Ingenieros, Dinámica (J.L Meriam)-Cinematica -Dinamica - solido rigido - 3° Edición`, pagina 163, chunk `bib-63ebd560dee7e28e:p163:c0`.

**Fragmentos aceptados:**
- [F1] `Bibliografía/Mecanica para Ingenieros, Dinámica (J.L Meriam)-Cinematica -Dinamica - solido rigido - 3° Edición.pdf`, pagina 163, chunk `bib-63ebd560dee7e28e:p163:c0`: Supondremos aquí que el resorte es del tipo lineal común de constante recuperadora o rigidez k, de tal modo que la fuerza F que de sarro lla, de tracción o compresión, es proporcional a su deformación x, es decir , F = kx.

#### Consulta 2: ¿Cómo se define el período de oscilación?

**Resultado:** respaldada. Recuperados: 20; aceptados: 2; descartados: 18.
**Respuesta presentada:**

```text
Período. [F1]
Es el tiempo al cabo del cual las magnitudes que caracterizan el estado de un sistema toman nuevamente los mismos valores. [F1]
El periodo , T , es el tiempo que tarda un ciclo, y siempre es positivo. [F2]
```

**Respuesta bruta de Qwen:**

```text
Período. Es el tiempo al cabo del cual las magnitudes que caracterizan el estado de un sistema toman nuevamente los mismos valores. [F1]

El periodo , T , es el tiempo que tarda un ciclo, y siempre es positivo. [F2]
```

**Afirmaciones verificadas:**
- `Período. [F1]` ? F: F1.
- `Es el tiempo al cabo del cual las magnitudes que caracterizan el estado de un sistema toman nuevamente los mismos valores. [F1]` ? F: F1.
- `El periodo , T , es el tiempo que tarda un ciclo, y siempre es positivo. [F2]` ? F: F2.

**Afirmaciones rechazadas:**
- Ninguna.

**Referencias presentadas:**
- [F1] `21-OscilaLibres 058-066`, pagina 2, chunk `bib-f75466805059de6b:p2:c0`.
- [F2] `Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009)`, pagina 443, chunk `bib-c9401bd9a6885a50:p443:c0`.

**Fragmentos aceptados:**
- [F1] `Bibliografía/Ochoa.rar!/21-OscilaLibres 058-066.pdf`, pagina 2, chunk `bib-f75466805059de6b:p2:c0`: Período. Es el tiempo al cabo del cual las magnitudes que caracterizan el estado de un sistema toman nuevamente los mismos valores.
- [F2] `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf`, pagina 443, chunk `bib-c9401bd9a6885a50:p443:c0`: El periodo , T , es el tiempo que tarda un ciclo, y siempre es positivo.

#### Consulta 3: ¿Qué relación existe entre la energía mecánica, cinética y potencial?

**Resultado:** sin evidencia suficiente. Recuperados: 20; aceptados: 0; descartados: 20.
**Respuesta presentada:**

```text
No se encontro evidencia bibliografica pertinente y confiable para responder.
```

**Respuesta bruta de Qwen:**

```text
(Qwen no invocado por falta de evidencia seleccionada.)
```

**Afirmaciones verificadas:**
- Ninguna.

**Afirmaciones rechazadas:**
- Ninguna.

**Referencias presentadas:**
- Ninguna; abstencion antes de Qwen.

**Fragmentos aceptados:**
- Ninguno.

#### Consulta 4: ¿Qué es la frecuencia angular?

**Resultado:** respaldada. Recuperados: 20; aceptados: 2; descartados: 18.
**Respuesta presentada:**

```text
Como lo veremos a lo largo de los próximos temas, a menudo resulta útil definir una nueva magnitud que conocemos como frecuencia angular (w), relacionada con las anteriores mediante: w=2pn por lo tanto T 2p w= [F1]
La frecuencia angular v es 2 p veces la frecuencia. [F2]
```

**Respuesta bruta de Qwen:**

```text
Como lo veremos a lo largo de los próximos temas, a menudo resulta útil definir una nueva magnitud que conocemos como frecuencia angular (w), relacionada con las anteriores mediante: w=2pn por lo tanto T 2p w= [F1]

La frecuencia angular v es 2 p veces la frecuencia. [F2]
```

**Afirmaciones verificadas:**
- `Como lo veremos a lo largo de los próximos temas, a menudo resulta útil definir una nueva magnitud que conocemos como frecuencia angular (w), relacionada con las anteriores mediante: w=2pn por lo tanto T 2p w= [F1]` ? F: F1.
- `La frecuencia angular v es 2 p veces la frecuencia. [F2]` ? F: F2.

**Afirmaciones rechazadas:**
- Ninguna.

**Referencias presentadas:**
- [F1] `21-OscilaLibres 058-066`, pagina 2, chunk `bib-f75466805059de6b:p2:c0`.
- [F2] `Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009)`, pagina 468, chunk `bib-c9401bd9a6885a50:p468:c0`.

**Fragmentos aceptados:**
- [F1] `Bibliografía/Ochoa.rar!/21-OscilaLibres 058-066.pdf`, pagina 2, chunk `bib-f75466805059de6b:p2:c0`: Como lo veremos a lo largo de los próximos temas, a menudo resulta útil definir una nueva magnitud que conocemos como frecuencia angular (w), relacionada con las anteriores mediante: w=2pn por lo tanto T 2p w= Introducción al Estudio de un Movimiento Armónico Simple.
- [F2] `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf`, pagina 468, chunk `bib-c9401bd9a6885a50:p468:c0`: La frecuencia angular v es 2 p veces la frecuencia.

**Hallazgo clave:** la afirmacion `La frecuencia angular v es 2 p veces la frecuencia.` de Sears p.468 fue verificada por coincidencia literal y se incorporo a una respuesta marcada respaldada. No se demostro que `v` equivalga a omega ni que `p` equivalga a pi; el control no detecto ni advirtio la ambiguedad.

## 6. Casos aprobados y rechazados

**Aprobados por comportamiento esperado:**
- Rechaza una afirmacion sin referencia o con un ID F inventado.
- Rechaza una sustitucion literal entre omega/pi y v/p cuando el texto fuente contiene el otro glifo.
- Rechaza las variantes concretas probadas para la fraccion Unicode vs `/` y para parentesis alterados.
- Rechaza U+FFFD y paginas con marcas de calidad; se abstiene ante la consulta real de energia.
- Las dos primeras consultas reales conservaron resultados respaldados con Ochoa p.2, Meriam p.163 y Sears p.443 segun el caso.

**Rechazados por comportamiento incorrecto del control (fallos de auditoria):**
- Acepta la cita exacta pero ambigua de Sears p.468.
- Acepta cambios semanticos super/subindice a texto plano por NFKC.
- Acepta una formula extraida incompleta si coincide literalmente y el fragmento pasa los perfiles de tema.
- Acepta un ejercicio/ejemplo con vocabulario definitorio y puede marcarlo respaldado.
- Puede marcar respaldada evidencia parcial complementaria de varias fuentes y una cita que mezcla contenido fuera de tema.
- No detecta la palabra partida `de sarro lla` en el fragmento aceptado de Meriam p.163.

## 7. Fallos encontrados y cambios realizados

- Fallos confirmados: notacion ambigua aceptada; normalizacion matematica destructiva; deteccion contextual limitada de ejercicios/ejemplos; agregacion de cobertura por union de fragmentos; validador no consciente de pregunta/clausulas; heuristicas de extraccion incompletas; resultado de frecuencia angular cambia de parcial a respaldada entre corridas.
- **Cambios de codigo: ninguno.** De acuerdo con el orden solicitado, primero se ejecutaron las pruebas sin tocar el codigo y se documentan aqui los cambios localizados propuestos antes de implementarlos.
- Unicamente se creo `INFORME_ETAPA_3C_1.md`. No se modificaron tests, `requirements-chatbot.txt`, indice, informes experimentales, interfaz ni archivos protegidos.

## 8. Propuestas de ajuste localizado para revision

1. Para afirmaciones que contienen expresiones matematicas, comparar simbolos preservando la forma Unicode (NFC como maximo, no NFKC) y rechazar/abstenerse ante letras o signos ambiguos sin verificacion en la fuente. No convertir `v` a omega ni `p` a pi.
2. En una consulta que pide una definicion general, usar una regla de contexto conservadora: los marcadores `Problema`, `Ejercicio`, `Ejemplo`, `Rta`, procedimiento o resultado no pasan por la presencia incidental de verbos definitorios. La evidencia general debe estar separada y ser explicita.
3. Para preguntas compuestas, no marcar `respaldada` por la union de grupos entre fragmentos parciales; exigir una relacion directa verificable para todos los componentes o mantener `parcial`/abstencion.
4. Hacer que la validacion reciba la pregunta/intencion y revise clausulas separables, para excluir afirmaciones literales pero ajenas al tema. No basta con que la frase aparezca en un fragmento aceptado.
5. Agregar regresiones deterministas para cada probe fallido y ejecutar las 44 pruebas anteriores mas las nuevas. Mantener tests sin modelos para que sean reproducibles.
Estas propuestas son deliberadamente restrictivas; no corrigen ni completan formulas extraidas. Requieren revision antes de implementarse.

## 9. Recursos y entorno

- Se usaron Ollama local, `qwen2.5:7b` y `bge-m3:latest`; no se hicieron solicitudes de red ni descargas.
- Durante las consultas, `ollama ps` informo ambos modelos en `100% GPU`. RAM total visible: 16,625,724 KB; minimo libre observado: 1,966,376 KB (~1.87 GiB). Ninguna consulta se detuvo.
- La auditoria visual de los PDF no pudo realizarse con un renderizador local disponible; no se instalo herramienta alguna. Por tanto el informe juzga el texto indexado y sus marcas, no la representacion tipografica original.

## 10. Limitaciones y riesgos no garantizados

- Las citas literales prueban que una cadena aparece en el contexto aceptado, no que la extraccion represente fielmente el PDF ni que la afirmacion sea cientificamente correcta.
- La marca de calidad depende de metadatos y heuristicas finitas; defectos semanticos que no usen caracteres reemplazados pueden pasar.
- Los sub/superindices pueden perder distincion al normalizar; variables visualmente parecidas requieren conservar/validar glifos originales.
- La deteccion de ejercicios, procedimientos y ejemplos no es completa y puede aceptar frases contextualmente particulares.
- Los estados de Qwen no son estables entre corridas: en particular, frecuencia angular paso de parcial a respaldada cuando el modelo copio la formula de origen con otra puntuacion.
- No se valido la apariencia visual de la pagina de Sears p.468 ni se interpreto su formula. Debe permanecer como evidencia dudosa hasta contrastar la fuente.

## 11. Recomendacion tecnica y cierre

**La Etapa 3C no debe considerarse estable ni confiable para respuestas academicas con formulas en su estado actual.** La suite de 44 pruebas pasa, pero los probes detectan rutas donde una cita literal ambigua, una salida de ejercicio o cobertura incompleta se etiqueta como respaldada.
La auditoria solicitada queda documentada. No se implementaron los ajustes propuestos porque debian presentarse antes de cambiar codigo. Se detiene aqui para revision; no se inicia integracion experimental ni interfaz.
