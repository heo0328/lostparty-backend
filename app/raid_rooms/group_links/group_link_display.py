"""Optional retained group link on authorized detail/plan, in the same snapshot."""

from app.groups import features

from app.raid_rooms.admissions import admission_service as base

from app.raid_rooms.reads import cycle_member_reads as members

from app.raid_rooms.participation import membership_readers

from app.raid_rooms.models.integrated_models import RecruitmentRoom

def get(principal, rid, key, kind, *, reader_profile=None, membership_id=None, cycle_member_id=None,
        include_resume_display=False):
    # Original reader owns authorization, including historical ownership anchors.
    with base.snapshot(principal) as snap:
        db, uid, stamp = snap
        features.ready(db)
        if reader_profile == 'membership-actions-1':
            result = membership_readers.get(principal,rid,key,kind,membership_id=membership_id,
                cycle_member_id=cycle_member_id,include_resume_display=include_resume_display,read_snapshot=snap)
        elif kind == 'detail':
            result = members.detail(principal,rid,key,reader_profile=reader_profile,read_snapshot=snap)
        else:
            result = members.plan(principal,rid,key,include_resume_display,read_snapshot=snap)
        room = db.get(RecruitmentRoom, rid)
        from app.raid_rooms.common import cycles
        from app.raid_rooms.group_links import cycle_group_policy as policy
        if policy.enabled(db):
            _,row=cycles.resolve(db,rid,key,stamp)
            # Membership detail can legitimately be relation-only before T opens.
            # No actual-T policy exists; never borrow the other week's group.
            if row is None:
                return dict(result,group_state=None)
            target=result.get('data',{}).get('target',{})
            value=policy.metadata(db,row,generation=target['target_generation']) if 'target_generation' in target else policy.metadata(db,row)
            return dict(result,group_state=features.group_state(db,value['group_id']))
        return dict(result, group_state=features.group_state(db,room.group_id))
