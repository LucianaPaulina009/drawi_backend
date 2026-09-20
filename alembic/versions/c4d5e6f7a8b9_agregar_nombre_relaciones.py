"""agregar nombre a relaciones

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, Sequence[str], None] = "b3c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("relaciones", sa.Column("nombre", sa.String(length=100), nullable=True))
    op.execute("UPDATE relaciones SET nombre = 'Asociación' WHERE tipo_relacion = 'asociacion'")


def downgrade() -> None:
    op.drop_column("relaciones", "nombre")
