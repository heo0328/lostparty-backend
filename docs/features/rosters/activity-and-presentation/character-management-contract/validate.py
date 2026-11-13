"""Validate documentation artifacts only: no app, provider, database or API calls."""
import json
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).parent

def normalize(raw):
    if not isinstance(raw, str) or not raw.strip(): return None
    try:
        with localcontext() as ctx:
            ctx.prec=128
            value=Decimal(raw)
            if not value.is_finite() or value<0:return None
            if value==0:return '0'
            result=format(value.normalize(),'f')
            return result if len(result)<=64 else None
    except (InvalidOperation,ValueError):return None

def order(row):
    level=normalize(row['level'])
    return (row['rank'] is None,row['rank'] if row['rank'] is not None else 0,
            level is None,Decimal(level).copy_negate() if level is not None else 0,
            row['name'].encode('utf-16-be'),row['id'])

def context_meaning(value):
    data=value['data']; ids=[x['character_id'] for x in data['characters']]
    assert ids==data['ordered_all_character_ids'] and len(ids)==len(set(ids))
    for row in data['characters']:
        assert row['usable']==(row['blocked_reason'] is None)
        if row['item_level'] is not None:assert normalize(row['item_level'])==row['item_level']
    # Stored selected/representative IDs may be outside the current non-retired
    # context even if the persisted configuration_state is still configured.

def put_meaning(value):
    chosen=set(value['activity_character_ids']);rep=value['representative_character_id']
    assert rep in chosen
    if 'ordered_character_ids' in value:
        assert set(value['ordered_character_ids'])==chosen-{rep}

def main():
    schema=json.loads((ROOT/'schema.json').read_text());Draft202012Validator.check_schema(schema)
    def validator(name):return Draft202012Validator({'$ref':'#/$defs/'+name,'$defs':schema['$defs']},format_checker=FormatChecker())
    examples=json.loads((ROOT/'examples.json').read_text());count=0
    for value in examples['contexts'].values():validator('Context').validate(value);context_meaning(value);count+=1
    for value in examples['puts'].values():validator('PutBody').validate(value);put_meaning(value);count+=1
    for row in examples['errors']:validator('Error').validate(row['body']);count+=1
    for row in examples['semantic_rejections']:
        if row['validation']=='schema':assert list(validator('PutBody').iter_errors(row['body']))
        else:
            validator('PutBody').validate(row['body'])
            try:put_meaning(row['body'])
            except AssertionError:pass
            else:raise AssertionError(row['kind'])
        count+=1
    for seq in examples['command_sequences']:
        for k in ('before','ack','stored_ack','current_get'):
            if k in seq:validator('Context').validate(seq[k]);context_meaning(seq[k])
        if 'request' in seq:validator('PutBody').validate(seq['request']);put_meaning(seq['request'])
        if 'error' in seq:validator('Error').validate(seq['error'])
        count+=1
    fixtures=json.loads((ROOT/'comparator-fixtures.json').read_text())
    for row in fixtures['levels']:assert normalize(row['raw'])==row['normalized'];count+=1
    for row in fixtures['cases']:assert [x['id'] for x in sorted(row['items'],key=order)]==row['expected'];count+=1
    print(json.dumps(dict(document_cases=count,schema='PASS',database_http_runtime_tests=False)))

if __name__=='__main__':main()
