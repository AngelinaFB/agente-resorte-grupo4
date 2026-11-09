param(
    [switch]$RebuildIndex,
    [switch]$RebuildEmbeddings
)

$ErrorActionPreference = "Stop"
$ProjectDir = $PSScriptRoot
Set-Location $ProjectDir

$OllamaUrl = "http://127.0.0.1:11434"

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [Parameter(Mandatory = $true)][string]$Action
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Action fallo (codigo $LASTEXITCODE)."
    }
}

function Test-OllamaApi {
    try {
        $null = Invoke-RestMethod -Uri "$OllamaUrl/api/tags" -TimeoutSec 3
        return $true
    }
    catch {
        return $false
    }
}

Write-Host "Proyecto: $ProjectDir"
Write-Host "Ollama:   $OllamaUrl"

# Usa el launcher de Windows si esta disponible; de lo contrario, usa python.
$PythonCommand = Get-Command py.exe -ErrorAction SilentlyContinue
if ($PythonCommand) {
    $PythonExe = $PythonCommand.Source
    $PythonPrefix = @("-3")
}
else {
    $PythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
    if (-not $PythonCommand) {
        throw "No se encontro Python. Instala Python 3.10 o posterior y vuelve a ejecutar este script."
    }
    $PythonExe = $PythonCommand.Source
    $PythonPrefix = @()
}

$PythonVersionText = & $PythonExe @PythonPrefix -c "import sys; print('.'.join(map(str, sys.version_info[:3])))"
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo iniciar Python."
}
$PythonVersion = [Version]$PythonVersionText.Trim()
if ($PythonVersion -lt [Version]"3.10") {
    throw "Se requiere Python 3.10 o posterior. Version detectada: $PythonVersion"
}
Write-Host "Python:   $PythonVersion"

$VenvDir = Join-Path $ProjectDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Host "Creando entorno virtual .venv..."
    Invoke-Checked -FilePath $PythonExe -Arguments ($PythonPrefix + @("-m", "venv", $VenvDir)) -Action "Creacion del entorno virtual"
}

Write-Host "Instalando dependencias de chatbot..."
Invoke-Checked -FilePath $VenvPython -Arguments @("-m", "pip", "install", "-r", "requirements-chatbot.txt") -Action "Instalacion de dependencias"

$OllamaExe = $null
$OllamaCommand = Get-Command ollama.exe -ErrorAction SilentlyContinue
if ($OllamaCommand) {
    $OllamaExe = $OllamaCommand.Source
}
else {
    $DefaultOllamaExe = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
    if (Test-Path $DefaultOllamaExe) {
        $OllamaExe = $DefaultOllamaExe
    }
    else {
        $MachineOllamaExe = Join-Path $env:ProgramFiles "Ollama\ollama.exe"
        if (Test-Path $MachineOllamaExe) {
            $OllamaExe = $MachineOllamaExe
        }
    }
}

if (-not $OllamaExe) {
    $Winget = Get-Command winget.exe -ErrorAction SilentlyContinue
    if (-not $Winget) {
        throw "Ollama no esta instalado y winget no esta disponible. Instala Ollama desde https://ollama.com/download y vuelve a ejecutar este script."
    }
    Write-Host "Instalando Ollama con winget. La descarga puede tardar..."
    Invoke-Checked -FilePath $Winget.Source -Arguments @(
        "install", "--id", "Ollama.Ollama", "--exact",
        "--accept-package-agreements", "--accept-source-agreements", "--silent"
    ) -Action "Instalacion de Ollama"

    $OllamaCommand = Get-Command ollama.exe -ErrorAction SilentlyContinue
    if ($OllamaCommand) {
        $OllamaExe = $OllamaCommand.Source
    }
    elseif (Test-Path $DefaultOllamaExe) {
        $OllamaExe = $DefaultOllamaExe
    }
    elseif (Test-Path $MachineOllamaExe) {
        $OllamaExe = $MachineOllamaExe
    }
    else {
        throw "La instalacion termino, pero no se encontro ollama.exe. Abre una terminal nueva y vuelve a ejecutar el script."
    }
}

