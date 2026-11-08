import os
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database import get_connection, init_db, DEFAULT_DB_PATH
from app.models import (
    EmployeeCreate,
    EmployeeOut,
    TimerStartRequest,
    TimerStopRequest,
    TimeEntryOut,
    ReportResponse
)
from app import crud

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Инициализация БД при старте приложения
    init_db()
    yield

app = FastAPI(
    title="Система учёта рабочего времени",
    description="Веб-приложение для учёта рабочего времени сотрудников компании",
    version="1.0.0",
    lifespan=lifespan
)

# Подключение статических файлов и шаблонов
static_dir = os.path.join(BASE_DIR, "static")
templates_dir = os.path.join(BASE_DIR, "templates")

os.makedirs(static_dir, exist_ok=True)
os.makedirs(os.path.join(static_dir, "css"), exist_ok=True)
os.makedirs(os.path.join(static_dir, "js"), exist_ok=True)
os.makedirs(templates_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)


@app.get("/", response_class=HTMLResponse)
async def index_page(request: Request):
    """Главная страница приложения с панелью управления."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/health")
async def health_check():
    """Проверка доступности сервиса."""
    return {"status": "ok", "app": "TimeTracker Pro"}


@app.get("/api/employees")
async def get_employees():
    """Возвращает список всех сотрудников с информацией об их активных таймерах."""
    with get_connection() as conn:
        employees = crud.get_all_employees(conn)
        return employees


@app.post("/api/employees", status_code=201)
async def create_employee(data: EmployeeCreate):
    """Добавляет нового сотрудника в систему."""
    with get_connection() as conn:
        new_emp = crud.create_employee(conn, data)
        return new_emp


@app.get("/api/timers/active")
async def get_active_timers():
    """Возвращает список всех запущенных таймеров."""
    with get_connection() as conn:
        timers = crud.get_active_timers(conn)
        return timers


@app.post("/api/timers/start")
async def start_timer(req: TimerStartRequest):
    """
    Запускает таймер с описанием задачи для сотрудника.
    Если у сотрудника уже есть активный таймер, возвращает ошибку 400.
    """
    with get_connection() as conn:
        try:
            entry = crud.start_timer(conn, req.employee_id, req.task_description)
            return entry
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/timers/stop")
async def stop_timer(req: TimerStopRequest):
    """
    Останавливает таймер по time_entry_id или employee_id.
    Вычисляет затраченное время и сохраняет запись.
    """
    if req.time_entry_id is None and req.employee_id is None:
        raise HTTPException(
            status_code=400,
            detail="Необходимо указать time_entry_id или employee_id для остановки таймера."
        )

    with get_connection() as conn:
        try:
            entry = crud.stop_timer(conn, time_entry_id=req.time_entry_id, employee_id=req.employee_id)
            return entry
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/reports", response_model=ReportResponse)
async def get_reports(
    start_date: Optional[str] = Query(None, description="Начальная дата (YYYY-MM-DD или ISO)"),
    end_date: Optional[str] = Query(None, description="Конечная дата (YYYY-MM-DD или ISO)"),
    employee_id: Optional[int] = Query(None, description="ID конкретного сотрудника (опционально)")
):
    """
    Возвращает отчёт и общее время сотрудников за указанный период.
    При отсутствии записей корректно возвращает пустой отчёт (0 часов, пустые списки).
    """
    with get_connection() as conn:
        report = crud.get_report_data(
            conn,
            start_date=start_date,
            end_date=end_date,
            employee_id=employee_id
        )
        return report
