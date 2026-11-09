# Informe de validacion real - Etapa 3B

Fecha: 8 de noviembre de 2026

## Conclusiones

Se descargo unicamente `qwen2.5:7b` y Ollama verifico su SHA-256. Ollama 0.40.15 lo reconoce con ID `845dbda0ea48` y tamano 4,7 GB. Se ejecuto el motor real `chatbot.generation.answer_question`, que recupera fragmentos hibridos y llama al endpoint local `/api/chat`; no se usaron APIs externas ni servicios de nube.

La generacion se completo en las cuatro consultas sin error de falta de memoria. Sin embargo, la comprobacion de fundamentacion **no pasa**: el modelo cambio de tema en dos consultas, dedujo un valor en otra y genero una formula cuya base no queda respaldada de forma clara en los fragmentos. Las instrucciones de sistema se reforzaron y se repitieron las consultas; los problemas persistieron. Por eso no se puede afirmar que las respuestas utilicen exclusivamente la bibliografia. Este resultado no implementa la validacion avanzada de Etapa 3C.

## Modelo y equipo

- Ollama: 0.40.15.
- Generador: Qwen 2.5 7B, tag `qwen2.5:7b`, ID `845dbda0ea48`, tamano Ollama 4,7 GB.
- Embeddings: BGE-M3 ya instalado, tag `bge-m3:latest`.
- Equipo: Windows 11 Home 64 bits; AMD Ryzen 5 5600H, 6 nucleos/12 hilos; 15,86 GB RAM; Radeon RX 6600M con 4 GB reportados por WMI.
- RAM libre antes de la generacion: 5,74 GB. Minimo muestreado durante la segunda ronda: 0,99 GB. El proceso Ollama y runners sumo un maximo observado de 5,69 GB de working set.
- `ollama ps` informo Qwen (4,8 GB) y BGE-M3 (689 MB) ejecutandose al 100% GPU, contexto 4096. Los contadores de GPU de Windows dieron un maximo agregado de 6,61 GB de memoria dedicada comprometida, 0,29 GB compartida y 100,2% en motores Compute/3D. El contador agrega adaptadores y su porcentaje puede superar 100 al sumar motores; no equivale a VRAM exclusiva de la RX 6600M.
- No hubo error de carga ni cierre por memoria, pero el margen de RAM fue reducido. Al terminar se detuvieron ambos runners; la RAM libre subio a 6,69 GB.

## Tiempos observados

Los tiempos de `answer_question` incluyen recuperacion hibrida, comprobacion local del tag y generacion. Los modelos ya estaban cargados durante esta ronda; no son una medicion de arranque en frio.


## Constante Elastica

**Pregunta:** ¿Qué representa la constante elástica de un resorte?  
**Tiempo:** 2.97 s  
**Modelo:** qwen2.5:7b  
**Fragmentos recuperados:** 5

### Respuesta completa de Qwen

La documentación disponible no permite responder con precisión a la pregunta sobre la compresión del resorte necesaria para que la partícula entre en la zona rugosa. Los documentos proporcionan un contexto general del problema pero no incluyen los cálculos específicos necesarios para determinar la compresión del resorte.

### Referencias y contexto completo enviado

#### [F1] Mecanica para Ingenieros, Dinámica (J.L Meriam)-Cinematica -Dinamica - solido rigido - 3° Edición - pagina 163

- Ruta: `Bibliografía/Mecanica para Ingenieros, Dinámica (J.L Meriam)-Cinematica -Dinamica - solido rigido - 3° Edición.pdf`
- Chunk: `bib-63ebd560dee7e28e:p163:c0`
- Requiere OCR: `False`
- Marcas de calidad: ninguna

```text
es- ue mo ión De pli- er- así es- ael dos las pro- ala arial rza, elas entre inte- peri- ieaa fun- una mo- Tracción ~LC X X2 I F=kx D~p ~x --j Compresión lAr X xl -i X2 I P ---.o~F=kx ~X~ 137 Sinestirar Sincomprimir .4 3.6 k viblealqu halleunido.Supondremosaquíqueelresort deo lineal comnstante recuperador rigidezk,ao queuerza Fque desarrollad,etracció compresión,esproporciona seformación x,es decirF,=kx.Eigu.os doson qul cuerpose muepccióuerzas quenoseeara all resorte unalongitudx,bie congitud x., za queejl resortberpo e sentiio aesplazamiento, porlue eabajulizbre eerp negativo.Asípues,tantosi elresortlarmo scortaajealizado sobreelcuerps ne- gativoyvale Cuandounresort liberad,esdstado racción odmpresión, vemohors dosejee lgur deformacióia desdeX2 eformacióenor Xl.sta situacióze actúaen cualquierelosdoaobre elcueriene elmismosentidoqueespla- zamient, o, erabajorealizadosobreelcuerp positivo. Elvaeabajo, positivoegativo, segeapezoi- dalsombreaara amboscaepresegur.4. Aar erabajoefectuaor luerze unresortedebnersad probarquelaades eas quxpresen kyxseancoherentessdecir, sixestos, kdebstar /m. Enrealidadla,expresiónF= kxesaturaleza elásticaysóloeálida cuandotodaslaspartesdeesortrecee aceleraciónEl.estudiodinámico deamieesorte cuandosetieneee esbas- tantecomplicad nmo tratarlquí;supondremosa delre- sorts pequeñacomparadaas masasdtras partesdelsistemaque esténaceleradas,o casolarelaciónestáticará errores apreciables. Consideremosahoraeajo realizadobreunapartíce masam(fig. 3.5e semuevedescribiendoayectoria bajolaaccióa fuer- Tracción Compresión F F=kx ""-----'--------'--------'---x L1i x Xl ~ x2 I F=kx D ~ p ~x --j Si n estirar I S2 Sin comprimir Figura 3.4 xl ~ x2 I vible al que se halle unido . Supondremos aquí que el resorte es del tipo lineal común de constante recuperadora o rigidez k, de tal modo que la fuerza F que de sarro lla, de tracción o compresión, es proporcional a su deformación x, es decir , F = kx. En la figura 3.4 se representan los dos casos en que el cuerpo se mueve (por acción de fuerzas que no se indican) bien para alargar el resorte una longitud x, bien para comprimirlo una longitud x . En cada caso, la fuerza que ejerce el resorte sobre el cuerpo es de sentido contrario al desplazamiento, por lo que el trabajo que realiza sobre el cuerpo es negativo. Así pu es, tanto si el resorte se alarga como si se acorta, el trabajo realizado sobre el cuerpo es ne­ gativo y vale Cuando un resorte se libera, de sde un estado de tracción o de compresión, vemos ahora en los dos ejemplos de la figura 3.4 que su deformación cambia desde X 2 a una deformación menor Xl. En esta situación la fuerza que actúa en cualquiera de los do s casos sobre el cuerpo tiene el mismo sentido que el despla­ z amiento y, por tanto , el trabajo realizado sobre el cuerpo es positivo. El valor del trabajo, positivo o negativo, se ve que es igual al área trapezoi­ dal sombreada que para ambos casos se representa en la figura 3.4. Al calcular el trabajo efectuado por la fuerza de un resorte debe ponerse cuidado en com­ probar que las unidades en las que se expresen k y x sean coherentes . Es decir, si x está en metros, k debe estar en N/m. En realidad, la expresión F = kx es de naturaleza elástica y sólo es válida cuando tod as las partes del resorte carecen de aceleración. El estudio dinámico del comportamiento de un resorte
```

#### [F2] libroejercicios - pagina 66

- Ruta: `Bibliografía/libroejercicios.pdf`
- Chunk: `bib-dea1bead6315754b:p66:c0`
- Requiere OCR: `False`
- Marcas de calidad: ninguna

```text
- 56 - VER Resumiendo, la constante elástica es una medi a gráfico, la constant e es la pendiente de la recta del gráfico fuerza en función del / Ahora un comentario: = − ¿ Por qué es esto ? Bueno, la fuerza F que yo puse en la fórmula es la que yo contraria. ( La reacción ). Esta fuerza que unta al revés que el estiramiento. Es decir, si el estiramiento va así: ← → . considerar la que la mano ha El signo menos viene de considerar que la fu del estiramiento. ¿ Tendés Rta : Es lo mismo. Se puede poner de las 2 maneras. Vos tenés que trabajar con el módulo La mano estirando el resorte
```

