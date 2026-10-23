@echo off
setlocal
rem Double-click: stop the local stack started by chay-local.bat. Data is kept (no -v).
cd /d "%~dp0"
curl -s -m 3 http://localhost:23750/_ping >nul 2>&1
if not errorlevel 1 set DOCKER_HOST=tcp://localhost:23750
podman compose down
echo Da dung. Du lieu van con, lan sau chay lai chay-local.bat.
if not defined NO_PAUSE pause
endlocal
