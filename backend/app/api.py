from collections import defaultdict
from datetime import datetime,timedelta,timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.db.session import get_db
from app.models import User, Product, ProductVariant, Customer, Order, OrderItem, Category, ProductImage, InventoryMovement, BusinessSettings, Banner, AuditLog, CashMovement, Purchase
from app.schemas import LoginIn, ProductOut, ProductCreate, ProductUpdate, VariantIn, OrderCreate, ManualSaleCreate, CashMovementIn, PurchaseIn, CategoryIn, CustomerIn, InventoryIn, SettingsIn
from app.core.security import verify_password, create_token, decode_token
from app.services.storage import storage
from app.services.orders import transition_pending_order, create_manual_sale, OrderNotFoundError, InvalidOrderTransitionError, InsufficientStockError
from app.services.cash import add_sale_income,add_manual_movement,create_purchase,cash_summary
router=APIRouter(); oauth=OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
def current_user(token:str=Depends(oauth), db:Session=Depends(get_db)):
    data=decode_token(token); user=db.get(User, int(data["sub"])) if data else None
    if not user or not user.is_active: raise HTTPException(401,"Sesión inválida")
    return user
def require_admin(user:User=Depends(current_user)):
    if user.role.name!="admin": raise HTTPException(403,"Permiso insuficiente")
    return user
@router.post("/auth/login")
def login(body:LoginIn, db:Session=Depends(get_db)):
    user=db.scalar(select(User).where(User.email==body.email))
    if not user or not verify_password(body.password,user.password_hash): raise HTTPException(401,"Credenciales incorrectas")
    return {"access_token":create_token(user.id,user.role.name),"token_type":"bearer","role":user.role.name}
def audit(db:Session,user:User,action:str,entity:str,entity_id:int|str): db.add(AuditLog(user_id=user.id,action=action,entity=entity,entity_id=str(entity_id)))
@router.get("/public/banners")
def public_banners(db:Session=Depends(get_db)):return db.scalars(select(Banner).where(Banner.is_active==True,Banner.image_url.is_not(None)).order_by(Banner.is_primary.desc(),Banner.position,Banner.id)).all()
@router.get("/admin/banners")
def admin_banners(user:User=Depends(current_user),db:Session=Depends(get_db)):return db.scalars(select(Banner).order_by(Banner.is_primary.desc(),Banner.position,Banner.id)).all()
@router.post("/admin/banners",status_code=201)
async def upload_banner(file:UploadFile=File(...),alt_text:str="Portada de KittyBoom",is_primary:bool=False,user:User=Depends(require_admin),db:Session=Depends(get_db)):
    saved=await storage.save(file)
    if is_primary:
        for item in db.scalars(select(Banner)).all():item.is_primary=False
    position=db.scalar(select(func.count(Banner.id))) or 0;banner=Banner(title="Portada",alt_text=alt_text.strip() or "Portada de KittyBoom",position=position,is_primary=is_primary,**saved);db.add(banner);db.flush();audit(db,user,"upload_banner","banner",banner.id);db.commit();db.refresh(banner);return banner
@router.patch("/admin/banners/{banner_id}")
def update_banner(banner_id:int,position:int|None=None,is_active:bool|None=None,is_primary:bool|None=None,alt_text:str|None=None,user:User=Depends(require_admin),db:Session=Depends(get_db)):
    banner=db.get(Banner,banner_id)
    if not banner:raise HTTPException(404,"Imagen de portada no encontrada")
    if position is not None:banner.position=max(0,position)
    if is_active is not None:banner.is_active=is_active
    if alt_text is not None:banner.alt_text=alt_text.strip() or "Portada de KittyBoom"
    if is_primary:
        for item in db.scalars(select(Banner)).all():item.is_primary=False
        banner.is_primary=True;banner.is_active=True
    audit(db,user,"update_banner","banner",banner.id);db.commit();return banner
@router.delete("/admin/banners/{banner_id}",status_code=204)
def delete_banner(banner_id:int,user:User=Depends(require_admin),db:Session=Depends(get_db)):
    banner=db.get(Banner,banner_id)
    if not banner:raise HTTPException(404,"Imagen de portada no encontrada")
    if banner.filename:storage.delete(banner.filename)
    db.delete(banner);audit(db,user,"delete_banner","banner",banner_id);db.commit()
