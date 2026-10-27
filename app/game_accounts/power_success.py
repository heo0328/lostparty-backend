"""Latest observed, successfully stored role power. Never a provider assertion.

Caller owns game-mutations lock and transaction. The public P1 head/response is
unchanged: null/failure can coexist with a retained, versioned success snapshot.
"""
from copy import deepcopy
from datetime import datetime
from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Integer, String, UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column
from app.auth.models import Base, stamp


class RolePowerSuccess(Base):
    __tablename__ = 'character_role_power_successes'
    user_id = mapped_column(UUID, primary_key=True)
    character_id = mapped_column(UUID, primary_key=True)
    ownership_revision = mapped_column(Integer, primary_key=True)
    role = mapped_column(String(16), primary_key=True)
    power_revision = mapped_column(Integer, nullable=False)
    combat_power = mapped_column(String(32), nullable=False)
    observed_at = stamp()
    source_summary_version = mapped_column(Integer, nullable=False)
    source_saved_at = stamp()
    source_summary = mapped_column(JSONB, nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(['user_id', 'character_id', 'ownership_revision', 'role'],
                             ['character_role_summaries.user_id', 'character_role_summaries.character_id',
                              'character_role_summaries.ownership_revision', 'character_role_summaries.role'], ondelete='CASCADE'),
        CheckConstraint("ownership_revision>=1 AND power_revision>=2 AND source_summary_version>=1 AND role IN ('dealer','support')"),
        CheckConstraint("combat_power ~ '^[0-9]+([.][0-9]+)?$'"),
        CheckConstraint("jsonb_typeof(source_summary)='object'"),
    )


def capture(db, head):
    """Persist the value, timestamp and exact warnings/version atomically.

    Accepted non-null power is a success even when build warnings/errors exist.
    Older delayed observations cannot replace the newer success; the public head
    still follows its existing save semantics. Equal observations use head CAS.
    """
    payload = head.summary
    value = payload['combat_power']
    if value is None:
        return
    observed = datetime.fromisoformat(payload['combat_power_observed_at'].replace('Z', '+00:00'))
    key = (head.user_id, head.character_id, head.ownership_revision, head.role)
    previous = db.get(RolePowerSuccess, key)
    if previous is not None and (observed, head.version) <= (previous.observed_at, previous.source_summary_version):
        return
    fields = dict(combat_power=value, observed_at=observed,
                  source_summary_version=head.version, source_saved_at=head.saved_at,
                  source_summary=deepcopy(payload))
    if previous is None:
        db.add(RolePowerSuccess(user_id=head.user_id, character_id=head.character_id,
                               ownership_revision=head.ownership_revision, role=head.role,
                               power_revision=2, **fields))
    else:
        for field, content in fields.items():
            setattr(previous, field, content)
        previous.power_revision += 1
