# Reporte de estado 6

**Fecha:** 13 de noviembre de 2026  
**Proyecto:** Analizador de video de un resorte

## Estado actual

La interfaz conserva el analizador completo en un panel y muestra el chat al lado. El chat mantiene el historial en un panel con desplazamiento propio. Por ahora responde de forma guiada con el estado de los datos ingresados; todavía no es un asistente de física conectado a un modelo o a la bibliografía.

La calibración espacial permite marcar con el mouse dos extremos de una distancia conocida en el primer cuadro. El tercer clic reinicia la selección. El selector de la regla y el del punto de seguimiento tienen un control de icono para ampliar la imagen al ancho disponible.

La vista previa del seguimiento conserva la trayectoria en píxeles y el análisis final la reutiliza para evitar rastrear nuevamente el video previsualizado.

## Entorno local y diagnóstico

Smart App Control bloqueaba una extensión nativa de pandas; el usuario lo desactivó y pandas 3.1.1 importa correctamente.

La sugerencia anterior de instalar numdifftools para resolver la covarianza fue incorrecta. El método least_squares de lmfit calcula la covarianza a partir del Jacobiano; si devuelve None, la matriz del ajuste es singular. Se quitó numdifftools de requirements.txt y del entorno local. El error ahora incluye período, ciclos, cuadros válidos y resumen del tracking para ayudar a identificar datos sin una oscilación bien determinada.

Se restauró el códec avc1 para la vista previa del seguimiento, como estaba antes del intento con mp4v, porque el usuario prefiere conservar el video aunque OpenCV deje un aviso de OpenH264 en la consola.

## Pendiente



- Analizar la trayectoria para determinar las entradas que realmente faltan en cada cálculo y pedirlas por chat.
- Aplicar las respuestas a los cálculos y producir el informe completo de cinemática, dinámica y energías.
- Conectar consultas de física con la bibliografía de la cátedra y mostrar citas.
- Validar visualmente la interfaz y el flujo completo con videos de referencia; actualizar la guía de instalación.

## Verificación de estos cambios

La sintaxis de app.py y main.py se verificó con ast.parse; pip check no reporta conflictos y git diff --check no detecta errores de whitespace. No se ejecutó el análisis con el video R1 P3 ni pruebas automatizadas.
