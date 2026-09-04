@echo off
REM Busca vagas novas nas fontes e pontua. Rode uma vez por dia.

cd /d "%~dp0..\backend"

if not exist ".venv\Scripts\python.exe" (
    echo Ambiente virtual nao encontrado em backend\.venv
    pause
    exit /b 1
)

chcp 65001 > nul
".venv\Scripts\python.exe" manage.py collect

echo.
echo Terminou. Abra o scripts\dev.bat para triar as novas.
pause
