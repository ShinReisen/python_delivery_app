"""add orders assigments

Revision ID: ed087f7208a9
Revises: 53909d79660c
Create Date: 2023-05-14 22:49:18.238400

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'ed087f7208a9'
down_revision = '53909d79660c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('orders_assignments',
    sa.Column('assignments_id', sa.Integer(), nullable=False),
    sa.Column('courier_id', sa.Integer(), nullable=False),
    sa.Column('courier_type', sa.String(), nullable=False),
    sa.Column('delivery_date', sa.Date(), nullable=False),
    sa.Column('turn_time', sa.Time(), nullable=False),
    sa.Column('regions', postgresql.ARRAY(sa.Integer()), nullable=False),
    sa.Column('orders', postgresql.ARRAY(sa.Integer()), nullable=False),
    sa.ForeignKeyConstraint(['courier_id'], ['couriers.courier_id'], ),
    sa.PrimaryKeyConstraint('assignments_id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('orders_assignments')
    # ### end Alembic commands ###
