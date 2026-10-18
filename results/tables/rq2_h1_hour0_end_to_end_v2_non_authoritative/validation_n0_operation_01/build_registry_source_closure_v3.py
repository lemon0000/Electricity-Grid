"""Preserve a new reconstructible draft after the runtime-registry repair."""
import base64
from difflib import SequenceMatcher
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
prior=json.loads((HERE/'registry_sources_02_non_authoritative/patch_manifest.json').read_bytes())
out=HERE/'registry_sources_03_non_authoritative'
out.mkdir(exist_ok=False)
patches=[]
for old in prior['patches']:
    source=REPO/old['predecessor'];target=REPO/old['successor']
    before=source.read_bytes();after=target.read_bytes()
    assert sha256(before).hexdigest()==old['predecessor_sha256']
    left,right=before.splitlines(keepends=True),after.splitlines(keepends=True)
    segments=[]
    for kind,i,j,k,l in SequenceMatcher(None,left,right,autojunk=False).get_opcodes():
        if kind=='equal':segments.append(dict(copy_lines=[i,j]))
        elif kind in ('insert','replace'):
            segments.append(dict(literal_base64=base64.b64encode(b''.join(right[k:l])).decode('ascii')))
    rebuilt=b''.join(b''.join(left[s['copy_lines'][0]:s['copy_lines'][1]]) if 'copy_lines' in s
        else base64.b64decode(s['literal_base64'],validate=True) for s in segments)
    assert rebuilt==after
    compile(rebuilt,str(target),'exec')
    with (out/target.name).open('xb') as stream:stream.write(after)
    patches.append(dict(predecessor=old['predecessor'],predecessor_sha256=old['predecessor_sha256'],
        successor=old['successor'],successor_sha256=sha256(after).hexdigest(),segments=segments))
tests=[REPO/'tests/test_h1_registry_runtime_store_binding_development_v1.py',
    REPO/'tests/test_h1_registry_validation_operation_development_v1.py']
value=dict(status='DRAFT_NONAUTHORITATIVE',schema='registry_source_patch_closure_v3',patches=patches,
    corrected_cause='definition-time constant snapshot included legitimate live store registry membership',
    contract='fixed registry/module/lock identity plus private operation membership snapshot; unchanged full numerical contexts',
    source_sha256={str(p):sha256(p.read_bytes()).hexdigest() for p in tests},
    builder_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
    check_script_sha256=sha256((HERE/'rebuild_registry_sources_v3.py').read_bytes()).hexdigest(),
    formal_result=False,resource_admission=False,full_hour0_chain_passed=False)
manifest=out/'patch_manifest.json'
with manifest.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
print(json.dumps(dict(manifest_sha256=sha256(manifest.read_bytes()).hexdigest(),
    sources=[dict(path=p['successor'],sha256=p['successor_sha256']) for p in patches])))
