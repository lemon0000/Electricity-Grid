"""Pin a single original saved common arm; reuse the unchanged prior measurement."""
from hashlib import sha256
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
ENTRY = HERE.parent / 'validation_path_optimization_01/entry_revision_07'
value = json.loads((HERE / 'entry_hotpaths_plan_02.json').read_bytes())
sources = dict(value['source_sha256'])
saved = Path('D:/h1_chain_06_non_authoritative')
saved_pins = {str(p): sha256(p.read_bytes()).hexdigest() for p in saved.rglob('*') if p.is_file()}
comparison = HERE.parent / 'validation_operation_witness_01/vendor_saved_arm_comparison_02.json'
prior = json.loads(comparison.read_bytes())
for name, pin in prior['files_sha256'].items():
    assert sha256(Path(name).read_bytes()).hexdigest() == pin
for path in (Path(__file__), HERE / 'measure_bounded_common_arm_v1.py', HERE / 'run_bounded_common_arm_v1.py',
        HERE.parent / 'replay_saved_with_fixture_v1.py', comparison,
        ENTRY / 'vendor_saved_arm_01/scientific.json', ENTRY / 'vendor_saved_arm_01/audit.json',
        HERE / 'entry_hotpaths_monitor_02/terminal.json',
        HERE / 'entry_hotpaths_02_non_authoritative/terminal.json'):
    sources[str(path)] = sha256(path.read_bytes()).hexdigest()
assert all(sha256(Path(p).read_bytes()).hexdigest() == pin for p, pin in sources.items())
value.update(question='How much does the bounded entry improve the unchanged real common._arm path on 461 saved files, with science and full audit exact equality?',
    attempts=1, modes=['bounded_v2'], saved_root=str(saved), saved_sha256=saved_pins,
    inner_output=str(HERE / 'bounded_common_arm_01_non_authoritative'),
    outer_output=str(HERE / 'bounded_common_arm_monitor_01'),
    basetemp='D:/h1_bounded_common_arm_01_non_authoritative',
    limits=dict(wall_seconds=120, sampled_rss_bytes=768 * 1024**2, storage_bytes=128 * 1024**2),
    source_sha256=sources, common_arm_calls=1, identity_calls_per_mode=0, registry_splits_per_mode=[],
    reused_baseline='entry07 vendor_saved_arm_01; 36.2791786s; pins and science/audit rechecked',
    dag=['fixed sources and saved pins', 'configured entry owns code before fixture imports',
        'original complete saved fixture', 'locked metadata lease', 'one original common._arm',
        'science/full audit byte equality', 'metadata exit before fixture undo',
        'owned entry close', 'source/saved/old-chain/process/lock postcheck'],
    order_effects='historical baseline reused after checking exact inputs; no isolated causal or whole-chain claim')
with (HERE / 'bounded_common_arm_plan_01.json').open('x', encoding='utf-8') as stream:
    json.dump(value, stream, indent=2)
print(json.dumps(dict(plan_sha256=sha256((HERE / 'bounded_common_arm_plan_01.json').read_bytes()).hexdigest(),
    source_files=len(sources), saved_files=len(saved_pins))))
