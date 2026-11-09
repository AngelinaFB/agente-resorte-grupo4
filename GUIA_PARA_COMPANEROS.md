# Guía para compañeros — Grupo 4

Esta guía describe el checkout local auditado el 9 de noviembre de 2026. **No todo ese estado está todavía en Git:** el último commit es `ac04b16` en `origin/main`, mientras que módulos del chatbot hasta 3C, pruebas e informes recientes permanecen modificados o sin seguimiento. Clonar el remoto ahora no reproducirá todo lo descrito aquí. Primero el grupo debe revisar y compartir esos cambios por Git. No se hizo commit como parte de esta tarea.

## A. Requisitos previos

### Agente original

- Windows y Git.
- Python **3.10 o posterior**: el instalador `setup-chatbot.ps1` exige 3.10+. La auditoría y la suite histórica más reciente están documentadas con Python 3.14.7; no hay archivo que fije versiones de dependencias.
- Entorno virtual recomendado.
- Paquetes listados en `agente-resorte/requirements.txt`: NumPy, SciPy, OpenCV, lmfit, uncertainties, Matplotlib y Streamlit. El archivo no fija versiones.

### Chatbot

- Además del entorno, `requirements-chatbot.txt` requiere NumPy (`numpy>=1.26`). La etapa FTS/ingesta usa en su mayoría biblioteca estándar.
- Ollama instalado y su servicio local activo.
- `bge-m3` para embeddings/búsqueda semántica e híbrida.
- `qwen2.5:7b` para el comando `ask` y `evaluate-3c`.
- Los modelos se almacenan localmente por usuario, no en el repo. Cada integrante debe descargarlos en su máquina. La descarga inicial necesita Internet; las consultas posteriores se hacen contra Ollama local.
- Para BGE-M3, almacenamiento adicional local aproximado según el listado Ollama observado: 1,2 GB; para Qwen2.5:7b: 4,7 GB. Son tamaños reportados en una máquina, no requisitos de RAM ni garantías de rendimiento.

## B. Clonar y preparar entorno

El remoto configurado durante la auditoría es `https://github.com/AngelinaFB/agente-resorte-grupo4`. Después de que el grupo comparta los cambios locales relevantes:

```powershell
git clone https://github.com/AngelinaFB/agente-resorte-grupo4.git
cd agente-resorte-grupo4\agente-resorte
```

Crear entorno virtual. Este comando usa Python 3.14, que es la versión de la última ejecución de pruebas registrada. Si no está instalado, use un Python 3.10+ disponible con el launcher `py` y sustituya `-3.14` por la versión instalada:

```powershell
py -3.14 -m venv .venv
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
python --version
```

Instalar dependencias del agente y chatbot en el mismo entorno:

```powershell
python -m pip install -r requirements.txt
python -m pip install -r requirements-chatbot.txt
```

La instalación de paquetes necesita acceso a los índices de Python o una preparación previa de wheels; no hay lockfile ni bundle offline verificado.

## C. Preparar el chatbot

### Comprobar Ollama y modelos

Inicie la aplicación de Ollama desde Windows y consulte:

```powershell
ollama --version
ollama list
```

Si el comando no está en PATH, en la instalación por usuario habitual:

```powershell
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" --version
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" list
```

Debe aparecer `bge-m3` o `bge-m3:latest` para recuperación semántica/híbrida y `qwen2.5:7b` para generación. Cada descarga se hace una sola vez por equipo/usuario, requiere Internet y guarda sus archivos fuera del repositorio:

```powershell
ollama pull bge-m3
ollama pull qwen2.5:7b
ollama list
```

No se ejecutaron estas descargas durante la auditoría. En la máquina auditada ambos modelos ya estaban presentes. Si Ollama no responde, abra la aplicación Ollama; `ollama serve` es una alternativa desde una terminal, dejando esa terminal abierta.

### Índice y embeddings

Los PDF fuente están en `Bibliografía/`. El índice y los embeddings no se incluyen en un clon porque `data/index/` está ignorado. Compruebe primero si ya existen:

```powershell
python -m chatbot.cli stats --json
python -m chatbot.cli verify --json
python -m chatbot.cli embed-stats --json
```

Si `bibliografia.sqlite` falta, cree el índice textual desde las fuentes:

```powershell
python -m chatbot.cli ingest
python -m chatbot.cli verify --json
```

La ingesta extrae los 31 PDF internos de `Bibliografía/Ochoa.rar` en `data/corpus/raw/ochoa/`. En Windows el código utiliza `tar.exe`; no instale ni extraiga otra herramienta sin revisar el entorno. Ingestar de nuevo reconstruye artefactos locales; no es necesario si el índice existente verifica correctamente.

