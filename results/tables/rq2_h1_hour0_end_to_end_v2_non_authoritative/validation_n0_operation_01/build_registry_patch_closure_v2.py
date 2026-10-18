"""Bind current provisional sources as deterministic patches of pinned predecessors."""
import base64
import difflib
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;REPO=HERE.parents[3]
OUT=HERE/'registry_sources_02_non_authoritative';OUT.mkdir(exist_ok=False)
original=json.loads((HERE/'registry_draft_sources_01.json').read_bytes())['predecessors_sha256']
mapping=(('h1_historical_n0_verifier_development_v2.py','h1_historical_n0_verifier_development_v3.py'),
    ('h1_bootstrap_integration_development_v2.py','h1_bootstrap_integration_development_v4.py'),
    ('h1_owned_bootstrap_controller_development_v3.py','h1_owned_bootstrap_controller_development_v4.py'))
patches=[]
for before_name,after_name in mapping:
    before=REPO/'experiments'/before_name;after=REPO/'experiments'/after_name
    source=before.read_bytes();target=after.read_bytes();assert sha256(source).hexdigest()==original[str(before)]
    left=source.splitlines(keepends=True);right=target.splitlines(keepends=True);segments=[]
    for tag,i,j,k,l in difflib.SequenceMatcher(None,left,right,autojunk=False).get_opcodes():
        if tag=='equal':segments.append(dict(copy_lines=[i,j]))
        elif tag in ('replace','insert'):segments.append(dict(literal_base64=base64.b64encode(b''.join(right[k:l])).decode('ascii')))
    rebuilt=b''.join(b''.join(left[s['copy_lines'][0]:s['copy_lines'][1]]) if 'copy_lines' in s
        else base64.b64decode(s['literal_base64']) for s in segments)
    assert rebuilt==target;compile(rebuilt,str(after),'exec')
    snapshot=OUT/'sources'/after_name;snapshot.parent.mkdir(exist_ok=True)
    with snapshot.open('xb') as stream:stream.write(target)
    patches.append(dict(predecessor=before.relative_to(REPO).as_posix(),predecessor_sha256=sha256(source).hexdigest(),
        successor=after.relative_to(REPO).as_posix(),successor_sha256=sha256(target).hexdigest(),segments=segments))
value=dict(status='DRAFT_NONAUTHORITATIVE',schema='registry_source_patch_closure_v2',patches=patches,
    builder_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
    supersedes='registry_draft_sources_01.json initial generation only; all prior attempts retained',
    full_hour0_chain_passed=False,formal_execution_ready=False,formal_result=False,
    resource_admission=False,native_execution_authorized=False)
with (OUT/'patch_manifest.json').open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
print(json.dumps(dict(status=value['status'],manifest=str(OUT/'patch_manifest.json'),
    manifest_sha256=sha256((OUT/'patch_manifest.json').read_bytes()).hexdigest())),flush=True)
