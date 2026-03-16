@echo off
setlocal

cd /d "%~dp0"

where ngrok >nul 2>&1
if errorlevel 1 (
    echo [ERRO] ngrok nao encontrado no PATH.
    echo Instale o ngrok e tente novamente.
    pause
    exit /b 1
)

echo [INFO] Iniciando ngrok na porta 5000...
ngrok http 5000

if errorlevel 1 (
    echo.
    echo [ERRO] Falha ao iniciar o ngrok.
    pause
)

endlocal
