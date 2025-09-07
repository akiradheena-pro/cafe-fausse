
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'customers',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=32), nullable=True),
        sa.Column('newsletter_opt_in', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_customers_email', 'customers', ['email'], unique=True)

    op.create_table(
        'reservations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('customer_id', sa.Integer(), sa.ForeignKey('customers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('time_slot', sa.DateTime(timezone=True), nullable=False),
        sa.Column('table_number', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_reservations_customer_id', 'reservations', ['customer_id'])
    op.create_index('ix_reservations_time_slot', 'reservations', ['time_slot'])
    op.create_unique_constraint('uq_reservation_slot_table', 'reservations', ['time_slot', 'table_number'])

def downgrade():
    op.drop_constraint('uq_reservation_slot_table', 'reservations', type_='unique')
    op.drop_index('ix_reservations_time_slot', table_name='reservations')
    op.drop_index('ix_reservations_customer_id', table_name='reservations')
    op.drop_table('reservations')
    op.drop_index('ix_customers_email', table_name='customers')
    op.drop_table('customers')