@router.get("/public/categories")
def public_categories(db:Session=Depends(get_db)): return db.scalars(select(Category).where(Category.is_active==True).order_by(Category.position,Category.name)).all()
@router.get("/public/products",response_model=list[ProductOut])
def products(q:str|None=None, category_id:int|None=None, material:str|None=None,color:str|None=None,min_price:Decimal|None=None,max_price:Decimal|None=None,sort:str="recent",skip:int=0,limit:int=24, db:Session=Depends(get_db)):
    stmt=select(Product).where(Product.is_active==True)
    if q: stmt=stmt.where(Product.name.ilike(f"%{q}%"))
    if category_id: stmt=stmt.where(Product.category_id==category_id)
    if material: stmt=stmt.where(Product.material==material)
    if color: stmt=stmt.where(Product.color==color)
    effective=func.coalesce(Product.sale_price,Product.price)
    if min_price is not None: stmt=stmt.where(effective>=min_price)
    if max_price is not None: stmt=stmt.where(effective<=max_price)
    ordering={"price_asc":effective.asc(),"price_desc":effective.desc(),"name_asc":Product.name.asc(),"name_desc":Product.name.desc()}.get(sort,Product.created_at.desc())
    return db.scalars(stmt.order_by(ordering).offset(skip).limit(min(limit,100))).all()
@router.get("/public/products/{product_id}",response_model=ProductOut)
def public_product(product_id:int,db:Session=Depends(get_db)):
    product=db.scalar(select(Product).where(Product.id==product_id,Product.is_active==True))
    if not product: raise HTTPException(404,"Producto no encontrado")
    return product
@router.get("/public/products/{product_id}/images")
def public_images(product_id:int,db:Session=Depends(get_db)): return db.scalars(select(ProductImage).where(ProductImage.product_id==product_id).order_by(ProductImage.position)).all()
@router.get("/admin/products",response_model=list[ProductOut])
def admin_products(user:User=Depends(current_user),db:Session=Depends(get_db)): return db.scalars(select(Product).order_by(Product.created_at.desc())).all()
@router.post("/admin/products",response_model=ProductOut,dependencies=[Depends(require_admin)])
def create_product(body:ProductCreate,user:User=Depends(require_admin),db:Session=Depends(get_db)):
    sku=f"KB-{datetime.now().strftime('%y%m%d%H%M%S%f')[-10:]}"; product=Product(sku=sku,**body.model_dump()); db.add(product); db.flush(); audit(db,user,"create","product",product.id); db.commit(); db.refresh(product); return product
@router.put("/admin/products/{product_id}",response_model=ProductOut)
def update_product(product_id:int,body:ProductUpdate,user:User=Depends(current_user),db:Session=Depends(get_db)):
    product=db.get(Product,product_id)
    if not product: raise HTTPException(404,"Producto no encontrado")
    if product.has_variants and not body.has_variants:
        variants=db.scalars(select(ProductVariant).where(ProductVariant.product_id==product.id)).all()
        if any(v.stock>0 for v in variants) or db.scalar(select(func.count(OrderItem.id)).where(OrderItem.variant_id.in_([v.id for v in variants]))):raise HTTPException(409,"No se puede desactivar variantes con stock o ventas asociadas")
    for key,value in body.model_dump().items(): setattr(product,key,value)
    audit(db,user,"update","product",product.id); db.commit(); db.refresh(product); return product
@router.delete("/admin/products/{product_id}",status_code=204)
def deactivate_product(product_id:int,user:User=Depends(require_admin),db:Session=Depends(get_db)):
    product=db.get(Product,product_id)
    if not product: raise HTTPException(404,"Producto no encontrado")
    product.is_active=False; audit(db,user,"deactivate","product",product.id); db.commit()
@router.post("/admin/products/{product_id}/variants",status_code=201)
def create_variant(product_id:int,body:VariantIn,user:User=Depends(require_admin),db:Session=Depends(get_db)):
    product=db.get(Product,product_id)
    if not product:raise HTTPException(404,"Producto no encontrado")
    try:
        variant=ProductVariant(product_id=product_id,**body.model_dump());db.add(variant);product.has_variants=True;db.flush();audit(db,user,"create_variant","product_variant",variant.id);db.commit();db.refresh(variant);return variant
    except IntegrityError:db.rollback();raise HTTPException(409,"El SKU de la variante ya existe")
