"""Generate static DTOs for the W2/W3/W4 candidate, without runtime docs dependencies.

Run in a disposable tooling venv with datamodel-code-generator==0.86.0.
The checked-in generated module is the application input, not this tool.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOTS={
    'SubmissionInput':'Input_contract3_put__v2_me_raid-rooms_room_id_availability-submission',
    'SubmissionOutput':'Output_contract3_get__v2_me_raid-rooms_room_id_availability-submission',
    'TimeContext':'Output_contract3_get__v2_me_raid-rooms_room_id_schedule-context',
    'OverlapPage':'Output_contract3_get__v2_me_raid-schedule-overlaps',
    'ConfirmationInput':'Input_contract3_post__v2_raid-sessions_session_id_participation-confirmations',
    **{n:n for n in ('ContinuationContext','ContinueCommand','ScopedCommand','CancellationContext','CancellationCommand',
        'OpeningContext','OpeningCommand','TransferContext','TransferCommand')},
    'CharacterChange':'Input_contract3_post__v2_raid-rooms_room_id_character-changes',
    'Error':'Error',
    'Projections':'Output_contract3_get__v2_groups_group_id_raid-room-member-projections',
    'Create':'Input_contract3_post__v2_raid-rooms',
    'CreationContext':'Output_contract3_get__v2_me_raid-room-creation-context',
    'CreateAck':'CreateAck',
    'Search':'Input_contract3_post__v2_raid-rooms_search',
    'Page':'Output_contract3_post__v2_raid-rooms_search',
    'Card':'Output_contract3_get__v2_raid-rooms_room_id',
    'Detail':'Output_contract3_get__v2_raid-rooms_room_id_detail',
    'Plan':'Output_contract3_get__v2_me_raid-rooms_room_id_plan',
    'AdmissionContext':'Output_contract3_get__v2_raid-rooms_room_id_admission-context',
    'Admission':'Input_contract3_post__v2_raid-rooms_room_id_join',
    'Ack':'Output_contract3_post__v2_raid-rooms_room_id_join',
    'ApplicationAck':'Output_contract3_post__v2_raid-rooms_room_id_applications',
    'Approve':'Input_contract3_post__v2_raid-room-applications_application_id_approve',
    'Withdraw':'Input_contract3_post__v2_raid-room-applications_application_id_withdraw',
    'Application':'Output_contract3_get__v2_raid-room-applications_application_id',
    'ApplicationPage':'Output_contract3_get__v2_raid-rooms_room_id_applications',
    'MembershipPage':'Output_contract3_get__v2_me_raid-room-memberships',
}


def main():
    arguments=argparse.ArgumentParser()
    arguments.add_argument('--generator',default='datamodel-codegen')
    arguments.add_argument('--output',default='app/raid_rooms/cycle_wire.py')
    options=arguments.parse_args()
    full=json.loads(Path('docs/design/issue13-two-cycle.full.openapi.json').read_text())
    digest=hashlib.sha256(json.dumps(full,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
    assert digest=='fb4c7d065594a9a0e7e8288e5f73179f90b078b68ac4323d1aade5c7a63b42f1'
    schemas=full['components']['schemas']
    found=set()
    def scan(value):
        if isinstance(value,dict):
            if '$ref' in value:
                name=value['$ref'].rsplit('/',1)[1]
                if name not in found:found.add(name);scan(schemas[name])
            for child in value.values():scan(child)
        elif isinstance(value,list):
            for child in value:scan(child)
    for name in ROOTS.values():scan({'$ref':'#/components/schemas/'+name})
    document={'type':'object','title':'W2Models','properties':{k:{'$ref':'#/components/schemas/'+v} for k,v in ROOTS.items()},
              'components':{'schemas':{k:schemas[k] for k in sorted(found)}}}
    with tempfile.TemporaryDirectory() as directory:
        source=Path(directory)/'w2.json'
        source.write_text(json.dumps(document,ensure_ascii=False))
        subprocess.run([options.generator,'--input',str(source),'--input-file-type','jsonschema',
            '--output',options.output,'--output-model-type','pydantic_v2.BaseModel',
            '--target-python-version','3.12','--strict-types','str','int','float','bool',
            '--extra-fields','forbid','--use-standard-collections','--use-union-operator',
            '--strict-nullable','--disable-timestamp','--use-subclass-enum'],check=True)


if __name__=='__main__':main()
