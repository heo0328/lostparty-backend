"""Initial additive authentication tables. Frozen DDL, no runtime model imports."""
from alembic import op
revision = "0001_auth"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.execute('\nCREATE TABLE auth_transactions (\n\tid UUID NOT NULL, \n\tnonce_digest VARCHAR(64) NOT NULL, \n\tsecret_digest VARCHAR(64) NOT NULL, \n\texpires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tconsumed_at TIMESTAMP WITH TIME ZONE, \n\tPRIMARY KEY (id), \n\tUNIQUE (nonce_digest)\n)\n\n')
    op.execute('CREATE INDEX ix_auth_transactions_expires_at ON auth_transactions (expires_at)')
    op.execute("\nCREATE TABLE users (\n\tid UUID NOT NULL, \n\tstatus VARCHAR(16) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tlast_login_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tCHECK (status IN ('active','disabled'))\n)\n\n")
    op.execute('\nCREATE TABLE auth_identities (\n\tid UUID NOT NULL, \n\tuser_id UUID NOT NULL, \n\tprovider VARCHAR(16) NOT NULL, \n\tissuer VARCHAR(128) NOT NULL, \n\tsubject VARCHAR(255) NOT NULL, \n\tlinked_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (provider, issuer, subject), \n\tFOREIGN KEY(user_id) REFERENCES users (id)\n)\n\n')
    op.execute('CREATE INDEX ix_auth_identities_user_id ON auth_identities (user_id)')
    op.execute('\nCREATE TABLE auth_sessions (\n\tid UUID NOT NULL, \n\tuser_id UUID NOT NULL, \n\tremember_me BOOLEAN NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tabsolute_expires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tidle_expires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\trevoked_at TIMESTAMP WITH TIME ZONE, \n\trevoked_reason VARCHAR(32), \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(user_id) REFERENCES users (id)\n)\n\n')
    op.execute('CREATE INDEX ix_auth_sessions_absolute_expires_at ON auth_sessions (absolute_expires_at)')
    op.execute('CREATE INDEX ix_auth_sessions_user_id ON auth_sessions (user_id)')
    op.execute('\nCREATE TABLE refresh_credentials (\n\tid UUID NOT NULL, \n\tsession_id UUID NOT NULL, \n\tgeneration INTEGER NOT NULL, \n\ttoken_digest VARCHAR(64) NOT NULL, \n\tissued_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\texpires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tconsumed_at TIMESTAMP WITH TIME ZONE, \n\trequest_digest VARCHAR(64), \n\tsuccessor_id UUID, \n\tPRIMARY KEY (id), \n\tUNIQUE (session_id, generation), \n\tUNIQUE (session_id, request_digest), \n\tFOREIGN KEY(session_id) REFERENCES auth_sessions (id), \n\tUNIQUE (token_digest), \n\tFOREIGN KEY(successor_id) REFERENCES refresh_credentials (id)\n)\n\n')
    op.execute('\nCREATE TABLE refresh_recoveries (\n\tid UUID NOT NULL, \n\told_id UUID NOT NULL, \n\tsuccessor_id UUID NOT NULL, \n\trequest_digest VARCHAR(64) NOT NULL, \n\texpires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tresend_count INTEGER NOT NULL, \n\tkey_id VARCHAR(64) NOT NULL, \n\tnonce BYTEA NOT NULL, \n\tciphertext BYTEA NOT NULL, \n\tPRIMARY KEY (id), \n\tCHECK (resend_count BETWEEN 0 AND 2), \n\tUNIQUE (key_id, nonce), \n\tUNIQUE (old_id), \n\tFOREIGN KEY(old_id) REFERENCES refresh_credentials (id), \n\tFOREIGN KEY(successor_id) REFERENCES refresh_credentials (id)\n)\n\n')
    op.execute('CREATE INDEX ix_refresh_recoveries_expires_at ON refresh_recoveries (expires_at)')

def downgrade():
    raise RuntimeError("Destructive authentication downgrade requires an explicit recovery plan")
