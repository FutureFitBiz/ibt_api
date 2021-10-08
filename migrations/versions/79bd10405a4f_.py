"""empty message

Revision ID: 79bd10405a4f
Revises: ba866013e208
Create Date: 2020-08-24 13:58:40.675310

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '79bd10405a4f'
down_revision = 'ba866013e208'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('company', sa.Column('hidden', sa.Boolean(), nullable=False))
    op.drop_column('company', 'ignored')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('company', sa.Column('ignored', mysql.TINYINT(display_width=1), autoincrement=False, nullable=False))
    op.drop_column('company', 'hidden')
    # ### end Alembic commands ###
