"""Update the non-authoritative draft manifest after an explicit root edit."""
from hashlib import sha256
import json
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
ENTRY=HERE.parent/'validation_path_optimization_01/entry_revision_03'
members={p.name:sha256(p.read_bytes()).hexdigest() for p in sorted(ENTRY.iterdir())
    if p.is_file() and p.name not in ('launch_validation.py','package_manifest_v1.json')}
manifest=dict(schema='h1_configured_validation_package_development_v1',
    files_sha256=members, formal_result=False, formal_execution_ready=False,
    native_execution_authorized=False)
raw=(json.dumps(manifest,indent=2)+'\n').encode()
(ENTRY/'package_manifest_v1.json').write_bytes(raw)
pin=sha256(raw).hexdigest()
launcher=ENTRY/'launch_validation.py'
value,count=re.subn(r"MANIFEST_SHA='[0-9a-f]{64}'", "MANIFEST_SHA='"+pin+"'",launcher.read_text(encoding='utf-8'))
assert count==1
launcher.write_text(value,encoding='utf-8',newline='\n')
print(json.dumps(dict(manifest_sha256=pin, members=len(members))))
