# agente-resorte-grupo4
## DATOS DE LA ESTRUCTURA GENERAL ##

En `agente-resorte/requirements.txt` están las dependencias:
instalación
```
cd agente-resorte
pip install -r requirements.txt
```

> Sin internet: `pip download -r requirements.txt -d wheels/` y luego `pip install --no-index --find-links wheels/ -r requirements.txt`.

## INTERFAZ PARA ANALIZAR VIDEOS

Desde la carpeta `agente-resorte`, instalá las dependencias y arrancá la interfaz:
```
pip install -r requirements.txt
python -m streamlit run app.py
```

En la página podés subir una o varias repeticiones, ingresar las masas y elegir el eje y
el color de la marca que se sigue. Para la escala espacial, indicá los px/m conocidos con
su incerteza, o medí una regla visible en el primer video ingresando las coordenadas de
sus extremos. El FPS real y el chequeo estático son opcionales.

Al terminar, la interfaz muestra los resultados y gráficos, y permite descargar el
informe, el JSON o un ZIP con todos los archivos generados. Los videos se procesan desde
una carpeta temporal; no los agregues al repositorio.

## CON RESPECTO A LOS VIDEOS ##
No suban videos al repo. Pesan mucho. Pónganlos en Google Drive y dejen el link en el README (agrego *.mp4 al .gitignore)


## RESPECTO A CADA ARCHIVO
# Calibracion
> En el sintético no hay regla, por eso el __main__ usa 2000 px/m directo. Con videos reales usan marcar_dos_puntos + escala_px_por_m.
> fps_real_con_led solo se usa si filman un LED o cronómetro (lo pide la receta). El Grupo 8 debería hacerlo (pedir ese dato al grupo del video).

# Señal
>Cómo probarlo
Correr tracking.py y después calibracion.py para tener tabla_m.csv.
Correr python señal.py.
Mirar salidas/señal.png: la aceleración cruda debería ser ruido puro y la filtrada una cosenoide limpia. Si la filtrada se ve aplastada, la ventana es demasiado grande.

>Qué probar y reportar
Ventana: probar 7, 11, 21, 41. Muy chica no limpia el ruido, muy grande aplasta la amplitud de a(t). Elegir con un criterio explícito. Por ejemplo, la ventana más chica donde el error de a(t) respecto de la verdad sintética deja de bajar. Con datos sintéticos pueden calcularlo porque conocen a(t) exacta.
Orden: 3 es un buen punto de partida.
Comparación obligatoria: crudo vs filtrado para x, v y a (ya sale en el gráfico).
Limitación a anotar: incerteza_cruda asume ruido independiente entre cuadros. Después del filtrado, σv y σa ya no valen así. Para la incerteza final conviene usar el ajuste del paso siguiente (ajuste.py), que es donde sale k con su error.
No suban videos al repo. Pesan mucho. Pónganlos en Google Drive y dejen el link en el README (agrego *.mp4 al .gitignore)

# Generador Sintético
Con esto puedo generar diferentes ruidos
python generador_sintetico.py --semilla 1 --salida sint1.mp4
python generador_sintetico.py --semilla 2 --salida sint2.mp4

# Main
Prueba con el sintético:
python generador_sintetico.py
python tracking.py sintetico.mp4 --ver

Con videos reales:
python main.py videos/*.mp4 --masa 0.250 --masa-resorte 0.030 --regla-m 0.30 --fps-real 29.97 \
  --eje y --masas-estaticas 0.1 0.2 0.3 0.4 --elongaciones 0.082 0.165 0.249 0.330

Argumentos de incerteza:
- `--sigma-px-por-m`: obligatorio si se usa `--px-por-m` (incerteza de la escala en px/m); sin él main.py aborta.
- `--sigma-g`: incerteza de g para el k estático, en m/s² (default 0.01).
- `--sigma-elongacion`: incerteza de cada elongación para el k estático, en m (un valor o uno por punto); si no se da, el informe lo anota en limitaciones.

fps real medido con LED:
- `--video-led RUTA`: video corto de un LED que parpadea, filmado con el mismo setup que los videos del experimento; mide los fps reales y los usa en lugar de `--fps-real` (si se dan los dos, gana el LED).
- `--f-led HZ`: frecuencia conocida del parpadeo del LED en Hz (obligatorio junto con `--video-led`).
- `--roi X Y W H`: región del LED en el cuadro en píxeles; si no se da, se usa el brillo de todo el cuadro.
- La incerteza del fps medida con el LED se propaga a T, γ y k, y el informe indica qué fps se usó, de dónde salió y con qué error.

>Si la detección falla o se pega a otras cosas, los rangos HSV de COLORES son el primer lugar a ajustar. Con --ver ves enseguida si engancha el objeto correcto.
Los colores saturados (rojo, verde, azul) funcionan mejor que el negro o el blanco. Pinten o pongan una marca de color fuerte sobre la masa.
Si hay otros objetos del mismo color en la imagen (ropa, carteles), el filtro del contorno más grande puede engancharse al equivocado. Cuiden el fondo.