"""
Скрипт запуска приложения учёта рабочего времени сотрудников.
Автоматически открывает веб-интерфейс в браузере при старте.
Запуск: python run.py или двойной клик по start.bat
"""
import uvicorn
import webbrowser
import threading
import time
import os
import sys

def open_browser(url: str, delay: float = 1.2):
    """Открывает браузер по переданному URL с небольшой задержкой для инициализации сервера."""
    time.sleep(delay)
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"Не удалось автоматически открыть браузер: {e}")

if __name__ == "__main__":
    host = "127.0.0.1"
    port = 8000
    url = f"http://{host}:{port}"

    print("=" * 65)
    print(" ⏱️  Запуск системы учёта рабочего времени сотрудников")
    print(f" 🌐 Веб-интерфейс: {url}")
    print(f" 📚 Документация API: {url}/docs")
    print(" 🚀 Браузер откроется автоматически через 1-2 секунды...")
    print("=" * 65)

    # Фоновый поток для открытия браузера после старта сервера
    threading.Thread(target=open_browser, args=(url,), daemon=True).start()

    # Запуск ASGI-сервера
    uvicorn.run("app.main:app", host=host, port=port, reload=False)
