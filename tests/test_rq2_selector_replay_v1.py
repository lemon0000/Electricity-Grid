from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

import pytest

from test_rq2_reference_grid_v1 import args
from test_rq2_reference_selector_v1 import run as reference_run, install, SELECTOR, SHORT
from test_rq2_actual_dispatch_selector_v1 import inputs as actual_inputs, run as actual_run
from test_rq2_continuous_grid_candidate_v1 import SPEC
from src.rq2_joint_deliverability_boundary_v1 import selector_replay as replay
from src.rq2_joint_deliverability_boundary_v1 import reference_selector as reference
from src.rq2_joint_deliverability_boundary_v1 import actual_dispatch_selector as actual
from src.rq2_joint_deliverability_boundary_v1 import continuous_grid_candidate as capture
from src.rq2_joint_deliverability_boundary_v1.prefix_handoff import _encoded


@pytest.fixture(scope='module', params=['reference', 'actual'])
def real(request):
    inputs = args() if request.param == 'reference' else actual_inputs()
    result = reference_run(inputs) if request.param == 'reference' else actual_run(inputs)
    assert result.status.startswith('selected_numerical')
    return request.param, inputs, result


def values(result, data):
    return dict(expected_sha256=sha256(data).hexdigest(), expected_input_identity=result.input_identity,
        expected_policy_identity=result.selector_policy_identity, selector=result.selector,
        solver_specification=result.specification, budget=result.budget)


def check(item, data=None, **changes):
    kind, inputs, result = item
    data = replay.export_selector_archive(result) if data is None else data
    expected = values(result, data)
    expected.update(changes)
    return (replay.replay_reference_archive if kind == 'reference' else replay.replay_actual_archive)(data, *inputs, **expected)


def forbid_solvers(monkeypatch):
    def forbidden(*a, **kw): raise AssertionError('native optimization forbidden in selector replay')
    for obj, name in ((capture, 'create_solver'), (capture, '_solve'), (reference, '_solve'), (actual, '_solve')):
        monkeypatch.setattr(obj, name, forbidden)


def test_real_full_source_bound_chain_without_solver(real, monkeypatch):
    data = replay.export_selector_archive(real[2])
    forbid_solvers(monkeypatch)
    report = check(real, data)
    result = real[2]
    state = result.next_reference_state if real[0] == 'reference' else result.next_dispatch_state
    assert report.status == 'reproduced_selected_chain'
    assert report.source_input_binding_verified and report.policy_binding_verified
    assert not report.business_power_binding_verified
    assert report.call_inventory_verified and report.recorded_solver_calls == result.solver_calls
    assert report.selector_chain_verified and report.selection_accepted and report.archive_reproduced
    assert report.reproduced_result_identity == result.identity
    assert report.selected_state_identity == state.identity
    assert report.accepted_prefix_length == report.verified_stage_count == result.planned_solver_calls
    assert report.solver_calls_by_replay_module == 0 and not report.external_builder_accepted
    assert not report.native_execution_authenticated and not report.resume_authorized
    assert report.exact_lexicographic_certificate is report.infeasibility_certificate is None
    assert report.capacity_certificate is report.causal_certificate is None
    assert not report.formal_result and not report.security_certified
    assert not hasattr(report, 'next_reference_state') and not hasattr(report, 'next_dispatch_state')


@pytest.mark.parametrize('field', ['digest', 'input', 'policy', 'selector'])
def test_independent_pins_reject_wrong_expectations(real, field):
    changed = ({'expected_sha256':'0'*64} if field == 'digest' else
        {'expected_input_identity':'1'*64} if field == 'input' else
        {'expected_policy_identity':'2'*64} if field == 'policy' else
        {'selector':replace(real[2].selector, lock_tolerance_mw=1e-8)})
    with pytest.raises(ValueError): check(real, **changed)


@pytest.mark.parametrize('mutation', ['swap', 'omit', 'extra', 'index', 'label', 'frozen', 'hex', 'purpose',
    'accepted', 'errors', 'witness', 'residual', 'objective_hex', 'raw_objective', 'calls', 'status', 'state'])
