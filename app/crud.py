import sqlite3
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from app.models import EmployeeCreate

def format_duration(seconds: int) -> str:
    """Форматирует секунды в читаемую строку вида 'ЧЧ:ММ:СС' и часы/минуты."""
    if seconds is None or seconds < 0:
        seconds = 0
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"

def parse_iso_datetime(dt_str: str) -> datetime:
    """Безопасный парсинг ISO 8601 строки с часовым поясом или без него."""
    if not dt_str:
        return datetime.now(timezone.utc)
    # Заменяем суффикс Z на +00:00 для совместимости с fromisoformat
    clean_str = dt_str.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(clean_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return datetime.now(timezone.utc)

def get_employee_by_id(conn: sqlite3.Connection, employee_id: int) -> Optional[sqlite3.Row]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM employees WHERE id = ?", (employee_id,))
    return cursor.fetchone()

def create_employee(conn: sqlite3.Connection, data: EmployeeCreate) -> Dict[str, Any]:
    cursor = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()
    cursor.execute(
        "INSERT INTO employees (name, position, department, created_at) VALUES (?, ?, ?, ?)",
        (data.name, data.position, data.department, now_iso)
    )
    conn.commit()
    emp_id = cursor.lastrowid
    return {
        "id": emp_id,
        "name": data.name,
        "position": data.position,
        "department": data.department,
        "created_at": now_iso,
        "active_timer": None
    }

def get_all_employees(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM employees ORDER BY id ASC")
    employees = cursor.fetchall()
    
    # Получаем все активные таймеры разом
    cursor.execute("SELECT * FROM time_entries WHERE end_time IS NULL")
    active_timers = {row["employee_id"]: row for row in cursor.fetchall()}

    now = datetime.now(timezone.utc)
    result = []
    for emp in employees:
        emp_dict = dict(emp)
        emp_id = emp["id"]
        if emp_id in active_timers:
            t = active_timers[emp_id]
            start_dt = parse_iso_datetime(t["start_time"])
            elapsed = max(0, int((now - start_dt).total_seconds()))
            emp_dict["active_timer"] = {
                "id": t["id"],
                "task_description": t["task_description"],
                "start_time": t["start_time"],
                "elapsed_seconds": elapsed
            }
        else:
            emp_dict["active_timer"] = None
        result.append(emp_dict)
    return result

def get_active_timer(conn: sqlite3.Connection, employee_id: int) -> Optional[sqlite3.Row]:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM time_entries WHERE employee_id = ? AND end_time IS NULL ORDER BY id DESC LIMIT 1",
        (employee_id,)
    )
    return cursor.fetchone()

def start_timer(conn: sqlite3.Connection, employee_id: int, task_description: str) -> Dict[str, Any]:
    cursor = conn.cursor()

    # 1. Проверяем существование сотрудника
    employee = get_employee_by_id(conn, employee_id)
    if not employee:
        raise ValueError(f"Сотрудник с ID {employee_id} не найден.")

    # 2. Проверяем, запущен ли уже таймер у сотрудника
    active = get_active_timer(conn, employee_id)
    if active:
        raise ValueError(
            f"У сотрудника '{employee['name']}' уже запущен таймер для задачи: "
            f"«{active['task_description']}». Завершите текущую задачу перед запуском новой."
        )

    # 3. Запускаем таймер
    now_iso = datetime.now(timezone.utc).isoformat()
    cursor.execute(
        """INSERT INTO time_entries 
           (employee_id, task_description, start_time, end_time, duration_seconds, created_at)
           VALUES (?, ?, ?, NULL, 0, ?)""",
        (employee_id, task_description.strip(), now_iso, now_iso)
    )
    conn.commit()
    entry_id = cursor.lastrowid

    return {
        "id": entry_id,
        "employee_id": employee_id,
        "employee_name": employee["name"],
        "employee_position": employee["position"],
        "task_description": task_description.strip(),
        "start_time": now_iso,
        "end_time": None,
        "duration_seconds": 0,
        "duration_formatted": "00:00:00"
    }

def stop_timer(
    conn: sqlite3.Connection,
    time_entry_id: Optional[int] = None,
    employee_id: Optional[int] = None
) -> Dict[str, Any]:
    cursor = conn.cursor()

    entry = None
    if time_entry_id is not None:
        cursor.execute("SELECT * FROM time_entries WHERE id = ?", (time_entry_id,))
        entry = cursor.fetchone()
    elif employee_id is not None:
        entry = get_active_timer(conn, employee_id)

    if not entry or entry["end_time"] is not None:
        raise ValueError("Активный таймер не найден или уже был остановлен.")

    now = datetime.now(timezone.utc)
    start_dt = parse_iso_datetime(entry["start_time"])
    duration_seconds = max(0, int((now - start_dt).total_seconds()))
    now_iso = now.isoformat()

    cursor.execute(
        "UPDATE time_entries SET end_time = ?, duration_seconds = ? WHERE id = ?",
        (now_iso, duration_seconds, entry["id"])
    )
    conn.commit()

    emp = get_employee_by_id(conn, entry["employee_id"])

    return {
        "id": entry["id"],
        "employee_id": entry["employee_id"],
        "employee_name": emp["name"] if emp else "Неизвестный сотрудник",
        "employee_position": emp["position"] if emp else "",
        "task_description": entry["task_description"],
        "start_time": entry["start_time"],
        "end_time": now_iso,
        "duration_seconds": duration_seconds,
        "duration_formatted": format_duration(duration_seconds)
    }

def get_active_timers(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Возвращает список всех активных таймеров в системе."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.id, t.employee_id, t.task_description, t.start_time,
               e.name as employee_name, e.position as employee_position
        FROM time_entries t
        JOIN employees e ON t.employee_id = e.id
        WHERE t.end_time IS NULL
        ORDER BY t.id DESC
    """)
    now = datetime.now(timezone.utc)
    result = []
    for row in cursor.fetchall():
        start_dt = parse_iso_datetime(row["start_time"])
        elapsed = max(0, int((now - start_dt).total_seconds()))
        result.append({
            "id": row["id"],
            "employee_id": row["employee_id"],
            "employee_name": row["employee_name"],
            "employee_position": row["employee_position"],
            "task_description": row["task_description"],
            "start_time": row["start_time"],
            "elapsed_seconds": elapsed,
            "elapsed_formatted": format_duration(elapsed)
        })
    return result

def get_report_data(
    conn: sqlite3.Connection,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    employee_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Формирует отчёт за выбранный период.
    Возвращает:
    - Общую сумму секунд и форматированное время
    - Количество задач
    - Сводку по каждому сотруднику (общее время и кол-во задач)
    - Список детальных записей
    Корректно обрабатывает пустые периоды, возвращая нули и пустые списки.
    """
    cursor = conn.cursor()

    query_parts = [
        """SELECT t.id, t.employee_id, t.task_description, t.start_time, t.end_time,
                  t.duration_seconds, e.name as employee_name, e.position as employee_position,
                  e.department as employee_department
           FROM time_entries t
           JOIN employees e ON t.employee_id = e.id
           WHERE t.end_time IS NOT NULL"""
    ]
    params: List[Any] = []

    if employee_id:
        query_parts.append("AND t.employee_id = ?")
        params.append(employee_id)

    if start_date:
        # Нормализация даты начала (добавляем начало дня 00:00:00, если указана только дата)
        sd = start_date.strip()
        if len(sd) == 10:  # YYYY-MM-DD
            sd = f"{sd}T00:00:00"
        query_parts.append("AND t.start_time >= ?")
        params.append(sd)

    if end_date:
        # Нормализация даты окончания (добавляем конец дня 23:59:59.999, если указана только дата)
        ed = end_date.strip()
        if len(ed) == 10:  # YYYY-MM-DD
            ed = f"{ed}T23:59:59.999999"
        query_parts.append("AND t.start_time <= ?")
        params.append(ed)

    query_parts.append("ORDER BY t.start_time DESC")
    full_query = " ".join(query_parts)

    cursor.execute(full_query, params)
    raw_entries = cursor.fetchall()

    entries = []
    employee_stats: Dict[int, Dict[str, Any]] = {}
    total_seconds = 0

    for r in raw_entries:
        dur = r["duration_seconds"] or 0
        total_seconds += dur

        entry_dict = {
            "id": r["id"],
            "employee_id": r["employee_id"],
            "employee_name": r["employee_name"],
            "employee_position": r["employee_position"],
            "task_description": r["task_description"],
            "start_time": r["start_time"],
            "end_time": r["end_time"],
            "duration_seconds": dur,
            "duration_formatted": format_duration(dur)
        }
        entries.append(entry_dict)

        emp_id = r["employee_id"]
        if emp_id not in employee_stats:
            employee_stats[emp_id] = {
                "employee_id": emp_id,
                "employee_name": r["employee_name"],
                "position": r["employee_position"],
                "department": r["employee_department"] or "",
                "total_seconds": 0,
                "tasks_count": 0
            }
        employee_stats[emp_id]["total_seconds"] += dur
        employee_stats[emp_id]["tasks_count"] += 1

    # Формируем сводку
    summary_by_employee = []
    for emp_stat in employee_stats.values():
        summary_by_employee.append({
            "employee_id": emp_stat["employee_id"],
            "employee_name": emp_stat["employee_name"],
            "position": emp_stat["position"],
            "department": emp_stat["department"],
            "total_seconds": emp_stat["total_seconds"],
            "total_formatted": format_duration(emp_stat["total_seconds"]),
            "tasks_count": emp_stat["tasks_count"]
        })

    # Сортируем сотрудников по общему времени (по убыванию)
    summary_by_employee.sort(key=lambda x: x["total_seconds"], reverse=True)

    return {
        "start_date": start_date,
        "end_date": end_date,
        "employee_id": employee_id,
        "total_seconds": total_seconds,
        "total_formatted": format_duration(total_seconds),
        "total_tasks_count": len(entries),
        "summary_by_employee": summary_by_employee,
        "entries": entries
    }
