"""initial_schema

Revision ID: 37df11e4c3e8
Revises: 
Create Date: 2026-09-30 18:42:06.706418

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '37df11e4c3e8'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema — create initial tables if not present."""
    from app.models.database import Base
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    """Downgrade schema — drop tables."""
    from app.models.database import Base
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
