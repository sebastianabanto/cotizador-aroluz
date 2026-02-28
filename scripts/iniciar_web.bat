@echo off
title AROLUZ Cotizador Web
echo.
echo  ====================================================
echo   AROLUZ Cotizador Web v2.0
echo  ====================================================
echo.
echo  Iniciando servidor en http://localhost:8000
echo  Para acceder desde otros dispositivos en la red:
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4"') do (
  set IP=%%a
  goto :found
)
:found
echo  http://%IP:~1%:8000
echo.
echo  Usuario: admin
echo  Contrasena: aroluz2024  (cambiar en Configuracion)
echo.
echo  Presiona Ctrl+C para detener el servidor.
echo  ====================================================
echo.

cd /d "%~dp0.."
venv\Scripts\python.exe -m uvicorn web.main:app --host 0.0.0.0 --port 8000

pause
