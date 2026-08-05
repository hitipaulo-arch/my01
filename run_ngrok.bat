@echo off
setlocal

cd /d "%~dp0"

if not exist "start_server_ngrok.ps1" (
    echo [ERRO] Script start_server_ngrok.ps1 nao encontrado.
    pause
    exit /b 1
)

echo [INFO] Iniciando Flask + ngrok...
powershell -NoProfile -ExecutionPolicy Bypass -File "start_server_ngrok.ps1"

if errorlevel 1 (
    echo.
    echo [ERRO] Falha ao iniciar Flask + ngrok.
    pause
)

endlocal
