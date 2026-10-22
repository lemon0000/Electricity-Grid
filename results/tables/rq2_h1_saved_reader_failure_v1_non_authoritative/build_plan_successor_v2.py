"""Preserve v1 registration and generate the metadata-qualified plan successor."""
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
source=HERE/'register_plan_v1.py';target=HERE/'register_plan_v2.py'
text=source.read_text(encoding='utf-8').replace('support_03','support_04').replace('plan_v1.json','plan_v2.json')
with target.open('x',encoding='utf-8',newline='\n') as stream:stream.write(text)
with (HERE/'plan_generation_v2.json').open('x',encoding='utf-8') as stream:
    json.dump(dict(status='DRAFT_NONAUTHORITATIVE',original=str(source),original_sha256=sha256(source.read_bytes()).hexdigest(),
        successor=str(target),successor_sha256=sha256(target.read_bytes()).hexdigest(),
        changes=['support_03 to support_04 with explicit native solver scope','plan_v2.json output'],
        failure_matrix_and_resource_limits_changed=False,Reader_launched=False),stream,indent=2)
    stream.write('\n')
