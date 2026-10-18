"""One fixed saved-only discovery, not performance or formal-run admission."""
from hashlib import sha256
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
value = json.loads((HERE / 'bounded_common_arm_plan_04.json').read_bytes())
assert all(sha256(Path(path).read_bytes()).hexdigest() == pin
    for path, pin in value['old_chain_sha256'].items())
assert all(sha256(Path(path).read_bytes()).hexdigest() == pin
    for path, pin in value['saved_sha256'].items())
assert all(sha256(Path(path).read_bytes()).hexdigest() == pin
    for path, pin in value['code_lease_sha256'].items())
sources = {path: sha256(Path(path).read_bytes()).hexdigest() for path in value['source_sha256']}
for path in (Path(__file__), HERE / 'measure_parent_inspection_footprint_v1.py',
        HERE / 'run_parent_inspection_footprint_bounded_v1.py', HERE / 'bounded_common_arm_plan_04.json'):
    sources[str(path)] = sha256(path.read_bytes()).hexdigest()
value.update(question='Which reads remain outside existing code/metadata/saved inventories during one full conditional Parent inspection?',
    attempts=1, modes=['one_full_saved_reference_inspection_with_open_discovery'],
    inner_output=str(HERE / 'parent_inspection_footprint_01_non_authoritative'),
    outer_output=str(HERE / 'parent_inspection_footprint_monitor_01'),
    basetemp='D:/h1_parent_inspection_footprint_01_non_authoritative',
    source_sha256=sources, limits=dict(wall_seconds=120,
        sampled_rss_bytes=768*1024**2, storage_bytes=128*1024**2),
    inspected_Parent_roots=1, complete_inspection_calls=1, synthetic_jobs=0,
    real_native_calls=0, Parent_completions_issued=0, common_arm_calls=0,
    stage_footprint_scope='Python audit open discovery plus explicit existing code/metadata inventories; no closure completeness claim',
    dag=['source and saved raw hash bookends', 'fixed configured code/path/metadata entry',
        'original saved synthetic source fixture and native denial',
        'six bounded input reads matched to retained pins and three retained output pins',
        'one original full conditional inspection', 'all fields exact equal saved retained-mode inspection',
        'read-footprint classification without reuse', 'fixture/metadata/path/code cleanup',
        'source/saved/old36 hashes, code r+b no write, saved locks and owned PID cleanup'],
    evidence_reuse='closed entry07/code/metadata/path behavior; current hashes and saved bytes rechecked',
    stop_conditions='first exception, acceptance mismatch or cap; preserve attempt; no retry/extension',
    formal_result=False, resource_admission=False, full_hour0_chain_passed=False,
    numerical_proof_reuse_admitted=False, native_execution_authorized=False)
out = HERE / 'parent_inspection_footprint_plan_01.json'
with out.open('x', encoding='utf-8') as stream:
    json.dump(value, stream, indent=2)
print(json.dumps(dict(plan_sha256=sha256(out.read_bytes()).hexdigest(),
    source_files=len(sources), saved_files=len(value['saved_sha256']),
    code_files=len(value['code_lease_sha256']), limits=value['limits'])))
