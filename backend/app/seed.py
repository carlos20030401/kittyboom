from decimal import Decimal
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models import Role, User, Category, Product, Customer, BusinessSettings
from app.core.config import settings
from app.core.security import hash_password
categories=["Aretes","Collares","Pulseras","Anillos","Sets","Accesorios"]
products=[("Aretes Aurora",39.90),("Collar Luna",59.90),("Pulsera Destello",34.90),("Anillo Siena",44.90),("Set Rosé",89.90),("Aretes Perla",42.90),("Collar Corazón",64.90),("Pulsera Mía",37.90),("Anillo Sol",48.90),("Set Gala",99.90),("Gancho Bloom",24.90),("Tobillera Mar",36.90)]
def run():
    db=SessionLocal()
    if db.scalar(select(Role).where(Role.name=="admin")): return
    admin=Role(name="admin"); seller=Role(name="seller"); db.add_all([admin,seller]); db.flush(); db.add(User(email=settings.admin_email,password_hash=hash_password(settings.admin_password),role_id=admin.id))
    cats=[]
    for i,name in enumerate(categories): cats.append(Category(name=name,position=i))
    db.add_all(cats); db.flush()
    for i,(name,price) in enumerate(products): db.add(Product(sku=f"KB-{i+1:04d}",name=name,description="Joya seleccionada para acompañar tus mejores momentos.",category_id=cats[i%len(cats)].id,price=Decimal(str(price)),material="Acero inoxidable",color="Dorado",stock=5+i,is_new=i<4,is_featured=i in {1,4,7}))
    db.add_all([Customer(name="Lucía Ramos",phone="999111222"),Customer(name="Camila Vega",phone="999333444")])
    db.add(BusinessSettings(business_name="KittyBoom",whatsapp=settings.whatsapp_number,instagram="@kittyboom",tiktok="@kittyboom",currency="S/")); db.commit(); db.close()
if __name__=="__main__": run()