@router.put("/admin/products/{product_id}/variants/{variant_id}")
def update_variant(product_id:int,variant_id:int,body:VariantIn,user:User=Depends(require_admin),db:Session=Depends(get_db)):
    variant=db.get(ProductVariant,variant_id)
    if not variant or variant.product_id!=product_id:raise HTTPException(404,"Variante no encontrada")
    try:
        for key,value in body.model_dump().items():setattr(variant,key,value)
        audit(db,user,"update_variant","product_variant",variant.id);db.commit();return variant
    except IntegrityError:db.rollback();raise HTTPException(409,"El SKU de la variante ya existe")
@router.patch("/admin/products/{product_id}/variants/{variant_id}/deactivate")
def deactivate_variant(product_id:int,variant_id:int,user:User=Depends(require_admin),db:Session=Depends(get_db)):
    variant=db.get(ProductVariant,variant_id)
    if not variant or variant.product_id!=product_id:raise HTTPException(404,"Variante no encontrada")
    if variant.stock>0:raise HTTPException(409,"La variante tiene stock. Ajústalo a cero antes de desactivarla")
    variant.is_active=False;audit(db,user,"deactivate_variant","product_variant",variant.id);db.commit();return variant
@router.get("/admin/products/{product_id}/images")
def admin_images(product_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)): return db.scalars(select(ProductImage).where(ProductImage.product_id==product_id).order_by(ProductImage.position)).all()
@router.post("/admin/products/{product_id}/images",status_code=201)
async def upload_image(product_id:int,file:UploadFile=File(...),is_primary:bool=False,user:User=Depends(current_user),db:Session=Depends(get_db)):
    if not db.get(Product,product_id): raise HTTPException(404,"Producto no encontrado")
    saved=await storage.save(file)
    if is_primary:
        for old in db.scalars(select(ProductImage).where(ProductImage.product_id==product_id)).all(): old.is_primary=False
    position=db.scalar(select(func.count(ProductImage.id)).where(ProductImage.product_id==product_id)) or 0
    image=ProductImage(product_id=product_id,position=position,is_primary=is_primary,image_url=saved["url"],filename=saved["filename"],mime_type=saved["mime_type"],size=saved["size"]); db.add(image); db.flush(); audit(db,user,"upload_image","product",product_id); db.commit(); db.refresh(image); return image
@router.patch("/admin/products/{product_id}/images/{image_id}")
def update_image(product_id:int,image_id:int,position:int|None=None,is_primary:bool|None=None,user:User=Depends(current_user),db:Session=Depends(get_db)):
    image=db.get(ProductImage,image_id)
    if not image or image.product_id!=product_id: raise HTTPException(404,"Imagen no encontrada")
    if position is not None: image.position=max(0,position)
    if is_primary:
        for old in db.scalars(select(ProductImage).where(ProductImage.product_id==product_id)).all(): old.is_primary=False
        image.is_primary=True
    audit(db,user,"update_image","product",product_id); db.commit(); return image
