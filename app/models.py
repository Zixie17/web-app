from pydantic import BaseModel, Field, field_validator
from typing import Optional, List

class EmployeeCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="ФИО сотрудника")
    position: str = Field(..., min_length=2, max_length=100, description="Должность")
    department: Optional[str] = Field("", max_length=100, description="Отдел")

    @field_validator("name", "position")
    @classmethod
    def not_empty(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("Поле не может быть пустым или состоять только из пробелов")
        return clean

    @field_validator("department")
    @classmethod
    def clean_department(cls, value: Optional[str]) -> str:
        return (value or "").strip()


class ActiveTimerInfo(BaseModel):
    id: int
    task_description: str
    start_time: str
    elapsed_seconds: Optional[int] = 0


class EmployeeOut(BaseModel):
    id: int
    name: str
    position: str
    department: str
    created_at: str
    active_timer: Optional[ActiveTimerInfo] = None


class TimerStartRequest(BaseModel):
    employee_id: int = Field(..., description="ID сотрудника")
    task_description: str = Field(..., min_length=1, max_length=255, description="Описание выполняемой задачи")

    @field_validator("task_description")
    @classmethod
    def not_empty(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("Описание задачи не может быть пустым")
        return clean


class TimerStopRequest(BaseModel):
    time_entry_id: Optional[int] = Field(None, description="ID записи таймера (если известен)")
    employee_id: Optional[int] = Field(None, description="ID сотрудника (для остановки активного таймера)")


class TimeEntryOut(BaseModel):
    id: int
    employee_id: int
    employee_name: Optional[str] = None
    employee_position: Optional[str] = None
    task_description: str
    start_time: str
    end_time: Optional[str] = None
    duration_seconds: Optional[int] = None
    duration_formatted: Optional[str] = None


class EmployeeReportSummary(BaseModel):
    employee_id: int
    employee_name: str
    position: str
    department: str
    total_seconds: int
    total_formatted: str
    tasks_count: int


class ReportResponse(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    employee_id: Optional[int] = None
    total_seconds: int
    total_formatted: str
    total_tasks_count: int
    summary_by_employee: List[EmployeeReportSummary]
    entries: List[TimeEntryOut]
