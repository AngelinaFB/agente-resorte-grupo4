# Agente Resorte - informe para el grupo

## Etapa 3A: busqueda bibliografica local

**Actualizado:** 8 de noviembre de 2026

## Estado

En esta computadora se instalo Ollama 0.40.15 y se descargo bge-m3:latest. Se generaron embeddings reales para los 2.531 chunks de la bibliografia en 449,85 segundos (7 min 30 s), con vectores de 1.024 dimensiones. La base local ocupa unos 11,3 MiB y la verificacion posterior del indice FTS5 termino OK.

Se detecto que consultas naturales sobre masa y energia podian dejar a la busqueda hibrida funcionando solo con su rama semantica: FTS5 exigia que aparecieran todos los terminos. Se agrego un respaldo: si la busqueda estricta no encuentra nada, FTS5 busca terminos de contenido con OR y esos resultados se fusionan con los semanticos mediante RRF. La busqueda textual independiente conserva su modo estricto. Los resultados FTS muestran las marcas OCR y calidad de la pagina.

Despues del cambio, las consultas reales recuperan candidatos de ambas ramas. Energia trae fragmentos que explican energia cinetica y potencial. Para masa aparecen paginas sobre masa y oscilacion, aunque algunas candidatas son indirectas. La pertinencia sigue siendo mixta y necesita revision humana en las fuentes originales.

El usuario reviso los resultados mostrados para energia y los considero satisfactorios. Acepta provisionalmente el resto, pero no reviso esas consultas una por una. Esta aceptacion es un criterio del usuario y no una evaluacion humana detallada de todos los resultados.

Se ejecutaron 8 pruebas de embeddings y 5 de indice: las 13 aprobaron. El modulo sigue siendo busqueda por CLI; no redacta respuestas conversacionales ni esta conectado a Streamlit, de acuerdo con el alcance de Etapa 3A.

## Cada integrante prepara su computadora

Ollama se instala en el sistema operativo de cada usuario, fuera del repo. BGE-M3 y las bases se descargan o generan localmente y no se guardan en Git. Por eso esta instalacion no deja Ollama disponible automaticamente para los companeros.

En Windows, cada integrante necesita el repo con los PDF fuente, Python 3.10 o posterior e Internet para la preparacion inicial. Desde PowerShell:

```powershell
cd agente-resorte
Set-ExecutionPolicy -Scope Process Bypass
.\setup-chatbot.ps1
```

La guia completa esta en agente-resorte/chatbot/README.md. El script prepara el entorno Python, instala Ollama si falta, descarga BGE-M3 y crea/verifica indices locales.

## Recursos y alcance de la medicion

El prompt de Etapa 3A describe Ryzen 7 5700U, 24 GB de RAM y Radeon integrada. Esta ejecucion se hizo en otro equipo detectado: Ryzen 5 5600H, aproximadamente 16 GB de RAM y Radeon RX 6600M. El tiempo de 7 min 30 s no predice el tiempo en el equipo de referencia. Ollama reporto uso de GPU en esta computadora; no se debe asumir el mismo resultado para otros equipos AMD sin probarlos.

El indice registra 35 documentos, 1.688 paginas y 2.531 chunks. Hay 48 paginas marcadas para OCR y 105 con marcas de calidad. No se instalo Tesseract; las marcas se conservaron y deben considerarse al evaluar evidencia.

## Siguientes pasos de mejora

1. Revisar resultados de masa y energia con mas contexto y en las paginas fuente.
2. Comparar FTS5, semantica e hibrida y definir entre el grupo que cuenta como resultado pertinente.
3. Si se confirma una falla, ajustar ranking o segmentacion y agregar casos de regresion, preservando IDs, referencias y marcas de calidad.
4. Repetir las consultas y pedir a otro integrante que pruebe la guia en su computadora.

No se avanzo a Etapa 3B, no se agrego generacion de respuestas ni integracion con Streamlit, y no se usaron APIs ni servicios en la nube.

### Mensaje breve para compartir

> Se probaron Ollama y BGE-M3 reales: se generaron embeddings para 2.531 chunks en 7 min 30 s. Se mejoro la busqueda hibrida para recuperar candidatos FTS cuando la consulta completa no coincide literalmente; pasan las 13 pruebas de embeddings e indice. Masa y energia todavia requieren revision de pertinencia. Ollama, el modelo y los indices son locales a cada computadora, asi que cada integrante debe seguir la guia del repo. La busqueda sigue en CLI y no se avanzo a Etapa 3B.
