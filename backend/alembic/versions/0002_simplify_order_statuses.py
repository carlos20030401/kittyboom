"""simplify order statuses without changing inventory

Revision ID: 0002
Revises: 0001
"""
from alembic import op

revision="0002"
down_revision="0001"
branch_labels=None
depends_on=None

def upgrade():
    op.execute("""
        UPDATE orders
        SET status = CASE
            WHEN status = 'pending' THEN 'pending'
            WHEN status IN ('confirmed','preparing','ready','delivered') THEN 'finalized'
            WHEN status = 'cancelled' THEN 'cancelled'
            ELSE 'pending'
        END
    """)
    op.create_check_constraint("ck_orders_status_simplified","orders","status IN ('pending','finalized','cancelled')")

def downgrade():
    op.drop_constraint("ck_orders_status_simplified","orders",type_="check")
    op.execute("UPDATE orders SET status='confirmed' WHERE status='finalized'")