#### [F3] Mecanica para Ingenieros, Dinámica (J.L Meriam)-Cinematica -Dinamica - solido rigido - 3° Edición - pagina 180

- Ruta: `Bibliografía/Mecanica para Ingenieros, Dinámica (J.L Meriam)-Cinematica -Dinamica - solido rigido - 3° Edición.pdf`
- Chunk: `bib-63ebd560dee7e28e:p180:c0`
- Requiere OCR: `False`
- Marcas de calidad: ninguna

```text
154 o e dichasposicionetremas careceancia Vgy~Ve. a ve T1+Vg 1«v,+U'12=T2+Vg +Ve (3.17a) (al s rencia eaes y3.17ga artícula asa mobligadascri- ycióas fuerzasF1yF2'erza gravitatoria W=mg,lafuerzaFdesorte ylareacciónN.arte bdelafigure- sgraasladlculajo F2'a s =kxparaevimiento estión, esdecir,desdeAhastaB,tre guala, mediante ción3.11, vnerinéTeaccgadura yectoria yaja. E figuraseilustraelotro procedimientoyesorte seincluyee delsistema.Ea F2durantee e U'l-2 ecuació elsegundo gurariaciones delasenergíaspotencialesgra- vitatoriayelástica.Adviértase, coneeétodo, alizado =kxeegraciógo molestaeneenta las variaciones ydireonforme artícula sedesplazadesde Ahac embarg egétodo sa asa Ve'emente los cálculos. sistemartícula orte, ra expresiec. 3.17)deeore- zas vivaspodemoolver aescribirla I,,~I N F1 ~I I~F2 F=k=mg Ul-2=st (bl (3.17b) -¡ dond = T+Vg +Veeslaenergíamecáotae lapartículan ee- s lla.Laecuación3.17bafir eo netalizado sobre ees ero gravitatoriaássticas esigualalavaria- gás casose sólointerven- ganfuerzaselásticas,fuerzasgravitatoria fuerzasgadura queno trabajen,érmino U'esnuloylaecuacióe laenergíasequedn Vg=O U'1_2=tlT+tlvg+tlVe (el ~E =O ose = constante (3.18) se, puemos quesepodrároambios deener- gíacinéotencial ceversa, ae naríe laenergíecánica to- talT+Vg+Ve'Laecuación3.18expresaelprinciprvacie lgía dinámica. l Hemrabajo realizado contraunafuerzagravitator elásticasóepende delriacióe posicióro yectoria concretamentlcanzae- vosición. Lerzas dedichascaracterísticaesstásociada camp fuerzasconservativosseeáran importan- cere fuerzascuyafuerzae oor- 1 Optativo. 154 CINÉTICA DEl PUNTO MATERIAL (al N F 1 \~I I~ F2 F=kx W = m g U l -2 = t:J.T (b l Figura 3.7 co . El camino seguido entre dichas posiciones e x tremas carece de importancia en el cálculo de ~ V g y ~ V e. Obsérvese que la ec uaci ón 3.17 puede escribirse otra vez en la forma (3.17a) Para aclarar más la dif erencia entre de las ecuaciones 3 .11 y 3.17, en la figura 3.7 se representa una partícula de masa m obligada a descri­ bir una trayectoria fija bajo la acción de las fuerzas Fl y F 2 , la fuerza gravitatoria W = m g , la fuerza F del resorte y la reacción N . En la parte b de la figura se pre­ senta el diagrama para sólido libre de la partícula aislada y se calcula el trabajo de la s fuerzas F 1 , F 2 , la del resorte F = kx para el intervalo de movimiento en cuestión, es decir, desde A hasta B, trabajo que se iguala, mediante la ecua­ ción 3 .11, a la variación de energía cinética ~T. La reacción de ligadura N es normal a la trayectoria y no trabaja . En la parte c de la figura se ilustra el otro procedimiento y el resorte se inclu y e como parte del sistema. El trabajo de Fl y F 2 durante el intervalo es el término U'l-2 de la ecuación 3.17 y en el segundo miembro de la ecuación figuran las variaciones de las energías potenciales gra­ vitatoria y elástica . Adviértase que, con el primer método, el trabajo realizado por F = kx podría requerir una integración algo molesta al tener en cuenta las variaciones en módulo y dirección de F conforme la partícula se despla z a desde A hacia B. Sin embargo, con el segundo método sólo harían falta las longitudes inicial y final del resorte para calcular ~ V e ' lo cual simplifica notablemente los cálculos . Para un sistema de partícula
```

#### [F4] Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009) - pagina 456

- Ruta: `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf`
- Chunk: `bib-c9401bd9a6885a50:p456:c0`
- Requiere OCR: `False`
- Marcas de calidad: ninguna

```text
433 l a) l D l x 5 0 m g F 5 k D l m g F 5 k (D l 2 x ) l x D l 2 x Un resorte colgante que obedece la ley de Hooke b) Cuerpo suspendido del resorte. Está en equilibrio cuando el resorte está estirado lo suficiente como para que la fuerza hacia arriba del resorte tenga la misma magnitud que el peso del objeto. c) Si el cuerpo se mueve con respecto al equilibrio, la fuerza neta sobre él será proporcional a su desplazamiento. Las oscilaciones son las de un MAS. Un cuerpo se adhiere a un resorte colgante. F 5 k D l m g D l Un resorte que obedece la ley de Hooke Se coloca un cuerpo en la parte superior del resorte, y está en equilibrio cuando la fuerza hacia arriba ejercida por el resorte comprimido es igual al peso del cuerpo. Si el peso m g comprime el resorte una distancia D l, la constante de fuerza es k 5 m g > D l y la frecuencia angular para un el cuerpo estuviera suspendido del resorte (véase la ﬁgura 13.17). v5 " k / m esto es, una fuerza total hacia abajo de magnitud kx debajo de la posición de equilibrio, hay una fuerza total hacia arriba de magnitud kx . En ambos casos, hay una fuerza de restitución de magnitud kx. en movimiento vertical, oscilará en MAS con la misma frecuencia angular que si fue- horizontal. El único cambio real es que la posición de equilibrio x 5 0 ya no corres- ponde al punto donde el resorte no está estirado. Las mismas ideas son válidas cuan- do un cuerpo con peso m g se coloca sobre un resorte compresible (ﬁgura 13.18) y lo comprime una distancia D l. v5 " k / m . Los amortiguadores de un automóvil viejo con masa de 1000 kg están gastados. Cuando una persona de 980 N se sube lentamente al auto en su centro de gravedad, el auto baja 2.8 cm. Cuando el auto, con la per- sona a bordo, cae en un bache, comienza a oscilar verticalmente en MAS. Modele el auto y la persona como un solo cuerpo en un solo re- sorte, y calcule el periodo y la frecuencia de la oscilación. La situación es similar a la de la ﬁgura 13.18. La compresión del resorte cuando se agrega el peso adi- cional nos da la constante de fuerza, que podemos usar para obtener el periodo y la frecuencia (las incógnitas). Cuando la fuerza aumenta en 980 N, el resorte se compri- me otros 0.028 m, y la coordenada x del auto cambia en 2 0.028 m. Por lo tanto, la constante de fuerza efectiva (incluido el efecto de toda la suspensión) es k 52 F x x 52 980 N 2 0.028 m 5 3.5 3 10 4 kg /s 2 La masa de la persona es w > g 5
```

#### [F5] Mecanica para Ingenieros, Dinámica (J.L Meriam)-Cinematica -Dinamica - solido rigido - 3° Edición - pagina 251

- Ruta: `Bibliografía/Mecanica para Ingenieros, Dinámica (J.L Meriam)-Cinematica -Dinamica - solido rigido - 3° Edición.pdf`
- Chunk: `bib-63ebd560dee7e28e:p251:c0`
- Requiere OCR: `False`
- Marcas de calidad: ninguna