Si `embeddings.sqlite` falta o no corresponde con el índice, genere embeddings con Ollama/BGE-M3:

```powershell
python -m chatbot.cli embed-build --model bge-m3 --ollama-url http://127.0.0.1:11434
python -m chatbot.cli embed-stats --json
```

Para una nueva máquina, ejecutar estos comandos genera copias locales de corpus/índices; no cambia los originales del repositorio. El proceso actual de preparación también está empaquetado en `setup-chatbot.ps1`, pero ese script **instala dependencias, puede instalar Ollama con winget, ejecuta `ollama pull bge-m3` y construye lo que falte**. No lo ejecute suponiendo que solo verifica archivos o que funciona sin Internet.

Su invocación, cuando el grupo decida usar este instalador integral en Windows, es:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\setup-chatbot.ps1
```

El script acepta `-RebuildIndex` y `-RebuildEmbeddings`, pero son opciones de reconstrucción local; no las use como simples verificaciones.

## D. Ejecutar el sistema

### Agente original (vídeos)

Desde `agente-resorte/`, después de instalar `requirements.txt`:

```powershell
python -m streamlit run app.py
```

La interfaz permite cargar videos, definir masas/calibración, ejecutar el análisis y descargar informe/JSON/ZIP. No se encontró una UI de chat conectada.

El procesamiento por CLI está en `main.py`. Para ver argumentos reales antes de ejecutar con un video:

```powershell
python main.py --help
```

El CLI requiere al menos la ruta del video y `--masa`; la escala se informa con los argumentos `--px-por-m` más `--sigma-px-por-m`, o mediante `--regla-m` y selección visual. El informe raíz `README.md` contiene un ejemplo con los parámetros del experimento. No existe video de medición real dentro del checkout auditado.

### Chatbot (línea de comandos)

La búsqueda textual no requiere Qwen:

```powershell
python -m chatbot.cli search "periodo de un resorte"
python -m chatbot.cli search-semantic "energia potencial elastica"
python -m chatbot.cli search-hybrid "movimiento armonico simple"
```

Responder con Qwen, solo si ya hay índice, embeddings, servicio Ollama y modelo instalado:

```powershell
python -m chatbot.cli ask "Que determina el periodo de un resorte?"
python -m chatbot.cli ask "Que relacion existe entre energia mecanica, cinetica y potencial?" --limit 20 --json
```

La evaluación real de las cuatro consultas de 3C es:

```powershell
python -m chatbot.cli evaluate-3c --model qwen2.5:7b --limit 20 --json
```

`ask` y `evaluate-3c` llaman a modelos por el endpoint local de Ollama cuando la selección de evidencia da contexto. No descargan modelos. No existe un comando para “abrir el chatbot” como interfaz: el chatbot sigue en CLI.

### Pruebas

Desde `agente-resorte/`:

```powershell
python -m unittest discover -s tests -v
```

La última ejecución registrada en el informe 3C.2 fue 56/56 OK. No se repitió durante la auditoría documental.

## E. Estructura del repositorio

```text
agente-resorte-grupo4/
├── README.md                         # ejecución general y agente de videos
├── ESTADO_ACTUAL_Y_HOJA_DE_RUTA.md  # auditoría técnica del estado
├── GUIA_PARA_COMPANEROS.md          # esta guía
├── REPORTE_ESTADO_*.md              # historial del agente original y etapa 3A
├── INFORME_ETAPA_3C*.md             # historial de evidencia 3C/3C.1/3C.2
└── agente-resorte/
    ├── app.py, main.py               # UI Streamlit y orquestador CLI de video
    ├── tracking.py, calibracion.py, señal.py, ajuste.py
    ├── requirements*.txt, setup-chatbot.ps1
    ├── Bibliografía/                 # PDFs fuente y Ochoa.rar
    ├── chatbot/                      # ingesta, FTS, embeddings, evidencia, generación y CLI
    ├── data/corpus/                   # PDFs extraídos localmente, ignorados por Git
    ├── data/index/bibliografia/       # SQLite/JSONL y embeddings, ignorados por Git
    └── tests/                         # suites automatizadas disponibles
