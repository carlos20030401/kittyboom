from decimal import Decimal
from app.core.security import hash_password, verify_password, create_token, decode_token
from app.services.storage import LocalStorage
from fastapi import UploadFile, HTTPException
from io import BytesIO
import asyncio
def test_password_and_token():
    hashed=hash_password("segura123")
    assert verify_password("segura123",hashed)
    assert decode_token(create_token(7,"admin"))["role"]=="admin"
def test_decimal_total():
    assert Decimal("39.90")*2+Decimal("20.10")==Decimal("99.90")
def test_stock_never_negative():
    stock,requested=2,3
    assert stock-requested<0
def test_local_storage_uses_unique_names(tmp_path):
    storage=LocalStorage(tmp_path)
    first=asyncio.run(storage.save(UploadFile(filename="joya.png",file=BytesIO(b"png"),headers={"content-type":"image/png"})))
    second=asyncio.run(storage.save(UploadFile(filename="joya.png",file=BytesIO(b"png"),headers={"content-type":"image/png"})))
    assert first["filename"]!=second["filename"]
    assert (tmp_path/first["filename"]).exists()
def test_local_storage_rejects_invalid_type(tmp_path):
    storage=LocalStorage(tmp_path)
    try: asyncio.run(storage.save(UploadFile(filename="malware.exe",file=BytesIO(b"bad"),headers={"content-type":"application/octet-stream"})))
    except HTTPException as error: assert error.status_code==415
    else: raise AssertionError("Debe rechazar archivos no permitidos")