```text
n el la d m antesdroyeaciespreciar las pérdidanergía cular (a)stante recuperadorak poo delonge stica, (b)ocidad máxima v Olax qulcane ensucaíday(e)suacele- racióáxima a max . Eoeatarse como unrtí- culujetl extree lacuerda. 3.339 Elsatéliteeircular Al satélita elíp- ticaBcolis srustan e C.sae amboguales, hallarlaxima hmax deie- sultante. Resp.hmax = 1438km 3.340 presenta nuevamentl automóvil depruebade choeema 2.30a determine laveloci- e impace 38,9km/h. asa ehículo esde 1100kgYse delante aplastax=0,8m,calculaa fuerzamediaFmed quesmo ejtl obstáculodu- rantacastáculo nosemueve, Fmed no trabaja.Coera aproximació análisinsideramos quvil estácompuee artes cos indi- cadasracta, demasag, semueve 0,8ran- l choqua dleracióedia de8g.Laparte acordeonada tieneuname u cent masalle- vaunadesaceleracióe 4g.HallarFmed analizanada parte poparad determinaa pérdidadnergía !lEdurantl choque. ==~.-3~S~,9-km/h "--- 6_5_0_kg 1 450kg \O,S.\ Sg 4g 3.341 Eloego a ecreativa espro- yecartícula demodo quntror egujero E.Cuando mprime elresorteyuelpentinamente, lapartícula eslanzadaistau lilamo rugosoBe, doay oeficiente derozamientinético J.1eEne toDartícula-onvierte ectil. Hallaompre- sión(5deesorte necesariaparaa partículaentn el A *O \---d-\ ----",¡E 1 Agujero .341 225 de 44 m antes de ser proyectado hacia aHiba. Despreciar las p érd idas de energía y calcular (a) la constante recuperadora k por metro de longitud de la cuerda elástica, (b) l a velocidad máxima v m ax que alcanza el hombre en su caída y (e) su acele­ ración máxima a m ax ' El hombre puede tratarse como un a partí­ cula sujeta al extremo de la cuerda. Figura problema 3.338 3.339 El satélite en órbita circular A y el satélite e n órbita elíp­ tica B colisionan y se incrustan en el punto C. Si las masas de ambos son igual es, hallar la altitud má x ima h max de la órbita re­ su ltant e. Resp. h m ax = 1438 km Figura problema 3.339 3.340 Se representa nuevamente el automóvil de prueba de choques del problema 2.30 y se ha determinado que la veloci­ dad de impacto era de 38,9 km/h. Si la masa del vehículo es de 1100 kg Y su parte d e lantera se aplasta x = 0,8 m, calcular la fuer za media F med que el mi s mo ejerce contra el obstáculo du­ rante el impacto. Dado que el obstáculo no se mueve, F m e d no trabaja. Como primera aproximación al análisis, consideramos que el automóvi l está compuesto d e dos partes como l as indi­ cadas. La part e intacta , d e masa 650 kg, se mueve 0 ,8 m duran­ te e l choque con una desaceleración media de 8g. La parte acorde ona da tiene una masa de 450 kg Y s u centro de ma sa lle­ va una desaceleración de 4g. Hallar F med analizando cada parte por separado y determinar la pérdida de energía !'lE durant e el choque. -- 38,9 km/h 650kg I 450 kg 8g 4 g Figura problema 3.340 3.341 El objeto del juego de una máquina recreativa es pro­ yectar la partícula de modo que entre por el agujero E. Cuando se comprime el resorte y se s uelta repentinamente, la partícula es lan za da por la pista, que es lisa salvo e l tramo r ugo so Be, donde hay un coeficiente de ro za miento cinético /l e ' En el pun­ to D la partículase convierte en un proyectil. Hallar la compre­ sió n 8 del resorte nece sar ia para que la partícula e ntr e en el ;>1- Dr-d~1 Zo na ru gosa )l e Figura problema 3.341 --- -----, ¡ E 1 Agujero 225
```

## Periodo Oscilacion

**Pregunta:** ¿De qué depende el período de oscilación de un resorte?  
**Tiempo:** 7.29 s  
**Modelo:** qwen2.5:7b  
**Fragmentos recuperados:** 5

### Respuesta completa de Qwen

La documentación disponible no permite responder con precisión a la pregunta sobre el periodo y la frecuencia de un oscilador de resorte. Sin embargo, se pueden extraer algunas afirmaciones relevantes sobre el periodo y la frecuencia de un oscilador de resorte:

[F4] Se menciona que la frecuencia propia del oscilador de resorte es 4 Hz en el problema 3.14, lo que sugiere que el periodo T = 1/f = 1/4 = 0.25 segundos.

[F4] Se define el periodo T como el tiempo que tarda un ciclo, y la frecuencia f como el número de ciclos por segundo, con la relación f = 1/T.

No obstante, la documentación no proporciona una definición explícita o fórmula general para calcular el periodo o la frecuencia de un oscilador de resorte, ni da información suficiente para responder a la pregunta de manera definitiva.

### Referencias y contexto completo enviado

#### [F1] Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009) - pagina 448

- Ruta: `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf`
- Chunk: `bib-c9401bd9a6885a50:p448:c0`
- Requiere OCR: `False`
- Marcas de calidad: ninguna

```text
425 m F 5 6.0 N a) b) x 5 0 x 5 0.020 m m 5 0.50 kg x x 5 0 x 5 0.030 m x a) La fuerza ejercida el resorte (indicada por el vector F ) tiene componente x : F x 51 6.0 N. La fuerza ejercida por el resorte tiene componente x : F x 52 6.0 N. b ) Un deslizador b ) Usando m 5 0.50 kg en la ecuación (13.10), vemos que La frecuencia f es El periodo T es el recíproco de la frecuencia f: El periodo por lo regular se da en “segundos”, en vez de en “segundos por ciclo”. La amplitud de la oscilación es de 0.020 m, la distancia a la derecha que movimos el deslizador conectado al resorte antes de soltarlo. No necesitamos esta información para calcular la frecuencia esas cantidades depende de la amplitud. T 5 1 f 5 1 3.2 ciclos /s 5 0.31 s f 5 v 2 p 5 20 rad /s 2 p rad /ciclo 5 3.2 ciclos /s 5 3.2 Hz v5 Å k m 5 Å 200 kg /s 2 0.50 kg 5 20 rad /s Aún necesitamos obtener el desplazamiento x en función del tiempo para un oscilador armónico. La ecuación (13.4) para un cuerpo en movimiento armónico simple en el eje x es idéntica a la ecuación (13.8), para la coordenada x del punto de referencia en que la ecuación (13.5), x 5 A cos u , describe la coordenada x para ambas situaciones. Si, en t 5 0, el fasor OQ forma un ángulo f (letra griega phi) con el eje 1 x , entonces en cualquier instante posterior t u5v t 1f . Sustituimos esto en la ecuación (13.5) para obtener el caso especíﬁco en que f5 0. El desplazamiento x es una función periódica de t, términos de la función seno en vez de coseno, usando la identidad cos a5 sen( a1 p > 2). En el movimiento armónico simple, la posición es una función periódica senoi- dal del tiempo. Hay muchas otras funciones periódicas, pero ninguna tan continua y simple como una función seno o coseno. El valor del coseno siempre está entre 2 1 y 1, así que en la ecuación (13.13) x siempre está entre 2 A y A . Esto conﬁrma que A es la amplitud del movimiento. El periodo T es lo que tarda un ciclo de oscilación (ﬁgura 13.9). La función coseno se repite cada vez que la cantidad entre paréntesis de la ecuación (13.13) aumenta en 2 p radianes. Si comenzamos en t 5 0, el tiempo T para completar un ciclo está dado por v T 5 Å k m T 5 2 p o bien, T 5 2 p Å m k v5 " k / m . x 5 A cos ( v t 1f ) (desplazamiento del MAS) v5 " k / m . 1 2 x 2 T O t x máx
```

#### [F2] Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009) - pagina 455

- Ruta: `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf`
- Chunk: `bib-c9401bd9a6885a50:p455:c0`
- Requiere OCR: `False`
- Marcas de calidad: ninguna

