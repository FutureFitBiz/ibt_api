"""empty message

Revision ID: 7703bc537ac2
Revises: ff5d561c6c01
Create Date: 2020-06-25 13:59:37.861893

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '7703bc537ac2'
down_revision = 'ff5d561c6c01'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('impact', 'option_text',
               existing_type=mysql.VARCHAR(length=200),
               type_=sa.String(length=500),
               existing_nullable=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('impact', 'option_text',
               existing_type=sa.String(length=500),
               type_=mysql.VARCHAR(length=200),
               existing_nullable=False)
    # ### end Alembic commands ###
