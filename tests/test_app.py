import pytest
import time
from fastapi.testclient import TestClient

def test_health_check(client: TestClient):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_employee_success(client: TestClient):
    """Сценарий 1: Успешное добавление сотрудника."""
    payload = {
        "name": "Иван Петров",
        "position": "Backend Разработчик",
        "department": "Разработка"
    }
    response = client.post("/api/employees", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["name"] == "Иван Петров"
    assert data["position"] == "Backend Разработчик"
    assert data["department"] == "Разработка"


def test_create_employee_validation_empty_name(client: TestClient):
    """Сценарий 2: Валидация при добавлении сотрудника с пустым именем."""
    payload = {
        "name": "   ",
        "position": "Тестировщик",
        "department": "QA"
    }
    response = client.post("/api/employees", json=payload)
    assert response.status_code == 422  # Ошибка валидации Pydantic


def test_start_timer_success(client: TestClient):
    """Сценарий 3: Запуск таймера для сотрудника."""
    emp_res = client.post("/api/employees", json={"name": "Анна Сидорова", "position": "Дизайнер"})
    emp_id = emp_res.json()["id"]

    timer_res = client.post("/api/timers/start", json={
        "employee_id": emp_id,
        "task_description": "Разработка макета главной страницы"
    })
    assert timer_res.status_code == 200
    timer_data = timer_res.json()
    assert timer_data["employee_id"] == emp_id
    assert timer_data["task_description"] == "Разработка макета главной страницы"
    assert timer_data["end_time"] is None


def test_start_timer_empty_task_rejected(client: TestClient):
    """Сценарий 4: Попытка запустить таймер с пустым описанием задачи."""
    emp_res = client.post("/api/employees", json={"name": "Максим Кузнецов", "position": "QA"})
    emp_id = emp_res.json()["id"]

    timer_res = client.post("/api/timers/start", json={
        "employee_id": emp_id,
        "task_description": "   "
    })
    assert timer_res.status_code == 422


def test_start_timer_nonexistent_employee(client: TestClient):
    """Сценарий 5: Попытка запустить таймер для несуществующего сотрудника."""
    timer_res = client.post("/api/timers/start", json={
        "employee_id": 99999,
        "task_description": "Несуществующая задача"
    })
    assert timer_res.status_code == 400
    assert "не найден" in timer_res.json()["detail"].lower()


def test_start_timer_duplicate_prevented(client: TestClient):
    """
    Сценарий 6 (Критический): Проверка повторного запуска таймера.
    Если у сотрудника уже запущен таймер, повторный запуск должен блокироваться с ошибкой 400.
    """
    emp_res = client.post("/api/employees", json={"name": "Дмитрий Орлов", "position": "DevOps"})
    emp_id = emp_res.json()["id"]

    # Первый запуск - успешно
    first_res = client.post("/api/timers/start", json={
        "employee_id": emp_id,
        "task_description": "Настройка CI/CD пайплайна"
    })
    assert first_res.status_code == 200

    # Повторный запуск для того же сотрудника без остановки предыдущего
    second_res = client.post("/api/timers/start", json={
        "employee_id": emp_id,
        "task_description": "Вторая задача параллельно"
    })
    assert second_res.status_code == 400
    detail = second_res.json()["detail"]
    assert "уже запущен таймер" in detail
    assert "Настройка CI/CD пайплайна" in detail


def test_stop_timer_success(client: TestClient):
    """Сценарий 7: Успешная остановка таймера с расчётом времени."""
    emp_res = client.post("/api/employees", json={"name": "Ольга Николаева", "position": "Аналитик"})
    emp_id = emp_res.json()["id"]

    start_res = client.post("/api/timers/start", json={
        "employee_id": emp_id,
        "task_description": "Анализ требований заказчика"
    })
    entry_id = start_res.json()["id"]

    time.sleep(0.05)

    stop_res = client.post("/api/timers/stop", json={"time_entry_id": entry_id})
    assert stop_res.status_code == 200
    data = stop_res.json()
    assert data["id"] == entry_id
    assert data["end_time"] is not None
    assert data["duration_seconds"] >= 0
    assert "duration_formatted" in data


def test_stop_timer_already_stopped_fails(client: TestClient):
    """Сценарий 8: Попытка остановить уже остановленный таймер."""
    emp_res = client.post("/api/employees", json={"name": "Сергей Белов", "position": "Архитектор"})
    emp_id = emp_res.json()["id"]

    start_res = client.post("/api/timers/start", json={
        "employee_id": emp_id,
        "task_description": "Разработка схемы БД"
    })
    entry_id = start_res.json()["id"]

    # Останавливаем первый раз
    stop1 = client.post("/api/timers/stop", json={"time_entry_id": entry_id})
    assert stop1.status_code == 200

    # Попытка остановить повторно
    stop2 = client.post("/api/timers/stop", json={"time_entry_id": entry_id})
    assert stop2.status_code == 400
    assert "не найден или уже был остановлен" in stop2.json()["detail"]


def test_stop_timer_by_employee_id(client: TestClient):
    """Сценарий 9: Остановка таймера по employee_id вместо time_entry_id."""
    emp_res = client.post("/api/employees", json={"name": "Валерий Григорьев", "position": "Team Lead"})
    emp_id = emp_res.json()["id"]

    client.post("/api/timers/start", json={
        "employee_id": emp_id,
        "task_description": "Проведение ежедневного дейли"
    })

    stop_res = client.post("/api/timers/stop", json={"employee_id": emp_id})
    assert stop_res.status_code == 200
    assert stop_res.json()["employee_id"] == emp_id
    assert stop_res.json()["end_time"] is not None


def test_sequential_timers_for_same_employee(client: TestClient):
    """Сценарий 10: Последовательный запуск нескольких задач (старт -> стоп -> старт -> стоп)."""
    emp_res = client.post("/api/employees", json={"name": "Татьяна Павлова", "position": "Frontend"})
    emp_id = emp_res.json()["id"]

    # Задача 1
    t1 = client.post("/api/timers/start", json={"employee_id": emp_id, "task_description": "Задача 1"}).json()
    client.post("/api/timers/stop", json={"time_entry_id": t1["id"]})

    # Задача 2 - должна успешно запуститься
    t2_res = client.post("/api/timers/start", json={"employee_id": emp_id, "task_description": "Задача 2"})
    assert t2_res.status_code == 200
    t2 = t2_res.json()
    client.post("/api/timers/stop", json={"time_entry_id": t2["id"]})

    # Проверяем отчёт по этому сотруднику
    report = client.get(f"/api/reports?employee_id={emp_id}").json()
    assert report["total_tasks_count"] == 2
    assert len(report["entries"]) == 2


def test_empty_report_scenario(client: TestClient):
    """
    Сценарий 11 (Критический): Проверка пустого отчёта.
    Если за выбранный диапазон дат записей нет, API должно вернуть:
    - total_seconds == 0
    - total_formatted == "00:00:00"
    - пустые списки summary_by_employee и entries
    - без исключений 500 и падений.
    """
    response = client.get("/api/reports?start_date=2099-01-01&end_date=2099-01-31")
    assert response.status_code == 200
    report = response.json()
    assert report["total_seconds"] == 0
    assert report["total_formatted"] == "00:00:00"
    assert report["total_tasks_count"] == 0
    assert report["summary_by_employee"] == []
    assert report["entries"] == []


def test_report_with_completed_tasks(client: TestClient):
    """Сценарий 12: Формирование отчёта с реальными завершёнными задачами и фильтрацией по сотруднику."""
    emp_res = client.post("/api/employees", json={"name": "Константин Морозов", "position": "Тестировщик"})
    emp_id = emp_res.json()["id"]

    # Запускаем и останавливаем задачу
    start_res = client.post("/api/timers/start", json={
        "employee_id": emp_id,
        "task_description": "Интеграционное тестирование"
    })
    entry_id = start_res.json()["id"]
    client.post("/api/timers/stop", json={"time_entry_id": entry_id})

    # Запрашиваем отчёт с фильтром по конкретному сотруднику
    report_res = client.get(f"/api/reports?employee_id={emp_id}")
    assert report_res.status_code == 200
    report = report_res.json()
    assert report["total_tasks_count"] == 1
    assert len(report["summary_by_employee"]) == 1
    assert report["summary_by_employee"][0]["employee_name"] == "Константин Морозов"
    assert len(report["entries"]) == 1
    assert report["entries"][0]["task_description"] == "Интеграционное тестирование"

    # Также проверяем, что в общем отчёте этот сотрудник тоже присутствует
    all_report = client.get("/api/reports").json()
    emp_names = [s["employee_name"] for s in all_report["summary_by_employee"]]
    assert "Константин Морозов" in emp_names


def test_persistence_across_connection_close(temp_db_path):
    """
    Сценарий 13: Проверка сохранения данных после перезапуска/переподключения к БД.
    """
    from app.database import get_connection, init_db
    import app.crud as crud
    from app.models import EmployeeCreate

    # Шаг 1: Инициализируем и записываем данные в первом соединении
    init_db(db_path=temp_db_path, seed=False)
    with get_connection(db_path=temp_db_path) as conn1:
        created = crud.create_employee(conn1, EmployeeCreate(name="Екатерина Смирнова", position="HR"))
        emp_id = created["id"]
        crud.start_timer(conn1, emp_id, "Собеседование кандидата")

    # Шаг 2: Открываем совершенно новое соединение к тому же файлу БД (симуляция рестарта)
    with get_connection(db_path=temp_db_path) as conn2:
        employees = crud.get_all_employees(conn2)
        katya = next(e for e in employees if e["name"] == "Екатерина Смирнова")
        assert katya["position"] == "HR"
        assert katya["active_timer"] is not None
        assert katya["active_timer"]["task_description"] == "Собеседование кандидата"
