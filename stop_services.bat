@echo off
chcp 65001 >nul
REM Скрипт для остановки всех сервисов (Windows)

echo Остановка всех сервисов...

REM Остановка процессов Python, которые могут быть нашими сервисами
REM ВНИМАНИЕ: Это остановит ВСЕ процессы Python! Используйте с осторожностью.

echo Поиск процессов Python на портах сервисов...

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5000"') do (
    echo Остановка процесса на порту 5000 (PID: %%a)
    taskkill /PID %%a /F >nul 2>&1
)

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5001"') do (
    echo Остановка процесса на порту 5001 (PID: %%a)
    taskkill /PID %%a /F >nul 2>&1
)

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5002"') do (
    echo Остановка процесса на порту 5002 (PID: %%a)
    taskkill /PID %%a /F >nul 2>&1
)

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5003"') do (
    echo Остановка процесса на порту 5003 (PID: %%a)
    taskkill /PID %%a /F >nul 2>&1
)

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5004"') do (
    echo Остановка процесса на порту 5004 (PID: %%a)
    taskkill /PID %%a /F >nul 2>&1
)

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5050"') do (
    echo Остановка процесса на порту 5050 (PID: %%a)
    taskkill /PID %%a /F >nul 2>&1
)

echo.
echo Все процессы остановлены.
pause

