"""records: orders, tickets and invoices for exact-ID lookup (H1)

Revision ID: 0001
Revises:
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE records (
            doc_id text PRIMARY KEY,
            kind text NOT NULL CHECK (kind IN ('order', 'ticket', 'invoice')),
            ref_id text NOT NULL,
            title text NOT NULL,
            body text NOT NULL,
            allowed_roles text[] NOT NULL,
            owner_customer_id text,
            UNIQUE (kind, ref_id)
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE records")