def test_rehashed_stage_and_result_mutations_rejected(real, mutation):
    payload = json.loads(replay.export_selector_archive(real[2]))
    r = payload['result']
    if mutation == 'swap': r['stages'] = r['stages'][::-1]
    elif mutation == 'omit': r['stages'].pop()
    elif mutation == 'extra': r['stages'].append(r['stages'][-1])
    elif mutation == 'index': r['stages'][0]['index'] = True
    elif mutation == 'label': r['stages'][0]['objective_label'] = 'foreign'
    elif mutation == 'frozen': r['stages'][1]['fixed_previous_objectives'][0] += .25
    elif mutation == 'hex': r['stages'][1]['fixed_previous_objective_hex'][0] = '0x0.0p+0'
    elif mutation == 'purpose': r['stages'][0]['raw_solve']['purpose'] = 'foreign'
    elif mutation == 'accepted': r['stages'][0]['accepted'] = False
    elif mutation == 'errors': r['stages'][0]['errors'] = ['invented']
    elif mutation == 'witness': r['stages'][0]['assignment_witness'] = None
    elif mutation == 'residual': r['stages'][0]['maximum_exact_selector_violation'] = .5
    elif mutation == 'objective_hex': r['stages'][0]['canonical_objective_hex'] = '0x0.0p+0'
    elif mutation == 'raw_objective': r['stages'][0]['raw_solve']['objective'] += .5
    elif mutation == 'calls': r['solver_calls'] += 1
    elif mutation == 'status': r['status'] = 'unresolved'
    elif mutation == 'state':
        key = 'next_reference_state' if real[0] == 'reference' else 'next_dispatch_state'
        r[key]['previous_state_identity'] = '0'*64
    with pytest.raises(ValueError): check(real, _encoded(payload))


@pytest.mark.parametrize('fault,index', [('timeout',0),('timeout',1),('infeasible',0),('missing_bound',0)])
def test_complete_unresolved_native_result_reproduces_no_selection(monkeypatch, fault, index):
    inputs = args()
    install(monkeypatch, fault, index)
    result = reference_run(inputs)
    data = replay.export_selector_archive(result)
    forbid_solvers(monkeypatch)
    report = check(('reference', inputs, result), data)
    assert report.status == 'reproduced_unresolved_chain'
    assert report.selector_chain_verified and report.archive_reproduced
    assert not report.selection_accepted and report.selected_state_identity is None
    assert report.selected_request_exact is None
    assert report.accepted_prefix_length == index
    assert report.verified_stage_count == index+1
    assert report.reproduced_result_identity == result.identity


@pytest.mark.parametrize('index', [0,1,2])
def test_partial_native_execution_never_returns_state(monkeypatch, index):
    inputs = args()
    install(monkeypatch, 'exception', index)
    result = reference_run(inputs)
    data = replay.export_selector_archive(result)
    forbid_solvers(monkeypatch)
    report = check(('reference', inputs, result), data)
    assert report.status == 'partial_native_evidence'
    assert not report.selector_chain_verified and not report.selection_accepted and not report.archive_reproduced
    assert report.verified_stage_count == report.accepted_prefix_length == index
    assert report.selected_state_identity is report.reproduced_result_identity is None
    assert report.call_inventory_verified and report.recorded_solver_calls == index+1


@pytest.mark.parametrize('calls', [-1, 0, 99, True])
def test_partial_recorded_call_inventory_cannot_be_changed(monkeypatch, calls):
    inputs = args()
    install(monkeypatch, 'exception', 1)
    result = reference_run(inputs)
    payload = json.loads(replay.export_selector_archive(result))
    payload['result']['solver_calls'] = calls
    with pytest.raises(ValueError, match='call inventory'):
        check(('reference', inputs, result), _encoded(payload))


@pytest.mark.parametrize('fault', ['timeout','exception'])
def test_rejected_or_partial_stage_has_no_suffix(monkeypatch, fault):
    inputs = args()
    install(monkeypatch, fault, 0)
    result = reference_run(inputs)
    payload = json.loads(replay.export_selector_archive(result))
    payload['result']['stages'].append(payload['result']['stages'][0])
    with pytest.raises(ValueError): check(('reference', inputs, result), _encoded(payload))


def test_invalid_assignment_replays_as_unresolved(monkeypatch):
    inputs = args()
    install(monkeypatch, values_override={'generation[G1]':0.})
    result = reference_run(inputs)
    report = check(('reference', inputs, result))
    assert report.selector_chain_verified and not report.selection_accepted
    assert report.status == 'reproduced_unresolved_chain'


def test_actual_power_is_independent_input_not_loaded_from_archive():
    inputs = actual_inputs()
    result = actual_run(inputs)
    from test_rq2_current_grid_step_v1 import power
    changed = inputs[:3]+(power(mw=6),)
    with pytest.raises(ValueError, match='input identity'):
        check(('actual', changed, result))


