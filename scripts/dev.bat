@echo off
REM Sobe o Vaggio inteiro: API do Django em :8000 e front do Vite em :5173.
REM Para parar: feche as duas janelas que abrirem.

cd /d "%~dp0.."

if not exist "backend\.venv\Scripts\python.exe" (
    echo Ambiente virtual nao encontrado em backend\.venv
    echo Rode:  python -m venv backend\.venv ^&^& backend\.venv\Scripts\pip install -r backend\requirements\development.txt
    pause
    exit /b 1
)
if not exist "frontend\node_modules" (
    echo Dependencias do front nao instaladas.
    echo Rode:  cd frontend ^&^& npm install
    pause
    exit /b 1
)

start "vaggio api" cmd /k "cd /d %~dp0..\backend && .venv\Scripts\python.exe manage.py runserver 8000"
start "vaggio web" cmd /k "cd /d %~dp0..\frontend && npm run dev"

timeout /t 4 > nul
start "" http://localhost:5173/
