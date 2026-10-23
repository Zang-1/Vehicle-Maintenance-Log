@echo off
setlocal
rem Double-click: run the whole stack locally (web + PostgreSQL) and open the browser.
rem Windows only. Needs Podman Desktop / Podman 4+ with "podman compose".
cd /d "%~dp0"
echo === Vehicle Maintenance Log - chay local ===

where podman >nul 2>&1
if errorlevel 1 (
  echo [Loi] Chua cai Podman. Cai Podman Desktop roi chay lai file nay.
  goto :end
)

podman machine list --format "{{.LastUp}}" | findstr /i "running" >nul
if errorlevel 1 (
  echo Dang khoi dong Podman machine...
  podman machine start
  if errorlevel 1 goto :fail
)

if not exist .env (
  echo Chua co .env: tao tu .env.example voi mat khau DB ngau nhien...
  powershell -NoProfile -Command "$p = -join ((48..57) + (97..122) | Get-Random -Count 16 | %% { [char]$_ }); (Get-Content .env.example) -replace '^DB_PASSWORD=$', ('DB_PASSWORD=' + $p) | Set-Content .env -Encoding ascii"
)

rem On some Windows machines "podman machine start" cannot create the Docker API pipe
rem (win-sshproxy fails), so compose talks to Podman over TCP, reachable from this PC only.
curl -s -m 3 http://localhost:23750/_ping >nul 2>&1
if errorlevel 1 (
  echo Mo cong API cua Podman tren 127.0.0.1:23750...
  podman machine ssh "nohup podman system service --time=0 tcp://127.0.0.1:23750 >/tmp/svc.log 2>&1 &"
  ping -n 4 127.0.0.1 >nul
)
set DOCKER_HOST=tcp://localhost:23750

echo Dang build va khoi dong web + database, lan dau mat 1-2 phut...
podman compose up --build -d
if errorlevel 1 goto :fail

echo Cho ung dung san sang...
set /a tries=0
:wait
curl -s -m 2 http://localhost:3000/health >nul 2>&1
if not errorlevel 1 goto :ready
set /a tries+=1
if %tries% geq 60 goto :fail
ping -n 3 127.0.0.1 >nul
goto :wait

:ready
echo.
echo San sang: http://localhost:3000
echo Kiem tra database: http://localhost:3000/health/db
echo De dung: bam dup dung-local.bat
if not defined NO_BROWSER start "" http://localhost:3000
goto :end

:fail
echo.
echo [Loi] Khong khoi dong duoc. Xem log bang lenh: podman compose logs web

:end
if not defined NO_PAUSE pause
endlocal
