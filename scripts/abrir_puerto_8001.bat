@echo off
netsh advfirewall firewall add rule name="AROLUZ Asistencias Puerto 8001" dir=in action=allow protocol=TCP localport=8001 profile=any
echo.
echo Listo. Puerto 8001 habilitado en el firewall.
pause
