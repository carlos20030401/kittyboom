from decimal import Decimal
import pytest
from sqlalchemy import create_engine,select,func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db.base import Base
from app.models import CashMovement,Category,Customer,InventoryMovement,Order,Product,ProductVariant,Purchase,Role,User
from app.schemas import ManualSaleCreate,OrderLine,PurchaseIn,PurchaseLineIn
from app.services.cash import create_purchase
from app.services.orders import create_manual_sale,transition_pending_order,InvalidOrderTransitionError

@pytest.fixture()
def db():
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool);Base.metadata.create_all(engine);s=sessionmaker(bind=engine,expire_on_commit=False)();role=Role(name='admin');category=Category(name='Variantes');s.add_all([role,category]);s.flush();user=User(email='variants@test.pe',password_hash='x',role_id=role.id);simple=Product(sku='SIMPLE',name='Simple',category_id=category.id,price=Decimal('30'),stock=5,min_stock=1);product=Product(sku='BASE',name='Anillo',category_id=category.id,price=Decimal('50'),sale_price=Decimal('45'),stock=9,min_stock=1,has_variants=True);s.add_all([user,simple,product]);s.flush();gold=ProductVariant(product_id=product.id,name='Dorado',sku='BASE-D',price=Decimal('60'),stock=4,min_stock=1,is_active=True,position=0);silver=ProductVariant(product_id=product.id,name='Plateado',sku='BASE-P',price=None,stock=2,min_stock=1,is_active=True,position=1);s.add_all([gold,silver]);s.commit();yield s,user,simple,product,gold,silver;s.close();Base.metadata.drop_all(engine)
def sale(items,key='variant-key',finalize=False):return ManualSaleCreate(payment_method='cash',payment_status='paid',sales_channel='in_store',finalize=finalize,idempotency_key=key,items=items)
def test_simple_and_variant_prices_and_independent_stock(db):
    s,user,simple,product,gold,silver=db;simple_order,_=create_manual_sale(s,sale([OrderLine(product_id=simple.id,quantity=1)],'simple-key',True),user.id);variant_order,_=create_manual_sale(s,sale([OrderLine(product_id=product.id,variant_id=gold.id,quantity=2),OrderLine(product_id=product.id,variant_id=silver.id,quantity=1)],'variant-key',True),user.id);s.commit()
    assert simple.stock==4 and product.stock==9 and gold.stock==2 and silver.stock==1
    assert variant_order.total==Decimal('165') and {i.unit_price for i in variant_order.items}=={Decimal('60'),Decimal('45')}
    assert len(variant_order.items)==2 and simple_order.items[0].variant_id is None
def test_variant_required_and_out_of_stock_rejected(db):
    s,user,_,product,gold,_=db
    with pytest.raises(ValueError,match='Selecciona una variante'):create_manual_sale(s,sale([OrderLine(product_id=product.id,quantity=1)]),user.id)
    s.rollback();gold.stock=0;s.commit();order,_=create_manual_sale(s,sale([OrderLine(product_id=product.id,variant_id=gold.id,quantity=1)],'empty-key'),user.id);s.commit()
    with pytest.raises(Exception):transition_pending_order(s,order.id,'finalized')
def test_repeat_finalization_never_duplicates_variant_discount(db):
    s,user,_,product,gold,_=db;order,_=create_manual_sale(s,sale([OrderLine(product_id=product.id,variant_id=gold.id,quantity=1)],finalize=True),user.id);s.commit()
    with pytest.raises(InvalidOrderTransitionError):transition_pending_order(s,order.id,'finalized',user.id)
    s.rollback();assert gold.stock==3 and s.scalar(select(func.count(InventoryMovement.id)))==1 and s.scalar(select(func.count(CashMovement.id)))==1
def test_purchase_updates_only_selected_variants(db):
    s,user,_,product,gold,silver=db;purchase=create_purchase(s,PurchaseIn(items=[PurchaseLineIn(product_id=product.id,variant_id=gold.id,quantity=2,unit_cost=Decimal('10')),PurchaseLineIn(product_id=product.id,variant_id=silver.id,quantity=3,unit_cost=Decimal('8'))]),user.id);s.commit()
    assert purchase.total==Decimal('44') and gold.stock==6 and silver.stock==5 and product.stock==9
    assert s.scalar(select(func.count(Purchase.id)))==1 and s.scalar(select(func.count(CashMovement.id)))==1
def test_migration_keeps_historical_relations_nullable_without_stock_updates():
    from pathlib import Path
    text=(Path(__file__).parents[1]/'alembic'/'versions'/'0005_product_variants.py').read_text(encoding='utf-8');upgrade=text.split('def downgrade',1)[0].lower();assert 'nullable=true' in upgrade and 'update products' not in upgrade and 'inventory_movements' in upgrade
