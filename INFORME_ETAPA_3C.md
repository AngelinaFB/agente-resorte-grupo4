# Informe Etapa 3C: Evidencia determinista y respuestas fundamentadas

Fecha de evaluacion: 2026-11-08.

## Resultado ejecutivo

- Se implemento seleccion determinista de evidencia, validacion extractiva por afirmacion y una evaluacion local reproducible para cuatro consultas.
- Suite completa: **44 pruebas aprobadas** (28 previas + 16 nuevas de evidencia).
- Qwen 2.5 7B se ejecuto localmente; no se descargaron modelos ni dependencias.
- Resultados reales: constante elastica y periodo respaldados; energia mecanica se abstuvo por evidencia deteriorada o particular; frecuencia angular quedo parcial porque Qwen altero una formula y esa afirmacion fue rechazada.
- La seleccion no usa la puntuacion de similitud como criterio suficiente. El modelo recibe unicamente los fragmentos aceptados.

## Arquitectura implementada

1. **Recuperacion**: se conserva la busqueda hibrida de la Etapa 3A.
2. **Seleccion de evidencia** (`chatbot/evidence.py`): perfila la pregunta, evalua correspondencia tematica, detecta ejercicios/ejemplos y aplica marcas y heuristicas de calidad. Devuelve aceptados y descartados con motivos.
3. **Generacion** (`chatbot/generation.py`): solo envia los aceptados a Ollama. Si no queda evidencia utilizable, no llama al modelo.
4. **Validacion**: divide la salida en afirmaciones y acepta solo citas textuales exactas con identificadores entregados al modelo. Conserva puntuacion matematica; rechaza formulas con signos cambiados, referencias inventadas, afirmaciones sin cita y texto no respaldado.
5. **Presentacion**: informa respuesta respaldada, parcial o abstencion, con documento/pagina y referencias junto a las citas. Si no hay respuesta validada, puede usar extraccion literal de evidencia ya aceptada.
6. **Evaluacion** (`chatbot/evaluation.py`, CLI `evaluate-3c`): registra por consulta los 20 candidatos, sus decisiones y razones, salida bruta, afirmaciones validadas/rechazadas, referencias y tiempos.

### Criterios y limites de seleccion

- **Constante elastica**: exige mencion explicita de constante/rigidez y relacion fuerza-deformacion; la ley de Hooke sin definicion explicita no alcanza.
- **Periodo**: exige periodo y una definicion que relacione tiempo con ciclo/valores repetidos. Una mencion del periodo dentro de otro tema no alcanza.
- **Energia mecanica**: exige energia mecanica, una relacion y evidencia de energia cinetica o potencial. Se informa como parcial cuando falta un componente; se rechazan ejemplos particulares como regla general.
- **Frecuencia angular**: exige el concepto y una definicion/relacion textual.
- Para preguntas genericas se requiere coincidencia de al menos dos terminos de contenido. El score solo mantiene el orden de busqueda.
- Se respetan `needs_ocr` y `quality_flags`; tambien se excluyen texto corto, caracteres de reemplazo, simbolos de fuente no decodificados, signos de reemplazo densos y patrones conocidos de palabras fisicas fragmentadas.
- La validacion no usa Qwen como juez. Compara cada afirmacion con evidencia aceptada y sus IDs exactos. Las citas compuestas se validan frase por frase.

## Archivos creados y modificados

- Creado `agente-resorte/chatbot/evidence.py`: perfiles, seleccion, abstencion y validador determinista.
- Modificado `agente-resorte/chatbot/generation.py`: contexto solo aceptado, validacion, respuesta parcial y trazas.
- Creado `agente-resorte/chatbot/evaluation.py`: cuatro preguntas reproducibles.
- Modificado `agente-resorte/chatbot/cli.py`: comando `evaluate-3c`.
- Modificado `agente-resorte/chatbot/README.md`: uso del nuevo flujo y evaluador.
- Creado `agente-resorte/tests/test_evidence.py`: 16 pruebas nuevas.
- Modificado `agente-resorte/tests/test_generation.py`: fixtures alineados con evidencia y pruebas de Ollama ausente/modelo ausente.
- Sin dependencias nuevas; `requirements-chatbot.txt` no se modifico.
- No se modificaron `tracking.py`, `calibracion.py`, `señal.py`, `ajuste.py`, `app.py`, `main.py`, la interfaz Streamlit ni la base/indice bibliografico.

## Pruebas automatizadas

Ejecucion final: `py -3.14 -m unittest discover -s tests -v`: **Ran 44 tests — OK**.

Las nuevas pruebas cubren ejercicios fuera de tema, formulas ausentes o alteradas, calculos derivados, afirmaciones sin referencia, referencias inventadas, desvio tematico, citas exactas, respuestas parciales, abstencion, paginas de mala calidad, palabras fragmentadas, ejemplos no generalizables y Ollama/modelo no disponibles. Los dobles prueban el flujo y las reglas deterministas; **no demuestran que Qwen obedezca por si solo las instrucciones**.

## Evaluacion real con Qwen 2.5 7B

Comando reproducible: `python -m chatbot.cli evaluate-3c --model qwen2.5:7b --limit 20 --json`.
Cada consulta recupero 20 candidatos. Los registros completos distinguen aceptados y descartados y conservan pagina, chunk, score, texto, senales, motivos y marcas de calidad.

| Consulta | Resultado final | Recuperados | Aceptados | Descartados | Recuperacion (s) | Generacion (s) | Validacion (s) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ¿Qué representa la constante elástica de un resorte? | respaldada | 20 | 1 | 19 | 1.076 | 2.466 | 0.0014 |
| ¿Cómo se define el período de oscilación? | respaldada | 20 | 2 | 18 | 0.651 | 2.145 | 0.0002 |
| ¿Qué relación existe entre la energía mecánica, cinética y potencial? | sin evidencia suficiente | 20 | 0 | 20 | 0.621 | 0.000 | 0.0000 |
| ¿Qué es la frecuencia angular? | parcial | 20 | 2 | 18 | 0.895 | 2.765 | 0.0002 |

