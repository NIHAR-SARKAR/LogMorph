@echo off
setlocal enabledelayedexpansion

:: LogMorph AI one-click development launcher
:: Starts the backend (Uvicorn) and frontend (Vite) in separate windows.

set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"

echo Starting LogMorph AI development servers...
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo.

:: Start backend in a new window
start "LogMorph AI Backend" cmd /k "cd /d "%ROOT%\backend" && call .venv\Scripts\activate && uvicorn app.main:app --reload --port 8000"

:: Give the backend a moment to initialize before the frontend starts
timeout /t 3 /nobreak >nul

:: Start frontend in a new window, pointing Vite directly at the backend API
start "LogMorph AI Frontend" cmd /k "cd /d "%ROOT%\frontend" && set VITE_API_URL=http://localhost:8000 && npm run dev -- --port 3000"

echo.
echo Both servers are starting in separate windows.
echo Close those windows to stop the servers.
pause
