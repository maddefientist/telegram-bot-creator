"""Add wallet authentication support.

Revision ID: 002
Revises: 001
Create Date: 2026-01-09 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add wallet authentication fields and nonces table."""
    # Add wallet_address column
    op.add_column('users', sa.Column('wallet_address', sa.String(44), nullable=True))

    # Add auth_method column with default 'email'
    op.add_column(
        'users',
        sa.Column('auth_method', sa.String(20), nullable=False, server_default='email')
    )

    # Make email and hashed_password nullable (wallet users won't have them)
    op.alter_column('users', 'email', nullable=True)
    op.alter_column('users', 'hashed_password', nullable=True)

    # Add unique index on wallet_address
    op.create_index(
        'ix_users_wallet_address',
        'users',
        ['wallet_address'],
        unique=True
    )

    # Add check constraint to ensure data integrity
    op.create_check_constraint(
        'user_auth_method_check',
        'users',
        "(auth_method = 'email' AND email IS NOT NULL AND hashed_password IS NOT NULL) OR "
        "(auth_method = 'wallet' AND wallet_address IS NOT NULL)"
    )

    # Create wallet_nonces table
    op.create_table(
        'wallet_nonces',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('wallet_address', sa.String(44), nullable=False),
        sa.Column('nonce', sa.String(64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used', sa.Boolean(), nullable=False, server_default='false'),
    )

    # Add indexes to wallet_nonces for fast lookups
    op.create_index('ix_wallet_nonces_wallet_address', 'wallet_nonces', ['wallet_address'])
    op.create_index('ix_wallet_nonces_expires_at', 'wallet_nonces', ['expires_at'])


def downgrade() -> None:
    """Remove wallet authentication support."""
    # Drop wallet_nonces table
    op.drop_index('ix_wallet_nonces_expires_at', 'wallet_nonces')
    op.drop_index('ix_wallet_nonces_wallet_address', 'wallet_nonces')
    op.drop_table('wallet_nonces')

    # Remove check constraint
    op.drop_constraint('user_auth_method_check', 'users', type_='check')

    # Remove wallet_address index
    op.drop_index('ix_users_wallet_address', 'users')

    # Make email and hashed_password required again
    op.alter_column('users', 'email', nullable=False)
    op.alter_column('users', 'hashed_password', nullable=False)

    # Remove new columns
    op.drop_column('users', 'auth_method')
    op.drop_column('users', 'wallet_address')