```text
432 Movimiento periódico El choque dura muy poco, así que poco después el bloque y la masilla vamente cinética, pero menor que antes del choque: Dado que E 2 A 2 es la amplitud después del cho- que, tenemos Cuanto mayor sea la masa m de la masilla, menor será la amplitud ﬁnal. Determinar el periodo de oscilación después del choque es la parte T 2 5 2 p Å M 1 m k A 2 5 A 1 Å M M 1 m 1 2 kA 2 2 5 1 M M 1 m 2 1 2 kA 1 2 1 2 kA 2 2 , 5 1 M M 1 m 2 E 1 E 2 5 1 2 1 M 1 m 2 v 2 2 5 1 2 M 2 M 1 m v 1 2 5 M M 1 m 1 1 2 M v 1 2 2 b reposo (ﬁgura 13.16b). La componente x del momento lineal es cero almacenada en el resorte, por lo que la adición de la masa extra no afecta y la amplitud después del choque es la misma ( A 2 5 A 1). El periodo sí cambia al agregarse la masilla; su valor no depende de cómo se agregó T 2 es el mismo que obtuvimos en el inciso a ), a ) pero no en el b )? La diferencia es que, en el inciso a ), la masilla se desliza contra el blo- ción cinética. T 2 5 2 p " 1 M 1 m 2 /k . E 2 5 E 1 5 1 2 kA 1 2 a de un sistema masa-resorte en oscilación, ¿en qué factor se debe aumentar la amplitud? b v) no cambia. ❚ " 4 " 2 5 1.414; 2 5 1.189; " 4 " 2 5 1.414; 2 5 1.189. Aplicaciones del movimiento armónico simple Hasta ahora, hemos examinado globalmente una situación donde hay movimiento ar- mónico simple (MAS): un cuerpo conectado a un resorte ideal horizontal. No obstante, el MAS puede presentarse en cualquier sistema donde haya una fuerza de restitución que sea directamente proporcional al desplazamiento con respecto al equilibrio, según la ecuación (13.3), F x 52 kx . Dicha fuerza se origina de diferentes maneras y en dis- tintas situaciones, por lo que debe determinarse la constante de fuerza k para cada ca- so, examinando la fuerza neta que actúa sobre el sistema. Una vez hecho esto, es fácil calcular la frecuencia angular v , la frecuencia f y el periodo T lor de k ideas para examinar varios ejemplos de movimiento armónico simple. Suponga que colgamos un resorte con constante de fuerza k (ﬁgura 13.17a) y suspen- demos de él un cuerpo de masa m . Las oscilaciones ahora serán verticales; ¿seguirán siendo MAS? En la ﬁgura 13.17b, el cuerpo cuelga en reposo, en equilibrio. En esta posición, el resorte se estira una distancia D l apenas suﬁciente para que la fuerza ver- tical k
```

#### [F3] Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009) - pagina 469

- Ruta: `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf`
- Chunk: `bib-c9401bd9a6885a50:p469:c0`
- Requiere OCR: `False`
- Marcas de calidad: ninguna

```text
Términos clave movimiento armónico simple (MAS), 421 oscilador armónico, 422 círculo de referencia, 423 423 ángulo de fase, 426 péndulo simple, 436 péndulo físico, 438 amortiguamiento, 440 oscilación amortiguada, 440 amortiguamiento crítico, 441 sobreamortiguamiento, 441 subamortiguamiento, 441 fuerza impulsora, 442 oscilación forzada, 442 frecuencia angular natural, 442 resonancia, 443 (v x 5 0), ya que la fuerza ejercida por el resorte depende de si se comprime o se estira, y con qué distancia. Esto explica las respuestas a ) a e ). Si la aceleración es cero como en f), la fuerza total también debe ser cero y por ello el resorte debe estar relajado: x 5 0. Respuestas: a ) A + 0.10 m, f * 0; b ) A + 0.10 m, f + 0 En ambas situaciones, la velocidad v 0x inicial ( t 5 0) no es cero, de mane- mayor que la coordenada inicial x 0 5 a ) x 0 y v 0x b ) x 0 es positivo y v 0x Respuestas: a) iii), b) v) en un factor de 2, la amplitud A debe aumentar en un fac- frecuencia. Respuesta: i) El periodo de oscilación de un cuerpo de masa m unido a un resorte colgante de constante de fuerza k está dado por T 5 2 p " m /k , la misma expresión que para el cuerpo unido al resorte " 2 . E 5 1 2 kA 2 2 v 0x /v x 0 . 0 f. 0. 2 v 0x /v x 0 , 0 f, 0. 2 v 0x /v x 0 2 v 0x /v x 0 f5 arctan 1 2 v 0x /v x 0 2 , A 5 " x 0 2 1 1 v 0x 2 /v 2 2 movimiento periódico (oscilación), 419 desplazamiento, 420 fuerza de restitución, 420 amplitud, 420 ciclo, 420 periodo, 420 frecuencia, 420 420 ? Ninguna de ellas; el reloj seguiría marcando correctamente el tiempo. Si la masa de su varilla es despreciable, el péndulo es simple y su pe- riodo es independiente de la masa [véase la ecuación (13.34)]. Si se in- cluye la masa de la varilla, se trata de un péndulo físico. Un aumento de su masa m al doble también duplica su momento de inercia I, así que la razón I> m (13.39)] sigue siendo el mismo. Evalúe su comprensión Respuestas: a ) x * 0, b ) x + 0, c ) x * 0, d ) x + 0, e ) x 5 0, f) x + 0 La ﬁgura 13.2 muestra que la componente x de la fuerza total F x y la aceleración a x son ambas positivas cuando x , 0 (así que el cuerpo se desplaza hacia la izquierda y el resorte se comprime); mientras que F x y a x son ambas negativas cuando x . 0 (así que el cuerpo se desplaza hacia la derecha y el resorte se estira). Por lo tanto, F x y a
```

#### [F4] Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009) - pagina 443

- Ruta: `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf`
- Chunk: `bib-c9401bd9a6885a50:p443:c0`
- Requiere OCR: `False`
- Marcas de calidad: ninguna

```text
420 Movimiento periódico Lo más sencillo es definir nuestro sistema de coordenadas con el origen O en x es la componente x del desplazamiento del cuerpo con respecto al equilibrio y también es el cambio de longitud del resorte. La componente x de la fuerza que el resorte ejerce sobre el cuerpo es F x y la componente x de la aceleración, a x, está dada por a x 5 F x> m . La ﬁgura 13.2 muestra el cuerpo para tres desplazamientos diferentes del resorte. Siempre que el cuerpo se desplaza con respecto a su posición de equilibrio, la fuerza del resorte tiende a regresarlo a dicha posición. Llamamos a una fuerza con esa carac- terística titución que tiende a regresar el sistema a la posición de equilibrio. Analicemos cómo se da la oscilación en este sistema. Si desplazamos el cuerpo a la derecha hasta x 5 A y lo soltamos, la fuerza total y la aceleración son hacia la iz- quierda. La rapidez aumenta al aproximarse el cuerpo a la posición de equilibrio O . Cuando el cuerpo está en O , la fuerza total que actúa sobre él es cero (ﬁgura 13.2b) pero, a causa de su movimiento, la posición de equilibrio. En el otro lado de esa posición, el cuerpo se sigue moviendo a la izquierda, pero la fuerza total y la ace- leración son a la derecha (ﬁgura 13.2c); por lo tanto, la rapidez disminuye hasta que el cuerpo se detiene. Después demostraremos que, con un resorte ideal, el punto en el que se detiene es x 52 A el equilibrio, y se detiene en el punto inicial x 5 A , listo para repetir todo el proceso. nica del sistema, el movimiento se repetirá eternamente; la fuerza de restitución tirará perpetuamente del cuerpo hacia la posición de equilibrio, la cual, el cuerpo rebasará una y otra vez. En situaciones diferentes, la fuerza puede depender de diversas maneras del des- plazamiento x con respecto al equilibrio, pero habrá oscilación si la fuerza es de y tiende a volver el sistema al equilibrio. Amplitud, periodo, frecuencia y frecuencia angular tipo: La amplitud del movimiento, denotada con A , es la magnitud máxima del despla- 0x 0 y siempre es posi- tiva. Si el resorte de la ﬁgura 13.2 es ideal, el rango global del movimiento es 2 A . La unidad de A en el SI es el metro. Una vibración completa, o ciclo (de ida y vuelta), digamos de A a 2 A y de regreso a A , o bien, de O a A, regresan- do por O hasta 2 A y volviendo a O . El movimiento de un lado al otro (digamos, de 2 A a A ) es medio ciclo. El periodo , T , es el tiempo que tarda un ciclo, y siempre es positivo. La unidad del periodo en el SI es el segundo, aunque a veces se expresa como “segundos por ciclo”. La , f, es el número
```

