from decimal import Decimal
from types import SimpleNamespace
import pytest
from sqlalchemy import create_engine,select,func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db.base import Base
from fastapi.testclient import TestClient
from app.main import app
from app.api import current_user
from app.db.session import get_db
from app.models import AuditLog,Category,Customer,InventoryMovement,Order,Product,Role,User
from app.schemas import ManualSaleCreate,OrderLine
from app.services.orders import create_manual_sale,InsufficientStockError

@pytest.fixture()
def db():
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool); Base.metadata.create_all(engine)
    session=sessionmaker(bind=engine,expire_on_commit=False)(); category=Category(name="Aretes"); session.add(category); session.flush()
    session.add_all([Product(sku="KB-A",name="Aurora",category_id=category.id,price=Decimal("50.00"),sale_price=Decimal("40.00"),stock=5,min_stock=1),Product(sku="KB-B",name="Luna",category_id=category.id,price=Decimal("30.00"),stock=1,min_stock=1)]); session.commit(); yield session; session.close(); Base.metadata.drop_all(engine)
def data(db,**values):
    product=db.scalar(select(Product).where(Product.sku=="KB-A")); base=dict(customer_name="Ocasional",customer_phone=None,payment_method="cash",payment_status="paid",sales_channel="in_store",finalize=False,idempotency_key="manual-sale-key-001",items=[OrderLine(product_id=product.id,quantity=2)])
    return ManualSaleCreate(**(base|values))
def test_pending_manual_sale_does_not_discount_and_backend_calculates_total(db):
    product=db.scalar(select(Product).where(Product.sku=="KB-A")); order,created=create_manual_sale(db,data(db)); db.commit()
    assert created and order.status=="pending" and product.stock==5 and order.total==Decimal("80.00")
def test_finalize_manual_sale_discounts_once_and_preserves_historical_price(db):
    product=db.scalar(select(Product).where(Product.sku=="KB-A")); order,_=create_manual_sale(db,data(db,finalize=True)); db.commit()
    assert order.status=="finalized" and product.stock==3 and order.items[0].unit_price==Decimal("40.00")
    duplicate,created=create_manual_sale(db,data(db,finalize=True)); db.commit(); assert not created and duplicate.id==order.id and product.stock==3
    assert db.scalar(select(func.count(InventoryMovement.id)))==1
def test_insufficient_stock_rolls_back_entire_manual_sale(db):
    product=db.scalar(select(Product).where(Product.sku=="KB-B")); payload=data(db,finalize=True,idempotency_key="manual-sale-key-002",items=[OrderLine(product_id=product.id,quantity=2)])
    with pytest.raises(InsufficientStockError): create_manual_sale(db,payload)
    db.rollback(); assert product.stock==1 and db.scalar(select(func.count(Order.id)))==0
def test_occasional_customer_works(db):
    order,_=create_manual_sale(db,data(db,customer_name=None,customer_phone=None)); db.commit(); customer=db.get(Customer,order.customer_id)
    assert customer.name=="Cliente ocasional" and customer.phone==""
def test_existing_customer_is_reused(db):
    customer=Customer(name="Camila",phone="999111222"); db.add(customer); db.commit(); order,_=create_manual_sale(db,data(db,customer_id=customer.id,customer_name=None)); db.commit()
    assert order.customer_id==customer.id and db.scalar(select(func.count(Customer.id)))==1
def test_payment_change_filters_and_admin_permission(db):
    role=Role(name="admin"); db.add(role); db.flush(); user=User(email="admin@test.pe",password_hash="unused",role_id=role.id); db.add(user); order,_=create_manual_sale(db,data(db,payment_status="pending",sales_channel="instagram")); db.commit()
    anonymous=TestClient(app); assert anonymous.get("/api/v1/admin/orders").status_code==401
    def override_db():
        yield db
    app.dependency_overrides[get_db]=override_db; app.dependency_overrides[current_user]=lambda:user
    client=TestClient(app)
    filtered=client.get("/api/v1/admin/orders",params={"customer":"Ocasional","payment_status":"pending","sales_channel":"instagram"})
    assert filtered.status_code==200 and len(filtered.json())==1
    changed=client.patch(f"/api/v1/admin/orders/{order.id}/payment",params={"payment_status":"paid"})
    assert changed.status_code==200 and db.get(Order,order.id).payment_status=="paid"
    log=db.scalar(select(AuditLog).where(AuditLog.entity=="order",AuditLog.entity_id==str(order.id),AuditLog.action=="payment_paid")); assert log is not None
    app.dependency_overrides.clear()