### 1. ¿Qué representa la constante elástica de un resorte?

**Resultado:** respaldada  
**Estado de generacion:** Qwen invocado; sin fallback.  
**Tiempo:** recuperacion 1.076 s; generacion 2.466 s; validacion 0.0014 s; total 3.544 s.

**Respuesta presentada:**

```text
Supondremos aquí que el resorte es del tipo lineal común de constante recuperadora o rigidez k, de tal modo que la fuerza F que de sarro lla, de tracción o compresión, es proporcional a su deformación x, es decir , F = kx. [F1]
```

**Respuesta bruta de Qwen:**

```text
Supondremos aquí que el resorte es del tipo lineal común de constante recuperadora o rigidez k, de tal modo que la fuerza F que de sarro lla, de tracción o compresión, es proporcional a su deformación x, es decir , F = kx. [F1]
```

**Afirmaciones verificadas:**
- `Supondremos aquí que el resorte es del tipo lineal común de constante recuperadora o rigidez k, de tal modo que la fuerza F que de sarro lla, de tracción o compresión, es proporcional a su deformación x, es decir , F = kx. [F1]` ? referencias verificadas: F1.

**Afirmaciones rechazadas:**
- Ninguna.

**Referencias usadas en la respuesta:**
- [F1] `Mecanica para Ingenieros, Dinámica (J.L Meriam)-Cinematica -Dinamica - solido rigido - 3° Edición`, pagina 163 (chunk `bib-63ebd560dee7e28e:p163:c0`).

**Fragmentos aceptados (texto enviado a Qwen):**
- [F1] `Bibliografía/Mecanica para Ingenieros, Dinámica (J.L Meriam)-Cinematica -Dinamica - solido rigido - 3° Edición.pdf`, pagina 163, chunk `bib-63ebd560dee7e28e:p163:c0`, calidad: sin marcas reportadas.
  > Supondremos aquí que el resorte es del tipo lineal común de constante recuperadora o rigidez k, de tal modo que la fuerza F que de sarro lla, de tracción o compresión, es proporcional a su deformación x, es decir , F = kx.

**Candidatos recuperados, descartes y motivos** (incluye todos los candidatos):

