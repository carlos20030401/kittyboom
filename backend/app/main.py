import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from sqlalchemy import text
from app.api import router
from app.core.config import settings
from app.db.session import engine
logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(name)s %(message)s")
app=FastAPI(title="KittyBoom API",version="1.0.0",description="API de tienda y administración",debug=False)
app.add_middleware(CORSMiddleware,allow_origins=settings.allowed_origins,allow_credentials=True,allow_methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS"],allow_headers=["Authorization","Content-Type"])
app.include_router(router,prefix="/api/v1")
if settings.storage_provider=="local":app.mount("/uploads",StaticFiles(directory="uploads",check_dir=False),name="uploads")
@app.get("/health")
def health():
    try:
        with engine.connect() as connection:connection.execute(text("SELECT 1"))
        return {"status":"ok","database":"ok"}
    except Exception:
        logging.getLogger("kittyboom.health").exception("Database health check failed")
        return JSONResponse(status_code=503,content={"status":"degraded","database":"unavailable"})
