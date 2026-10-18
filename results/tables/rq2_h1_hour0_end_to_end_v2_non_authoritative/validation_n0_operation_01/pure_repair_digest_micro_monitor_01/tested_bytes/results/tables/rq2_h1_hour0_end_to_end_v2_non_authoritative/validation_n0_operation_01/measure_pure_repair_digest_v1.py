"""Fixed ABAB computation-only comparison: 4 x 128 fresh repair identities."""
from hashlib import sha256
import json
from pathlib import Path
from statistics import median
import sys
from time import perf_counter

if not sys.flags.isolated or not sys.dont_write_bytecode:
    raise ValueError('fixed isolated no-bytecode diagnostic required')
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
ENTRY = HERE.parent / 'validation_path_optimization_01/entry_revision_07'
sys.path[:] = json.loads((ENTRY/'interpreter_path_policy_v1.json').read_bytes())['configured_paths']
OUT = HERE/'pure_repair_digest_micro_01_non_authoritative'
OUT.mkdir(exist_ok=False)
from experiments import h1_pure_repair_digest_lease_development_v1 as optimized
from experiments import h1_origin_grid_step_development_v1 as physical

original = physical._digest
expected = physical.repair_mechanism_identity()
registry = physical.registry
pins = {registry.AUTHORITY: registry.AUTHORITY_SHA}
authority = json.loads(registry.AUTHORITY.read_bytes())
pins[registry.ROOT/authority['cap_table_path']] = authority['cap_table_sha256']
files = (Path(__file__).resolve(), Path(optimized.__file__), Path(physical.__file__),
    Path(optimized.normal.__file__), ENTRY/'interpreter_path_policy_v1.json')
sources = {str(path): sha256(path.read_bytes()).hexdigest() for path in files}
old = json.loads((HERE/'negative_handoff_alias_plan_03.json').read_bytes())['old_chain_sha256']
assert all(sha256(Path(path).read_bytes()).hexdigest() == pin for path, pin in old.items())
blocks = []
for index in range(4):
    times = []
    def run():
        for _ in range(128):
            started = perf_counter()
            result = physical.repair_mechanism_identity()
            times.append(perf_counter()-started)
            assert result == expected
    if index % 2:
        with optimized.reuse_pure_repair_digest() as snapshot:
            run()
        receipt = dict(snapshot())
        assert receipt['computed_keys'] == 1 and receipt['cache_hits'] == 127
        assert receipt['remaining_keys'] == 0 and receipt['failure'] is None
    else:
        run()
        receipt = None
    assert physical._digest is original
    blocks.append(dict(mode='memo' if index % 2 else 'original', seconds=sum(times),
        median_seconds=median(times), calls=len(times), receipt=receipt))
assert all(sha256(path.read_bytes()).hexdigest() == pin for path, pin in pins.items())
assert all(sha256(Path(path).read_bytes()).hexdigest() == pin for path, pin in sources.items())
assert all(sha256(Path(path).read_bytes()).hexdigest() == pin for path, pin in old.items())
result = dict(blocks=blocks, source_sha256=sources, input_sha256={str(p):h for p,h in pins.items()},
    old_chain_sha256=old, pure_digest=expected, source_bytes_cached=False,
    every_call_still_reads_pins_parses_both_json_and_builds_all_rationals=True,
    sample_design='one process, fixed ABAB 128 calls per block, no independent repetitions',
    performance_scope='repair identity computation only; full chain speed unknown',
    full_hour0_chain_passed=False, resource_admission=False, formal_result=False,
    native_execution_authorized=False, exit_code=0)
with (OUT/'terminal.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, indent=2)
print(json.dumps(dict(blocks=blocks, savings_fraction=1-sum(b['seconds'] for b in blocks if b['mode']=='memo')/
    sum(b['seconds'] for b in blocks if b['mode']=='original'))))