#### [F5] 32-PmasCapitulo III 064-067 - pagina 3

- Ruta: `Bibliografía/Ochoa.rar!/32-PmasCapitulo III 064-067.pdf`
- Chunk: `bib-717a7a2553717eaf:p3:c0`
- Requiere OCR: `False`
- Marcas de calidad: ninguna

```text
Ochoa Aplicaciones del Tercer Módulo Facultad de Ingeniería - Universidad Nacional de La Pampa Problema 3.14 Un oscilador de resorte con una frecuencia propia de 4 Hz para el movimiento no amortiguado, y un factor de amortiguamiento h=0,2 está montado sobre una estructura que vibra con frecuencia f variable. Si la amplitud de la vibración absoluta del oscilador no debe superar el doble de la de la estructura, especificar el intervalo aceptable de frecuencia de vibración de la estructura. Problema 3.15 Un sismógrafo tiene una masa de 250 gramos y está soportado por un resorte de constante 36 N/cm. Si la desviación de la masa relativa al armazón es de 0,52 cm cuando el instrumento se encuentra sobre un aparato que vibra en la misma dirección con frecuencia de 5 Hz, Determinar la máxima aceleración del aparato. Problema 3.16 Determinar la amplitud de vibración vertical de un remolque montado sobre resortes cuando avanza a una velocidad de 25 Km./hora sobre el camino sinuoso cuyo contorno puede asimilarse a una sinusoide. El remolque pesa 500 kilogramos, la masa de las ruedas es despreciable y los resortes del remolque se comprimen 3 mm por cada carga de 75 kilogramos. Suponiendo que las ruedas están en contacto con el camino en todo momento y despreciando el amortiguamiento, determinar a que velocidad es máxima la vibración del remolque. Problema 3.17 La frecuencia del oscilador masa resorte mostrado en la figura es de 4 Hz. Si el oscilador se sumerge en un recipiente con aceite, su frecuencia propia de oscilación se reduce a 3,8 Hz. ¿Cuál es el decrecimiento logarítmico de las vibraciones de la masa en tal situación? Suponiendo que el recipiente oscila en la dirección del movimiento con frecuencia angular w y con amplitud de 0,09 centímetros, ¿Cuál debe ser el rango de frecuencias prohibidos si se quiere que la masa no oscile respecto del recipiente con amplitud mayor al doble de la amplitud con que vibra el recipiente? Problema 3.18 La masa de 40 kg. de la figura se encuentra soportada por resortes a la base de hormigón que vibra en dirección vertical con pequeña amplitud. Si cada uno de los cuatro resortes tiene una contante elástica de 80 N/cm, determinar la gama de frecuencia de oscilación que provocaría para la masa m una amplitud de oscilación mayor del doble de la amplitud de oscilación con que vibra la base. Problema 3.19 Un instrumento de 50 kg. se apoya en cuatro resortes de 7500 N/m cada uno. Si la base sobre la que descansa el conjunto está sometida a un movimiento armónico en metros dado por: XB = 0,002cos(50t). Determinar la amplitud estacionaria del movimiento del instrumento si el amortiguamiento es despreciable. - 7.66 -
```

## Energia Mecanica

**Pregunta:** ¿Qué es la energía mecánica y cómo se relaciona con las energías cinética y potencial?  
**Tiempo:** 43.66 s  
**Modelo:** qwen2.5:7b  
**Fragmentos recuperados:** 5

### Respuesta completa de Qwen

La energía mecánica es la suma de las energías cinética y potencial de un sistema [F1, F3, F5]. Según el documento [F1], se ilustra que la energía mecánica del carrito en un punto A es la suma de las energías cinética, potencial y elástica. Asimismo, el documento [F3] menciona que la energía mecánica del sistema no cambia mientras se conserva, y que la energía mecánica es la suma de la energía cinética y la energía potencial.

Además, la energía mecánica puede ser conservada en un sistema, lo que significa que la suma de la energía cinética y la energía potencial permanece constante, a menos que se realice trabajo por fuerzas no conservativas [F2, F5]. Esto se expresa matemáticamente como \( E = T + F \), donde \( E \) es la energía mecánica, \( T \) es la energía cinética y \( F \) es la energía potencial [F2, F5].

No puedo responder con la documentación recuperada sobre cómo se relaciona específicamente la energía mecánica con las energías cinética y potencial en situaciones particulares, ya que la documentación proporcionada se centra más en la definición y la conservación de la energía mecánica en general.

### Referencias y contexto completo enviado

#### [F1] libroejercicios - pagina 133

- Ruta: `Bibliografía/libroejercicios.pdf`
- Chunk: `bib-dea1bead6315754b:p133:c0`
- Requiere OCR: `False`
- Marcas de calidad: palabras_muy_cortas

```text
Ejemplo PUNTO A. DATOS EN EL DIBUJO. La energía mecánica del carrito en A va a ser la suma de las energías cinética, potencial y elástica. Hago la cuenta: Î E MA = ½ 2 kg . (1 m/s) 2 + 2 kg . 10 m/s 2 . 1 m Î E MA = 21 Joule Otro ejemplo EN EL PUNTO A : La energía mecánica en A va a ser: E MA = E CA + E PA EN EL PUNTO B : E MB = E CB + E PB 0 ( ← No hay resortes ) E mA = E cA + E pA + E EA m A 2 m s () 2 1 M B 2 2 m s M A ⇒= B 2 2 B 1 m B ⇒ E = m ⋅ v + m ⋅ g ⋅ h
```

#### [F2] 33-EnergiaMecanica 101-111 - pagina 5

- Ruta: `Bibliografía/Ochoa.rar!/33-EnergiaMecanica 101-111.pdf`
- Chunk: `bib-0e691243d2a495ff:p5:c0`
- Requiere OCR: `False`
- Marcas de calidad: ninguna

```text
Ochoa Campo Conservativo y Energía Mecánica Facultad de Ingeniería - Universidad Nacional de La Pampa 3.08ENERGÍA MECÁNICA. Consideremos el caso de una partícula que se desplaza a lo largo de una determinada trayectoria entre dos puntos (A) y (B) de la misma, sometida a la interacción con diferentes campos de fuerza conservativos, cuya resultante identificaremos con (FC) y no conservativos, cuya resultante identificaremos con (FNC), teniendo en cuenta el teorema de las fuerzas vivas resulta que: ( ) B A B òA FC+FNC ×dr=T-T    Que sin lugar a dudas podemos expresar como: B A B A NC B òAFC×dr+òF ×dr=T-T     3.31 Donde la primera integral puede expresarse en términos de la función energía potencial asociada con la resultante de las fuerzas de interacción, que en vista de su definición no es otra cosa que la suma de las funciones energías potenciales asociadas con cada uno de los campos de fuerza conservativos involucrados, o sea. F=åF i i Puesto que: ò òå ÷× =åò × =-å(F -F ) ø ö ç è æ × = i iB iA i B A Ci B A i Ci B AFC dr F dr F dr      Con lo que: ( ) B B i i iB iA B AFC dr ÷=-F -F ø ö ç è æ ò × =-åF -åF   De (3.31) resulta: ( )( ) B A B B B òAFNC×dr=T-T +F -F   Que podemos expresar como: ( )( ) B B A B B òAFNC×dr=T+F -T +F   Definiendo la Energía Mecánica del Sistema, como: E=T+F Es claro que la anterior puede expresarse en términos de esta nueva magnitud, como: B A B òAFNC×dr=E -E   Que nos muestra a los cambios observados en la energía mecánica de un sistema directamente vinculados con el trabajo mecánico que realizan las fuerzas no conservativas a que esta sometido. Conservación de la Energía Mecánica. De la expresión anterior resulta que, si el trabajo realizado por la resultante de las fuerzas no conservativas es nulo o bien si la totalidad de las fuerzas actuantes son conservativas, entonces la energía mecánica del sistema permanecerá constante e igual al valor que tenia en el instante inicial. E=E Conclusión que en adelante reconoceremos como Teorema de Conservación de la Energía Mecánica y que como veremos es una herramienta sumamente útil para la resolución de problemas. Finalmente, es oportuno destacar que la conservación de la energía mecánica de ninguna manera implica la conservación de las energías, cinética y potencial. Implica la conservación de la suma de ambas magnitudes y por lo tanto un incremento en una de ellas deberá estar acompañado necesariamente de una disminución en la restante y viceversa. Ejemplo. Consideremos el caso de una partícula que es lanzada verticalmente desde un punto a una distancia (ro) del centro de la tierra con una velocidad (Vo) inferior a la velocidad de escape. - 3.105 -
```

