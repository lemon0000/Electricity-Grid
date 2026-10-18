"""One cause-specific comparison of the unchanged path lease in the current entry."""
from hashlib import sha256
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENTRY = HERE.parent / 'validation_path_optimization_01/entry_revision_07'
value = json.loads((HERE / 'bounded_common_arm_plan_02.json').read_bytes())
sources = dict(value['source_sha256'])
prior = json.loads((HERE / 'bounded_common_arm_monitor_02/terminal.json').read_bytes())
assert prior['exit_code'] == 0 and prior['source_unchanged'] and prior['old_chain_unchanged']
assert json.loads((HERE / 'common_entry_postcheck_03_non_authoritative/terminal.json').read_bytes())['exit_code'] == 0
for path in (Path(__file__), HERE / 'measure_bounded_common_arm_v3.py',
        HERE / 'run_bounded_common_arm_v3.py', ENTRY / 'canonical_path_lease.py',
        HERE / 'bounded_common_arm_plan_02.json', HERE / 'bounded_common_arm_monitor_02/terminal.json',
        HERE / 'bounded_common_arm_02_non_authoritative/terminal.json',
        HERE / 'bounded_common_arm_02_non_authoritative/scientific.json',
        HERE / 'bounded_common_arm_02_non_authoritative/audit.json',
        HERE / 'common_entry_postcheck_03_non_authoritative/terminal.json'):
    sources[str(path)] = sha256(path.read_bytes()).hexdigest()
assert all(sha256(Path(p).read_bytes()).hexdigest() == pin for p, pin in sources.items())
assert all(sha256(Path(p).read_bytes()).hexdigest() == pin for p, pin in value['old_chain_sha256'].items())
assert all(sha256(Path(p).read_bytes()).hexdigest() == pin for p, pin in value['saved_sha256'].items())
value.update(
    question='Does connecting the unchanged canonical-path lease to the corrected bounded-v2/metadata entry reduce the real common arm cost?',
    attempts=1, modes=['bounded_v2_parse_path'],
    inner_output=str(HERE / 'bounded_common_arm_03_non_authoritative'),
    outer_output=str(HERE / 'bounded_common_arm_monitor_03'),
    basetemp='D:/h1_bounded_common_arm_03_non_authoritative',
    limits=dict(wall_seconds=120, sampled_rss_bytes=768 * 1024**2, storage_bytes=128 * 1024**2),
    source_sha256=sources,
    path_roots=[str(HERE.parents[3]), value['saved_root']],
    synthetic_jobs=0, real_native_calls=0,
    reused_baseline='closed common arm 02; 33.7944072s; exact source/input/science/full-audit pins reused',
    dag=['fixed sources/saved inputs and closed baseline', 'configured bounded entry',
        'unchanged path lease before project definitions', 'original saved fixture',
        'policy admission before metadata lease', 'one original common._arm',
        'science/full-audit exact bytes and positive cache counters',
        'metadata exit and fixture undo', 'path then code cleanup',
        'saved/source/old pins, process identities and real locks postcheck'],
    path_semantics='fresh leaf lstat and ancestor reparse/case queries per call; no bytes or result cache',
    stop_conditions='first exception, output drift or resource cap; no retry/extension in this plan',
    order_effects='single fixed-order observation with a closed historical baseline; no causal/statistical/full-chain claim')
target = HERE / 'bounded_common_arm_plan_03.json'
with target.open('x', encoding='utf-8') as stream:
    json.dump(value, stream, indent=2)
print(json.dumps(dict(plan_sha256=sha256(target.read_bytes()).hexdigest(), source_files=len(sources),
    saved_files=len(value['saved_sha256']), code_files=len(value['code_lease_sha256']))))
