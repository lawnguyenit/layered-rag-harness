"""H4: document chunks with embeddings (pgvector), under the same row-level security as records

Revision ID: 0003
Revises: 0002

Embedding dimension is not fixed in the column: the model id is stored per row and a query only
matches rows built with its own model, so changing model means re-ingesting, not a schema change.
No vector index: the corpus is tens of chunks and an exact scan is both faster and exact; revisit at scale.
CREATE EXTENSION needs a privileged role (the table owner here); managed databases may need the provider to enable it.
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("""
        CREATE TABLE chunks (
            chunk_id text PRIMARY KEY,
            doc_id text NOT NULL,
            ord integer NOT NULL,
            title text NOT NULL,
            kind text NOT NULL,
            text text NOT NULL,
            allowed_roles text[] NOT NULL,
            owner_customer_id text,
            embedding vector NOT NULL,
            embedding_model text NOT NULL,
            input_hash text NOT NULL,
            UNIQUE (doc_id, ord)
        )
    """)
    op.execute("GRANT SELECT ON chunks TO bepmay_app")
    op.execute("ALTER TABLE chunks ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE chunks FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY chunks_visible ON chunks FOR SELECT TO bepmay_app USING (
            current_setting('app.role', true) = ANY (allowed_roles)
            AND (
                owner_customer_id IS NULL
                OR current_setting('app.role', true) <> 'customer'
                OR owner_customer_id = nullif(current_setting('app.customer_id', true), '')
            )
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE chunks")  # drops its policy and grants with it; the extension is left installed
