from dataclasses import replace
from fractions import Fraction as Q
from functools import lru_cache

import pytest

from test_rq2_reference_grid_v1 import args
from test_rq2_reference_selector_v1 import run as select, install
from test_rq2_continuous_capacity_policy_v1 import init, advance
from test_rq2_continuous_recovery_controller_v1 import obs
from src.rq2_joint_deliverability_boundary_v1 import common_request_adapter as adapter
from src.rq2_joint_deliverability_boundary_v1.capacity_policy import CapacityObservation, initialize_capacity_policy
from src.rq2_joint_deliverability_boundary_v1.causal_policy import CurrentObservation
from src.rq2_joint_deliverability_boundary_v1.four_arm_replay import NETWORK, CFE, JOINT, B6
from src.rq2_joint_deliverability_boundary_v1.prefix_handoff import (
    export_prefix_handoff, import_prefix_handoff, prefix_digest)


def mapping(unit='45'):
    return adapter.CommonRequestMapping(unit, '1'*64, 'linear_workload_power_no_idle_offset_v1',
        'declared_power_source_and_workload_pairing_mechanism_v1', 'mechanism_assumption')


@pytest.fixture(scope='module')
def selected():
    inputs = args()
    result = select(inputs)
    assert result.status == 'selected_numerical_reference', result.errors
    return inputs, result


def source(inputs, unit='45', cfe=0.):
    return replace(obs(1, g=0., c=0., due=None).hour,
        split='training', power_outage_seed=1,
        workload_occupancy=Q(str(inputs[0].current.dc_baseline_mw))/Q(unit), cfe_request=cfe)


@lru_cache(maxsize=1)
def normal_source():
    from test_rq2_continuous_grid_normal_v1 import fixture
    from test_rq2_grid_information_v1 import prepare
    inputs = fixture()
    inputs = replace(inputs, data=replace(inputs.data, generators=(replace(inputs.data.generators[0],
        ramp_mw_per_hour=10., ramp_mw_per_minute=10./60.),)),
        carry=replace(inputs.carry, limits=(replace(inputs.carry.limits[0], ramp_mw_per_hour=10.),)))
    return inputs, prepare(inputs)


def source_audit(inputs):
    from src.rq2_joint_deliverability_boundary_v1.continuous_grid_normal import normal_input_identity
    normal, prepared = normal_source()
    return adapter.bind_request_source(normal, prepared, inputs[0],
        expected_normal_identity=normal_input_identity(normal), expected_prepared_identity=prepared.audit_identity)


def run(selected, hour=None, spec=None):
    inputs, result = selected
    spec = mapping() if spec is None else spec
    hour = source(inputs, spec.normalized_unit_mw) if hour is None else hour
    audit = source_audit(inputs)
    identity = adapter.common_request_input_identity(*inputs, result, hour, spec, audit)
    return adapter.adapt_common_request(*inputs, result, hour, spec, audit, expected_identity=identity)


def test_exact_one_third_request_preserves_source_and_conservation(selected):
    original = source(selected[0])
    mapped = run(selected, original)
    assert mapped.status == 'mapped_exact_common_request', mapped.errors
    assert mapped.raw_grid_request_mw == 15
    assert mapped.normalized_grid_request == mapped.mapped_hour.grid_request == Q(1, 3)
    assert mapped.mapped_hour.grid_request*45 == mapped.raw_grid_request_mw
    assert mapped.normalized_float_projection == float(Q(1, 3))
    assert mapped.normalized_float_hex == float(Q(1, 3)).hex()
    assert mapped.binary_projection_error == abs(Q.from_float(float(Q(1, 3)))-Q(1, 3)) > 0
    assert replace(mapped.mapped_hour, grid_request=0.) == original
    assert original.grid_request == 0.
    assert mapped.identity == run(selected, original).identity
    assert mapped.causal_certificate is mapped.capacity_certificate is None
    assert not mapped.formal_result and not mapped.security_certified


