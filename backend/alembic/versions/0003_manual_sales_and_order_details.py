"""manual sales and order detail fields

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa
revision="0003"
down_revision="0002"
branch_labels=None
depends_on=None
def upgrade():
    op.add_column("orders",sa.Column("sales_channel",sa.String(30),nullable=False,server_default="web"))
    op.add_column("orders",sa.Column("idempotency_key",sa.String(80),nullable=True))
    op.create_unique_constraint("uq_orders_idempotency_key","orders",["idempotency_key"])
def downgrade():
    op.drop_constraint("uq_orders_idempotency_key","orders",type_="unique")
    op.drop_column("orders","idempotency_key")
    op.drop_column("orders","sales_channel")
