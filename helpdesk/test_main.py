from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from main import app, get_db
from models import Ticket, PrestamoEquipo

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine_test = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)

Base.metadata.create_all(bind=engine_test)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

def test_camino_feliz_y_rechazo_duplicado():
    db = TestingSessionLocal()
    ticket = Ticket(id=1, title="Prueba", description="Test", status="open")
    db.add(ticket)
    db.commit()
    db.close()

    futuro = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()

    # Camino feliz
    res = client.post(
        "/api/tickets/1/equipment-loans",
        json={"etiqueta_equipo": "PC-09", "receptor": "Juan Pérez", "devolucion_esperada": futuro}
    )
    assert res.status_code == 201

    # Rechazo por duplicado activo
    res_dup = client.post(
        "/api/tickets/1/equipment-loans",
        json={"etiqueta_equipo": "PC-09", "receptor": "Otro", "devolucion_esperada": futuro}
    )
    assert res_dup.status_code == 422

    # Verificar que solo hay 1 registro en BD
    db_v = TestingSessionLocal()
    total = db_v.query(PrestamoEquipo).count()
    assert total == 1
    db_v.close()