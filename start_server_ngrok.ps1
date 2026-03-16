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

Write-Host ''
Write-Host '=== INICIANDO FLASK + NGROK ===' -ForegroundColor Cyan
Write-Host ''

$workspace = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $workspace

# 1) Flask server
if (-not (Test-PortListening -TestPort $Port)) {
    Write-Host "[1/2] Subindo servidor Flask na porta $Port..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$workspace'; py app.py"
}
else {
    Write-Host "[1/2] Servidor Flask ja ativo na porta $Port." -ForegroundColor Green
}

Start-Sleep -Seconds $WaitSeconds

# 2) ngrok
$ngrokRunning = Get-Process ngrok -ErrorAction SilentlyContinue
if (-not $ngrokRunning) {
    Write-Host "[2/2] Subindo ngrok para http://localhost:$Port ..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "ngrok http $Port"
    Start-Sleep -Seconds 3
}
else {
    Write-Host '[2/2] ngrok ja ativo.' -ForegroundColor Green
}

# 3) Summary
$localUrl = "http://localhost:$Port"
$publicUrl = Get-NgrokPublicUrl

Write-Host ''
Write-Host '=== STATUS ===' -ForegroundColor Cyan
Write-Host "Local:  $localUrl" -ForegroundColor White

if ($publicUrl) {
    Write-Host "Publico: $publicUrl" -ForegroundColor White
}
else {
    Write-Host 'Publico: (ainda indisponivel, aguarde alguns segundos e rode novamente)' -ForegroundColor DarkYellow
}

Write-Host ''
Write-Host 'Pronto. Os processos foram iniciados em janelas separadas.' -ForegroundColor Green
