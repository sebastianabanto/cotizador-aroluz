@echo off
cd /d "%~dp0\.."
echo Iniciando AROLUZ Asistencias en http://localhost:8001
venv\Scripts\python.exe -m uvicorn asistencias.main:app --host 0.0.0.0 --port 8001
pause
