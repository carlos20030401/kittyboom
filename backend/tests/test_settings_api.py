from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.api import require_admin
from app.models import Role, User

engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
TestingSession=sessionmaker(bind=engine,expire_on_commit=False)

def test_saved_whatsapp_is_returned_after_new_request():
    Base.metadata.create_all(engine)
    db=TestingSession(); role=Role(name="admin"); db.add(role); db.flush(); user=User(email="test@kittyboom.pe",password_hash="unused",role_id=role.id); db.add(user); db.commit()
    def override_db():
        session=TestingSession()
        try: yield session
        finally: session.close()
    app.dependency_overrides[get_db]=override_db
    app.dependency_overrides[require_admin]=lambda:user
    client=TestClient(app)
    response=client.put("/api/v1/admin/settings",json={"business_name":"KittyBoom","whatsapp":"987654321","currency":"S/"})
    assert response.status_code==200
    reloaded=TestClient(app).get("/api/v1/public/settings")
    assert reloaded.status_code==200
    assert reloaded.json()["whatsapp"]=="987654321"
    app.dependency_overrides.clear(); Base.metadata.drop_all(engine)
