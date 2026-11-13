"""H2: row-level security under a non-bypass app role

Revision ID: 0002
Revises: 0001

The app role is read-only and is not the table owner. The actor comes from two transaction-local
settings the adapter sets with set_config(..., true): app.role and app.customer_id. A missing
setting is NULL, so the policy fails closed. The role has no password here; set it out of band
(`python -m bepmay_host.provision`).
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'bepmay_app') THEN
                CREATE ROLE bepmay_app LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
            END IF;
        END $$
    """)
    op.execute("GRANT SELECT ON records TO bepmay_app")
    op.execute("ALTER TABLE records ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE records FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY records_visible ON records FOR SELECT TO bepmay_app USING (
            current_setting('app.role', true) = ANY (allowed_roles)
            AND (
                owner_customer_id IS NULL
                OR current_setting('app.role', true) <> 'customer'
                OR owner_customer_id = nullif(current_setting('app.customer_id', true), '')
            )
        )
    """)


def downgrade() -> None:
    op.execute("DROP POLICY records_visible ON records")
    op.execute("ALTER TABLE records NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE records DISABLE ROW LEVEL SECURITY")
    op.execute("REVOKE SELECT ON records FROM bepmay_app")
    # The role is cluster-level and may be used elsewhere; it is intentionally not dropped.
