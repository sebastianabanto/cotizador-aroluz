@echo off
netsh advfirewall firewall add rule name="AROLUZ Web Puerto 8000" dir=in action=allow protocol=TCP localport=8000 profile=any
echo.
echo Listo. Puerto 8000 habilitado en el firewall.
pause
