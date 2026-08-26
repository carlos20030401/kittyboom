"""virtual cash purchases and paid timestamp

Revision ID: 0004
Revises: 0003
"""
from alembic import op
import sqlalchemy as sa
revision="0004"; down_revision="0003"; branch_labels=None; depends_on=None
def upgrade():
    op.add_column("orders",sa.Column("paid_at",sa.DateTime(timezone=True),nullable=True))
    op.create_table("purchases",sa.Column("id",sa.Integer,primary_key=True),sa.Column("number",sa.String(30),unique=True,nullable=False),sa.Column("supplier",sa.String(180)),sa.Column("receipt_number",sa.String(100)),sa.Column("total",sa.Numeric(12,2),nullable=False),sa.Column("payment_method",sa.String(30),nullable=False),sa.Column("notes",sa.Text),sa.Column("user_id",sa.Integer,sa.ForeignKey("users.id"),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now()))
    op.create_table("purchase_items",sa.Column("id",sa.Integer,primary_key=True),sa.Column("purchase_id",sa.Integer,sa.ForeignKey("purchases.id"),nullable=False),sa.Column("product_id",sa.Integer,sa.ForeignKey("products.id"),nullable=False),sa.Column("quantity",sa.Integer,nullable=False),sa.Column("unit_cost",sa.Numeric(12,2),nullable=False),sa.Column("subtotal",sa.Numeric(12,2),nullable=False),sa.CheckConstraint("quantity > 0"),sa.CheckConstraint("unit_cost > 0"))
    op.create_table("cash_movements",sa.Column("id",sa.Integer,primary_key=True),sa.Column("movement_type",sa.String(40),nullable=False),sa.Column("direction",sa.String(10),nullable=False),sa.Column("amount",sa.Numeric(12,2),nullable=False),sa.Column("description",sa.String(255),nullable=False),sa.Column("payment_method",sa.String(30),nullable=False),sa.Column("order_id",sa.Integer,sa.ForeignKey("orders.id")),sa.Column("purchase_id",sa.Integer,sa.ForeignKey("purchases.id")),sa.Column("user_id",sa.Integer,sa.ForeignKey("users.id")),sa.Column("notes",sa.Text),sa.Column("idempotency_key",sa.String(100),unique=True),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now()),sa.CheckConstraint("amount > 0",name="ck_cash_movement_amount_positive"),sa.CheckConstraint("direction IN ('income','expense')"))
def downgrade():
    op.drop_table("cash_movements"); op.drop_table("purchase_items"); op.drop_table("purchases"); op.drop_column("orders","paid_at")
