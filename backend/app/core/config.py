from pydantic import model_validator
from pydantic_settings import BaseSettings,SettingsConfigDict
class Settings(BaseSettings):
    environment:str="development";database_url:str="sqlite:///./kittyboom.db";jwt_secret:str="development-only-change-me";cors_origins:str="http://localhost:5173";storage_provider:str="local";cloudinary_cloud_name:str|None=None;cloudinary_api_key:str|None=None;cloudinary_api_secret:str|None=None;cloudinary_folder:str="kittyboom";admin_email:str|None="admin@kittyboom.pe";admin_password:str|None="KittyBoom123!";whatsapp_number:str="51999999999";business_timezone:str="America/Lima";port:int=8000
    model_config=SettingsConfigDict(env_file=".env",extra="ignore")
    @property
    def is_production(self):return self.environment.lower()=="production"
    @property
    def sqlalchemy_url(self):
        value=self.database_url
        if value.startswith("postgres://"):value="postgresql://"+value.removeprefix("postgres://")
        if value.startswith("postgresql://"):value="postgresql+psycopg://"+value.removeprefix("postgresql://")
        return value
    @property
    def allowed_origins(self):return [x.strip().rstrip("/") for x in self.cors_origins.split(",") if x.strip()]
    @model_validator(mode="after")
    def validate_production(self):
        if self.is_production:
            if self.jwt_secret in {"development-only-change-me","change-this-in-production"} or len(self.jwt_secret)<32:raise ValueError("JWT_SECRET debe tener al menos 32 caracteres y no puede ser el valor de desarrollo")
            if not self.database_url.startswith(("postgres://","postgresql://","postgresql+psycopg://")):raise ValueError("DATABASE_URL de producción debe ser PostgreSQL")
            if self.storage_provider!="cloudinary":raise ValueError("Producción requiere STORAGE_PROVIDER=cloudinary")
            if not all([self.cloudinary_cloud_name,self.cloudinary_api_key,self.cloudinary_api_secret]):raise ValueError("Faltan credenciales de Cloudinary")
            if not self.allowed_origins or "*" in self.allowed_origins:raise ValueError("CORS_ORIGINS de producción debe declarar orígenes explícitos")
        return self
settings=Settings()