def test_no_external_builder_or_owned_state_on_public_interface(real):
    with pytest.raises(ValueError, match='structure'):
        check(real, builder=lambda: None)


def test_create_only_archive(real, tmp_path):
    path = tmp_path/'selector_non_authoritative.json'
    digest = replay.write_selector_archive(real[2], path)
    before = path.read_bytes()
    assert digest == sha256(before).hexdigest()
    with pytest.raises(FileExistsError): replay.write_selector_archive(real[2], path)
    assert path.read_bytes() == before
    assert check(real, before).archive_reproduced


def test_fresh_import_closure():
    script = '''
import sys,json
from pathlib import Path
import src.rq2_joint_deliverability_boundary_v1.selector_replay
root=Path.cwd()
print(json.dumps(sorted(Path(m.__file__).resolve().relative_to(root).as_posix()
    for n,m in sys.modules.items() if n=='src' or n.startswith('src.'))))
'''
    result = subprocess.run([sys.executable, '-B', '-c', script], cwd=Path(__file__).resolve().parents[1],
        capture_output=True, text=True, timeout=30, check=True)
    assert set(json.loads(result.stdout)) == set(replay.DEPENDENCIES)


@pytest.mark.parametrize('kind', ['reference', 'actual'])
@pytest.mark.parametrize('phase', ['solve', 'native_result', 'native_inventory', 'load', 'canonical_assignment', 'post_snapshot'])
def test_partial_call_count_and_total_cannot_be_jointly_rewritten(monkeypatch, kind, phase):
    from test_rq2_actual_dispatch_selector_v1 import install as actual_install
    inputs = args() if kind == 'reference' else actual_inputs()
    (install if kind == 'reference' else actual_install)(monkeypatch, 'exception', 1)
    result = (reference_run if kind == 'reference' else actual_run)(inputs)
    payload = json.loads(replay.export_selector_archive(result))
    raw = payload['result']['stages'][-1]['raw_solve']
    raw['errors'] = [phase+':RuntimeError:injected interruption']
    raw['calls'] = 0
    payload['result']['solver_calls'] -= 1
    with pytest.raises(ValueError, match='stage and call inventory'):
        check((kind, inputs, result), _encoded(payload))


@pytest.mark.parametrize('kind', ['reference', 'actual'])
def test_create_failure_keeps_zero_calls_and_rejects_inflation(monkeypatch, kind):
    inputs = args() if kind == 'reference' else actual_inputs()
    def failed(*a, **kw): raise RuntimeError('create interrupted')
    monkeypatch.setattr(capture, 'create_solver', failed)
    result = (reference_run if kind == 'reference' else actual_run)(inputs)
    report = check((kind, inputs, result))
    assert report.status == 'partial_native_evidence'
    assert report.recorded_solver_calls == 0 and report.call_inventory_verified
    payload = json.loads(replay.export_selector_archive(result))
    payload['result']['stages'][0]['raw_solve']['calls'] = 1
    payload['result']['solver_calls'] = 1
    with pytest.raises(ValueError, match='stage and call inventory'):
        check((kind, inputs, result), _encoded(payload))


@pytest.mark.parametrize('fault,index', [('timeout',0),('timeout',1),('infeasible',0),('exception',1)])
def test_actual_unresolved_and_partial_chains(monkeypatch, fault, index):
    from test_rq2_actual_dispatch_selector_v1 import install as actual_install
    inputs = actual_inputs()
    actual_install(monkeypatch, fault, index)
    result = actual_run(inputs)
    data = replay.export_selector_archive(result)
    forbid_solvers(monkeypatch)
    report = check(('actual', inputs, result), data)
    assert not report.selection_accepted and report.selected_state_identity is None
    assert report.accepted_prefix_length == index
    assert report.recorded_solver_calls == index+1
    assert report.selector_chain_verified == (fault != 'exception')


@pytest.mark.parametrize('fault', ['small_lock_drift', 'small_l1_slack'])
def test_exact_objective_lock_gate_is_replayed(monkeypatch, fault):
    inputs = args()
    install(monkeypatch, fault, 1)
    spec = replace(SPEC, feasibility_tolerance=1e-6, optimality_tolerance=1e-6, integer_feasibility_tolerance=1e-6)
    result = reference_run(inputs, selector=replace(SELECTOR, absolute_gap_mw=1e-8), spec=spec)
    assert result.stages[-1].raw_solve.optimal and result.stages[-1].maximum_objective_lock_violation == 5e-7
    report = check(('reference', inputs, result))
    assert report.selector_chain_verified and not report.selection_accepted
    assert report.reproduced_result_identity == result.identity