```

El primer recorrido recomendado es `README.md`, `agente-resorte/chatbot/README.md`, `chatbot/cli.py` y los informes 3A/3B/3C.2. `agente-resorte/selector_punto_tracking/index.html` es una página auxiliar donde se hace clic sobre el punto rojo de la masa; no forma parte de la arquitectura del chatbot.

## F. Archivos y datos importantes

### Conservar y compartir

- Los cuatro PDF fuente y `Ochoa.rar` en `agente-resorte/Bibliografía/` están registrados en Git y son necesarios para reconstruir el índice.
- `tabla.csv` también está versionado, pero su procedencia no está documentada en los datos inspeccionados. Confirme con el grupo si es sintético o experimental antes de usarlo como evidencia o resultado.
- Mantener informes y mediciones con procedencia clara; hoy los informes experimentales aún no son entradas del chatbot.
- Mantener las marcas de OCR/calidad; no borrar flags manualmente para hacer que una respuesta pase.

### Artefactos locales que no se comparten por Git

`agente-resorte/.gitignore` excluye `data/index/`, `data/corpus/`, videos (`*.mp4`, `*.avi`, `*.mov`), `.venv`, carpetas `datos/` y `salidas/`, modelos locales `models/` y `*.gguf`. Las bases del chatbot, el corpus extraído y los modelos de Ollama no deben subirse como cambios normales de código. Ollama mantiene sus modelos bajo el perfil del sistema operativo, no en el repo.

El archivo local `agente-resorte/.audit3c1_eval.err` estaba sin seguimiento en esta auditoría; no es fuente ni configuración y no debe usarse como requisito. Los archivos de índice se pueden generar desde los PDF presentes, pero hacerlo puede tomar varios minutos y requiere bajar BGE-M3 para crear embeddings. Si faltan modelos, instalarlos según la sección C; no asuma que un clon los trae.

**Nota de estado Git:** en el momento de auditar, `main` estaba alineada con `origin/main` en `ac04b16ebd336fb448b39c47d27bac96b0f01f15` (8 de noviembre de 2026), pero había modificaciones y numerosos archivos sin seguimiento. Entre estos últimos están `embeddings.py`, `evidence.py`, `generation.py`, `evaluation.py`, `setup-chatbot.ps1`, sus pruebas y varios informes. El índice local no aparece en Git porque está ignorado. Esta guía no publica ni comparte esos cambios.

## G. Flujo de trabajo colaborativo

- Antes de empezar, actualicen desde la rama acordada y revisen `git status`; no trabajen sobre una copia con cambios ajenos sin coordinarlo.
- Usen ramas por tarea (`docs/...`, `chatbot/evidence/...`, `agent/calibration/...`) y comuniquen archivos que se van a editar.
- Se pueden trabajar en paralelo, con coordinación de interfaces, las pruebas del agente y la documentación del chatbot. Eviten editar simultáneamente `evidence.py`/`generation.py` o `main.py`/`app.py`.
- El chatbot depende del contrato de chunks/IDs en `index.py`; cambios de esquema o referencias deben coordinarse entre indexación, embeddings, evidencia y tests.
- El agente depende del formato de resultados de `main.py`; una futura ingestión experimental debe coordinar ese esquema antes de incorporar informes.
- Antes de integrar cambios, cada rama debe correr las pruebas pertinentes; la integración corre `python -m unittest discover -s tests -v` y una verificación `python -m chatbot.cli verify --json`.
- No incluir `.venv`, videos, corpus extraído, bases SQLite o modelos en commits. Aseguren que los PDF fuente sigan presentes.
- Cada etapa debe registrar objetivo, alcance, archivos tocados, comandos ejecutados, resultados reales, limitaciones y punto de detención. Diferencien resultado con doble de una ejecución con modelo real.
- Integren primero en ramas/PR revisables. Verifiquen que los cambios del chatbot no alteren el análisis de videos y viceversa.

## H. Primeros pasos para quien recién clona

1. Confirmar con el grupo que el commit ya contiene el código e informes recientes que necesita; hoy el remoto no coincide con el checkout auditado.
2. Clonar, crear `.venv`, activar e instalar `requirements.txt` y `requirements-chatbot.txt`.
3. Ejecutar `python -m streamlit run app.py` y revisar el agente con un video de prueba autorizado.
4. Revisar que los PDF fuente existan; correr `python -m chatbot.cli stats --json` y `verify --json`. Si no hay índice, coordinar antes de ejecutar `ingest`.
5. Comprobar Ollama y modelos con `ollama list`. Si faltan, coordinar su descarga; luego preparar embeddings según la sección C.
6. Ejecutar las pruebas y leer `INFORME_ETAPA_3C_2.md`. No considerar la etapa estable por el solo resultado de unittest.
7. Elegir una tarea prioritaria de la hoja de ruta, abrir una rama y acordar con el grupo archivos y criterio de aceptación antes de cambiar código.
