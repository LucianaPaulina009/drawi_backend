"""agregar procedencia a atributos

Revision ID: a2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-09-17 18:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "atributos",
        sa.Column("procedencia", sa.String(), nullable=False, server_default="manual"),
    )
    op.alter_column("atributos", "procedencia", server_default=None)


def downgrade() -> None:
    op.drop_column("atributos", "procedencia")
