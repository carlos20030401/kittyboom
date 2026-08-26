from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from app.core.config import Settings
from app.create_admin import ensure_admin
from app.db.base import Base
from app.main import app
from app.models import User
from app.services.storage import CloudinaryStorage
def test_neon_url_normalization_and_production_validation():
    config=Settings(_env_file=None,environment='production',database_url='postgresql://user:pass@host/db?sslmode=require',jwt_secret='x'*40,cors_origins='https://kittyboom.pages.dev',storage_provider='cloudinary',cloudinary_cloud_name='cloud',cloudinary_api_key='key',cloudinary_api_secret='secret')
    assert config.sqlalchemy_url.startswith('postgresql+psycopg://') and config.allowed_origins==['https://kittyboom.pages.dev']
def test_health_and_cors_configuration():
    client=TestClient(app);assert client.get('/health').json()['status'] in {'ok','degraded'}
    allowed=client.options('/api/v1/public/products',headers={'Origin':'http://localhost:5173','Access-Control-Request-Method':'GET'});assert allowed.headers.get('access-control-allow-origin')=='http://localhost:5173'
    denied=client.options('/api/v1/public/products',headers={'Origin':'https://evil.example','Access-Control-Request-Method':'GET'});assert denied.headers.get('access-control-allow-origin') is None
def test_admin_creation_is_idempotent():
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool);Base.metadata.create_all(engine);db=sessionmaker(bind=engine)();first,created=ensure_admin(db,'owner@example.com','safe-password-123');db.commit();second,again=ensure_admin(db,'owner@example.com','different-password');db.commit();assert created and not again and first.id==second.id and db.query(User).count()==1;db.close();Base.metadata.drop_all(engine)
def test_cloudinary_upload_and_delete_with_simulated_provider(monkeypatch):
    import asyncio,sys,types
    from io import BytesIO
    from fastapi import UploadFile
    calls=[];uploader=types.SimpleNamespace(upload=lambda content,**kwargs:{'public_id':'kittyboom/image-1','secure_url':'https://res.cloudinary.com/demo/image/upload/image-1.webp'},destroy=lambda identifier,**kwargs:calls.append(identifier));module=types.SimpleNamespace(config=lambda **kwargs:None,uploader=uploader);monkeypatch.setitem(sys.modules,'cloudinary',module);monkeypatch.setitem(sys.modules,'cloudinary.uploader',uploader);provider=CloudinaryStorage();saved=asyncio.run(provider.save(UploadFile(filename='image.webp',file=BytesIO(b'image'),headers={'content-type':'image/webp'})));provider.delete(saved['filename']);assert saved['url'].startswith('https://') and calls==['kittyboom/image-1']
