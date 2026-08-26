from decimal import Decimal
from pydantic import BaseModel, EmailStr, Field
class LoginIn(BaseModel): email: EmailStr; password: str
class VariantOut(BaseModel):
    id:int; product_id:int; name:str; sku:str|None; color:str|None; size:str|None; model:str|None; finish:str|None; price:Decimal|None; stock:int; min_stock:int; is_active:bool; image_url:str|None; position:int
    model_config={"from_attributes":True}
class ProductOut(BaseModel):
    id:int; sku:str; name:str; description:str; category_id:int; price:Decimal; sale_price:Decimal|None; material:str|None; color:str|None; stock:int; min_stock:int; has_variants:bool=False; is_active:bool; is_new:bool; is_featured:bool; primary_image_url:str|None=None; variants:list[VariantOut]=[]
    model_config={"from_attributes":True}
class ProductCreate(BaseModel):
    name:str=Field(min_length=2,max_length=180); category_id:int; description:str=""; price:Decimal=Field(gt=0); sale_price:Decimal|None=None; material:str|None=None; color:str|None=None; stock:int=Field(ge=0); min_stock:int=Field(ge=0,default=2); has_variants:bool=False; is_new:bool=False; is_featured:bool=False
class ProductUpdate(ProductCreate):
    is_active:bool=True
class CategoryIn(BaseModel):
    name:str=Field(min_length=2,max_length=80); description:str|None=None; image_url:str|None=None; position:int=0; is_active:bool=True
class CustomerIn(BaseModel):
    name:str=Field(min_length=2); phone:str=Field(min_length=6); email:EmailStr|None=None; address:str|None=None; instagram:str|None=None; notes:str|None=None
class InventoryIn(BaseModel):
    quantity:int; reason:str=Field(min_length=3); movement_type:str="adjustment"
class SettingsIn(BaseModel):
    business_name:str="KittyBoom"; whatsapp:str|None=None; instagram:str|None=None; tiktok:str|None=None; address:str|None=None; hours:str|None=None; currency:str="S/"; logo_url:str|None=None
class OrderLine(BaseModel): product_id:int; variant_id:int|None=None; quantity:int=Field(gt=0)
class OrderCreate(BaseModel): name:str; phone:str; address:str|None=None; notes:str|None=None; delivery_method:str="delivery"; payment_method:str="cash"; items:list[OrderLine]=Field(min_length=1)
class ManualSaleCreate(BaseModel):
    customer_id:int|None=None; customer_name:str|None=None; customer_phone:str|None=None
    payment_method:str; payment_status:str="paid"; sales_channel:str="in_store"; notes:str|None=None
    finalize:bool=False; idempotency_key:str=Field(min_length=8,max_length=80); items:list[OrderLine]=Field(min_length=1)
class CashMovementIn(BaseModel):
    movement_type:str; amount:Decimal=Field(gt=0); description:str=Field(min_length=3); payment_method:str="cash"; notes:str|None=None; reason:str|None=None
class PurchaseLineIn(BaseModel): product_id:int; variant_id:int|None=None; quantity:int=Field(gt=0); unit_cost:Decimal=Field(gt=0)
class PurchaseIn(BaseModel):
    items:list[PurchaseLineIn]=Field(min_length=1); supplier:str|None=None; receipt_number:str|None=None; payment_method:str="cash"; notes:str|None=None
class VariantIn(BaseModel):
    name:str=Field(min_length=1,max_length=120); sku:str=Field(min_length=1,max_length=50); color:str|None=None; size:str|None=None; model:str|None=None; finish:str|None=None; price:Decimal|None=Field(default=None,gt=0); stock:int=Field(ge=0,default=0); min_stock:int=Field(ge=0,default=2); is_active:bool=True; image_url:str|None=None; position:int=0
