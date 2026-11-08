import sqlite3
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "timetracker.db")

def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Создаёт и настраивает подключение к базе данных SQLite."""
    path = db_path or DEFAULT_DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db(db_path: Optional[str] = None, seed: bool = True):
    """Инициализация схемы базы данных и заполнение первичными вымышленными данными."""
    path = db_path or DEFAULT_DB_PATH
    with get_connection(path) as conn:
        cursor = conn.cursor()
        
        # Таблица сотрудников
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                position TEXT NOT NULL,
                department TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );
        """)

        # Таблица записей времени
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS time_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                task_description TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                duration_seconds INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
            );
        """)

        # Индексы для ускорения выборок по датам и сотрудникам
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entries_employee ON time_entries(employee_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entries_start_time ON time_entries(start_time);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entries_end_time ON time_entries(end_time);")

        conn.commit()

        if seed:
            seed_mock_data_if_empty(conn)

def seed_mock_data_if_empty(conn: sqlite3.Connection):
    """Заполняет базу вымышленными данными, если таблица сотрудников пуста."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM employees;")
    count = cursor.fetchone()["count"]
    if count > 0:
        return

    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    fictional_employees = [
        ("Алексей Смирнов", "Senior Backend Developer", "IT разработка"),
        ("Елена Васильева", "Frontend Разработчик", "IT разработка"),
        ("Максим Кузнецов", "QA Инженер", "Контроль качества"),
        ("Ольга Морозова", "UI/UX Дизайнер", "Продуктовый дизайн"),
    ]

    for name, pos, dept in fictional_employees:
        cursor.execute(
            "INSERT INTO employees (name, position, department, created_at) VALUES (?, ?, ?, ?)",
            (name, pos, dept, now_iso)
        )

    # Добавим несколько завершённых задач за последние 2 дня
    today_start = now.replace(hour=6, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)

    mock_entries = [
        (1, "Проектирование архитектуры REST API", yesterday_start.isoformat(), (yesterday_start + timedelta(hours=3, minutes=30)).isoformat(), 12600),
        (2, "Верстка компонентов карточек и таймера", yesterday_start.isoformat(), (yesterday_start + timedelta(hours=4, minutes=15)).isoformat(), 15300),
        (3, "Составление тест-кейсов для сценариев таймера", yesterday_start.isoformat(), (yesterday_start + timedelta(hours=2, minutes=45)).isoformat(), 9900),
        (4, "Создание UI-кита и цветовой палитры интерфейса", yesterday_start.isoformat(), (yesterday_start + timedelta(hours=5, minutes=0)).isoformat(), 18000),
        (1, "Оптимизация SQL-запросов отчетов", today_start.isoformat(), (today_start + timedelta(hours=2, minutes=20)).isoformat(), 8400),
        (2, "Интеграция API таймера с фронтендом", today_start.isoformat(), (today_start + timedelta(hours=3, minutes=10)).isoformat(), 11400),
        (3, "Автоматизированное тестирование сценариев повторного запуска", today_start.isoformat(), (today_start + timedelta(hours=1, minutes=50)).isoformat(), 6600),
    ]

    for emp_id, task, start_t, end_t, dur in mock_entries:
        cursor.execute(
            """INSERT INTO time_entries 
               (employee_id, task_description, start_time, end_time, duration_seconds, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (emp_id, task, start_t, end_t, dur, start_t)
        )

    conn.commit()
