<#
.SYNOPSIS
  Instala o NutEV/NutMEV no Windows e prepara uma demo local.

.USAGE
  PowerShell:
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
    .\scripts\setup_windows.ps1

Depois rode:
    .\scripts\run_dashboard_windows.ps1
#>

$ErrorActionPreference = "Stop"

function Write-Step($Message) {
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)][string]$Command,
        [Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments
    )

    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Comando falhou com codigo ${LASTEXITCODE}: $Command $($Arguments -join ' ')"
    }
}

function Test-PythonExecutable {
    param([Parameter(Mandatory = $true)][string]$PythonExe)

    if (-not (Test-Path $PythonExe)) {
        return $false
    }

    & $PythonExe -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 12) and sys.version_info < (3, 14) else 1)" | Out-Null
    return ($LASTEXITCODE -eq 0)
}

function Resolve-PythonExecutable {
    $candidatePaths = @(
        "C:\Program Files\Python312\python.exe",
        "C:\Program Files\Python313\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe"
    )

    foreach ($candidate in $candidatePaths) {
        if (Test-PythonExecutable $candidate) {
            return $candidate
        }
    }

    $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        try {
            $pyExe = & py -3.12 -c "import sys; print(sys.executable)"
            if ($LASTEXITCODE -eq 0 -and (Test-PythonExecutable $pyExe)) {
                return $pyExe
            }
        } catch {
            Write-Host "Python 3.12 nao encontrado pelo launcher py." -ForegroundColor Yellow
        }
    }

    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        try {
            $pythonExe = & python -c "import sys; print(sys.executable)"
            if ($LASTEXITCODE -eq 0 -and (Test-PythonExecutable $pythonExe)) {
                return $pythonExe
            }
        } catch {
            Write-Host "Comando python encontrado, mas nao e uma versao compativel." -ForegroundColor Yellow
        }
    }

    throw "Instale Python 3.12 ou 3.13 e tente novamente: https://www.python.org/downloads/"
}

function Test-ProjectPathLength {
    $rootPath = (Resolve-Path ".").Path
    Write-Host "Pasta atual: $rootPath"

    if ($rootPath.Length -gt 120) {
        Write-Host "" -ForegroundColor Yellow
        Write-Host "ATENCAO: o caminho desta pasta esta longo demais para algumas dependencias no Windows." -ForegroundColor Yellow
        Write-Host "Comprimento atual: $($rootPath.Length) caracteres." -ForegroundColor Yellow
        Write-Host "Use uma unica pasta do projeto, por exemplo: H:\Meu Drive\NUT MEV_NEW" -ForegroundColor Yellow
        throw "Caminho longo detectado. Mova ou clone o projeto para uma pasta unica e rode novamente."
    }
}

if (-not (Test-Path "pyproject.toml")) {
    throw "Execute este script dentro da pasta raiz do repositorio NutEV-Evidence-Engine, onde existe pyproject.toml."
}

Write-Step "Validando caminho do projeto"
Test-ProjectPathLength

Write-Step "Configurando Git para aceitar caminhos longos neste usuario"
try {
    git config --global core.longpaths true
} catch {
    Write-Host "Aviso: nao consegui configurar git core.longpaths. Continue se o projeto estiver em uma pasta curta." -ForegroundColor Yellow
}

Write-Step "Validando Python"
$PythonExe = Resolve-PythonExecutable
Write-Host "Python selecionado: $PythonExe"

Write-Step "Criando ambiente virtual .venv"
if (-not (Test-Path ".venv")) {
    Invoke-Checked $PythonExe -m venv .venv
}

$VenvPython = Join-Path ".venv" "Scripts\python.exe"
$VenvNutev = Join-Path ".venv" "Scripts\nutev.exe"
$ConstraintsFile = Join-Path "constraints" "windows.txt"

Write-Step "Atualizando pip"
Invoke-Checked $VenvPython -m pip install --upgrade pip

Write-Step "Instalando NutEV/NutMEV com dashboard e API"
if (Test-Path $ConstraintsFile) {
    Invoke-Checked $VenvPython -m pip install --no-cache-dir -c $ConstraintsFile -e ".[dashboard,platform]"
} else {
    Invoke-Checked $VenvPython -m pip install --no-cache-dir -e ".[dashboard,platform]"
}

Write-Step "Estabilizando stack HTTP no Windows"
if (Test-Path $ConstraintsFile) {
    Invoke-Checked $VenvPython -m pip install --no-cache-dir -c $ConstraintsFile requests urllib3 charset-normalizer chardet
}
Invoke-Checked $VenvPython -c "import requests, urllib3, charset_normalizer; print('requests=', requests.__version__, 'urllib3=', urllib3.__version__, 'charset_normalizer=', charset_normalizer.__version__)"

Write-Step "Instalando navegador Chromium do Playwright quando disponivel"
try {
    Invoke-Checked $VenvPython -m playwright install chromium
} catch {
    Write-Host "Aviso: Playwright Chromium nao foi instalado automaticamente. O dashboard e a demo ainda podem funcionar; para captura web, rode depois: .\.venv\Scripts\python.exe -m playwright install chromium" -ForegroundColor Yellow
}

Write-Step "Gerando dados demo"
Invoke-Checked $VenvNutev demo-data --project-root ./project_output_demo

Write-Step "Checando instalacao"
Invoke-Checked $VenvPython scripts/check_local.py

Write-Host "`nPronto. Para abrir o dashboard:" -ForegroundColor Green
Write-Host "  .\scripts\run_dashboard_windows.ps1"
Write-Host "`nPara abrir a API local:" -ForegroundColor Green
Write-Host "  .\scripts\run_api_windows.ps1"
