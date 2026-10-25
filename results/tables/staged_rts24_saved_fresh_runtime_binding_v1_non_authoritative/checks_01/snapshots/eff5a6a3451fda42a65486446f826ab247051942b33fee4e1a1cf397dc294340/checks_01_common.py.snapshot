"""Fixed stdlib evidence helpers; no current ENTRY import."""
from hashlib import sha256
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
PRIOR=ROOT/'results/tables/staged_rts24_saved_fresh_source_bytes_reuse_v1_non_authoritative/checks_01'
EXE=Path('D:/Miniconda3/envs/compute/python.exe')
SOURCE_PATHS=('src/staged_rts24_saved_fresh_adoption_v1.py',
    'experiments/staged_rts24_saved_fresh_adoption_v1.py',
    'tests/test_staged_rts24_saved_fresh_adoption_v1.py')
OUTPUT_PARENT=ROOT/'results/tables/staged_rts24_saved_fresh_adoption_v1_non_authoritative'
FROZEN_EPOCH='84b6dafc7793caa2799ec99d3a38a5dfe3f3275448e3d30d3f2f01755a79e419'


def pin(raw): return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def canonical(value): return json.dumps(value,ensure_ascii=True,sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii')
def read(name): return json.loads((OUT/name).read_bytes())


def selected():
    expected=json.loads((PRIOR/'frozen_epoch.json').read_bytes())['source_pins']
    assert len(expected)==49 and set(SOURCE_PATHS)<=set(expected)
    assert sha256(canonical({n:expected[n] for n in SOURCE_PATHS})).hexdigest()==FROZEN_EPOCH
    actual={name:pin((ROOT/name).read_bytes()) for name in expected}
    assert actual==expected
    return actual


def save(name,value):
    path=OUT/name;assert not path.exists(),name
    path.write_bytes((json.dumps(value,sort_keys=True,indent=2)+'\n').encode())


def snapshot(path):
    raw=path.read_bytes();target=OUT/'snapshots'/sha256(raw).hexdigest()/(path.parent.name+'_'+path.name+'.snapshot')
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists(): assert target.read_bytes()==raw
    else: target.write_bytes(raw)
    return dict(snapshot=target.relative_to(ROOT).as_posix(),pin=pin(raw))