| Estado | Documento | Pagina | Chunk | Score | Motivo / senales | Fragmento recuperado (extracto) |
| --- | --- | ---: | --- | ---: | --- | --- |
| Aceptado | `Bibliografía/Mecanica para Ingenieros, Dinámica (J.L Meriam)-Cinematica -Dinamica - solido rigido - 3° Edición.pdf` | 163 | `bib-63ebd560dee7e28e:p163:c0` | 0.03178 | senales presentes: concepto, relacion_fuerza_deformacion; aceptado: correspondencia tematica y evidencia directa | Supondremos aquí que el resorte es del tipo lineal común de constante recuperadora o rigidez k, de tal modo que la fuerza F que de sarro lla, de tr... |
| Descartado | `Bibliografía/libroejercicios.pdf` | 66 | `bib-dea1bead6315754b:p66:c0` | 0.01639 | senales presentes: concepto, relacion_fuerza_deformacion; extraccion con palabras fisicas fragmentadas | - 56 - VER Resumiendo, la constante elástica es una medi a gráfico, la constant e es la pendiente de la recta del gráfico fuerza en función del / A... |
| Descartado | `Bibliografía/Mecanica para Ingenieros, Dinámica (J.L Meriam)-Cinematica -Dinamica - solido rigido - 3° Edición.pdf` | 180 | `bib-63ebd560dee7e28e:p180:c0` | 0.01613 | faltan senales: concepto, relacion_fuerza_deformacion | Para un sistema de partícula |
| Descartado | `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf` | 456 | `bib-c9401bd9a6885a50:p456:c0` | 0.01613 | senales presentes: relacion_fuerza_deformacion; faltan senales: concepto | c) Si el cuerpo se mueve con respecto al equilibrio, la fuerza neta sobre él será proporcional a su desplazamiento. |
| Descartado | `Bibliografía/Mecanica para Ingenieros, Dinámica (J.L Meriam)-Cinematica -Dinamica - solido rigido - 3° Edición.pdf` | 251 | `bib-63ebd560dee7e28e:p251:c0` | 0.01587 | senales presentes: concepto; faltan senales: relacion_fuerza_deformacion; el pasaje es un enunciado de ejercicio, no una definicion o explicacion | Despreciar las p érd idas de energía y calcular (a) la constante recuperadora k por metro de longitud de la cuerda elástica, (b) l a velocidad máxi... |
| Descartado | `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf` | 246 | `bib-c9401bd9a6885a50:p246:c0` | 0.01587 | senales presentes: concepto; faltan senales: relacion_fuerza_deformacion | En la sección 6.3 vimos que el trabajo que debemos efectuar el resorte para x l x 2 es (trabajo efectuado un resorte) donde k es la constante de fu... |
| Descartado | `Bibliografía/libroejercicios.pdf` | 68 | `bib-dea1bead6315754b:p68:c0` | 0.01562 | faltan senales: concepto, relacion_fuerza_deformacion; extraccion con caracter de reemplazo | F = K. |
| Descartado | `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf` | 250 | `bib-c9401bd9a6885a50:p250:c0` | 0.01515 | senales presentes: concepto; faltan senales: relacion_fuerza_deformacion | Ésta es aproximadamente un décimo de la constante de fuerza de un resorte en la suspensión de un automóvil. |
| Descartado | `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf` | 231 | `bib-c9401bd9a6885a50:p231:c1` | 0.01493 | senales presentes: concepto; faltan senales: relacion_fuerza_deformacion | a ) Demues- tre que la constante de fuerza efectiva de esta com- binación es k efe 5 k 1 1 k 2. |
| Descartado | `Bibliografía/Ochoa.rar!/32-PmasCapitulo III 064-067.pdf` | 2 | `bib-717a7a2553717eaf:p2:c0` | 0.01471 | senales presentes: concepto; faltan senales: relacion_fuerza_deformacion | Cada uno de los cuatro resortes tiene una constante elástica de 65,5 N/cm. |
| Descartado | `Bibliografía/libroejercicios.pdf` | 73 | `bib-dea1bead6315754b:p73:c0` | 0.01449 | faltan senales: concepto, relacion_fuerza_deformacion; extraccion con caracter de reemplazo | = 4 N . |
| Descartado | `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf` | 247 | `bib-c9401bd9a6885a50:p247:c0` | 0.01429 | faltan senales: concepto, relacion_fuerza_deformacion | tanto gravitacional como elástica es la elástica. |
| Descartado | `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf` | 216 | `bib-c9401bd9a6885a50:p216:c0` | 0.01408 | senales presentes: concepto; faltan senales: relacion_fuerza_deformacion | Para mantener un resorte esti- rado una distancia x más allá de su longitud sin estiramiento, debemos aplicar una x no es excesivo, vemos que la fu... |
| Descartado | `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf` | 260 | `bib-c9401bd9a6885a50:p260:c0` | 0.01389 | faltan senales: concepto, relacion_fuerza_deformacion | El trabajo realizado por fuerzas no potencial e interna siempre se conserva. |
| Descartado | `Bibliografía/Mecanica para Ingenieros, Dinámica (J.L Meriam)-Cinematica -Dinamica - solido rigido - 3° Edición.pdf` | 163 | `bib-63ebd560dee7e28e:p163:c1` | 0.01370 | faltan senales: concepto, relacion_fuerza_deformacion | en la figura 3.4. |
| Descartado | `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf` | 443 | `bib-c9401bd9a6885a50:p443:c0` | 0.01351 | faltan senales: concepto, relacion_fuerza_deformacion | La , f, es el número |
| Descartado | `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf` | 477 | `bib-c9401bd9a6885a50:p477:c1` | 0.01333 | senales presentes: concepto; faltan senales: relacion_fuerza_deformacion; el pasaje es un enunciado de ejercicio, no una definicion o explicacion | Calcule la constante de fuerza efectiva k efe en cada uno de los tres casos: a ), b ) y c ) de la figura 13.43. |
| Descartado | `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf` | 248 | `bib-c9401bd9a6885a50:p248:c0` | 0.01316 | senales presentes: concepto; faltan senales: relacion_fuerza_deformacion | El “sistema” se compone del cuerpo de masa m, vés de la fuerza gravitacional y el resorte de constante de fuerza k. |
| Descartado | `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf` | 474 | `bib-c9401bd9a6885a50:p474:c1` | 0.01299 | senales presentes: concepto; faltan senales: relacion_fuerza_deformacion | Un huevo duro (cocido) de 50.0 g se mueve en el extremo de un resorte cuya constante de fuerza es k 5 25.0 N > m. |
| Descartado | `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf` | 245 | `bib-c9401bd9a6885a50:p245:c0` | 0.01282 | senales presentes: concepto; faltan senales: relacion_fuerza_deformacion | Para mantener un resorte ideal esti- rado una distancia x, debemos ejercer una fuerza F 5 kx, donde k es la constante de fuerza del resorte. |


### 2. ¿Cómo se define el período de oscilación?

**Resultado:** respaldada  
**Estado de generacion:** Qwen invocado; sin fallback.  
**Tiempo:** recuperacion 0.651 s; generacion 2.145 s; validacion 0.0002 s; total 2.795 s.

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
- `Período. [F1]` ? referencias verificadas: F1.
- `Es el tiempo al cabo del cual las magnitudes que caracterizan el estado de un sistema toman nuevamente los mismos valores. [F1]` ? referencias verificadas: F1.
- `El periodo , T , es el tiempo que tarda un ciclo, y siempre es positivo. [F2]` ? referencias verificadas: F2.

**Afirmaciones rechazadas:**
- Ninguna.

**Referencias usadas en la respuesta:**
- [F1] `21-OscilaLibres 058-066`, pagina 2 (chunk `bib-f75466805059de6b:p2:c0`).
- [F2] `Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009)`, pagina 443 (chunk `bib-c9401bd9a6885a50:p443:c0`).

**Fragmentos aceptados (texto enviado a Qwen):**
- [F1] `Bibliografía/Ochoa.rar!/21-OscilaLibres 058-066.pdf`, pagina 2, chunk `bib-f75466805059de6b:p2:c0`, calidad: sin marcas reportadas.
  > Período. Es el tiempo al cabo del cual las magnitudes que caracterizan el estado de un sistema toman nuevamente los mismos valores.
- [F2] `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf`, pagina 443, chunk `bib-c9401bd9a6885a50:p443:c0`, calidad: sin marcas reportadas.
  > El periodo , T , es el tiempo que tarda un ciclo, y siempre es positivo.

**Candidatos recuperados, descartes y motivos** (incluye todos los candidatos):