if (-not (Test-OllamaApi)) {
    Write-Host "Iniciando el servicio local de Ollama..."
    Start-Process -FilePath $OllamaExe -ArgumentList "serve" -WindowStyle Hidden
    $Deadline = (Get-Date).AddSeconds(60)
    while (-not (Test-OllamaApi) -and (Get-Date) -lt $Deadline) {
        Start-Sleep -Seconds 2
    }
    if (-not (Test-OllamaApi)) {
        throw "Ollama no respondio en $OllamaUrl. Inicia la aplicacion Ollama y vuelve a ejecutar el script."
    }
}

$env:OLLAMA_HOST = $OllamaUrl
Write-Host "Descargando/actualizando el modelo bge-m3..."
Invoke-Checked -FilePath $OllamaExe -Arguments @("pull", "bge-m3") -Action "Descarga de BGE-M3"

$IndexDb = Join-Path $ProjectDir "data\index\bibliografia\bibliografia.sqlite"
$EmbeddingsDb = Join-Path $ProjectDir "data\index\bibliografia\embeddings.sqlite"
if ($RebuildIndex -or -not (Test-Path $IndexDb)) {
    Write-Host "Construyendo el indice bibliografico desde Bibliografia..."
    Invoke-Checked -FilePath $VenvPython -Arguments @("-m", "chatbot.cli", "ingest") -Action "Ingesta de bibliografia"
}
else {
    Write-Host "El indice bibliografico ya existe; verificando..."
    Invoke-Checked -FilePath $VenvPython -Arguments @("-m", "chatbot.cli", "verify") -Action "Verificacion del indice"
}

$StatsJson = & $VenvPython -m chatbot.cli stats --json
if ($LASTEXITCODE -ne 0) {
    throw "No se pudieron leer las estadisticas del indice."
}
$IndexStats = ($StatsJson -join "`n") | ConvertFrom-Json
$ExpectedChunks = [int]$IndexStats.chunks
if ($ExpectedChunks -le 0) {
    throw "El indice no contiene chunks para vectorizar."
}

$BuildEmbeddings = [bool]$RebuildEmbeddings -or [bool]$RebuildIndex -or -not (Test-Path $EmbeddingsDb)
if (-not $BuildEmbeddings) {
    $EmbeddingsJson = & $VenvPython -m chatbot.cli embed-stats --json
    if ($LASTEXITCODE -ne 0) {
        $BuildEmbeddings = $true
    }
    else {
        $EmbeddingsStats = ($EmbeddingsJson -join "`n") | ConvertFrom-Json
        $StoredModel = [string]$EmbeddingsStats.metadata.model
        $StoredChunks = [int]$EmbeddingsStats.chunks
        $BuildEmbeddings = ($StoredChunks -ne $ExpectedChunks) -or ($StoredModel -ne "bge-m3")
    }
}

if ($BuildEmbeddings) {
    Write-Host "Generando embeddings BGE-M3 para $ExpectedChunks chunks..."
    Invoke-Checked -FilePath $VenvPython -Arguments @(
        "-m", "chatbot.cli", "embed-build", "--model", "bge-m3", "--ollama-url", $OllamaUrl
    ) -Action "Construccion de embeddings"
}
else {
    Write-Host "Los embeddings BGE-M3 ya existen y coinciden con el indice; se conservan."
}

$FinalJson = & $VenvPython -m chatbot.cli embed-stats --json
if ($LASTEXITCODE -ne 0) {
    throw "No se pudieron verificar los embeddings generados."
}
$FinalStats = ($FinalJson -join "`n") | ConvertFrom-Json
if ([int]$FinalStats.chunks -ne $ExpectedChunks -or [string]$FinalStats.metadata.model -ne "bge-m3") {
    throw "La verificacion final no coincide: indice=$ExpectedChunks, embeddings=$($FinalStats.chunks), modelo=$($FinalStats.metadata.model)."
}

Write-Host ""
Write-Host "Preparacion completada."
Write-Host "Documentos: $($IndexStats.documents); chunks y embeddings: $ExpectedChunks."
Write-Host "Base local: $EmbeddingsDb"
Write-Host "Consultas de ejemplo:"
Write-Host '  .\.venv\Scripts\python.exe -m chatbot.cli search-hybrid "movimiento armonico simple"'
Write-Host '  .\.venv\Scripts\python.exe -m chatbot.cli search-semantic "energia potencial elastica"'
