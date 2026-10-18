"""Reconstruct exact draft sources into a new, bounded non-authoritative directory."""
import base64
from hashlib import sha256
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent;REPO=HERE.parents[3]
expected_pin,=sys.argv[1:]
manifest=HERE/'registry_sources_03_non_authoritative/patch_manifest.json';raw=manifest.read_bytes()
assert sha256(raw).hexdigest()==expected_pin
out=HERE/'registry_rebuild_check_03_non_authoritative';out.mkdir(exist_ok=False)
result=[]
for patch in json.loads(raw)['patches']:
    source=REPO/patch['predecessor'];before=source.read_bytes()
    assert sha256(before).hexdigest()==patch['predecessor_sha256']
    lines=before.splitlines(keepends=True)
    after=b''.join(b''.join(lines[s['copy_lines'][0]:s['copy_lines'][1]]) if 'copy_lines' in s
        else base64.b64decode(s['literal_base64'],validate=True) for s in patch['segments'])
    assert sha256(after).hexdigest()==patch['successor_sha256']
    assert after==(REPO/patch['successor']).read_bytes()
    compile(after,patch['successor'],'exec')
    with (out/Path(patch['successor']).name).open('xb') as stream:stream.write(after)
    result.append(dict(path=patch['successor'],sha256=patch['successor_sha256']))
value=dict(exit_code=0,status='DRAFT_NONAUTHORITATIVE',sources=result,patch_manifest_sha256=expected_pin,
    script_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),formal_result=False,resource_admission=False)
with (out/'terminal.json').open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
print(json.dumps(value),flush=True)