| Estado | Documento | Pagina | Chunk | Score | Motivo / senales | Fragmento recuperado (extracto) |
| --- | --- | ---: | --- | ---: | --- | --- |
| Descartado | `Bibliografía/Ochoa.rar!/62-SisRigMovPlano II 119-135.pdf` | 9 | `bib-9acb1441cbbedd72:p9:c0` | 0.03227 | senales presentes: periodo; faltan senales: definicion_tiempo_ciclo | Por lo tanto en general a cada círculo de suspensión le estará asociado un circulo de oscilación y serán tales que al suspender el cuerpo de un pun... |
| Aceptado | `Bibliografía/Ochoa.rar!/21-OscilaLibres 058-066.pdf` | 2 | `bib-f75466805059de6b:p2:c0` | 0.03202 | senales presentes: periodo, definicion_tiempo_ciclo; aceptado: correspondencia tematica y evidencia directa | Período. Es el tiempo al cabo del cual las magnitudes que caracterizan el estado de un sistema toman nuevamente los mismos valores. |
| Descartado | `Bibliografía/Ochoa.rar!/62-SisRigMovPlano II 119-135.pdf` | 8 | `bib-9acb1441cbbedd72:p8:c0` | 0.03150 | senales presentes: periodo; faltan senales: definicion_tiempo_ciclo; extraccion con simbolo de fuente no decodificado | Operando con la anterior es inmediato que el período de la oscilación puede expresarse como: g mR I R T 2 c + = p Definiendo la Longitud Equivalent... |
| Descartado | `Bibliografía/Ochoa.rar!/14-Gravitacion 031-043.pdf` | 5 | `bib-03bc0f2b24fd3c86:p5:c0` | 0.03031 | faltan senales: periodo, definicion_tiempo_ciclo | x 0 1 2 3 4 2 1 0 -1 -2 x 0 1 2 3 4 6 4 2 0 -2 -4 -6 x 0 1 2 3 4 15 10 5 0 -5 -10 -15 - 1.35 - |
| Descartado | `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf` | 462 | `bib-c9401bd9a6885a50:p462:c0` | 0.03002 | senales presentes: periodo; faltan senales: definicion_tiempo_ciclo; el pasaje es un enunciado de ejercicio, no una definicion o explicacion | Calcule el periodo de su movimiento. |
| Descartado | `Bibliografía/Ochoa.rar!/21-OscilaLibres 058-066.pdf` | 8 | `bib-f75466805059de6b:p8:c0` | 0.02983 | senales presentes: periodo; faltan senales: definicion_tiempo_ciclo; extraccion con simbolo de fuente no decodificado | Solución General para el Período de un Péndulo Puntual. |
| Descartado | `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf` | 463 | `bib-c9401bd9a6885a50:p463:c0` | 0.02748 | senales presentes: periodo; faltan senales: definicion_tiempo_ciclo | ¿Cómo se compara el periodo de esta varilla uniforme con el periodo de más corto; iii) la varilla tiene el mismo periodo. |
| Descartado | `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf` | 465 | `bib-c9401bd9a6885a50:p465:c0` | 0.02724 | senales presentes: periodo; faltan senales: definicion_tiempo_ciclo | ❚ Oscilaciones forzadas y resonancia Un oscilador amortiguado aislado dejará de moverse tarde o temprano; no obstante, podemos mantener una oscilac... |
| Descartado | `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf` | 442 | `bib-c9401bd9a6885a50:p442:c0` | 0.02712 | senales presentes: periodo; faltan senales: definicion_tiempo_ciclo | 13 APRENDIZAJE Al estudiar este capítulo, usted aprenderá: en términos de amplitud, periodo, movimiento armónico simple, energía para analizar el m... |
| Descartado | `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf` | 462 | `bib-c9401bd9a6885a50:p462:c1` | 0.02639 | senales presentes: periodo; faltan senales: definicion_tiempo_ciclo | Cuanto más corto sea el periodo, el ritmo al caminar será más rápido. |
| Descartado | `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf` | 475 | `bib-c9401bd9a6885a50:p475:c0` | 0.02637 | senales presentes: periodo; faltan senales: definicion_tiempo_ciclo | Si plitud y el periodo de las oscilaciones resultantes de este péndulo. |
| Descartado | `Bibliografía/Ochoa.rar!/24-Problemas II 080-087.pdf` | 6 | `bib-84431277cfc2f6c5:p6:c0` | 0.02578 | senales presentes: periodo; faltan senales: definicion_tiempo_ciclo; el pasaje es un enunciado de ejercicio, no una definicion o explicacion | Calcular el periodo y la frecuencia de la oscilación. |
| Descartado | `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf` | 449 | `bib-c9401bd9a6885a50:p449:c0` | 0.02565 | senales presentes: periodo; faltan senales: definicion_tiempo_ciclo | El periodo no depende de la amplitud A (ﬁgura 13.10c). |
| Descartado | `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf` | 455 | `bib-c9401bd9a6885a50:p455:c0` | 0.02496 | senales presentes: periodo; faltan senales: definicion_tiempo_ciclo | El periodo sí cambia al agregarse la masilla; su valor no depende de cómo se agregó T 2 es el mismo que obtuvimos en el inciso a ), a ) pero no en ... |
| Descartado | `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf` | 473 | `bib-c9401bd9a6885a50:p473:c2` | 0.02491 | senales presentes: periodo; faltan senales: definicion_tiempo_ciclo; el pasaje es un enunciado de ejercicio, no una definicion o explicacion | Calcule su periodo. |
| Aceptado | `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf` | 443 | `bib-c9401bd9a6885a50:p443:c0` | 0.02393 | senales presentes: periodo, definicion_tiempo_ciclo; aceptado: correspondencia tematica y evidencia directa | El periodo , T , es el tiempo que tarda un ciclo, y siempre es positivo. |
| Descartado | `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf` | 470 | `bib-c9401bd9a6885a50:p470:c0` | 0.02374 | senales presentes: periodo; faltan senales: definicion_tiempo_ciclo | ¿Qué sucede con el periodo? |
| Descartado | `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf` | 456 | `bib-c9401bd9a6885a50:p456:c1` | 0.02281 | senales presentes: periodo; faltan senales: definicion_tiempo_ciclo | para obtener el periodo y la frecuencia (las incógnitas). |
| Descartado | `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf` | 471 | `bib-c9401bd9a6885a50:p471:c0` | 0.02261 | senales presentes: periodo; faltan senales: definicion_tiempo_ciclo; el pasaje es un enunciado de ejercicio, no una definicion o explicacion | Calcule la frecuencia angular y el periodo del movimiento. |
| Descartado | `Bibliografía/Ochoa.rar!/32-PmasCapitulo III 064-067.pdf` | 1 | `bib-717a7a2553717eaf:p1:c0` | 0.02244 | senales presentes: periodo; faltan senales: definicion_tiempo_ciclo; el pasaje es un enunciado de ejercicio, no una definicion o explicacion | Calcular el periodo y la frecuencia de la oscilación. |