#### [F3] libroejercicios - pagina 227

- Ruta: `Bibliografía/libroejercicios.pdf`
- Chunk: `bib-dea1bead6315754b:p227:c0`
- Requiere OCR: `False`
- Marcas de calidad: ninguna

```text
ENERGÍA POTENCIAL ELÁSTICA a cinética. Pero si suelto el resorte... Esa Energía Cinética que adquirió el cuerpo fue entregada por el resorte. La fórmula que me da la energía almacenada ) es: La E m el tipo tiene en ese momento. Es decir: energía mecánica del sistema no cambia mientras ella conservar. Es decir, la ener Energía mecánica que había al E mec Final = E RESORTE COMPRIMIDO Ahora el cuerpo sale despedido con una velocidad V. E Elás. = ½ K ⋅ ( ∆ x) 2 almacenada en un resorte. Constante del resorte. acumulada en el resorte. E m = E c + E p + E E Energía mecánica.
```

#### [F4] 52-SisCposPuntuales II 092-102 - pagina 4

- Ruta: `Bibliografía/Ochoa.rar!/52-SisCposPuntuales II 092-102.pdf`
- Chunk: `bib-56174f8d2747ebf7:p4:c0`
- Requiere OCR: `False`
- Marcas de calidad: ninguna

```text
Ochoa Dinámica para un Sistema de Cuerpos Puntuales Facultad de Ingeniería - Universidad Nacional de La Pampa Energía Mecánica. Consideraremos ahora el conjunto de fuerzas externas e internas conservativas a que pudiera encontrarse sometido un sistema, o sea, el conjunto de fuerzas externas que satisfacen relaciones del tipo: i i B òAFi×dr=-DF   Y de fuerzas internas, que satisfacen relaciones del tipo: i ij B òAfij×dr=-DF   Donde las funciones escalares recientemente indicadas están asociadas con cada una de las fuerzas internas conservativas a que pudiera estar sometida cada una de las partículas que integran nuestro sistema, con lo que podemos definir un conjunto de funciones energía potencial, asociadas con éstos mecanismos de interacción, mediante expresiones del tipo: F =åF j ij int i Teniendo en cuenta lo indicado anteriormente, podremos definir una función energía potencial externa asociada con la totalidad de dichas fuerzas conservativas, como: Fext=åFi 5.32 Y una función energía potencial asociada con el conjunto de fuerza internas conservativas, dada por: F = åF int int i 2 1 5.33 Donde el factor (1/2) debe ser incluido ya que de lo contrario se contabilizaría en dos oportunidades la misma función bajo el signo de la sumatoria. Con lo mencionado anteriormente, definiremos a la Energía Mecánica del sistema como: E=T+Fext+Fint 5.34 Donde el primer término es la energía cinética del sistema definida por (5.20) o bien por (5.21) y los restantes corresponden a los expresados mediante (5.32) y (5.33) respectivamente. Procediendo de manera semejante a lo realizado para el caso de una partícula y teniendo en cuenta las últimas conclusiones y definiciones desarrolladas en esta oportunidad, se puede verificar fácilmente que las variaciones observadas en la energía mecánica de un sistema estarán directamente vinculadas con el trabajo mecánico realizado por las fuerzas externas e internas, no conservativas lo que formalmente podemos expresar mediante la igualdad siguiente: DE=Fext-nc+Fint-nc 5.35 De donde resulta que, si el trabajo mecánico realizado por las fuerzas externas e internas, no conservativas, fuera nulo o bien si la totalidad de las fuerzas a que estuviera sometido el sistema fueran conservativas, la energía mecánica del mismo permanecerá constante. Ejemplo (5.5) Estamos ahora en condiciones de retomar la situación planteada en el ejemplo (5.2). En aquella oportunidad y teniendo en cuenta la conservación del vector cantidad de movimiento del sistema obtuvimos que las velocidades de ambos cuerpos al finalizar su interacción con el resorte, que originalmente se encontraba comprimido, deberían ser tales que: 2 2 1 1 v m m v   =- Teniendo en cuenta que hemos supuesto al sistema libre de rozamiento es claro entonces que la resultante de las fuerzas externas es nula y por lo tanto el trabajo realizado por las mismas también lo será. Puesto que además las fuerzas internas a que está sometido resultan de la interacción con el - 5.95 -
```

#### [F5] 63-SisRigMovPlano III 136-143 - pagina 6

- Ruta: `Bibliografía/Ochoa.rar!/63-SisRigMovPlano III 136-143.pdf`
- Chunk: `bib-a8eaefb2c2f1c8ee:p6:c0`
- Requiere OCR: `False`
- Marcas de calidad: ninguna

```text
Ochoa Sistemas Rígidos Animados de un Movimiento Plano Facultad de Ingeniería - Universidad Nacional de La Pampa Donde: Rw 2 1 vc= Con lo que: g Rw 8 1 D d 2 2 m =  En este caso la variación observada en la energía cinética de spin, como consecuencia de la presencia de la fuerza de rozamiento dinámica será tal que: I(w w) 2 1 fRd 2 2 ò q= c - De donde, luego de haber recorrido la distancia necesaria para iniciar el rodamiento sin deslizamiento, el ángulo barrido por una recta perpendicular al eje de rotación vendrá dado por: mgR Iw 8 3 d 2 c m q=  Que para el caso de una esfera nos queda: g Rw 16 3 d 2 m q=  Con lo que: D 2 3 Rq= Y por lo tanto: Rq>D Como era de esperar si tenemos en cuenta el deslizamiento de la esfera sobre la superficie horizontal. Finalmente, la energía disipada durante el recorrido puede determinarse como diferencia de la energía cinética entre el instante inicial y el instante a partir del que se inicia la rodadura sin deslizamiento. Como aplicaciones del tema en consideración, se recomienda trabajar con las simulaciones a las que puede acceder mediante los archivos Rototraslacion-3.htm, Discos.htm y Rotacion-2.htm 6.07 CONSERVAC IÓN DE LA ENERGÍA MECÁNICA Considerando un sistema rígido sometido a un conjunto de fuerza conservativas y no conservativas, el trabajo mecánico realizado sobre dicho sistema estará relacionado con los cambios observados en su energía cinética, por: Wcons+Wno cons=DT Teniendo en cuenta que al trabajo mecánico realizado por las fuerza conservativas lo podemos expresar en término de la variación observada en una función escalar de las coordenadas del punto, a la que continuaremos identificando como función energía potencial, de las anteriores resulta que el trabajo mecánico realizado por el conjunto de fuerzas no conservativas estará relacionado con los cambios observados en la energía cinética y potencial del sistema, mediante: DT+DF=Wno cons Definiendo la energía mecánica del sistema como la suma de las energías cinética y potencial, es claro que la anterior puede expresarse en término de ésta magnitud, como: DE=Wno cons Donde, como siempre: E=T+F Que, en el caso de un movimiento plano, podemos expresar como: - 6.141 -
```

## Frecuencia Angular

**Pregunta:** ¿Cómo se obtiene la frecuencia angular de un movimiento oscilatorio?  
**Tiempo:** 6.33 s  
**Modelo:** qwen2.5:7b  
**Fragmentos recuperados:** 5

### Respuesta completa de Qwen

