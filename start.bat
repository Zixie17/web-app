@echo off
cd /d "%~dp0"
title TimeTracker Pro

echo ==========================================================
echo   Запуск системы учета рабочего времени...
echo   Открытие веб-интерфейса в браузере...
echo ==========================================================

start "" cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:8000"
python run.py

pause