@router.delete("/admin/products/{product_id}/images/{image_id}",status_code=204)
def delete_image(product_id:int,image_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    image=db.get(ProductImage,image_id)
    if not image or image.product_id!=product_id: raise HTTPException(404,"Imagen no encontrada")
    storage.delete(image.filename); db.delete(image); audit(db,user,"delete_image","product",product_id); db.commit()
@router.get("/admin/categories")
def categories(user:User=Depends(current_user),db:Session=Depends(get_db)): return db.scalars(select(Category).order_by(Category.position,Category.name)).all()
@router.post("/admin/categories",status_code=201)
def create_category(body:CategoryIn,user:User=Depends(require_admin),db:Session=Depends(get_db)):
    category=Category(**body.model_dump()); db.add(category); db.flush(); audit(db,user,"create","category",category.id); db.commit(); db.refresh(category); return category
@router.put("/admin/categories/{category_id}")
def update_category(category_id:int,body:CategoryIn,user:User=Depends(require_admin),db:Session=Depends(get_db)):
    category=db.get(Category,category_id)
    if not category: raise HTTPException(404,"Categoría no encontrada")
    for k,v in body.model_dump().items(): setattr(category,k,v)
    audit(db,user,"update","category",category.id); db.commit(); return category
@router.delete("/admin/categories/{category_id}",status_code=204)
def deactivate_category(category_id:int,user:User=Depends(require_admin),db:Session=Depends(get_db)):
    category=db.get(Category,category_id)
    if not category: raise HTTPException(404,"Categoría no encontrada")
    category.is_active=False; audit(db,user,"deactivate","category",category.id); db.commit()
@router.get("/admin/customers")
def customers(q:str|None=None,user:User=Depends(current_user),db:Session=Depends(get_db)):
    stmt=select(Customer)
    if q: stmt=stmt.where(or_(Customer.name.ilike(f"%{q}%"),Customer.phone.ilike(f"%{q}%")))
    return db.scalars(stmt.order_by(Customer.name)).all()
@router.post("/admin/customers",status_code=201)
def create_customer(body:CustomerIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    customer=Customer(**body.model_dump()); db.add(customer); db.flush(); audit(db,user,"create","customer",customer.id); db.commit(); db.refresh(customer); return customer
@router.put("/admin/customers/{customer_id}")
def update_customer(customer_id:int,body:CustomerIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    customer=db.get(Customer,customer_id)
    if not customer: raise HTTPException(404,"Cliente no encontrado")
    for k,v in body.model_dump().items(): setattr(customer,k,v)
    audit(db,user,"update","customer",customer.id); db.commit(); return customer
@router.get("/admin/orders")
def admin_orders(number:str|None=None,customer:str|None=None,status_filter:str|None=None,payment_status:str|None=None,payment_method:str|None=None,sales_channel:str|None=None,date_from:datetime|None=None,date_to:datetime|None=None,user:User=Depends(current_user),db:Session=Depends(get_db)):
    stmt=select(Order).join(Customer)
    if number: stmt=stmt.where(Order.number.ilike(f"%{number}%"))
    if customer: stmt=stmt.where(or_(Customer.name.ilike(f"%{customer}%"),Customer.phone.ilike(f"%{customer}%")))
    if status_filter: stmt=stmt.where(Order.status==status_filter)
    if payment_status: stmt=stmt.where(Order.payment_status==payment_status)
    if payment_method: stmt=stmt.where(Order.payment_method==payment_method)
    if sales_channel: stmt=stmt.where(Order.sales_channel==sales_channel)
    if date_from: stmt=stmt.where(Order.created_at>=date_from)
    if date_to: stmt=stmt.where(Order.created_at<=date_to)
    return db.scalars(stmt.order_by(Order.created_at.desc())).all()
@router.get("/admin/orders/{order_id}")
def order_detail(order_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    order=db.get(Order,order_id)
    if not order: raise HTTPException(404,"Pedido no encontrado")
    items=[]
    for line in order.items:
        product=db.get(Product,line.product_id); image=db.scalar(select(ProductImage).where(ProductImage.product_id==line.product_id).order_by(ProductImage.is_primary.desc(),ProductImage.position))
        items.append({"id":line.id,"product_id":line.product_id,"variant_id":line.variant_id,"name":line.product_name,"variant_name":line.variant_name,"sku":line.variant_sku or (product.sku if product else "—"),"image_url":line.variant_image_url or (image.url if image else None),"quantity":line.quantity,"unit_price":line.unit_price,"subtotal":line.subtotal})
    history=[]
    logs=db.execute(select(AuditLog,User.email).outerjoin(User,AuditLog.user_id==User.id).where(AuditLog.entity=="order",AuditLog.entity_id==str(order.id)).order_by(AuditLog.created_at)).all()
    for log,email in logs: history.append({"action":log.action,"created_at":log.created_at,"user":email})
    terminal=next((entry for entry in reversed(history) if entry["action"] in {"order_finalized","order_cancelled"}),None)
    return {"id":order.id,"number":order.number,"created_at":order.created_at,"status":order.status,"payment_status":order.payment_status,"payment_method":order.payment_method,"sales_channel":order.sales_channel,"address":order.address,"notes":order.notes,"total":order.total,"customer":{"id":order.customer.id,"name":order.customer.name,"phone":order.customer.phone},"items":items,"history":history,"closed_by":terminal["user"] if terminal else None}
@router.post("/admin/manual-sales",status_code=201)
def manual_sale(body:ManualSaleCreate,user:User=Depends(current_user),db:Session=Depends(get_db)):
    try:
        order,created=create_manual_sale(db,body,user.id)
        if created:
            audit(db,user,"create_manual_sale","order",order.id)
            if body.finalize: audit(db,user,"order_finalized","order",order.id)
        db.commit(); return {"id":order.id,"number":order.number,"status":order.status,"total":order.total,"created":created}
    except (ValueError,InsufficientStockError) as error:
        db.rollback(); detail=f"Stock insuficiente para {error.product_name}. No se guardó la venta." if isinstance(error,InsufficientStockError) else str(error)
        raise HTTPException(409,detail)
    except IntegrityError:
        db.rollback(); existing=db.scalar(select(Order).where(Order.idempotency_key==body.idempotency_key))
        if existing: return {"id":existing.id,"number":existing.number,"status":existing.status,"total":existing.total,"created":False}
        raise HTTPException(409,"La venta ya fue procesada")
@router.patch("/admin/orders/{order_id}/payment")
def update_payment_status(order_id:int,payment_status:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    if payment_status not in {"pending","paid"}: raise HTTPException(400,"Estado de pago inválido")
    order=db.get(Order,order_id)
    if not order: raise HTTPException(404,"Pedido no encontrado")
    order.payment_status=payment_status
    if payment_status=="paid":
        order.paid_at=order.paid_at or datetime.now().astimezone()
        if order.status=="finalized": add_sale_income(db,order,user.id)
    audit(db,user,f"payment_{payment_status}","order",order.id); db.commit(); return {"payment_status":payment_status,"paid_at":order.paid_at}
@router.get("/admin/inventory")
def inventory(user:User=Depends(current_user),db:Session=Depends(get_db)): return db.scalars(select(Product).order_by(Product.stock,Product.name)).all()
@router.post("/admin/inventory/{product_id}/movements",status_code=201)
def inventory_movement(product_id:int,body:InventoryIn,variant_id:int|None=None,user:User=Depends(current_user),db:Session=Depends(get_db)):
    product=db.get(Product,product_id)
    if not product: raise HTTPException(404,"Producto no encontrado")
    variant=db.get(ProductVariant,variant_id) if variant_id else None
    if product.has_variants and (not variant or variant.product_id!=product.id):raise HTTPException(400,"Selecciona una variante válida")
    target=variant if variant else product
    if target.stock+body.quantity<0: raise HTTPException(409,"El stock no puede quedar negativo")
    target.stock+=body.quantity; movement=InventoryMovement(product_id=product_id,variant_id=variant_id,**body.model_dump()); db.add(movement); db.flush(); audit(db,user,"adjust_stock","product",product_id); db.commit(); db.refresh(movement); return movement
@router.get("/admin/inventory/{product_id}/movements")
def movements(product_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)): return db.scalars(select(InventoryMovement).where(InventoryMovement.product_id==product_id).order_by(InventoryMovement.created_at.desc())).all()
@router.get("/public/settings")
def public_settings(response:Response,db:Session=Depends(get_db)):
    response.headers["Cache-Control"]="no-store"
    return db.scalar(select(BusinessSettings)) or {"business_name":"KittyBoom","currency":"S/"}
@router.get("/admin/settings")
def get_settings(user:User=Depends(current_user),db:Session=Depends(get_db)): return db.scalar(select(BusinessSettings)) or {"business_name":"KittyBoom","currency":"S/"}
@router.put("/admin/settings")
def update_settings(body:SettingsIn,user:User=Depends(require_admin),db:Session=Depends(get_db)):
    item=db.scalar(select(BusinessSettings)) or BusinessSettings(); db.add(item)
    for k,v in body.model_dump().items(): setattr(item,k,v)
    db.flush(); audit(db,user,"update","business_settings",item.id); db.commit(); return item
@router.post("/public/orders",status_code=201)
def create_order(body:OrderCreate,db:Session=Depends(get_db)):
    requested=defaultdict(int)
    for item in body.items:requested[(item.product_id,item.variant_id)]+=item.quantity
    product_ids={key[0] for key in requested};products={p.id:p for p in db.scalars(select(Product).where(Product.id.in_(product_ids),Product.is_active==True)).all()}
    if len(products)!=len(product_ids):raise HTTPException(400,"Uno o más productos no existen")
    variant_ids={key[1] for key in requested if key[1]};variants={v.id:v for v in db.scalars(select(ProductVariant).where(ProductVariant.id.in_(variant_ids),ProductVariant.is_active==True)).all()};total=Decimal("0");lines=[]
    for (product_id,variant_id),quantity in requested.items():
        p=products[product_id]
        if p.has_variants and not variant_id:raise HTTPException(400,f"Selecciona una variante para {p.name}")
        variant=variants.get(variant_id) if variant_id else None
        if variant_id and (not variant or variant.product_id!=p.id):raise HTTPException(400,"Variante inválida o inactiva")
        available=variant.stock if variant else p.stock
        if available<quantity:raise HTTPException(409,f"Stock insuficiente para {variant.name if variant else p.name}")
        price=variant.price if variant and variant.price is not None else p.sale_price if p.sale_price is not None else p.price;subtotal=price*quantity;total+=subtotal
        lines.append(OrderItem(product_id=p.id,variant_id=variant.id if variant else None,product_name=p.name,variant_name=variant.name if variant else None,variant_sku=variant.sku if variant else None,variant_image_url=variant.image_url if variant else None,quantity=quantity,unit_price=price,subtotal=subtotal))
    customer=db.scalar(select(Customer).where(Customer.phone==body.phone)) or Customer(name=body.name,phone=body.phone,address=body.address)
    db.add(customer); db.flush(); number=f"KB-{datetime.now().strftime('%Y%m%d')}-{(db.scalar(select(func.count(Order.id))) or 0)+1:04d}"
    order=Order(number=number,customer_id=customer.id,total=total,address=body.address,notes=body.notes,delivery_method=body.delivery_method,payment_method=body.payment_method,items=lines)
    db.add(order); db.commit(); return {"id":order.id,"number":number,"total":total,"status":order.status}
@router.patch("/admin/orders/{order_id}/status")
def order_status(order_id:int,new_status:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    try:
        order=transition_pending_order(db,order_id,new_status,user.id); audit(db,user,f"order_{new_status}","order",order.id); db.commit(); return {"status":order.status,"payment_status":order.payment_status,"paid_at":order.paid_at}
    except OrderNotFoundError:
        db.rollback(); raise HTTPException(404,"Pedido no encontrado")
    except InvalidOrderTransitionError as error:
        db.rollback(); raise HTTPException(409,str(error))
    except InsufficientStockError as error:
        db.rollback(); raise HTTPException(409,f"Stock insuficiente para {error.product_name}. No se modificó el inventario.")
@router.get("/admin/dashboard")
def dashboard(user:User=Depends(current_user),db:Session=Depends(get_db)):
    return {"total_products":db.scalar(select(func.count(Product.id))),"pending_orders":db.scalar(select(func.count(Order.id)).where(Order.status=="pending")),"low_stock":db.scalar(select(func.count(Product.id)).where(Product.stock<=Product.min_stock)),"customers":db.scalar(select(func.count(Customer.id)))}
@router.get("/admin/cash/summary")
def get_cash_summary(user:User=Depends(current_user),db:Session=Depends(get_db)): return cash_summary(db)
@router.get("/admin/cash/movements")
def cash_movements(direction:str|None=None,movement_type:str|None=None,payment_method:str|None=None,search:str|None=None,date_from:datetime|None=None,date_to:datetime|None=None,user_id:int|None=None,order_number:str|None=None,skip:int=0,limit:int=20,user:User=Depends(current_user),db:Session=Depends(get_db)):
    stmt=select(CashMovement,User.email,Order.number,Purchase.number).outerjoin(User,CashMovement.user_id==User.id).outerjoin(Order,CashMovement.order_id==Order.id).outerjoin(Purchase,CashMovement.purchase_id==Purchase.id)
    if direction:stmt=stmt.where(CashMovement.direction==direction)
    if movement_type:stmt=stmt.where(CashMovement.movement_type==movement_type)
    if payment_method:stmt=stmt.where(CashMovement.payment_method==payment_method)
    if search:stmt=stmt.where(CashMovement.description.ilike(f"%{search}%"))
    if date_from:stmt=stmt.where(CashMovement.created_at>=date_from)
    if date_to:stmt=stmt.where(CashMovement.created_at<=date_to)
    if user_id:stmt=stmt.where(CashMovement.user_id==user_id)
    if order_number:stmt=stmt.where(or_(Order.number.ilike(f"%{order_number}%"),Purchase.number.ilike(f"%{order_number}%"),Purchase.receipt_number.ilike(f"%{order_number}%")))
    running=Decimal("0");balances={}
    for item in db.scalars(select(CashMovement).order_by(CashMovement.created_at,CashMovement.id)).all():
        running+=item.amount if item.direction=="income" else -item.amount;balances[item.id]=running
    all_rows=db.execute(stmt.order_by(CashMovement.created_at,CashMovement.id)).all();serialized=[]
    for movement,email,number,purchase_number in all_rows:
        serialized.append({"id":movement.id,"created_at":movement.created_at,"movement_type":movement.movement_type,"direction":movement.direction,"amount":movement.amount,"description":movement.description,"payment_method":movement.payment_method,"order_id":movement.order_id,"order_number":number,"purchase_id":movement.purchase_id,"purchase_number":purchase_number,"user_id":movement.user_id,"user":email,"balance":balances[movement.id]})
    page=serialized[skip:skip+min(limit,100)];return {"items":page,"total":len(serialized),"skip":skip,"limit":limit}
@router.post("/admin/cash/movements",status_code=201)
def create_cash_movement(body:CashMovementIn,user:User=Depends(require_admin),db:Session=Depends(get_db)):
    try:
        if body.movement_type=="initial_balance" and db.scalar(select(CashMovement).where(CashMovement.movement_type=="initial_balance")):raise ValueError("El saldo inicial ya fue configurado")
        movement=add_manual_movement(db,body,user.id);audit(db,user,"create_cash_movement","cash_movement",movement.id);db.commit();return movement
    except ValueError as error:db.rollback();raise HTTPException(409,str(error))
@router.post("/admin/cash/purchases",status_code=201)
def register_purchase(body:PurchaseIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    try:
        purchase=create_purchase(db,body,user.id);audit(db,user,"create_purchase","purchase",purchase.id);db.commit();return {"id":purchase.id,"number":purchase.number,"total":purchase.total}
    except ValueError as error:db.rollback();raise HTTPException(409,str(error))
@router.get("/admin/analytics")
def analytics(days:int=30,user:User=Depends(current_user),db:Session=Depends(get_db)):
    days=max(7,min(days,90));cutoff=datetime.now(timezone.utc)-timedelta(days=days);orders=db.scalars(select(Order).where(Order.status=="finalized",Order.created_at>=cutoff).order_by(Order.created_at)).all();movements=db.scalars(select(CashMovement).where(CashMovement.created_at>=cutoff).order_by(CashMovement.created_at)).all()
    sales_by_day={};sales_by_month={};by_method={};by_channel={};product_totals={}
    for order in orders:
        key=order.created_at.date().isoformat();month=key[:7];sales_by_day[key]=sales_by_day.get(key,Decimal("0"))+order.total;sales_by_month[month]=sales_by_month.get(month,Decimal("0"))+order.total;by_method[order.payment_method]=by_method.get(order.payment_method,0)+1;by_channel[order.sales_channel]=by_channel.get(order.sales_channel,0)+1
        for item in order.items:product_totals[item.product_name]=product_totals.get(item.product_name,0)+item.quantity
    income=sum((m.amount for m in movements if m.direction=="income"),Decimal("0"));expense=sum((m.amount for m in movements if m.direction=="expense"),Decimal("0"));count=len(orders)
    return {"period_days":days,"sales_by_day":[{"date":k,"total":v} for k,v in sales_by_day.items()],"sales_by_month":[{"month":k,"total":v} for k,v in sales_by_month.items()],"finalized_orders":count,"income":income,"expense":expense,"result":income-expense,"average_ticket":income/count if count else Decimal("0"),"payment_methods":by_method,"sales_channels":by_channel,"top_products":[{"name":k,"quantity":v} for k,v in sorted(product_totals.items(),key=lambda x:x[1],reverse=True)[:8]]}