La documentación disponible no permite responder directamente a la pregunta sobre la relación entre las frecuencias naturales de oscilación de una estructura y las frecuencias típicas de terremotos, ni sobre si la estructura debe tener mucho o poco amortiguamiento. Sin embargo, se puede inferir que en una región de alta sismicidad, es importante que las frecuencias naturales de la estructura no coincidan con las frecuencias típicas de los terremotos para evitar resonancias perjudiciales. Esto se menciona implícitamente en el ejercicio 13.4, donde se pregunta sobre la relación entre las frecuencias naturales de oscilación de una estructura y las frecuencias típicas de terremotos, pero no se proporciona una respuesta directa en los documentos.

### Referencias y contexto completo enviado

#### [F1] 21-OscilaLibres 058-066 - pagina 8

- Ruta: `Bibliografía/Ochoa.rar!/21-OscilaLibres 058-066.pdf`
- Chunk: `bib-f75466805059de6b:p8:c0`
- Requiere OCR: `False`
- Marcas de calidad: ninguna

```text
Ochoa Interacción Elástica y Oscilaciones Libres Facultad de Ingeniería - Universidad Nacional de La Pampa Con lo que las conclusiones logradas en aquella oportunidad serán válidas para la situación en consideración y por lo tanto la coordenada angular variará en el tiempo según: cos(wt) f=f Donde la frecuencia angular vendrá dada por: L g w= Y por lo tanto la partícula oscilará alrededor de su posición de equilibrio con un período dado por: g L T=2p Siendo interesante destacar que en el tratamiento no se ha considerado la fuerza que resulta de la interacción con la atmósfera, que de considerarse daría lugar a un movimiento oscilatorio con una amplitud decreciente, que será tratado en el próximo volumen. Asimismo es importante mencionar que la solución lograda recientemente es solamente una adecuada aproximación, útil en el tratamiento de algunas situaciones de interés como la que consideraremos en la experiencia virtual que se recomienda posteriormente. Solución General para el Período de un Péndulo Puntual. Considerando nuevamente la ecuación. ÷ f ø ö ç è æ f=- sen L g  Es posible demostrar que en general, el período con el que oscilará el péndulo vendrá dado por: ÷ ø ö ç è æ ÷÷ + + + ø ö çç è æ = p k ............. 64 9 k 4 1 1 g L T 2 2 4 2 1 Donde la constante (k) depende de la amplitud con la que oscila el sistema, según: ÷ ø ö ç è æf = 2 k sen  Con lo que vemos que en general el período de un péndulo dependerá de la amplitud con la oscila alrededor de su posición de equilibrio. Considerando nuevamente aquella situación en la que es válida la aproximación: senf@f De la expresión recientemente obtenida para el período del péndulo, resulta que bajo estas condiciones, la mencionada magnitud vendrá dada por: ÷ ø ö ç è æ ÷÷ + f+ f+ ø ö çç è æ = p ............. 1024 9 16 1 1 g L T 2 2 4 2 1   Que como podemos notar no coincide con la obtenida anteriormente bajo las mismas condiciones, esto es. g L T=2p Motivo por el que cuando la obtuvimos, mencionamos que solo se trataba de una adecuada aproximación al período de un péndulo puntual que oscila con pequeñas amplitudes, ya que cuando la amplitud de la oscilación es tal que el segundo término del desarrollo en serie de potencias es inferior al error con el que deseamos determinaremos el período de las oscilaciones, dicho término y los restantes podrán despreciare y considerar al período dado por la expresión anterior. - 2.65 -
```

#### [F2] Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009) - pagina 447

- Ruta: `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf`
- Chunk: `bib-c9401bd9a6885a50:p447:c0`
- Requiere OCR: `False`
- Marcas de calidad: ninguna

```text
424 Movimiento periódico bien, kg > s 2 , así que k > m está en (kg > s 2 ) > kg 5 s 2 2 en la ecuación (13.10), obtenemos s 2 1 o, mejor dicho, rad > s, porque se trata de una frecuencia angular (recuerde que el radián no es una unidad verdadera). Según las ecuaciones (13.1) y (13.2), la frecuencia f T son (movimiento armónico simple) (movimiento armónico simple) Por la ecuación (13.12), vemos que una masa mayor m , con su mayor inercia, tiene menos aceleración, se mueve más lentamente y tarda más en completar un ciclo (ﬁgu- ra 13.7). En cambio, un resorte más rígido (con mayor constante de fuerza k ) ejerce una mayor fuerza para una deformación x dada, causando una mayor aceleración, ve- locidades más altas y ciclos más cortos. No confunda frecuencia con frecuencia angular Podemos meternos en pro- blemas si no distinguimos entre frecuencia f y frecuencia angular v5 2 p f. La frecuencia nos indica cuántos ciclos de oscilación se dan por segundo; mientras que la frecuencia angular nos dice a cuántos radianes por segundo corresponde esto en el círculo de referencia. Al re- solver problemas, fíjese bien si el objetivo es obtener f o bien v . ❚ miento armónico simple están determinadas solamente por la masa m y la constante de fuerza m y k , el tiempo de una oscilación com- pleta es el mismo, sea la amplitud grande o pequeña. La ecuación (13.3) muestra por qué esto es lógico. Una mayor A implica que la masa alcanza valores mayores de y se somete a fuerzas de restitución mayores. Esto aumenta la rapidez media del cuer- po durante un ciclo completo, lo cual compensa exactamente la necesidad de recorrer una mayor distancia, de modo que el tiempo total es el mismo. En esencia las oscilaciones de un diapasón son movimiento armónico simple; ello implica que siempre vibra con la misma frecuencia, sea cual fuere la amplitud. Esto permite usar el diapasón como estándar para tono musical. Si no fuera por esta carac- terística del movimiento armónico simple, sería imposible hacer que los relojes mecá- nicos y electrónicos que conocemos fueran exactos, o tocar aﬁnadamente la mayoría de los instrumentos musicales. Si encontramos un cuerpo oscilante cuyo periodo sí de- pende de la amplitud, su movimiento no 0x 0 T 5 1 f 5 2 p v 5 2 p Å m k f 5 v 2 p 5 1 2 p Å k m Brazos con masa m grande: frecuencia baja f 5 128 Hz Brazos con masa m pequeña: frecuencia alta f 5 4096 Hz Cuanto mayor sea la masa m de los brazos de un diapasón, más baja será la frecuencia de oscilación y más bajo será el tono del sonido producido por el diapasón. f 5 1 1 / 2 p 2 " k / m Un resorte se monta horizontalmente con su extremo izquierdo ﬁjo. Conectando una balanza de resorte
```

#### [F3] 21-OscilaLibres 058-066 - pagina 2

- Ruta: `Bibliografía/Ochoa.rar!/21-OscilaLibres 058-066.pdf`
- Chunk: `bib-f75466805059de6b:p2:c0`
- Requiere OCR: `False`
- Marcas de calidad: ninguna