### 3. ¿Qué relación existe entre la energía mecánica, cinética y potencial?

**Resultado:** sin evidencia suficiente  
**Estado de generacion:** Qwen no invocado; sin fallback.  
**Tiempo:** recuperacion 0.621 s; generacion 0.000 s; validacion 0.0000 s; total 0.621 s.

**Respuesta presentada:**

```text
No se encontro evidencia bibliografica pertinente y confiable para responder.
```

**Respuesta bruta de Qwen:**

```text
(No se invoco: no habia evidencia pertinente y confiable.)
```

**Afirmaciones verificadas:**
- Ninguna.

**Afirmaciones rechazadas:**
- Ninguna.

**Referencias usadas en la respuesta:**
- Ninguna.

**Fragmentos aceptados (texto enviado a Qwen):**
- Ninguno.

**Candidatos recuperados, descartes y motivos** (incluye todos los candidatos):

| Estado | Documento | Pagina | Chunk | Score | Motivo / senales | Fragmento recuperado (extracto) |
| --- | --- | ---: | --- | ---: | --- | --- |
| Descartado | `Bibliografía/libroejercicios.pdf` | 227 | `bib-dea1bead6315754b:p227:c0` | 0.03175 | senales presentes: energia_mecanica, energia_cinetica, relacion_entre_energias; faltan senales: energia_potencial; el fragmento pertenece a un ejemplo particular y no se generaliza como regla | Esa Energía Cinética que adquirió el cuerpo fue entregada por el resorte. La fórmula que me da la energía almacenada ) es: La E m el tipo tiene en ... |
| Descartado | `Bibliografía/Ochoa.rar!/11-RevDinCpoPtual 001-020.pdf` | 9 | `bib-381685947e839158:p9:c0` | 0.03048 | senales presentes: energia_cinetica; faltan senales: energia_mecanica, energia_potencial, relacion_entre_energias; extraccion con simbolo de fuente no decodificado | 2 mv 2 1 T= Que en adelante reconoceremos como función Energía Cinética o simplemente energía cinética de la partícula o del centro de masa del sis... |
| Descartado | `Bibliografía/Ochoa.rar!/52-SisCposPuntuales II 092-102.pdf` | 4 | `bib-56174f8d2747ebf7:p4:c0` | 0.03037 | senales presentes: energia_mecanica, energia_cinetica; faltan senales: energia_potencial, relacion_entre_energias; el fragmento pertenece a un ejemplo particular y no se generaliza como regla; extraccion con simbolo de fuente no decodificado | Con lo mencionado anteriormente, definiremos a la Energía Mecánica del sistema como: E=T+Fext+Fint 5.34 Donde el primer término es la energía cinét... |
| Descartado | `Bibliografía/libroejercicios.pdf` | 133 | `bib-dea1bead6315754b:p133:c0` | 0.03008 | senales presentes: energia_mecanica, relacion_entre_energias; faltan senales: energia_cinetica, energia_potencial; el fragmento pertenece a un ejemplo particular y no se generaliza como regla; marca de calidad: palabras_muy_cortas | La energía mecánica del carrito en A va a ser la suma de las energías cinética, potencial y elástica. |
| Descartado | `Bibliografía/Ochoa.rar!/63-SisRigMovPlano III 136-143.pdf` | 6 | `bib-a8eaefb2c2f1c8ee:p6:c0` | 0.02927 | senales presentes: energia_cinetica; faltan senales: energia_mecanica, energia_potencial, relacion_entre_energias; extraccion con simbolo de fuente no decodificado | Finalmente, la energía disipada durante el recorrido puede determinarse como diferencia de la energía cinética entre el instante inicial y el insta... |
| Descartado | `Bibliografía/Ochoa.rar!/33-EnergiaMecanica 101-111.pdf` | 5 | `bib-0e691243d2a495ff:p5:c0` | 0.02899 | senales presentes: energia_mecanica, energia_potencial, relacion_entre_energias; faltan senales: energia_cinetica; el fragmento pertenece a un ejemplo particular y no se generaliza como regla; extraccion con simbolo de fuente no decodificado | Ochoa Campo Conservativo y Energía Mecánica Facultad de Ingeniería - Universidad Nacional de La Pampa 3.08ENERGÍA MECÁNICA. Consideremos el caso de... |
| Descartado | `Bibliografía/Ochoa.rar!/33-EnergiaMecanica 101-111.pdf` | 6 | `bib-0e691243d2a495ff:p6:c0` | 0.02889 | senales presentes: energia_mecanica, energia_cinetica, energia_potencial; faltan senales: relacion_entre_energias; extraccion con simbolo de fuente no decodificado | En particular si deseáramos alcanzar puntos infinitamente alejados del centro de la tierra será necesario que la energía mecánica mínima en el inst... |
| Descartado | `Bibliografía/libroejercicios.pdf` | 132 | `bib-dea1bead6315754b:p132:c0` | 0.02783 | senales presentes: energia_mecanica, energia_cinetica, energia_potencial, relacion_entre_energias; el fragmento pertenece a un ejemplo particular y no se generaliza como regla; descartado: no supera las reglas de evidencia directa | Es decir: *NOTA : De ahora en adelante () () 22 11 22 N EK ∆ m E MEC = E CIN + E POT + E El Energía mecánica. |
| Descartado | `Bibliografía/Ochoa.rar!/11-RevDinCpoPtual 001-020.pdf` | 10 | `bib-381685947e839158:p10:c0` | 0.02753 | senales presentes: energia_potencial; faltan senales: energia_mecanica, energia_cinetica, relacion_entre_energias; extraccion con simbolo de fuente no decodificado | Asignaremos arbitrariamente el valor nulo a la función energía potencial cuando la coordenada radial involucrada es nula, con lo que la constante s... |
| Descartado | `Bibliografía/Mecanica para Ingenieros, Dinámica (J.L Meriam)-Cinematica -Dinamica - solido rigido - 3° Edición.pdf` | 178 | `bib-63ebd560dee7e28e:p178:c0` | 0.02669 | senales presentes: energia_cinetica, energia_potencial; faltan senales: energia_mecanica, relacion_entre_energias; el pasaje es un enunciado de ejercicio, no una definicion o explicacion | =mgR2/r2yanu- dnstantabajtuado contra ubiar la posiciónradialdelasa puntualdesderar'eslavariaciónVg'-Vgdela enertatoria: S r' mgR2dr =mgR2(~ -~) =-... |
| Descartado | `Bibliografía/libroejercicios.pdf` | 129 | `bib-dea1bead6315754b:p129:c0` | 0.02599 | senales presentes: energia_cinetica, energia_potencial; faltan senales: energia_mecanica, relacion_entre_energias; el fragmento pertenece a un ejemplo particular y no se generaliza como regla; extraccion con caracter de reemplazo | V y su energía cinética valdrá ½ m . V 2 . E p = P ⋅ h ó m ⋅ g ⋅ h Energía potencial que P que está a una altura h . |
| Descartado | `Bibliografía/Ochoa.rar!/33-EnergiaMecanica 101-111.pdf` | 2 | `bib-0e691243d2a495ff:p2:c0` | 0.02546 | senales presentes: energia_mecanica, energia_cinetica, energia_potencial; faltan senales: relacion_entre_energias; extraccion con simbolo de fuente no decodificado | Ochoa Campo Conservativo y Energía Mecánica Facultad de Ingeniería - Universidad Nacional de La Pampa () k(r r) cte 2 1 r 2 Fm = - +  (r)mgy cte F... |
| Descartado | `Bibliografía/Mecanica para Ingenieros, Dinámica (J.L Meriam)-Cinematica -Dinamica - solido rigido - 3° Edición.pdf` | 179 | `bib-63ebd560dee7e28e:p179:c1` | 0.02525 | senales presentes: energia_cinetica, energia_potencial; faltan senales: energia_mecanica, relacion_entre_energias | Si representamos por U\_2 el trabajo que sobre la partícula efectúan las fuerzas que no son ni de la grave­ dad ni del resorte, la ecuación 3.11 qu... |
| Descartado | `Bibliografía/Ochoa.rar!/33-EnergiaMecanica 101-111.pdf` | 1 | `bib-0e691243d2a495ff:p1:c0` | 0.02475 | senales presentes: energia_mecanica, energia_potencial; faltan senales: energia_cinetica, relacion_entre_energias; extraccion con simbolo de fuente no decodificado | Ochoa Campo Conservativo y Energía Mecánica Facultad de Ingeniería - Universidad Nacional de La Pampa 3.07CAMPO DE FUERZA CONSERVA TIVO. Función En... |
| Descartado | `Bibliografía/libroejercicios.pdf` | 136 | `bib-dea1bead6315754b:p136:c0` | 0.02468 | senales presentes: energia_mecanica, energia_potencial; faltan senales: energia_cinetica, relacion_entre_energias | Su energía potencial inicial vale: Por cinemática sé que la velocidad final con la caer desde una altura h es: Es decir, toda la E pot se transform... |
| Descartado | `Bibliografía/Ochoa.rar!/11-RevDinCpoPtual 001-020.pdf` | 11 | `bib-381685947e839158:p11:c0` | 0.02434 | senales presentes: energia_mecanica; faltan senales: energia_cinetica, energia_potencial, relacion_entre_energias; extraccion con simbolo de fuente no decodificado | Energía Mecánica. |
| Descartado | `Bibliografía/Ochoa.rar!/33-EnergiaMecanica 101-111.pdf` | 3 | `bib-0e691243d2a495ff:p3:c0` | 0.02391 | senales presentes: energia_mecanica, energia_potencial; faltan senales: energia_cinetica, relacion_entre_energias; extraccion con simbolo de fuente no decodificado | Ochoa Campo Conservativo y Energía Mecánica Facultad de Ingeniería - Universidad Nacional de La Pampa Por lo tanto el campo de fuerza estará relaci... |
| Descartado | `Bibliografía/libroejercicios.pdf` | 140 | `bib-dea1bead6315754b:p140:c0` | 0.02353 | senales presentes: energia_mecanica, energia_cinetica; faltan senales: energia_potencial, relacion_entre_energias | Planteo: La energía mecánica abajo es sólo cinética No hay energía cinética. |
| Descartado | `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf` | 236 | `bib-c9401bd9a6885a50:p236:c0` | 0.02343 | senales presentes: energia_potencial; faltan senales: energia_mecanica, energia_cinetica, relacion_entre_energias | 213 ENERGÍA POTENCIAL DE LA ENERGÍA ? |
| Descartado | `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf` | 204 | `bib-c9401bd9a6885a50:p204:c0` | 0.02325 | senales presentes: energia_cinetica; faltan senales: energia_mecanica, energia_potencial, relacion_entre_energias | 181 TRABAJO Y ENERGÍA CINÉTICA ? |


