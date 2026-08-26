"""complete optional product variants

Revision ID: 0005
Revises: 0004
"""
from alembic import op
import sqlalchemy as sa
revision="0005";down_revision="0004";branch_labels=None;depends_on=None
def upgrade():
    op.add_column("products",sa.Column("has_variants",sa.Boolean(),nullable=False,server_default=sa.false()))
    for name,column in [
        ("color",sa.Column("color",sa.String(80))),
        ("size",sa.Column("size",sa.String(80))),
        ("model",sa.Column("model",sa.String(80))),
        ("finish",sa.Column("finish",sa.String(80))),
        ("price",sa.Column("price",sa.Numeric(12,2))),
        ("min_stock",sa.Column("min_stock",sa.Integer(),nullable=False,server_default="2")),
        ("is_active",sa.Column("is_active",sa.Boolean(),nullable=False,server_default=sa.true())),
        ("image_url",sa.Column("image_url",sa.String(500))),
        ("position",sa.Column("position",sa.Integer(),nullable=False,server_default="0")),
    ]:op.add_column("product_variants",column)
    op.add_column("order_items",sa.Column("variant_id",sa.Integer(),sa.ForeignKey("product_variants.id"),nullable=True))
    op.add_column("order_items",sa.Column("variant_name",sa.String(120),nullable=True))
    op.add_column("order_items",sa.Column("variant_sku",sa.String(50),nullable=True))
    op.add_column("order_items",sa.Column("variant_image_url",sa.String(500),nullable=True))
    op.add_column("purchase_items",sa.Column("variant_id",sa.Integer(),sa.ForeignKey("product_variants.id"),nullable=True))
    op.add_column("inventory_movements",sa.Column("variant_id",sa.Integer(),sa.ForeignKey("product_variants.id"),nullable=True))
def downgrade():
    op.drop_column("inventory_movements","variant_id");op.drop_column("purchase_items","variant_id")
    for name in ["variant_image_url","variant_sku","variant_name","variant_id"]:op.drop_column("order_items",name)
    for name in ["position","image_url","is_active","min_stock","price","finish","model","size","color"]:op.drop_column("product_variants",name)
    op.drop_column("products","has_variants")