```text
Ochoa Interacción Elástica y Oscilaciones Libres Facultad de Ingeniería - Universidad Nacional de La Pampa 2.01FENÓMENOS PERIÓDICOS. Como una adecuada introducción al tema se recomienda correr el video 06-Periodicos.wmv, destinado a ilustrar el comportamiento de sistemas físicos que evolucionan con características que se repiten en el tiempo, en cuyo caso diremos que estamos frente a un fenómeno periódico, que podremos caracterizar mediante parámetros como los que se indican a continuación. Período. Es el tiempo al cabo del cual las magnitudes que caracterizan el estado de un sistema toman nuevamente los mismos valores. Así en el caso de una partícula que se mueve a lo largo de una trayectoria circular con una velocidad de módulo constante, al tiempo que tarda en dar una vuelta completa lo identificamos como el período del movimiento. De la misma manera un cuerpo suspendido a un muelle que es apartado de su posición de equilibrio para luego dejarlo en libertad, oscilará alrededor de dicha posición, en cuyo caso identificaremos al tiempo que tarda en efectuar una oscilación completa como el período de la oscilación. Un vídeo es en realidad una secuencia de fotografías tomadas con intervalos de tiempo muy pequeños para lo cual el obturador de la filmadora esta diseñado de manera que la apertura y cierre del mismo se produce cada un cierto intervalo de tiempo, que reconocemos como período de obturación. Una lámpara de destellos o estroboscópica esta diseñada de manera que produce un corto destello a intervalos de tiempo que podemos prefijar y que reconocemos como período de destellos. Frecuencia. Entenderemos por frecuencia al número de veces que en un segundo las magnitudes que caracterizan el estado de un sistema toman los mismos valores. Teniendo en cuenta esto es claro que la relación entre la frecuencia y el período vendrá dada por: T 1 n= Así, en el caso de una partícula animada de un movimiento circular uniforme, la frecuencia del movimiento nos proporciona el número de vueltas que completa en un segundo (vueltas/seg.). En el caso del resorte que oscila alrededor de su posición de equilibrio, la frecuencia de la oscilación nos proporcionará el número de oscilaciones en la unidad de tiempo. En el caso de la filmadora, la frecuencia de obturación nos proporciona el número de aperturas por segundo y en el caso de la lámpara estroboscópica, su frecuencia de disparos nos proporciona el número de destellos en la unidad de tiempo. Frecuencia angular. Como lo veremos a lo largo de los próximos temas, a menudo resulta útil definir una nueva magnitud que conocemos como frecuencia angular (w), relacionada con las anteriores mediante: w=2pn por lo tanto T 2p w= Introducción al Estudio de un Movimiento Armónico Simple. Previamente a iniciar con el tratamiento del tema se recomienda ejecutar el archivo 06-Mas.htm, incluido en la carpeta del mismo nombre que le permitirá acceder a una simulación en la que se ofrece una interesante comparación entre las variaciones temporales observadas en la coordenada vertical de un cuerpo que oscila suspendido a un muelle, con las variaciones temporales en una de las coordenadas que caracterizan la posición de una partícula animada de un movimiento circular uniforme, para diferentes valores que podrá establecer manualmente, de la frecuencia, ángulo de fase y amplitud de la oscilación, en cuyo caso y como se muestra en la figura siguiente, la coordenada de la partícula que se mueve a lo largo de la trayectoria circular dependerá de la coordenada angular según. - 2.59 -
```

#### [F4] Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009) - pagina 471

- Ruta: `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf`
- Chunk: `bib-c9401bd9a6885a50:p471:c0`
- Requiere OCR: `False`
- Marcas de calidad: ninguna

```text
448 Movimiento periódico –10.0 O x (cm) t (s) 10.0 Figura Ejercicio 13.4. Un deslizador está conectado a un resorte ideal ﬁjo y oscila so- bre una pista de aire horizontal sin fricción. Se coloca una moneda en- cima del deslizador y oscila con éste. ¿En qué puntos del movimiento es máxima la fuerza de fricción sobre la moneda? ¿En qué puntos es mínima? Justiﬁque sus respuestas. Al diseñar estructuras en una región de alta sismicidad, ¿qué relación debe haber entre las frecuencias naturales de oscilación de una estructura y las frecuencias típicas de terremoto? ¿Por qué? ¿La estruc- tura debe tener mucho o poco amortiguamiento? Ejercicios Una cuerda de piano produce una nota la medio vibrando pri- mordialmente a 220 Hz. a b ) Calcule el periodo y la frecuencia angular de una soprano que canta un la una octava más arriba, que tiene el doble de la frecuencia de la cuerda de piano. Si un objeto en una superﬁcie horizontal sin fricción se une a un resorte, se desplaza y después se suelta, oscilará. Si se desplaza 0.120 m de su posición de equilibrio y se suelta con rapidez inicial cero, después de 0.800 s su desplazamiento es de 0.120 m en el lado opuesto, habiendo pasado la posición de equilibrio una vez durante este intervalo. Calcule a ) la amplitud, b ) el periodo y c ) la frecuencia. La punta de un diapasón efectúa 440 vibraciones completas en 0.500 s. Calcule la frecuencia angular y el periodo del movimiento. En la ﬁgura 13.30 se muestra el desplazamiento de un objeto os- cilante en función del tiempo. Calcule a ) la frecuencia, b ) la amplitud, c ) el periodo y d ) la frecuencia angular de este movimiento. –12.0 –6.0 O a x (m /s 2 ) t (s) 12.0 6.0 0.40 Figura Ejercicio 13.17. Una pieza de una máquina está en MAS con frecuencia de 5.00 Hz y amplitud de 1.80 cm. ¿Cuánto tarda la pieza en ir de x 5 0 a x 5 2 1.80 cm? En un laboratorio de física, se conecta un deslizador de riel de ai- re de 0.200 kg al extremo de un resorte ideal de masa despreciable y se zador pasa por la posición de equilibrio y la segunda vez que pasa por este punto es de 2.60 s. Determine la constante de fuerza del resorte. Un cuerpo de masa desconocida se une a un resorte ideal con constante de fuerza de 120 N > m. Se observa que vibra con una frecuen- cia de 6.00 Hz. Calcule a ) el periodo del movimiento; b ) la frecuencia angular; y c ) la masa del cuerpo. Cuando una masa de 0.750 kg oscila en un resorte ideal, la fre- cuencia es de 1.33 Hz. a ) ¿Cuál será la frecuencia si se agregan 0.220 kg a la masa original, y b ) y si se restan de la masa original? Intente resol- ver este problema sin calcular la
```

#### [F5] Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009) - pagina 446

- Ruta: `Bibliografía/Francis Sears, Mark Zemansky, Hugh D. Young, Roger A. Freedman - Física Universitaria. 1-Pearson Addison - Wesley (2009).pdf`
- Chunk: `bib-c9401bd9a6885a50:p446:c1`
- Requiere OCR: `False`
- Marcas de calidad: ninguna

```text
p > És- ta es la ecuación (13.2) para la frecuencia angular de P , lo cual veriﬁca nuestra aﬁr- mación acerca de las dos interpretaciones de v . Por ello, introdujimos la frecuencia angular en la sección 13.1; es la cantidad que conecta la oscilación y el movimiento angular del movimiento armónico simple para un cuerpo de masa m túa una fuerza de restitución con constante de fuerza k : (movimiento armónico simple) Cuando un cuerpo comienza a oscilar en un MAS, no podemos elegir el valor de v , pues está predeterminado por los valores de k y m . Las unidades de k son N > m, o v5 Å k m v 2 5 k m o bien, v5 Å k m a x 52 a Q cos 2 A cos u a a x 52 a Q cos u . S Q a Q 5v 2 A a S Q a S Q x 5 A cos u u u u u O P y x Q v Q 5 2 v Q sen u a) Uso del círculo de referencia para determinar la velocidad x del punto P v x O P y x Q 5 2 a Q cos u b) Uso del círculo de referencia para determinar la aceleración x del punto P a Q a x a) La velocidad x y b) la aceleración de x de la sombra de la esfera representada por el punto P (véase la ﬁgura 13.5) son las componentes x de los vectores de velocidad y aceleración, respectivamente, de la esfera Q . a x 2 x
```

## Evaluacion de las respuestas

- **Constante elastica:** respuesta fuera de tema; habla de una compresion para que una particula entre en una zona rugosa y no responde que representa la constante elastica.
- **Periodo:** extrae un ejemplo de 4 Hz y calcula 0,25 s, pese a que la pregunta pide una relacion general. Esa conversion es una deduccion y no una respuesta estrictamente textual a lo pedido.
- **Energia mecanica:** incluye contenido pertinente, pero tambien expresa `E = T + F` y asigna significados a sus terminos sin que la respuesta deje una cita textual verificable que respalde esa formula.
- **Frecuencia angular:** deriva hacia frecuencias de terremotos y amortiguamiento, tema que no pregunto el usuario, y reconoce que esta infiriendo.

Las referencias documentales y sus textos completos se preservan arriba para revisar cada caso. Las marcas de calidad se muestran; una referencia sobre energia tiene `palabras_muy_cortas`.

## Pruebas automatizadas

La suite completa aprobo: **28 pruebas en 2,00 s**. Incluye 9 pruebas del nuevo modulo: las cuatro preguntas tematicas, contexto de varios fragmentos, Ollama no disponible, modelo ausente y contexto vacio, ademas de la deteccion del tag `:latest`. Estas pruebas usan dobles para aislar el flujo y no sustituyen la evaluacion con Qwen; las cuatro generaciones reales se registran en este informe.

No se agregaron dependencias. No se modificaron archivos del agente de medicion ni la interfaz Streamlit. No se avanzo a Etapa 3C.