### 4. ¿Qué es la frecuencia angular?

**Resultado:** parcial  
**Estado de generacion:** Qwen invocado; sin fallback.  
**Tiempo:** recuperacion 0.895 s; generacion 2.765 s; validacion 0.0002 s; total 3.660 s.

**Respuesta presentada:**

```text
Respuesta parcial: la bibliografía recuperada solo respalda los fragmentos citados; no hay evidencia suficiente para cubrir: los enunciados generados que no pudieron verificarse.
La frecuencia angular v es 2 p veces la frecuencia. [F2]
```

**Respuesta bruta de Qwen:**

```text
Como lo veremos a lo largo de los próximos temas, a menudo resulta útil definir una nueva magnitud que conocemos como frecuencia angular (w), relacionada con las anteriores mediante: w=2pn por lo tanto T 2p w. [F1]

La frecuencia angular v es 2 p veces la frecuencia. [F2]
```

**Afirmaciones verificadas:**
- `La frecuencia angular v es 2 p veces la frecuencia. [F2]` ? referencias verificadas: F2.

**Afirmaciones rechazadas:**
- `Como lo veremos a lo largo de los próximos temas, a menudo resulta útil definir una nueva magnitud que conocemos como frecuencia angular (w), relacionada con las anteriores mediante: w=2pn por lo tanto T 2p w. [F1]` ? formula o valor no coincide literalmente con la evidencia citada.

