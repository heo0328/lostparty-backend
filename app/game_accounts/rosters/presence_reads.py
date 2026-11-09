"""Batch owned observation projections shared by bootstrap and paged reads."""
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import distinct_on
from app.game_accounts import roster_presence
from app.game_accounts.models import Account, Character
from app.game_accounts.rosters.lifecycle import digest
from app.game_accounts.support import fail
from fastapi.encoders import jsonable_encoder


def attach(db, uid, stamp, pages):
    if not roster_presence.enabled(db):
        fail('RECRUITMENT_COMMAND_NOT_READY', 503)
    aids = {p['game_account_id'] for p in pages if p['ownership_status'] == 'owned'}
    accounts = {a.id:a for a in db.scalars(select(Account).where(Account.id.in_(aids), Account.owner_id==uid))} if aids else {}
    chars = list(db.scalars(select(Character).where(Character.account_id.in_(accounts), Character.lifecycle_state!='retired').order_by(Character.id))) if accounts else []
    observations = list(db.scalars(select(roster_presence.RosterTransition).where(
        roster_presence.RosterTransition.account_id.in_(accounts), roster_presence.RosterTransition.owner_id==uid,
        roster_presence.RosterTransition.character_id.in_([c.id for c in chars]))
        .ext(distinct_on(roster_presence.RosterTransition.character_id,roster_presence.RosterTransition.ownership_revision))
        .order_by(roster_presence.RosterTransition.character_id,roster_presence.RosterTransition.ownership_revision,roster_presence.RosterTransition.to_revision.desc()))) if accounts else []
    latest = {(o.character_id,o.ownership_revision):o for o in observations}
    by_account = {}
    for c in chars:
        a = accounts[c.account_id]
        o = latest.get((c.id,a.ownership_revision))
        state = 'unknown'
        if o and o.to_revision == c.lifecycle_revision:
            if o.state=='missing' and c.lifecycle_state=='suspect' and c.status=='suspect':state='missing'
            elif o.state=='present' and c.lifecycle_state=='active' and c.status=='confirmed':state='present'
        by_account.setdefault(a.id,{})[str(c.id)] = (dict(state=state, observed_at=o.observed_at if state!='unknown' else None), c.lifecycle_revision)
    for page in pages:
        account = accounts.get(page['game_account_id'])
        values = by_account.get(account.id,{}) if account else {}
        scope = dict(profile='roster-presence-1', registration_id=page['registration_id'],
            registration_version=page['registration_version'], ownership_revision=page['ownership_revision'],
            roster_revision=page['roster_revision'], evaluated_at=stamp)
        scope['presence_revision'] = digest(jsonable_encoder([uid,scope['registration_id'],scope['registration_version'],
            scope['ownership_revision'],scope['roster_revision'],sorted(values.items())]))
        page['roster_presence_scope'] = scope
        for item in page['items']:
            item['roster_presence'] = values.get(str(item['character_id']), (dict(state='unknown',observed_at=None),None))[0]
    return pages
