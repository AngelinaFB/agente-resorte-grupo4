# Agente bibliografico

El modulo permite buscar en los PDF de `Bibliografia` con FTS5, BGE-M3 semantico e hibrido, y generar respuestas en espanol con un modelo local de Ollama. Las bases y modelos permanecen en cada computadora.

## Preparacion de Etapa 3A en Windows

Requisitos: Windows 10/11 de 64 bits, Python 3.10+ e Internet durante la preparacion inicial. Desde PowerShell:

```powershell
cd agente-resorte
Set-ExecutionPolicy -Scope Process Bypass
.\setup-chatbot.ps1
```

El script de preparacion configura dependencias y el modelo de embeddings de Etapa 3A. Ollama y modelos se almacenan fuera del repo. La busqueda bibliografica no esta integrada en Streamlit.

Para reconstruir los indices locales despues de cambiar los PDF:

```powershell
.\setup-chatbot.ps1 -RebuildIndex
```

Para reconstruir solo embeddings:

```powershell
.\setup-chatbot.ps1 -RebuildEmbeddings
```

## Consultas de Etapa 3A

```powershell
.\.venv\Scripts\python.exe -m chatbot.cli search "oscilador armonico"
.\.venv\Scripts\python.exe -m chatbot.cli search-semantic "energia potencial elastica"
.\.venv\Scripts\python.exe -m chatbot.cli search-hybrid "periodo de un resorte"
.\.venv\Scripts\python.exe -m chatbot.cli stats
.\.venv\Scripts\python.exe -m chatbot.cli embed-stats
```

La busqueda hibrida intenta coincidencia FTS estricta y, si no obtiene resultados, reintenta con terminos de contenido en OR antes de fusionar con resultados semanticos. La busqueda `search` conserva el modo estricto. Resultados FTS y semanticos informan marcas OCR/calidad.

## Respuestas locales y controles de Etapa 3C

El comando `ask` recupera fragmentos mediante la busqueda hibrida, aplica reglas deterministas de pertinencia y calidad, y solo entrega la evidencia aceptada a Ollama. La respuesta del modelo se conserva para auditoria, pero solo se presenta una afirmacion si es una cita textual exacta con referencias incluidas en el contexto. Una cita con formula alterada, referencia inventada o afirmacion sin referencia se rechaza. Si no hay evidencia confiable, el sistema se abstiene antes de llamar a Ollama. El modelo predeterminado es `qwen2.5:7b`; el comando no descarga modelos.

```powershell
.\.venv\Scripts\python.exe -m chatbot.cli ask "Que determina el periodo de un resorte?"
.\.venv\Scripts\python.exe -m chatbot.cli ask "Que es la energia mecanica?" --limit 8 --json
```

La salida JSON incluye candidatos recuperados, fragmentos aceptados y descartados con motivos, afirmaciones verificadas y rechazadas, referencias y tiempos de recuperacion/generacion/validacion. `ask` no se integra a Streamlit.

Para repetir la evaluacion local de las cuatro consultas de 3C:

```powershell
.\.venv\Scripts\python.exe -m chatbot.cli evaluate-3c --model qwen2.5:7b --limit 20 --json
```

El evaluador no declara una consulta exitosa solo porque Qwen genere texto. Las reglas de evidencia son deliberadamente conservadoras y actualmente tienen perfiles tematicos especificos para constante elastica, periodo, energia mecanica y frecuencia angular; las consultas generales usan coincidencia de terminos. La cita literal no demuestra por si sola la verdad del documento y no sustituye una revision academica.

Para habilitar respuestas reales, Qwen debe estar instalado manualmente despues de autorizacion explicita. El comando esperado es `ollama pull qwen2.5:7b`. No ejecutar la descarga hasta contar con esa autorizacion y verificar espacio disponible.

## Datos compartidos

- El checkout debe incluir los PDF fuente de `Bibliografia` y `Ochoa.rar` cuando se usa ese material.
- `.venv`, corpus extraido, bases SQLite, manifiestos y modelos son locales e ignorados por Git.
- Cada usuario puede regenerar sus indices desde los PDF. Para usar una biblioteca actualizada, sincronizar los PDF fuente y reconstruir el indice.
