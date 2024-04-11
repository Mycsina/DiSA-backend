"""empty message

Revision ID: 2833ff4e875f
Revises: 88fd9b16e507
Create Date: 2024-04-11 20:08:39.543079

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '2833ff4e875f'
down_revision: Union[str, None] = '88fd9b16e507'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('collection', 'submission_date')
    op.drop_column('collection', 'last_update')
    op.drop_column('document', 'submission_date')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('document', sa.Column('submission_date', sa.DATETIME(), nullable=False))
    op.add_column('collection', sa.Column('last_update', sa.DATETIME(), nullable=True))
    op.add_column('collection', sa.Column('submission_date', sa.DATETIME(), nullable=False))
    # ### end Alembic commands ###