@pytest.mark.parametrize('arm', [NETWORK, CFE, JOINT, B6])
def test_exact_fraction_reaches_four_arm_debt_and_persistent_handoff(selected, arm):
    mapped = run(selected)
    origin = init(arm=arm, committed_capacity=1., curtailment_ramp_per_hour=1., response_time_hours=1.)
    track = origin.initial.tracks[0][1]
    origin = initialize_capacity_policy(origin.spec, anchor=replace(track.physical.anchor, split='training', power_outage_seed=1),
        envelope=dict(track.physical.envelope), accounting_period_id=track.ledger.accounting_period_id,
        zero_carry_in_assumption=True)
    observation = CurrentObservation(mapped.mapped_hour, obs(1, g=0., c=0., due=None).limits, 5)
    cursor = advance(origin, CapacityObservation(observation, 1.))
    assert not cursor.stopped, cursor.records[-1]
    record = cursor.records[-1]
    assert record.current.observation.hour.grid_request == Q(1, 3)
    assert record.response.action.grid_served == (0 if arm == CFE else Q(1, 3))
    assert cursor.execution.tracks[0][1].ledger.debt == (0 if arm == CFE else Q(1, 3))
    encoded = export_prefix_handoff(cursor)
    restored = import_prefix_handoff(encoded, expected_sha256=prefix_digest(encoded), expected_origin=origin)
    assert restored == cursor
    assert type(restored.records[0].current.observation.hour.grid_request) is Q


@pytest.mark.parametrize('unit', ['15000000', '30000000', '14999999.9999999999999999999999'])
def test_positive_subresolution_or_float_cutoff_ambiguous_request_stops(selected, unit):
    result = run(selected, spec=mapping(unit))
    assert result.status == 'unresolved' and result.mapped_hour is None
    assert result.raw_grid_request_mw == 15 and result.normalized_grid_request > 0
    assert result.errors == ('positive_grid_request_below_business_resolution',)
    if unit.startswith('1499'):
        assert result.normalized_grid_request > Q('0.000001')


def test_resolvable_small_positive_request_is_retained(selected):
    result = run(selected, spec=mapping('10000000'))
    assert result.status == 'mapped_exact_common_request', result.errors
    assert result.mapped_hour.grid_request == Q(3, 2000000)


def test_separate_cfe_component_cutoff_mismatch_is_unresolved(selected):
    result = run(selected, hour=source(selected[0], cfe=Q(1, 2000000)))
    assert result.mapped_hour is None
    assert result.errors == ('separate_and_shared_request_activity_mismatch',)
    assert result.original_source_hour.cfe_request == Q(1, 2000000)


@pytest.mark.parametrize('unit', ['0', '-1', '1.0', '01', '1e3', 'nan', '', '1/3', 45, True])
def test_invalid_or_noncanonical_unit_rejected(unit):
    with pytest.raises(ValueError):
        mapping(unit)


@pytest.mark.parametrize('changes,match', [({'grid_request': 1.}, 'overwritten'),
    ({'power_source_hour': 2}, 'source-hour'), ({'workload_occupancy': .5}, 'baseline'),
    ({'workload_normalization_sha256': 'f'*64}, 'normalization'),
    ({'arm_id': NETWORK}, 'JOINT/shared')])
def test_input_mismatch_never_produces_mapped_hour(selected, changes, match):
    with pytest.raises(ValueError, match=match):
        run(selected, replace(source(selected[0]), **changes))


def test_unresolved_reference_does_not_become_zero_request(monkeypatch):
    inputs = args()
    install(monkeypatch, 'timeout', 0)
    result = run((inputs, select(inputs)))
    assert result.errors == ('reference_selection_unresolved',)
    assert result.mapped_hour is result.raw_grid_request_mw is result.normalized_grid_request is None


@pytest.mark.parametrize('baseline,demand,generation', [(20., 0., 25.), (0., 20., 20.)])
def test_audited_zero_request_including_zero_baseline(baseline, demand, generation):
    inputs = args(baseline=baseline, demand=demand, generation=generation)
    selected = select(inputs)
    assert selected.status == 'selected_numerical_reference', selected.errors
    result = run((inputs, selected))
    assert result.status == 'mapped_exact_common_request', result.errors
    assert result.raw_grid_request_mw == result.normalized_grid_request == 0


