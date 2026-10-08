# agente-resorte-grupo4
## DATOS DE LA ESTRUCTURA GENERAL ##

En Requirements.txt fijamos versiones:
instalación correr
cd agente-resorte
pip install -r requirements.txt


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