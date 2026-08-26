from decimal import Decimal
from pathlib import Path
import pytest
from sqlalchemy import create_engine,select,func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db.base import Base
from app.models import CashMovement,Category,Customer,InventoryMovement,Order,OrderItem,Product
from app.services.orders import transition_pending_order,InvalidOrderTransitionError,InsufficientStockError

@pytest.fixture()
def db():
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    Base.metadata.create_all(engine); session=sessionmaker(bind=engine,expire_on_commit=False)()
    yield session
    session.close(); Base.metadata.drop_all(engine)

def make_order(db,stock=5,quantity=2,status="pending"):
    category=Category(name=f"Aretes-{id(db)}"); customer=Customer(name="Lucía",phone=f"999{id(db)}"); db.add_all([category,customer]); db.flush()
    product=Product(sku=f"KB-{id(db)}",name="Aretes Aurora",category_id=category.id,price=Decimal("39.90"),stock=stock,min_stock=1)
    db.add(product); db.flush()
    order=Order(number=f"PED-{id(db)}",customer_id=customer.id,status=status,total=Decimal("79.80"),items=[OrderItem(product_id=product.id,product_name=product.name,quantity=quantity,unit_price=product.price,subtotal=product.price*quantity)])
    db.add(order); db.commit(); return order,product

def movement_count(db): return db.scalar(select(func.count(InventoryMovement.id)))

def test_new_order_starts_pending_and_does_not_discount_stock(db):
    order,product=make_order(db); assert order.status=="pending"; assert product.stock==5; assert movement_count(db)==0

def test_finalized_discounts_once_and_creates_movement(db):
    order,product=make_order(db); transition_pending_order(db,order.id,"finalized"); db.commit()
    assert order.status=="finalized"; assert product.stock==3
    movement=db.scalar(select(InventoryMovement)); assert movement.quantity==-2; assert movement.movement_type=="order_finalized"
    income=db.scalar(select(CashMovement)); assert income.amount==Decimal("79.80") and income.direction=="income"
    assert order.payment_status=="paid" and order.paid_at is not None
    with pytest.raises(InvalidOrderTransitionError): transition_pending_order(db,order.id,"finalized")
    db.rollback(); assert db.get(Product,product.id).stock==3; assert movement_count(db)==1; assert db.scalar(select(func.count(CashMovement.id)))==1

def test_cancelled_does_not_change_inventory_or_create_movements(db):
    order,product=make_order(db); transition_pending_order(db,order.id,"cancelled"); db.commit()
    assert order.status=="cancelled"; assert product.stock==5; assert movement_count(db)==0; assert db.scalar(select(func.count(CashMovement.id)))==0

def test_cancelled_cannot_be_finalized(db):
    order,_=make_order(db); transition_pending_order(db,order.id,"cancelled"); db.commit()
    with pytest.raises(InvalidOrderTransitionError): transition_pending_order(db,order.id,"finalized")

def test_finalized_cannot_be_cancelled(db):
    order,_=make_order(db); transition_pending_order(db,order.id,"finalized"); db.commit()
    with pytest.raises(InvalidOrderTransitionError): transition_pending_order(db,order.id,"cancelled")

def test_insufficient_stock_changes_nothing(db):
    order,product=make_order(db,stock=1,quantity=2)
    with pytest.raises(InsufficientStockError): transition_pending_order(db,order.id,"finalized")
    db.rollback(); assert db.get(Product,product.id).stock==1; assert db.get(Order,order.id).status=="pending"; assert movement_count(db)==0

def test_migration_only_maps_statuses_and_never_touches_inventory():
    migration=(Path(__file__).parents[1]/"alembic"/"versions"/"0002_simplify_order_statuses.py").read_text(encoding="utf-8")
    assert "confirmed','preparing','ready','delivered" in migration
    assert "THEN 'finalized'" in migration
    upgrade=migration.split("def downgrade",1)[0].lower()
    assert "inventory_movements" not in upgrade; assert "product.stock" not in upgrade; assert "delete from orders" not in upgrade