def test_mapping_and_source_provenance_are_in_identity(selected):
    first = run(selected)
    assert run(selected, spec=mapping('50')).identity != first.identity
    changed = replace(source(selected[0]), workload_provenance_sha256='f'*64)
    assert run(selected, hour=changed).identity != first.identity


def test_expected_identity_and_reference_source_binding(selected):
    inputs, reference = selected
    hour, spec = source(inputs), mapping()
    audit = source_audit(inputs)
    identity = adapter.common_request_input_identity(*inputs, reference, hour, spec, audit)
    with pytest.raises(ValueError, match='identity mismatch'):
        adapter.adapt_common_request(*inputs, reference, hour, spec, audit, expected_identity='f'*64)
    class EqualAnything:
        def __eq__(self, other): return True
    with pytest.raises(ValueError, match='SHA256'):
        adapter.adapt_common_request(*inputs, reference, hour, spec, audit, expected_identity=EqualAnything())
    changed = args(baseline=24.)
    with pytest.raises(ValueError, match='different current inputs'):
        run((changed, reference), source(changed))
    assert identity == adapter.common_request_input_identity(*inputs, reference, hour, spec, audit)


def test_plain_assignment_is_not_selected_reference(selected):
    inputs, reference = selected
    with pytest.raises(ValueError, match='owned reference selector'):
        run((inputs, reference.stages[-1].assignment_witness))


@pytest.mark.parametrize('target', ['contract', 'threshold', 'reference_policy'])
def test_runtime_drift_rejected(selected, monkeypatch, target):
    if target == 'contract':
        monkeypatch.setattr(adapter, 'CONTRACT', 'changed')
    elif target == 'threshold':
        monkeypatch.setattr(adapter.boundary, 'SERVICE_TOLERANCE', 1e-5)
    else:
        monkeypatch.setattr(adapter.selection, '_policy_identity', lambda *a: 'f'*64)
    with pytest.raises(ValueError, match='drift'):
        run(selected)


@pytest.mark.parametrize('changes', [{'split': 'holdout'}, {'power_outage_seed': 0}])
def test_cross_split_or_outage_seed_request_mapping_is_rejected(selected, changes):
    with pytest.raises(ValueError, match='split or outage seed'):
        run(selected, replace(source(selected[0]), **changes))


def test_source_audit_cannot_be_forged_or_bound_to_another_visible_hour(selected):
    inputs, reference = selected
    audit = source_audit(inputs)
    with pytest.raises(TypeError):
        replace(audit, split='holdout')
    other = args(demand=19.)
    with pytest.raises(ValueError, match='source audit'):
        adapter.common_request_input_identity(*other, reference, source(other), mapping(), audit)
    normal, prepared = normal_source()
    with pytest.raises(ValueError, match='linkage'):
        adapter.bind_request_source(normal, prepared, inputs[0], expected_normal_identity='f'*64,
            expected_prepared_identity=prepared.audit_identity)


def test_adapter_fresh_import_dependency_closure():
    from pathlib import Path
    import subprocess
    import sys
    from src.rq2_joint_deliverability_boundary_v1.continuous_grid_normal import SOURCE_DEPENDENCIES
    from src.rq2_joint_deliverability_boundary_v1.continuous_grid_candidate import EXTRA_DEPENDENCIES
    script = '''
import json, sys
from pathlib import Path
import src.rq2_joint_deliverability_boundary_v1.common_request_adapter
root = Path.cwd()
print(json.dumps(sorted(Path(module.__file__).resolve().relative_to(root).as_posix()
    for name, module in sys.modules.items() if name == 'src' or name.startswith('src.'))))
'''
    import json
    result = subprocess.run([sys.executable, '-B', '-c', script], check=True, capture_output=True,
        text=True, cwd=Path(__file__).resolve().parents[1], timeout=30)
    expected = set(SOURCE_DEPENDENCIES) | set(EXTRA_DEPENDENCIES) | set(adapter.IMPLEMENTATION) | {
        'src/rq2_joint_deliverability_boundary_v1/'+name+'.py'
        for name in ('common_request_adapter', 'reference_selector', 'reference_grid', 'current_grid_step',
            'grid_information', 'event_disclosure')}
    assert set(json.loads(result.stdout)) == expected
