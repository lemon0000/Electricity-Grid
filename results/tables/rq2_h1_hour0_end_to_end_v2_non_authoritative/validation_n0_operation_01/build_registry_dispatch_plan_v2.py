"""One zero-Job checkpoint diagnostic for the cold03 rejection."""
from hashlib import sha256
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
value = json.loads((HERE / 'entry_hotpaths_plan_02.json').read_bytes())
sources = dict(value['source_sha256'])
for path in (Path(__file__), HERE / 'run_registry_dispatch_entry_v2.py',
        HERE / 'run_registry_dispatch_bounded_v2.py',
        REPO / 'tests/test_h1_registry_dispatch_probe_development_v1.py',
        REPO / 'tests/test_h1_registry_validation_fresh_n0_development_v1.py',
        HERE / 'fresh_n0_monitor_03/terminal.json',
        HERE / 'fresh_n0_entry_03_non_authoritative/bounded_closed_receipt.json'):
    sources[str(path)] = sha256(path.read_bytes()).hexdigest()
assert all(sha256(Path(p).read_bytes()).hexdigest() == pin for p, pin in sources.items())
value.update(question='At which pre-bootstrap checkpoint does the real v3 definition-time project view first differ, and which exact keys change?',
    attempts=1, modes=['bounded_v2'], roots=1, hours=0, synthetic_jobs=0, native_calls=0,
    target='tests/test_h1_registry_dispatch_probe_development_v1.py',
    inner_output=str(HERE / 'registry_dispatch_02_non_authoritative'),
    outer_output=str(HERE / 'registry_dispatch_monitor_02'),
    basetemp='D:/h1_registry_dispatch_02_non_authoritative',
    limits=dict(wall_seconds=120, sampled_rss_bytes=768 * 1024**2, storage_bytes=128 * 1024**2),
    source_sha256=sources, identity_calls_per_mode=0, registry_splits_per_mode=[],
    dag=['original cold fixture without identity caches', 'import actual successor',
        'capture existing definition baseline without altering it', 'profile build/readback',
        'continuation seam', 'real owner constructor', 'foreign opener rejection',
        'owner close', 'save exact keyed diffs and postcheck'],
    order_effects='diagnosis only; does not execute bootstrap, N0, or any Job; a completed diagnostic is not a candidate pass')
out = HERE / 'registry_dispatch_plan_02.json'
with out.open('x', encoding='utf-8') as stream:
    json.dump(value, stream, indent=2)
print(json.dumps(dict(plan_sha256=sha256(out.read_bytes()).hexdigest(), source_files=len(sources))))
