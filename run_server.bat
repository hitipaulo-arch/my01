@echo off
setlocal

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    echo [INFO] Usando ambiente virtual .venv
    .venv\Scripts\python.exe app.py
) else (
    echo [INFO] Usando Python do sistema
    python app.py
)

if errorlevel 1 (
    echo.
    echo [ERRO] Falha ao iniciar o servidor.
    pause
)

endlocal
