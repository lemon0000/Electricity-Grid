"""Select current-compatible immutable inputs; preserve the live original chain."""
from hashlib import sha256
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
value = json.loads((HERE / 'parent_inspection_footprint_plan_01.json').read_bytes())
preflight = json.loads((HERE / 'parent_snapshot_identity_unit_02/terminal.json').read_bytes())
assert preflight['exit_code'] == 0 and preflight['source_unchanged']
row = json.loads((HERE / 'parent_snapshot_identity_unit_02/stdout.log').read_text(encoding='utf-8').strip())['rows'][1]
assert row['identity_matches'] and row['canonical_bytes_match']
snapshot_path = Path(row['path'])
assert sha256(snapshot_path.read_bytes()).hexdigest() == row['raw_sha256']
base = snapshot_path.parents[2]
root = snapshot_path.parents[1]
doc = json.loads(snapshot_path.read_bytes())
source_root = Path(doc['declaration']['source_binding']['root'])
roots = [root, source_root, base / 'source.yaml', base / 'synthetic_registry.json', base / 'upstream']
saved_pins = {}
for input_root in roots:
    for path in (input_root.rglob('*') if input_root.is_dir() else (input_root,)):
        if path.is_file() and path.suffix != '.lock':
            saved_pins[str(path)] = sha256(path.read_bytes()).hexdigest()
assert saved_pins[str(snapshot_path)] == row['raw_sha256']
assert all(sha256(Path(path).read_bytes()).hexdigest() == pin for path, pin in value['old_chain_sha256'].items())
sources = {path: sha256(Path(path).read_bytes()).hexdigest() for path in value['source_sha256']}
for path in (Path(__file__), HERE / 'measure_parent_inspection_footprint_v2.py',
        HERE / 'run_parent_inspection_footprint_bounded_v2.py',
        HERE / 'parent_snapshot_identity_unit_02/terminal.json', HERE / 'parent_snapshot_identity_unit_02/stdout.log',
        HERE / 'parent_inspection_footprint_monitor_01/terminal.json'):
    sources[str(path)] = sha256(path.read_bytes()).hexdigest()
value.update(question='Discover the conditional Parent inspection read footprint using preflight-matched immutable chain07 inputs',
    attempts=1, inner_output=str(HERE / 'parent_inspection_footprint_02_non_authoritative'),
    outer_output=str(HERE / 'parent_inspection_footprint_monitor_02'),
    basetemp='D:/h1_parent_inspection_footprint_02_non_authoritative',
    saved_root=str(root), saved_inventory_roots=list(map(str, roots)), saved_sha256=saved_pins,
    fixture_base=str(base), path_saved_root=str(base.parent), source_sha256=sources,
    expected_saved_locks=0, input_lock_policy='all existing input locks belong to the original chain; never open or acquire them',
    excluded_input_lock_content=True,
    old_chain_policy='read immutable completed Parent/controller/source bytes only; no process hook, lifecycle action, owner open, resume or restart',
    preflight_current_snapshot_identity=row['current_implementation_identity'],
    changed_input_reason='chain06 snapshot identity mismatch stopped before numerical work; chain07 identity is exact current bytes',
    scope_excludes_live_phase_global_roster_handoff_journals=True,
    limits=dict(wall_seconds=120, sampled_rss_bytes=768*1024**2, storage_bytes=128*1024**2))
out = HERE / 'parent_inspection_footprint_plan_02.json'
with out.open('x', encoding='utf-8') as stream:
    json.dump(value, stream, indent=2)
print(json.dumps(dict(plan_sha256=sha256(out.read_bytes()).hexdigest(), source_files=len(sources),
    saved_files=len(saved_pins), saved_inventory_roots=value['saved_inventory_roots'], limits=value['limits'])))
