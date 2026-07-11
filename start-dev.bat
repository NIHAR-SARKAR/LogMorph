@echo off
setlocal enabledelayedexpansion

:: LogMorph AI one-click development launcher
:: Reads all config from backend/.env and frontend/.env
:: SSL is optional — only added if SSL_KEY_FILE and SSL_CERT_FILE are both set

set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"

:: --- Read backend config from backend/.env ---
set "BACKEND_HOST=0.0.0.0"
set "BACKEND_PORT=8000"
set "SSL_KEY_FILE="
set "SSL_CERT_FILE="
if exist "%ROOT%\backend\.env" (
    for /f "usebackq tokens=1,2 delims==" %%a in ("%ROOT%\backend\.env") do (
        set "_key=%%a"
        set "_val=%%b"
        if "!_key!"=="BACKEND_HOST" set "BACKEND_HOST=!_val!"
        if "!_key!"=="BACKEND_PORT" set "BACKEND_PORT=!_val!"
        if "!_key!"=="SSL_KEY_FILE" set "SSL_KEY_FILE=!_val!"
        if "!_key!"=="SSL_CERT_FILE" set "SSL_CERT_FILE=!_val!"
    )
)

:: --- Read frontend config from frontend/.env ---
set "FRONTEND_PORT=3000"
:: VITE_ALLOWED_HOSTS is handled inside vite.config.ts, not passed as --host
:: --host 0.0.0.0 binds to all interfaces so all allowed hosts can reach it
set "FRONTEND_BIND_HOST=0.0.0.0"
if exist "%ROOT%\frontend\.env" (
    for /f "usebackq tokens=1,2 delims==" %%a in ("%ROOT%\frontend\.env") do (
        set "_key=%%a"
        set "_val=%%b"
        if "!_key!"=="VITE_PORT" set "FRONTEND_PORT=!_val!"
    )
)

:: --- Build SSL args for uvicorn (only if both key + cert are set) ---
set "SSL_ARGS="
if defined SSL_KEY_FILE (
    if defined SSL_CERT_FILE (
        if not "!SSL_KEY_FILE!"=="" (
            if not "!SSL_CERT_FILE!"=="" (
                set "SSL_ARGS= --ssl-keyfile !SSL_KEY_FILE! --ssl-certfile !SSL_CERT_FILE!"
            )
        )
    )
)

:: --- Determine protocol for display ---
set "PROTOCOL=http"
if not "!SSL_ARGS!"=="" set "PROTOCOL=https"

echo Starting LogMorph AI development servers...
echo Backend:  !PROTOCOL://!localhost:!BACKEND_PORT!
if not "!SSL_ARGS!"=="" echo   SSL: !SSL_KEY_FILE!
echo Frontend: http://localhost:!FRONTEND_PORT!
echo.

:: Start backend in a new window
start "LogMorph AI Backend" cmd /k "cd /d "%ROOT%\backend" && call .venv\Scripts\activate && uvicorn app.main:app --reload --host !BACKEND_HOST! --port !BACKEND_PORT!!SSL_ARGS!"

:: Give the backend a moment to initialize before the frontend starts
timeout /t 3 /nobreak >nul

:: Start frontend in a new window
start "LogMorph AI Frontend" cmd /k "cd /d "%ROOT%\frontend" && npm run dev -- --host !FRONTEND_BIND_HOST! --port !FRONTEND_PORT!"

echo.
echo Both servers are starting in separate windows.
echo Close those windows to stop the servers.
pause
