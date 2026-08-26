from pathlib import Path
from uuid import uuid4
from fastapi import UploadFile,HTTPException
from app.core.config import settings
ALLOWED={"image/jpeg":"jpg","image/png":"png","image/webp":"webp"};MAX_BYTES=5*1024*1024
async def validated_content(file:UploadFile):
    if file.content_type not in ALLOWED:raise HTTPException(415,"Solo se permiten imágenes JPG, PNG o WebP")
    content=await file.read(MAX_BYTES+1)
    if len(content)>MAX_BYTES:raise HTTPException(413,"La imagen supera el máximo de 5 MB")
    return content
class LocalStorage:
    def __init__(self,root:Path=Path("uploads")):self.root=root
    async def save(self,file:UploadFile):
        content=await validated_content(file);self.root.mkdir(parents=True,exist_ok=True);name=f"{uuid4().hex}.{ALLOWED[file.content_type]}";(self.root/name).write_bytes(content);return {"filename":name,"url":f"/uploads/{name}","mime_type":file.content_type,"size":len(content)}
    def delete(self,identifier:str):
        path=self.root/Path(identifier).name
        if path.exists():path.unlink()
class CloudinaryStorage:
    def __init__(self):
        import cloudinary
        cloudinary.config(cloud_name=settings.cloudinary_cloud_name,api_key=settings.cloudinary_api_key,api_secret=settings.cloudinary_api_secret,secure=True)
    async def save(self,file:UploadFile):
        import cloudinary.uploader
        content=await validated_content(file);result=cloudinary.uploader.upload(content,folder=settings.cloudinary_folder,resource_type="image",use_filename=False,unique_filename=True,overwrite=False)
        return {"filename":result["public_id"],"url":result["secure_url"],"mime_type":file.content_type,"size":len(content)}
    def delete(self,identifier:str):
        if not identifier:return
        import cloudinary.uploader
        cloudinary.uploader.destroy(identifier,resource_type="image",invalidate=True)
def create_storage():return CloudinaryStorage() if settings.is_production and settings.storage_provider=="cloudinary" else LocalStorage()
storage=create_storage()
