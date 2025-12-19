@echo off
chcp 65001 >nul
REM Script to start all services (Windows)

cd /d "%~dp0"

set "PYTHON_CMD=python"
if exist .venv\Scripts\python.exe (
    set "PYTHON_CMD=.venv\Scripts\python.exe"
)

echo Starting all services...
echo Current directory: %CD%
echo.

REM Check if Flask is installed
%PYTHON_CMD% -c "import flask" 2>nul
if errorlevel 1 (
    echo ERROR: Flask not installed!
    echo Install dependencies: pip install -r requirements.txt
    pause
    exit /b 1
)

echo Dependencies OK.
echo.
echo Starting services in separate windows...
echo.

REM Start services with delays
echo [1/6] Starting Message Broker (port 5050)...
start "Message Broker - 5050" /MIN cmd /k "cd /d %CD% && %PYTHON_CMD% backend\message_broker\main.py"
timeout /t 3 /nobreak >nul

echo [2/6] Starting Booking Service (port 5001)...
start "Booking Service - 5001" cmd /k "cd /d %CD% && %PYTHON_CMD% backend\booking_service\main.py"
timeout /t 3 /nobreak >nul

echo [3/6] Starting Payment Service (port 5002)...
start "Payment Service - 5002" cmd /k "cd /d %CD% && %PYTHON_CMD% backend\payment_service\main.py"
timeout /t 3 /nobreak >nul

echo [4/6] Starting Integration Service (port 5003)...
start "Integration Service - 5003" cmd /k "cd /d %CD% && %PYTHON_CMD% backend\integration_service\main.py"
timeout /t 3 /nobreak >nul

echo [5/6] Starting Notification Service (port 5004)...
start "Notification Service - 5004" cmd /k "cd /d %CD% && %PYTHON_CMD% backend\notification_service\main.py"
timeout /t 3 /nobreak >nul

echo [6/6] Starting API Gateway (port 5000)...
start "API Gateway - 5000" cmd /k "cd /d %CD% && %PYTHON_CMD% backend\api_gateway\main.py"
timeout /t 3 /nobreak >nul

echo.
echo ========================================
echo All services started!
echo ========================================
echo.
echo API Gateway:      http://localhost:5000
echo Booking Service:  http://localhost:5001
echo Payment Service:  http://localhost:5002
echo Integration:      http://localhost:5003
echo Notification:     http://localhost:5004
echo Message Broker:   http://localhost:5050
echo.
echo Check status:
echo   curl http://localhost:5000/health
echo.
echo If services show "unavailable", wait 5-10 seconds
echo and check service windows for errors.
echo.
pause