**Referencias usadas en la respuesta:**
- [F2] `Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009)`, pagina 468 (chunk `bib-c9401bd9a6885a50:p468:c0`).

**Fragmentos aceptados (texto enviado a Qwen):**
- [F1] `Bibliografía/Ochoa.rar!/21-OscilaLibres 058-066.pdf`, pagina 2, chunk `bib-f75466805059de6b:p2:c0`, calidad: sin marcas reportadas.
  > Como lo veremos a lo largo de los próximos temas, a menudo resulta útil definir una nueva magnitud que conocemos como frecuencia angular (w), relacionada con las anteriores mediante: w=2pn por lo tanto T 2p w= Introducción al Estudio de un Movimiento Armónico Simple.
- [F2] `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf`, pagina 468, chunk `bib-c9401bd9a6885a50:p468:c0`, calidad: sin marcas reportadas.
  > La frecuencia angular v es 2 p veces la frecuencia.

**Candidatos recuperados, descartes y motivos** (incluye todos los candidatos):

| Estado | Documento | Pagina | Chunk | Score | Motivo / senales | Fragmento recuperado (extracto) |
| --- | --- | ---: | --- | ---: | --- | --- |
| Descartado | `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf` | 447 | `bib-c9401bd9a6885a50:p447:c0` | 0.03175 | senales presentes: frecuencia_angular; faltan senales: definicion_o_relacion | No confunda frecuencia con frecuencia angular Podemos meternos en pro- blemas si no distinguimos entre frecuencia f y frecuencia angular v5 2 p f. |
| Descartado | `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf` | 444 | `bib-c9401bd9a6885a50:p444:c0` | 0.03105 | senales presentes: frecuencia_angular; faltan senales: definicion_o_relacion | ¿Cuánto tarda cada oscilación, y qué frecuencia angular tiene? |
| Descartado | `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf` | 446 | `bib-c9401bd9a6885a50:p446:c1` | 0.03089 | senales presentes: frecuencia_angular; faltan senales: definicion_o_relacion | p > És- ta es la ecuación (13.2) para la frecuencia angular de P , lo cual veriﬁca nuestra aﬁr- mación acerca de las dos interpretaciones de v . |
| Aceptado | `Bibliografía/Ochoa.rar!/21-OscilaLibres 058-066.pdf` | 2 | `bib-f75466805059de6b:p2:c0` | 0.02991 | senales presentes: frecuencia_angular, definicion_o_relacion; aceptado: correspondencia tematica y evidencia directa | Como lo veremos a lo largo de los próximos temas, a menudo resulta útil definir una nueva magnitud que conocemos como frecuencia angular (w), relac... |
| Descartado | `Bibliografía/Ochoa.rar!/41-OndasElasticas 068-080.pdf` | 6 | `bib-ddd7e2e3e4dc9f7e:p6:c0` | 0.02939 | faltan senales: frecuencia_angular, definicion_o_relacion; extraccion con simbolo de fuente no decodificado | - 4.73 - |
| Descartado | `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf` | 471 | `bib-c9401bd9a6885a50:p471:c0` | 0.02608 | senales presentes: frecuencia_angular; faltan senales: definicion_o_relacion; el pasaje es un enunciado de ejercicio, no una definicion o explicacion | Calcule la frecuencia angular y el periodo del movimiento. |
| Descartado | `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf` | 473 | `bib-c9401bd9a6885a50:p473:c0` | 0.02564 | senales presentes: frecuencia_angular; faltan senales: definicion_o_relacion | La rueda de balance de un reloj vibra con amplitud angular U , frecuencia angular v y ángulo de fase f5 0. |
| Aceptado | `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf` | 468 | `bib-c9401bd9a6885a50:p468:c0` | 0.02515 | senales presentes: frecuencia_angular, definicion_o_relacion; aceptado: correspondencia tematica y evidencia directa | La frecuencia angular v es 2 p veces la frecuencia. |
| Descartado | `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf` | 545 | `bib-c9401bd9a6885a50:p545:c1` | 0.02339 | senales presentes: frecuencia_angular; faltan senales: definicion_o_relacion; el pasaje es un enunciado de ejercicio, no una definicion o explicacion | a ) Calcule la frecuencia, frecuencia angular y el número de on- da. |
| Descartado | `Bibliografía/Ochoa.rar!/21-OscilaLibres 058-066.pdf` | 8 | `bib-f75466805059de6b:p8:c0` | 0.02166 | senales presentes: frecuencia_angular, definicion_o_relacion; extraccion con simbolo de fuente no decodificado | Ochoa Interacción Elástica y Oscilaciones Libres Facultad de Ingeniería - Universidad Nacional de La Pampa Con lo que las conclusiones logradas en ... |
| Descartado | `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf` | 465 | `bib-c9401bd9a6885a50:p465:c0` | 0.01639 | senales presentes: frecuencia_angular; faltan senales: definicion_o_relacion | Suponga que se obliga al oscilador a vibrar con una frecuencia angular v d casi ig ual a la frecuencia angular v r que tendría sin fuerza impulsora. |
| Descartado | `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf` | 466 | `bib-c9401bd9a6885a50:p466:c0` | 0.01538 | senales presentes: frecuencia_angular; faltan senales: definicion_o_relacion | La frecuencia impulsora v d es igual a la frecuencia angular natural v de un oscilador |
| Descartado | `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf` | 356 | `bib-c9401bd9a6885a50:p356:c1` | 0.01538 | faltan senales: frecuencia_angular, definicion_o_relacion | ONLINE |
| Descartado | `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf` | 331 | `bib-c9401bd9a6885a50:p331:c2` | 0.01515 | senales presentes: definicion_o_relacion; faltan senales: frecuencia_angular | En t 5 0, se invierte la corriente de un motor eléctrico de corrien- te continua, causando un desplazamiento angular del eje del motor dado por a )... |
| Descartado | `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf` | 332 | `bib-c9401bd9a6885a50:p332:c0` | 0.01493 | senales presentes: definicion_o_relacion; faltan senales: frecuencia_angular | El ángulo u que describe una unidad de disco al girar está dado por u (t) 5 a 1 bt 2 ct 3 , donde a , b y c son constantes positivas, t está en seg... |
| Descartado | `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf` | 477 | `bib-c9401bd9a6885a50:p477:c2` | 0.01471 | senales presentes: frecuencia_angular; faltan senales: definicion_o_relacion | El resultado no mueve con la misma rapidez.) b ) Obtenga la derivada de la ecuación po, para una masa m que se mueve en el extremo de un resorte si... |
| Descartado | `Bibliografía/Ochoa.rar!/31-MomentoAngular 088-095.pdf` | 6 | `bib-2e93771c59e640c9:p6:c0` | 0.01471 | faltan senales: frecuencia_angular, definicion_o_relacion; extraccion con simbolo de fuente no decodificado | La figura muestra una partícula de masa (m) que se mueve a lo largo de una trayectoria circular contenida en un plano horizontal libre de rozamient... |
| Descartado | `Bibliografía/Mecanica para Ingenieros, Dinámica (J.L Meriam)-Cinematica -Dinamica - solido rigido - 3° Edición.pdf` | 375 | `bib-63ebd560dee7e28e:p375:c1` | 0.01449 | faltan senales: frecuencia_angular, definicion_o_relacion | __. |
| Descartado | `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf` | 470 | `bib-c9401bd9a6885a50:p470:c1` | 0.01429 | senales presentes: frecuencia_angular; faltan senales: definicion_o_relacion | Para un péndulo simple, diferencie claramente entre v (la ve- locidad angular) y v la frecuencia angular). |
| Descartado | `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf` | 471 | `bib-c9401bd9a6885a50:p471:c1` | 0.01408 | senales presentes: frecuencia_angular; faltan senales: definicion_o_relacion; el pasaje es un enunciado de ejercicio, no una definicion o explicacion | Calcule a ) el periodo, b ) la frecuencia y c ) la frecuencia angular de las oscilaciones. |

