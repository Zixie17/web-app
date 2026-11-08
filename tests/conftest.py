import os
import gc
import tempfile
import pytest
from fastapi.testclient import TestClient
import app.database as database
from app.main import app

@pytest.fixture
def temp_db_path(monkeypatch):
    """Создает временный файл базы данных для изоляции тестов."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    monkeypatch.setattr("app.database.DEFAULT_DB_PATH", path)
    
    yield path

    # Принудительный сбор мусора для закрытия дескрипторов файлов на Windows
    gc.collect()
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


@pytest.fixture
def client(monkeypatch, temp_db_path):
    """Тестовый клиент FastAPI с чистой базой данных без начальных фиктивных данных."""
    database.init_db(db_path=temp_db_path, seed=False)

    def test_get_connection():
        return database.get_connection(db_path=temp_db_path)

    monkeypatch.setattr("app.main.get_connection", test_get_connection)
    monkeypatch.setattr("app.database.DEFAULT_DB_PATH", temp_db_path)

    with TestClient(app) as test_client:
        yield test_client
