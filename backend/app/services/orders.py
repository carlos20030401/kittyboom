from collections import defaultdict
from datetime import datetime,timezone
from decimal import Decimal
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from app.models import Customer, InventoryMovement, Order, OrderItem, Product, ProductVariant
from app.services.cash import add_sale_income

TERMINAL_STATUSES={"finalized","cancelled"}
class OrderNotFoundError(Exception): pass
class InvalidOrderTransitionError(Exception): pass
class InsufficientStockError(Exception):
    def __init__(self,product_name:str): self.product_name=product_name; super().__init__(product_name)

def transition_pending_order(db:Session,order_id:int,target_status:str,user_id:int|None=None):
    if target_status not in TERMINAL_STATUSES: raise InvalidOrderTransitionError("Estado de destino inválido")
    order=db.scalar(select(Order).where(Order.id==order_id).with_for_update())
    if not order: raise OrderNotFoundError()
    if order.status!="pending": raise InvalidOrderTransitionError("El pedido ya está cerrado y no admite cambios")
    if target_status=="cancelled":
        order.status="cancelled"; db.flush(); return order
    simple=defaultdict(int);variant_required=defaultdict(int)
    for item in order.items:
        (variant_required if item.variant_id else simple)[item.variant_id or item.product_id]+=item.quantity
    products={p.id:p for p in db.scalars(select(Product).where(Product.id.in_(sorted(simple))).order_by(Product.id).with_for_update()).all()};variants={v.id:v for v in db.scalars(select(ProductVariant).where(ProductVariant.id.in_(sorted(variant_required))).order_by(ProductVariant.id).with_for_update()).all()}
    for product_id,quantity in simple.items():
        product=products.get(product_id)
        if not product or product.stock<quantity:raise InsufficientStockError(product.name if product else f"Producto {product_id}")
    for variant_id,quantity in variant_required.items():
        variant=variants.get(variant_id)
        if not variant or variant.stock<quantity:raise InsufficientStockError(variant.name if variant else f"Variante {variant_id}")
    for product_id,quantity in simple.items():
        product=products[product_id];product.stock-=quantity;db.add(InventoryMovement(product_id=product.id,variant_id=None,quantity=-quantity,movement_type="order_finalized",reason=f"Pedido {order.number} finalizado"))
    for variant_id,quantity in variant_required.items():
        variant=variants[variant_id];variant.stock-=quantity;db.add(InventoryMovement(product_id=variant.product_id,variant_id=variant.id,quantity=-quantity,movement_type="order_finalized",reason=f"Pedido {order.number} finalizado · {variant.name}"))
    order.status="finalized"; order.payment_status="paid"; order.paid_at=datetime.now(timezone.utc); db.flush(); add_sale_income(db,order,user_id); return order

def create_manual_sale(db:Session,data,user_id:int|None=None):
    existing=db.scalar(select(Order).where(Order.idempotency_key==data.idempotency_key))
    if existing: return existing,False
    if data.payment_method not in {"cash","yape","plin","transfer","other"}: raise ValueError("Método de pago inválido")
    if data.payment_status not in {"pending","paid"}: raise ValueError("Estado de pago inválido")
    if data.sales_channel not in {"web","whatsapp","instagram","in_store","other"}: raise ValueError("Canal de venta inválido")
    if data.customer_id:
        customer=db.get(Customer,data.customer_id)
        if not customer: raise ValueError("Cliente no encontrado")
    else:
        customer=Customer(name=(data.customer_name or "Cliente ocasional").strip() or "Cliente ocasional",phone=(data.customer_phone or "").strip())
        db.add(customer); db.flush()
    requested=defaultdict(int)
    for line in data.items:requested[(line.product_id,line.variant_id)]+=line.quantity
    product_ids={key[0] for key in requested};products={p.id:p for p in db.scalars(select(Product).where(Product.id.in_(product_ids),Product.is_active==True)).all()};variant_ids={key[1] for key in requested if key[1]};variants={v.id:v for v in db.scalars(select(ProductVariant).where(ProductVariant.id.in_(variant_ids),ProductVariant.is_active==True)).all()}
    if len(products)!=len(product_ids):raise ValueError("Uno o más productos no existen o están inactivos")
    total=Decimal("0"); items=[]
    for (product_id,variant_id),quantity in requested.items():
        product=products[product_id]
        if product.has_variants and not variant_id:raise ValueError(f"Selecciona una variante para {product.name}")
        if not product.has_variants and variant_id:raise ValueError(f"{product.name} no utiliza variantes")
        variant=variants.get(variant_id) if variant_id else None
        if variant_id and (not variant or variant.product_id!=product.id):raise ValueError("Variante inválida o inactiva")
        price=variant.price if variant and variant.price is not None else product.sale_price if product.sale_price is not None else product.price;subtotal=price*quantity;total+=subtotal
        items.append(OrderItem(product_id=product.id,variant_id=variant.id if variant else None,product_name=product.name,variant_name=variant.name if variant else None,variant_sku=variant.sku if variant else None,variant_image_url=variant.image_url if variant else None,quantity=quantity,unit_price=price,subtotal=subtotal))
    count=db.scalar(select(func.count(Order.id))) or 0
    order=Order(number=f"KB-{datetime.now().strftime('%Y%m%d')}-{count+1:04d}",customer_id=customer.id,status="pending",payment_method=data.payment_method,payment_status=data.payment_status,sales_channel=data.sales_channel,idempotency_key=data.idempotency_key,notes=data.notes,total=total,items=items)
    db.add(order); db.flush()
    if data.finalize: transition_pending_order(db,order.id,"finalized",user_id)
    return order,True
