"""administrable hero banners

Revision ID: 0006
Revises: 0005
"""
from alembic import op
import sqlalchemy as sa
revision="0006";down_revision="0005";branch_labels=None;depends_on=None
def upgrade():
    op.add_column("banners",sa.Column("filename",sa.String(255),nullable=True))
    op.add_column("banners",sa.Column("mime_type",sa.String(60),nullable=True))
    op.add_column("banners",sa.Column("size",sa.Integer(),nullable=True))
    op.add_column("banners",sa.Column("alt_text",sa.String(255),nullable=False,server_default="Portada de KittyBoom"))
    op.add_column("banners",sa.Column("position",sa.Integer(),nullable=False,server_default="0"))
    op.add_column("banners",sa.Column("is_primary",sa.Boolean(),nullable=False,server_default=sa.false()))
def downgrade():
    for name in ["is_primary","position","alt_text","size","mime_type","filename"]:op.drop_column("banners",name)
