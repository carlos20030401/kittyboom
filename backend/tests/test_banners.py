from pathlib import Path
from sqlalchemy import create_engine,select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db.base import Base
from app.models import Banner
def test_banner_primary_order_and_persistence_after_reload():
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool);Base.metadata.create_all(engine);Session=sessionmaker(bind=engine,expire_on_commit=False);db=Session();db.add_all([Banner(title='Portada',image_url='/uploads/a.webp',filename='a.webp',alt_text='Primera',position=0,is_primary=False),Banner(title='Portada',image_url='/uploads/b.webp',filename='b.webp',alt_text='Principal',position=4,is_primary=True)]);db.commit();db.close();reloaded=Session();items=reloaded.scalars(select(Banner).order_by(Banner.is_primary.desc(),Banner.position)).all();assert items[0].alt_text=='Principal' and items[0].is_primary;assert len(items)==2;reloaded.close();Base.metadata.drop_all(engine)
def test_banner_migration_is_after_variants_and_preserves_existing_rows():
    text=(Path(__file__).parents[1]/'alembic'/'versions'/'0006_admin_hero_banners.py').read_text(encoding='utf-8');upgrade=text.split('def downgrade',1)[0].lower();assert 'down_revision="0005"' in text and 'delete from banners' not in upgrade and 'drop_table' not in upgrade
