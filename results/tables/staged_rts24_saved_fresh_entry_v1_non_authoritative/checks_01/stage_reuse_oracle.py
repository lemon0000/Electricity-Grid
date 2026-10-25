"""AST/byte closure for unchanged historical standalone stage/guard tests."""
import ast
import copy
from hashlib import sha256
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
PRIOR = ROOT/'results/tables/staged_rts24_saved_fresh_invocation_v1_non_authoritative/checks_01'
ENTRY = 'experiments/staged_rts24_saved_fresh_adoption_v1.py'
TESTS = 'tests/test_staged_rts24_saved_fresh_adoption_v1.py'


def pin(raw): return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())
def dump(node): return ast.dump(node, include_attributes=False)
def definitions(raw): return {n.name: n for n in ast.parse(raw).body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}


def verify():
    sources = json.loads((OUT/'baseline_source.json').read_bytes())
    old = (ROOT/sources[ENTRY]['snapshot']).read_bytes(); current = (ROOT/ENTRY).read_bytes()
    assert pin(old) == sources[ENTRY]['pin']
    before, after = definitions(old), definitions(current)
    names = [name for name in before if name.startswith(('_stage_', '_bounded_stage_error', 'StageChannel', 'StageConstruction', 'OwnedStage'))]
    names += ['_native', '_own_process_identity', '_stop_owned_job', '_ordinary_probe_argv', 'create_probe_owner',
        '_create_probe_owner', '_construct_stage_owner', 'watch_probe_stage', '_watch_stage', '_terminal_console_helpers', '_system_console_path',
        'require', 'canonical', 'parse', 'keys', 'pin', 'digest', 'environment']
    names = sorted(set(names))
    exact_names = [n for n in names if n not in ('_construct_stage_owner', '_terminal_console_helpers')]
    for name in exact_names: assert dump(before[name]) == dump(after[name]), name
    # The only constructor delta is factory selection. Closed generic probes
    # select the original base; injected owners keep their exact old identity.
    normalized = copy.deepcopy(after['_construct_stage_owner'])
    factory = [n for n in normalized.body if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == 'factory' for t in n.targets)]
    assert len(factory) == 1 and dump(factory[0].value) == dump(ast.parse(
        '_stage_owner_factory(OwnedChild, owner_factory, label)', mode='eval').body)
    factory[0].value = ast.parse('owner_factory or OwnedChild', mode='eval').body
    assert dump(before['_construct_stage_owner']) == dump(normalized)
    selector = after['_stage_owner_factory']; space = {}
    def forbidden(*args): raise AssertionError('historical generic probe selected cache')
    space['_console_observed_factory'] = forbidden
    exec(compile(ast.Module(body=[selector], type_ignores=[]), '<isolated-selector>', 'exec'), space)
    probe = before['_ordinary_probe_argv']
    probe_map = next(n.value for n in probe.body if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == 'probes' for t in n.targets))
    labels = [ast.literal_eval(k) for k in probe_map.keys]
    base, injected = object(), object()
    for label in labels:
        assert space['_stage_owner_factory'](base, None, label) is base
        assert space['_stage_owner_factory'](base, injected, label) is injected
    # _watch_stage remains byte-independent AST identical. Its helper branch
    # requires role_graph/invocation plus real_owner; historical stage presets
    # and injected owners do not enter that branch. No role graph reuse follows.
    def assignments(raw):
        return {n.targets[0].id: n for n in ast.parse(raw).body if isinstance(n, ast.Assign)
            and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)}
    a, b = assignments(old), assignments(current)
    constants = ['ROOT', 'EXE', 'CAPS', 'GATES', 'STAGE_SECONDS', *[n for n in a if n.startswith('STAGE_')]]
    for name in constants: assert dump(a[name]) == dump(b[name]), name
    run = json.loads((PRIOR/'stages_23.exit.json').read_bytes()); assert run['exit_code'] == 0 and len(run['nodes']) == 87
    old_tests = definitions((ROOT/sources[TESTS]['snapshot']).read_bytes()); tests = definitions((ROOT/TESTS).read_bytes())
    helper_names = [n for n in old_tests if n.startswith(('_Stage', '_unit_stage', '_write_unit', '_real_stage', '_closed_stage'))]
    for name in helper_names: assert dump(old_tests[name]) == dump(tests[name]), name
    for node in run['nodes']:
        if not node.startswith(TESTS+'::'): continue
        name = node.split('::')[1].split('[')[0]; assert dump(old_tests[name]) == dump(tests[name]), name
    for name, expected in run['source_pins'].items():
        if name not in (ENTRY, TESTS): assert pin((ROOT/name).read_bytes()) == expected, name
    baseline_head = json.loads((OUT/'baseline_snapshot.json').read_bytes())['head']
    guard = 'tests/test_staged_rts24_process_guard_v1.py'
    frozen_guard = subprocess.run(['git', 'show', baseline_head+':'+guard], cwd=ROOT,
        capture_output=True, check=True, timeout=5).stdout
    assert (ROOT/guard).read_bytes() == frozen_guard
    baseline = json.loads((OUT/'baseline_saved_01.stdout.log').read_bytes())
    assert baseline['canonical_draft_matches_final_snapshot'] is baseline['frozen_source_snapshots_verified'] is True
    return dict(authority='DRAFT_NONAUTHORITATIVE', scope='historical standalone stage/guard domain only',
        unchanged_stage_definitions=exact_names, unchanged_constants=sorted(set(constants)), historical_nodes=87,
        constructor_delta='closed internal factory selection only', generic_probe_labels=labels,
        role_graph_and_invocation_cache_runtime_reused=False,
        guard_test_pin=pin(frozen_guard), guard_test_baseline_commit=baseline_head,
        historical_exit_pin=pin((PRIOR/'stages_23.exit.json').read_bytes()), baseline_check_pin=pin((OUT/'baseline_saved_01.stdout.log').read_bytes()),
        counted_as_current_epoch_nodes=False, actual_saved_F_execution=False, current_stage_runtime_or_resource_admission=False)


if __name__ == '__main__': print(json.dumps(verify(), sort_keys=True, indent=2))
