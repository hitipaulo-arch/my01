@echo off
setlocal

cd /d "%~dp0"

set "NGROK_EXE=%LOCALAPPDATA%\ngrok\ngrok.exe"
if not exist "%NGROK_EXE%" (
    set "NGROK_EXE=%LOCALAPPDATA%\Microsoft\WinGet\Packages\Ngrok.Ngrok_Microsoft.Winget.Source_8wekyb3d8bbwe\ngrok.exe"
)

if not exist "%NGROK_EXE%" (
    for /f "delims=" %%I in ('where ngrok 2^>nul') do (
        set "NGROK_EXE=%%I"
        goto :ngrok_found
    )
)

:ngrok_found
if not defined NGROK_EXE (
    echo [ERRO] ngrok nao encontrado no PATH.
    echo Instale o ngrok e tente novamente.
    pause
    exit /b 1
)

echo %NGROK_EXE% | findstr /I "\WindowsApps\ngrok.exe" >nul
if not errorlevel 1 (
    echo [ERRO] Foi detectada a versao do ngrok da Microsoft Store/MSIX.
    echo Essa distribuicao esta causando a falha de inicializacao.
    echo Instale a versao oficial do ngrok ^(https://ngrok.com/download^) e tente novamente.
    pause
    exit /b 1
)

echo [INFO] Iniciando ngrok na porta 5000...
"%NGROK_EXE%" http 5000

if errorlevel 1 (
    echo.
    echo [ERRO] Falha ao iniciar o ngrok.
    pause
)

endlocal
