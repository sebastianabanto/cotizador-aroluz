@echo off
title Reset historial de cotizaciones
cd /d "%~dp0.."
venv\Scripts\python.exe reset_cotizaciones.py
echo.
pause
