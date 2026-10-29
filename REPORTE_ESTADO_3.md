# REPORTE_ESTADO_3 — Estado del proyecto (Grupo 4, Línea III, movimiento 3: resorte)

Actualización al 29 de octubre de 2026. Este reporte resume el trabajo realizado en la sesión y los dos pendientes principales acordados por el grupo. No reemplaza la consigna del curso ni afirma validación con videos reales.

## Resumen

1. Se mejoró la legibilidad de la interfaz y de los archivos de resultados.
2. El seguimiento también cambió respecto de la versión anterior: dejó de depender de elegir un color HSV y ahora detecta movimiento con MOG2, funciona mejor.
3. La interfaz muestra el avance porcentual del análisis, bloquea el botón mientras procesa y reduce el tamaño de la vista previa del video.
4. La calibración se simplificó visualmente, pero todavía requiere que el usuario ingrese la longitud real de la regla y las coordenadas de sus extremos.
5. Quedan dos tareas principales: continuar mejorando el seguimiento ante movimientos ajenos y automatizar la detección de la regla para calibrar.

## Cambios realizados en esta sesión

| Área | Cambio | Estado |
|---|---|---|
| Interfaz de resultados | Se incorporaron tablas resumidas por video y para el promedio de repeticiones. El JSON completo queda en un desplegable. | Implementado en `agente-resorte/app.py`. |
| JSON | Se creó un formato versionado con magnitudes nombradas, unidades, incertidumbres, datos de seguimiento, FPS y alertas de calidad. | Implementado en `agente-resorte/main.py`. |
| Informe Markdown | Se reorganizaron resultados, seguimiento, calidad del ajuste, agregados, energía, máximos y limitaciones en secciones. | Implementado en `agente-resorte/main.py`. |
| Progreso | El seguimiento informa cuadros procesados; la interfaz actualiza un porcentaje y deshabilita el botón durante el análisis. | Conectado entre `tracking.py`, `main.py` y `app.py`. |
| Vista previa | El primer cuadro se limita a 520 px de ancho y se cachea para evitar decodificarlo en cada interacción. | Implementado en `agente-resorte/app.py`. |
| Calibración y controles | Se quitó la elección entre escala conocida y regla, y se quitó el FPS manual de la interfaz. Longitud, ventana de filtrado y coordenadas se agruparon; los campos se compactaron y recibieron ayudas. | Mejora visual implementada. La detección automática de la regla sigue pendiente. |
| Evolución del tracker | Antes el flujo dependía de una región de interés (ROI) y de segmentar rangos HSV de colores predefinidos; la interfaz pedía escoger el color de la marca. Ahora procesa el cuadro completo sin selección manual de ROI ni color y usa MOG2 para separar movimiento del fondo. También aplica operaciones morfológicas, límites de área y continuidad con el centroide anterior y un umbral adaptativo de salto. | Cambio implementado en `agente-resorte/tracking.py`; el usuario reporta que el seguimiento actual funciona mucho mejor. Aún puede confundirse con manos u otros objetos móviles. |

## Estado actual del flujo

| Etapa | Estado | Observación |
|---|---|---|
| Carga de videos | Implementada | Acepta uno o varios videos del experimento. |
| Calibración espacial | Parcial | Se ingresa la longitud de la regla y, al cargar un video, las coordenadas en píxeles de ambos extremos. El programa calcula px/m a partir de esos datos. |
| Seguimiento de la pesa | Mejorado, parcial | MOG2 y el análisis del cuadro completo reemplazaron el flujo anterior basado en ROI y color HSV. La selección inicial todavía elige el contorno de mayor área y luego sigue el candidato cercano; movimientos ajenos pueden interferir. |
| Análisis físico | Implementado | Filtrado, ajuste de oscilación, magnitudes físicas e incertezas según el pipeline existente. |
| Resultados | Mejorado | Informe y JSON más legibles; la interfaz muestra resúmenes y alertas. |
| Operación sin internet | Objetivo conservado | No se añadieron servicios en la nube ni descargas de modelos durante la ejecución. |

## Pendientes principales

### 1. Mejorar el seguimiento de la pesa

El tracker ya no depende del recorte de una región de interés ni de los rangos HSV de colores predefinidos que usaba el flujo anterior. MOG2 detecta cambios frente al fondo y la continuidad entre cuadros hace el seguimiento más robusto; el usuario informa que el resultado mejoró mucho. Queda fortalecerlo para que distinga la pesa de manos y otros movimientos y conserve una trayectoria coherente durante todo el video. La solución debe servir en distintos videos del mismo tipo de experimento, no depender de ajustar manualmente cada grabación. Debe informar cuando la detección sea dudosa para evitar presentar un seguimiento incorrecto como válido.

**Criterio de aceptación sugerido:** comprobar sobre videos representativos que el tracker sigue la pesa a través de varios ciclos, no salta a una mano u otro objeto y reporta cuadros perdidos o baja confianza.

### 2. Automatizar la calibración de la regla

El objetivo de la interfaz es pedir solamente la longitud real de la regla. El programa debe localizar automáticamente sus extremos en el primer video, medir la distancia en píxeles y calcular la escala px/m con su incertidumbre. Actualmente los campos de coordenadas siguen existiendo y son necesarios para el cálculo; todavía no se debe describir esta etapa como automática.

**Criterio de aceptación sugerido:** con la longitud real ingresada y la regla visible, el sistema detecta su segmento y calcula la escala sin pedir coordenadas. Debe señalar cuando no encuentra la regla o no puede estimar una escala fiable.

## Restricciones y validación

- El programa debe funcionar sin internet. Cualquier dependencia o peso de modelo necesario debe estar disponible localmente y no descargarse al iniciar la app.
- No se incorporó una IA preentrenada en esta sesión; el seguimiento existente continúa siendo visión clásica con OpenCV.
- Comparación histórica: Git muestra el tracker anterior basado en rangos HSV y la interfaz con selector de color/eje; el flujo anterior también trabajaba con ROI. El diff actual elimina la segmentación por color y el código actual procesa el cuadro completo con MOG2, sin selector de ROI/color. El usuario informa que el resultado práctico mejoró.
- Se ajustó la interfaz a partir de las capturas compartidas durante la sesión. No se ejecutó una corrida completa con videos reales ni se midió el porcentaje de progreso contra un archivo de prueba.
- Para la calibración automática, un eventual método basado en visión debe incluir una medida de confianza e incertidumbre, ya que un detector equivocado puede sesgar todas las magnitudes espaciales.

## Archivos principales modificados

- `agente-resorte/app.py`: distribución de controles, ayudas, vista previa, progreso y presentación resumida.
- `agente-resorte/main.py`: seguimiento incluido en resultados, JSON legible y nuevo informe Markdown.
- `agente-resorte/tracking.py`: callback de avance por cuadros.