## Observacion de recursos

- Ollama confirmo `qwen2.5:7b` (ID `845dbda0ea48`) y `bge-m3:latest` (ID `790764642607`) instalados localmente. No se descargaron modelos ni dependencias.
- Durante las evaluaciones `ollama ps` informo ambos modelos en `100% GPU` (Qwen 4.8 GB reportados por Ollama; BGE-M3 689 MB). No se obtuvo una medicion de VRAM dedicada independiente.
- RAM visible: 16.63 millones KB (~15.85 GiB). Minimo libre observado en la ultima evaluacion: 1,997,716 KB (~1.90 GiB). No se bajo del umbral preventivo de 900,000 KB y no se detuvo ninguna consulta.
- Los tiempos variaron entre consultas y entre ejecuciones (calentamiento de modelos/caches); el informe registra la ultima corrida completa con el comparador final.

## Limitaciones pendientes

- La validacion por coincidencia literal es conservadora: puede abstenerse ante evidencia valida formulada de otra manera, y no verifica la verdad cientifica del documento ni entiende equivalencias semanticas nuevas.
- Los perfiles tematicos se limitan a los cuatro conceptos evaluados; el perfil generico usa solapamiento de terminos y requiere ampliacion/evaluacion antes de consultas abiertas.
- Las reglas heuristicas detectan ciertos defectos de extraccion, pero no sustituyen OCR ni una auditoria de calidad de todos los PDF. Las marcas del indice se conservaron; no se reconstruyo el indice.
- La consulta sobre energia mecanica termino en abstencion: los fragmentos top recuperados estaban marcados como deficientes, contenian formula OCR dudosa o pertenecian a un ejemplo particular. La documentacion requiere mejorar OCR/extraccion antes de poder contestarla con seguridad.
- La frecuencia angular quedo parcial: Qwen produjo una formula con puntuacion distinta de la fuente; el validador la rechazo. La relacion textual literal de otra fuente se mantuvo.
- Las pruebas con dobles validan reglas y manejo de fallos locales; las cuatro consultas reales constituyen una comprobacion de esta corrida, no una garantia de obediencia futura del modelo.

## Cierre de alcance

Se completo la Etapa 3C y se detiene aqui para revision. No se integraron informes experimentales ni interfaz de chatbot; tampoco se modifico la aplicacion de medicion, Streamlit, la bibliografia ni su indice.
