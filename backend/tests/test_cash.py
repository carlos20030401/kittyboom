from decimal import Decimal
import pytest
from sqlalchemy import create_engine,select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db.base import Base
from app.models import CashMovement,Category,InventoryMovement,Product,Purchase,PurchaseItem,Role,User
from app.schemas import CashMovementIn,PurchaseIn,PurchaseLineIn
from app.services.cash import add_manual_movement,cash_summary,create_purchase

@pytest.fixture()
def db():
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool);Base.metadata.create_all(engine);s=sessionmaker(bind=engine,expire_on_commit=False)()
    role=Role(name="admin");s.add(role);s.flush();user=User(email="cash@test.pe",password_hash="x",role_id=role.id);category=Category(name="Collares");s.add_all([user,category]);s.flush();product=Product(sku="KB-CASH",name="Collar",category_id=category.id,price=Decimal("50"),stock=2,min_stock=1);s.add(product);s.commit();yield s,user,product;s.close();Base.metadata.drop_all(engine)

def test_purchase_increases_stock_and_registers_expense_atomically(db):
    s,user,product=db;payload=PurchaseIn(items=[PurchaseLineIn(product_id=product.id,quantity=3,unit_cost=Decimal("12.50"))],supplier="Proveedor",payment_method="yape")
    purchase=create_purchase(s,payload,user.id);s.commit()
    assert product.stock==5 and purchase.total==Decimal("37.50")
    assert s.scalar(select(InventoryMovement)).quantity==3
    movement=s.scalar(select(CashMovement));assert movement.direction=="expense" and movement.amount==Decimal("37.50") and movement.purchase_id==purchase.id

def test_multi_product_purchase_is_one_purchase_and_one_expense(db):
    s,user,first=db;second=Product(sku="KB-CASH-2",name="Pulsera",category_id=first.category_id,price=Decimal("40"),stock=4,min_stock=1);s.add(second);s.commit()
    payload=PurchaseIn(items=[PurchaseLineIn(product_id=first.id,quantity=2,unit_cost=Decimal("10")),PurchaseLineIn(product_id=second.id,quantity=3,unit_cost=Decimal("7.50"))],payment_method="transfer")
    purchase=create_purchase(s,payload,user.id);s.commit()
    assert purchase.total==Decimal("42.50") and first.stock==4 and second.stock==7
    assert len(s.scalars(select(Purchase)).all())==1 and len(s.scalars(select(PurchaseItem)).all())==2
    expenses=s.scalars(select(CashMovement).where(CashMovement.direction=="expense")).all();assert len(expenses)==1 and expenses[0].amount==Decimal("42.50")
    assert len(s.scalars(select(InventoryMovement)).all())==2

def test_failed_purchase_leaves_stock_and_cash_untouched(db):
    s,user,product=db;payload=PurchaseIn(items=[PurchaseLineIn(product_id=9999,quantity=1,unit_cost=Decimal("10"))])
    with pytest.raises(ValueError):create_purchase(s,payload,user.id)
    s.rollback();assert product.stock==2 and s.scalar(select(CashMovement)) is None

def test_manual_adjustment_requires_reason_and_summary_uses_signed_balance(db):
    s,user,_=db
    with pytest.raises(ValueError):add_manual_movement(s,CashMovementIn(movement_type="negative_adjustment",amount=Decimal("5"),description="Ajuste"),user.id)
    s.rollback();add_manual_movement(s,CashMovementIn(movement_type="initial_balance",amount=Decimal("100"),description="Apertura"),user.id);add_manual_movement(s,CashMovementIn(movement_type="business_expense",amount=Decimal("25"),description="Empaque"),user.id);s.commit()
    assert cash_summary(s)["balance"]==Decimal("75")

def test_cash_migration_preserves_existing_orders():
    from pathlib import Path
    text=(Path(__file__).parents[1]/"alembic"/"versions"/"0004_virtual_cash_and_purchases.py").read_text(encoding="utf-8").split("def downgrade",1)[0].lower()
    assert "delete from orders" not in text and "update orders" not in text and "inventory_movements" not in text
