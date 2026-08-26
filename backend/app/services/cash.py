from datetime import datetime,timezone
from decimal import Decimal
from sqlalchemy import select,func,case
from sqlalchemy.orm import Session
from app.models import CashMovement,InventoryMovement,Product,ProductVariant,Purchase,PurchaseItem
def add_sale_income(db:Session,order,user_id:int|None=None):
    key=f"sale:{order.id}"; existing=db.scalar(select(CashMovement).where(CashMovement.idempotency_key==key))
    if existing:return existing
    movement=CashMovement(movement_type="sale_income",direction="income",amount=order.total,description=f"Ingreso por venta {order.number}",payment_method=order.payment_method,order_id=order.id,user_id=user_id,idempotency_key=key)
    db.add(movement); db.flush(); return movement
def add_manual_movement(db:Session,data,user_id:int):
    allowed={"manual_income":"income","business_expense":"expense","initial_balance":"income","positive_adjustment":"income","negative_adjustment":"expense"}
    if data.movement_type not in allowed:raise ValueError("Tipo de movimiento inválido")
    if data.movement_type in {"positive_adjustment","negative_adjustment"} and not (data.reason or "").strip():raise ValueError("El motivo del ajuste es obligatorio")
    movement=CashMovement(movement_type=data.movement_type,direction=allowed[data.movement_type],amount=data.amount,description=data.description,payment_method=data.payment_method,user_id=user_id,notes=data.reason or data.notes)
    db.add(movement);db.flush();return movement
def create_purchase(db:Session,data,user_id:int):
    ids=[item.product_id for item in data.items];products={p.id:p for p in db.scalars(select(Product).where(Product.id.in_(ids)).order_by(Product.id).with_for_update()).all()};variant_ids={item.variant_id for item in data.items if item.variant_id};variants={v.id:v for v in db.scalars(select(ProductVariant).where(ProductVariant.id.in_(variant_ids)).order_by(ProductVariant.id).with_for_update()).all()}
    if len(products)!=len(set(ids)):raise ValueError("Uno o más productos no existen")
    total=Decimal("0");lines=[]
    for item in data.items:
        product=products[item.product_id]
        if product.has_variants and not item.variant_id:raise ValueError(f"Selecciona una variante para {product.name}")
        variant=variants.get(item.variant_id) if item.variant_id else None
        if item.variant_id and (not variant or variant.product_id!=product.id):raise ValueError("Variante inválida")
        subtotal=item.unit_cost*item.quantity;total+=subtotal;lines.append(PurchaseItem(product_id=item.product_id,variant_id=item.variant_id,quantity=item.quantity,unit_cost=item.unit_cost,subtotal=subtotal))
    count=db.scalar(select(func.count(Purchase.id))) or 0;purchase=Purchase(number=f"COMP-{datetime.now().strftime('%Y%m%d')}-{count+1:04d}",supplier=data.supplier,receipt_number=data.receipt_number,total=total,payment_method=data.payment_method,notes=data.notes,user_id=user_id,items=lines);db.add(purchase);db.flush()
    for item in data.items:
        if item.variant_id:variants[item.variant_id].stock+=item.quantity
        else:products[item.product_id].stock+=item.quantity
        db.add(InventoryMovement(product_id=item.product_id,variant_id=item.variant_id,quantity=item.quantity,movement_type="purchase",reason=f"Compra {purchase.number}"))
    db.add(CashMovement(movement_type="merchandise_purchase",direction="expense",amount=total,description=f"Compra de mercadería {purchase.number}",payment_method=data.payment_method,purchase_id=purchase.id,user_id=user_id,idempotency_key=f"purchase:{purchase.id}",notes=data.notes));db.flush();return purchase
def cash_summary(db:Session):
    now=datetime.now(timezone.utc);day=now.date();month_start=now.replace(day=1,hour=0,minute=0,second=0,microsecond=0)
    movements=db.scalars(select(CashMovement)).all();signed=lambda m:m.amount if m.direction=="income" else -m.amount
    balance=sum((signed(m) for m in movements),Decimal("0"));today=[m for m in movements if m.created_at and m.created_at.date()==day];month=[m for m in movements if m.created_at and (m.created_at.replace(tzinfo=timezone.utc) if m.created_at.tzinfo is None else m.created_at)>=month_start]
    calc=lambda rows,direction:sum((m.amount for m in rows if m.direction==direction),Decimal("0"))
    by_method={method:sum((m.amount for m in movements if m.direction=="income" and m.payment_method==method),Decimal("0")) for method in ["cash","yape","plin","transfer","other"]}
    return {"balance":balance,"today_income":calc(today,"income"),"today_expense":calc(today,"expense"),"today_result":sum((signed(m) for m in today),Decimal("0")),"month_income":calc(month,"income"),"month_expense":calc(month,"expense"),"month_result":sum((signed(m) for m in month),Decimal("0")),"by_method":by_method}