def test_independent_predecessor_must_match_archive(real):
    different = args(generation=19.) if real[0] == 'reference' else actual_inputs(generation=19.)
    with pytest.raises(ValueError, match='input identity'):
        check((real[0], different, real[2]))


def test_second_hour_state_and_policy_lineage(real, monkeypatch):
    if real[0] == 'reference':
        from test_rq2_current_grid_step_v1 import prepared, current, view
        from src.rq2_joint_deliverability_boundary_v1.event_disclosure import CurrentOutageReport, disclose_current
        state = real[2].next_reference_state
        info = view(prepared(10.), replace(current(2, demand=20.), dc_baseline_mw=25.))
        inputs = (info, disclose_current(state.physical_carry.disclosure, CurrentOutageReport(2, None, None)), state)
        result = reference_run(inputs)
    else:
        from test_rq2_actual_dispatch_selector_v1 import second_inputs
        state = real[2].next_dispatch_state
        inputs = second_inputs(state)
        result = actual_run(inputs)
    assert result.status.startswith('selected_numerical')
    data = replay.export_selector_archive(result)
    forbid_solvers(monkeypatch)
    report = check((real[0], inputs, result), data)
    assert report.selection_accepted and report.reproduced_result_identity == result.identity
    assert report.selected_state_identity != state.identity


def test_final_diagnostic_construction_drift_is_rejected(real, monkeypatch):
    data = replay.export_selector_archive(real[2])
    owned = replay._owned
    def changed(cls, **kw):
        item = owned(cls, **kw)
        if cls is replay.SelectorReplayDiagnostic:
            monkeypatch.setattr(replay, 'SCHEMA', 'changed after report construction')
        return item
    monkeypatch.setattr(replay, '_owned', changed)
    with pytest.raises(ValueError, match='schema drift'):
        check(real, data)


@pytest.mark.parametrize('mutation', ['duplicate', 'extra', 'noncanonical', 'formal'])
def test_selector_archive_canonical_envelope(real, mutation):
    data = replay.export_selector_archive(real[2])
    if mutation == 'duplicate':
        data = data.replace(b'{', b'{"kind":"foreign",', 1)
    elif mutation == 'noncanonical': data += b'\n'
    else:
        payload = json.loads(data)
        payload['extra' if mutation == 'extra' else 'formal_result'] = True
        data = _encoded(payload)
    with pytest.raises(ValueError): check(real, data)


def test_fresh_process_complete_archive_replay(real, tmp_path):
    import os
    path = tmp_path/'fresh_selector_non_authoritative.json'
    digest = replay.write_selector_archive(real[2], path)
    script = '''
import sys
from pathlib import Path
from src.rq2_joint_deliverability_boundary_v1 import selector_replay as replay
from src.rq2_joint_deliverability_boundary_v1 import reference_selector, actual_dispatch_selector, continuous_grid_candidate
from test_rq2_continuous_grid_candidate_v1 import SPEC
kind=sys.argv[3]
if kind=='reference':
    from test_rq2_reference_grid_v1 import args
    from test_rq2_reference_selector_v1 import SELECTOR,SHORT
    inputs=args()
    call=replay.replay_reference_archive
else:
    from test_rq2_actual_dispatch_selector_v1 import inputs as make,SELECTOR,SHORT
    inputs=make()
    call=replay.replay_actual_archive
def forbidden(*a, **kw): raise AssertionError('solver forbidden in fresh replay')
continuous_grid_candidate.create_solver=continuous_grid_candidate._solve=forbidden
reference_selector._solve=actual_dispatch_selector._solve=forbidden
r=call(Path(sys.argv[1]).read_bytes(), *inputs, expected_sha256=sys.argv[2],
    expected_input_identity=sys.argv[4], expected_policy_identity=sys.argv[5],
    selector=SELECTOR, solver_specification=SPEC, budget=SHORT)
assert r.archive_reproduced and r.selection_accepted
assert r.reproduced_result_identity==sys.argv[6]
assert not r.resume_authorized
print('full selector archive replay matched')
'''
    root = Path(__file__).resolve().parents[1]
    env = dict(os.environ, PYTHONPATH=str(root/'tests')+os.pathsep+str(root))
    completed = subprocess.run([sys.executable, '-B', '-c', script, str(path), digest, real[0],
        real[2].input_identity, real[2].selector_policy_identity, real[2].identity],
        cwd=root, env=env, capture_output=True, text=True, timeout=30, check=True)
    assert 'full selector archive replay matched' in completed.stdout
