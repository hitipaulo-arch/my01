param(
    [int]$Port = 5000,
    [int]$WaitSeconds = 4
)

$ErrorActionPreference = 'Stop'

function Test-PortListening {
    param([int]$TestPort)

    $output = netstat -ano | Select-String ":$TestPort"
    foreach ($line in $output) {
        if ($line.Line -match 'LISTENING') {
            return $true
        }
    }

    return $false
}

function Wait-ForPortListening {
    param(
        [int]$TestPort,
        [int]$TimeoutSeconds = 20
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-PortListening -TestPort $TestPort) {
            return $true
        }

        Start-Sleep -Milliseconds 500
    }

    return $false
}

function Get-NgrokPublicUrl {
    try {
        $response = Invoke-WebRequest -Uri 'http://127.0.0.1:4040/api/tunnels' -UseBasicParsing -TimeoutSec 5
        $json = $response.Content | ConvertFrom-Json

        if ($json.tunnels -and $json.tunnels.Count -gt 0) {
            $httpsTunnel = $json.tunnels | Where-Object { $_.proto -eq 'https' } | Select-Object -First 1
            if ($httpsTunnel) {
                return $httpsTunnel.public_url
            }

            return $json.tunnels[0].public_url
        }
    }
    catch {
        return $null
    }

    return $null
}

function Wait-ForNgrokPublicUrl {
    param(
        [int]$TimeoutSeconds = 15
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $publicUrl = Get-NgrokPublicUrl
        if ($publicUrl) {
            return $publicUrl
        }

        Start-Sleep -Milliseconds 500
    }

    return $null
}

function Get-NgrokExecutable {
    $candidatePaths = @(
        Join-Path $env:LOCALAPPDATA 'ngrok\ngrok.exe'
        Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Packages\Ngrok.Ngrok_Microsoft.Winget.Source_8wekyb3d8bbwe\ngrok.exe'
    )

    foreach ($candidate in $candidatePaths) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    try {
        $command = Get-Command ngrok -ErrorAction Stop
        $source = $command.Source

        if ($source -match 'WindowsApps\\ngrok\.exe$') {
            throw "Foi detectada a versao do ngrok da Microsoft Store/MSIX em $source. Instale a versao oficial do ngrok para evitar a falha 'disabled updater should never run'."
        }

        return $source
    }
    catch {
        if ($_.Exception.Message) {
            Write-Host $_.Exception.Message -ForegroundColor Red
        }

        return $null
    }
}

Write-Host ''
Write-Host '=== INICIANDO FLASK + NGROK ===' -ForegroundColor Cyan
Write-Host ''

$workspace = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $workspace

$pythonExe = Join-Path $workspace '.venv\Scripts\python.exe'
if (-not (Test-Path $pythonExe)) {
    $pythonExe = (Get-Command py -ErrorAction Stop).Source
}

# 1) Flask server
if (-not (Test-PortListening -TestPort $Port)) {
    Write-Host "[1/2] Subindo servidor Flask na porta $Port..." -ForegroundColor Yellow
    Start-Process -FilePath $pythonExe -ArgumentList 'app.py' -WorkingDirectory $workspace

    if (-not (Wait-ForPortListening -TestPort $Port -TimeoutSeconds 20)) {
        Write-Host "[ERRO] O Flask nao respondeu na porta $Port dentro do tempo esperado." -ForegroundColor Red
        Write-Host "[ERRO] Verifique o terminal do Flask para identificar a falha de inicializacao." -ForegroundColor Red
        exit 1
    }
}
else {
    Write-Host "[1/2] Servidor Flask ja ativo na porta $Port." -ForegroundColor Green
}

Start-Sleep -Seconds $WaitSeconds

# 2) ngrok
$ngrokExecutable = Get-NgrokExecutable
if (-not $ngrokExecutable) {
    Write-Host '[2/2] ngrok nao encontrado ou instalacao invalida.' -ForegroundColor Red
    Write-Host 'Instale a versao oficial do ngrok em https://ngrok.com/download e tente novamente.' -ForegroundColor Red
    exit 1
}

$ngrokRunning = Get-Process ngrok -ErrorAction SilentlyContinue
if (-not $ngrokRunning) {
    Write-Host "[2/2] Subindo ngrok para http://localhost:$Port ..." -ForegroundColor Yellow
    Start-Process -FilePath $ngrokExecutable -ArgumentList @('http', $Port)
    Start-Sleep -Seconds 3
}
else {
    Write-Host '[2/2] ngrok ja ativo.' -ForegroundColor Green
}

# 3) Summary
$localUrl = "http://localhost:$Port"
$publicUrl = Wait-ForNgrokPublicUrl -TimeoutSeconds 15

Write-Host ''
Write-Host '=== STATUS ===' -ForegroundColor Cyan
Write-Host "Local:  $localUrl" -ForegroundColor White

if ($publicUrl) {
    Write-Host "Publico: $publicUrl" -ForegroundColor White
    try {
        Start-Process $publicUrl
    }
    catch {
        Write-Host '[AVISO] Nao foi possivel abrir o navegador automaticamente.' -ForegroundColor DarkYellow
    }
}
else {
    Write-Host 'Publico: (ainda indisponivel, aguarde alguns segundos e rode novamente)' -ForegroundColor DarkYellow
}

Write-Host ''
Write-Host 'Pronto. Os processos foram iniciados em janelas separadas.' -ForegroundColor Green
