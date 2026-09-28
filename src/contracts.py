"""Shared conversion boundary for designer drafts and strict contract validation."""
import copy
import json
from pathlib import Path
from uuid import uuid4

from jsonschema import Draft202012Validator

SCHEMA = json.loads((Path(__file__).resolve().parents[1] / 'schemas/robot-design.schema.json').read_text())
VALIDATOR = Draft202012Validator(SCHEMA)
COLORS = dict(zip(
    ['red','blue','green','yellow','pink','purple','orange','black','white','silver','gold'],
    ['#FF0000','#0000FF','#008000','#FFFF00','#FFC0CB','#800080','#FFA500','#000000','#FFFFFF','#C0C0C0','#FFD700']))

def validate_contract(value):
    errors = sorted(VALIDATOR.iter_errors(value), key=lambda e: str(list(e.path)))
    if errors:
        raise ValueError('; '.join(f'{list(e.path)}: {e.message}' for e in errors[:5]))
    return value

def from_designer(draft, ip_id=None):
    design = draft['design']
    appearance = copy.deepcopy(design['appearance'])
    appearance['body_color'] = COLORS[appearance['color_primary']]
    appearance['wing_type'] = 'round'
    personality = copy.deepcopy(design['personality'])
    personality['trait'] = {'timid':'calm','gentle':'calm','naughty':'silly'}.get(personality['type'], 'lively')
    personality['catchphrase'] = ''
    result = {
        'ip_id': ip_id or 'child-' + uuid4().hex,
        'designer':'child', 'appearance':appearance, 'personality':personality,
        'expression_set':['natural'],
        'locomotion':{'mode':'fly' if '翅膀' in appearance.get('parts',[]) else 'walk', 'physics_profile':'standard'},
        'battery':100, 'safety':{'role_boundaries':'ally-of-child-not-parent-spy','content_filter':True},
        'source':design.get('source','text'),
    }
    result.update({k:draft[k] for k in ('image_prompt','code_stub','build_hint') if k in draft})
    return validate_contract(result)
