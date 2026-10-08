"""Reproducible H=25 real-source build-only mechanism example; no solver."""
import argparse
from dataclasses import asdict
from datetime import timezone
from hashlib import sha256
import json
from math import ceil
from pathlib import Path

from src.evaluation import ChronologicalFlexibilityEnvelope
from src.grid.chronological_dispatch import ChronologicalDispatchRequest
from src.grid.rts_gmlc import load_rts_gmlc_chronological_data, RTS_GMLC_MANIFEST_SHA256
from src.grid.rts_gmlc_scuc import RtsGmlcInitialState
from src.solvers import rq2_solver_adapter as scale_implementation
from src.rq2_joint_deliverability_boundary_v1.grid_carry import GridIdentity, GridCarry, UnitLimits, UnitPoint
from src.rq2_joint_deliverability_boundary_v1.continuous_grid_normal import build_continuous_normal_model, _dependencies
from src.rq2_joint_deliverability_boundary_v1.source_normal import assemble_source_normal, _source
from src.rq2_joint_deliverability_boundary_v1 import source_normal as source_implementation


def build_report(root):
    _source(root)
    data = load_rts_gmlc_chronological_data(root)
    points = data.hourly_points[:25]
    thermal = tuple(sorted((g for g in data.generators if g.dispatch_mode == 'committable'), key=lambda g: g.uid))
    # Explicit build-only scenario, not an observed or previously feasible state.
    initial = RtsGmlcInitialState(
        {g.uid: g.enabled and g.dispatch_mode != 'committable' for g in data.generators},
        {g.uid: 0. for g in data.generators},
        {g.uid: ceil(g.minimum_down_time_hours) for g in data.generators},
        'mechanism_assumption_build_only_thermal_off_zero_generation_minimum_down_age')
    carry = GridCarry(GridIdentity('training', 'build_only_mechanism_example', 0, RTS_GMLC_MANIFEST_SHA256), 0,
        tuple(UnitLimits(g.uid, g.p_min_mw, g.p_max_mw, g.ramp_mw_per_hour,
            g.minimum_up_time_hours, g.minimum_down_time_hours) for g in thermal),
        tuple(UnitPoint(g.uid, False, 0.) for g in thermal),
        tuple(initial.time_in_state_hours[g.uid] for g in thermal), 'mechanism_assumption')
    period = 'normal_build_only'
    envelope = ChronologicalFlexibilityEnvelope(
        time_step_hours=1., maximum_event_duration_hours=1., minimum_recovery_hours=1.,
        maximum_events_by_period={period: 0}, maximum_curtailment_energy_mwh_by_period={period: 0.},
        maximum_recovery_debt_mwh=0., maximum_recovery_power_mw=0., minimum_event_power_mw=1.,
        response_time_hours=1., curtailment_ramp_mw_per_hour=1., recovery_efficiency=1.,
        terminal_debt_limit_mwh_by_period={period: 0.}, parameter_status='mechanism_assumption_normal_build_only')
    zero = (0.,)*25
    request = ChronologicalDispatchRequest(
        timestamps=tuple(p.timestamp.replace(tzinfo=timezone.utc) for p in points),
        periods=(period,)*25, time_step_hours=1.,
        system_demand_by_bus_mw=tuple(dict(p.demand_by_bus_mw) for p in points),
        generator_availability=tuple({g.uid: g.enabled for g in data.generators} for _ in points), dc_bus=108,
        dc_requested_mw=(250.,)*25, dc_flexible_demand_mw=zero, dc_recoverable_flexible_mw=zero,
        dc_physical_maximum_mw=(250.,)*25, dc_connected_capacity_mw=(250.,)*25,
        dc_call_limit_mw=zero, recovery_headroom_mw=zero, flexibility_envelope=envelope,
        flexibility_boundary_state_status='clean_boundary_with_zero_carry_in', completed_periods=frozenset(),
        initial_has_prior_event=False, initial_recovery_debt_mwh=0., initial_grid_call_mw=0.,
        initial_active_event_duration_hours=0., initial_interevent_rest_hours=None,
        initial_event_count_by_period={}, initial_curtailment_energy_mwh_by_period={},
        require_terminal_event_inactive=False, incidents=(), initial_commitment=initial.commitment,
        initial_generation_mw=initial.generation_mw, initial_time_in_state_hours=initial.time_in_state_hours)
    assembled = assemble_source_normal(root, tuple(range(25)), request, initial, carry,
        source_time_basis='naive_source_labelled_utc')
    model = build_continuous_normal_model(assembled.inputs, expected_identity=assembled.normal_identity)
    def encode(obj):
        if isinstance(obj, frozenset):
            return sorted(obj)
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        raise TypeError(type(obj).__name__)
    return json.loads(json.dumps({
        'status': 'DRAFT_NONAUTHORITATIVE', 'solver_calls': 0, 'model_builds': 1,
        'formal_ready': False, 'feasibility_assessed': False, 'initial_state_observed': False,
        'source_files_verified': True, 'initial_history_authenticated': False,
        'trajectory_binding_verified': False, 'formal_result': False,
        'source_root': root.as_posix(), 'source_manifest_sha256': assembled.source_manifest_sha256,
        'raw_source_hours': assembled.raw_source_hours, 'continuous_source_hours': assembled.inputs.source_hours,
        'source_time_basis': assembled.inputs.source_time_basis,
        'normal_identity': assembled.normal_identity, 'assembly_identity': assembled.assembly_identity,
        'initial': asdict(initial), 'carry': asdict(carry), 'request': asdict(request),
        'model_scale': asdict(scale_implementation.model_scale(model)), 'dependencies': _dependencies(),
        'audit_script_sha256': sha256(Path(__file__).read_bytes()).hexdigest(),
        'adapter_sha256': sha256(Path(source_implementation.__file__).read_bytes()).hexdigest(),
        'model_scale_implementation_sha256': sha256(Path(scale_implementation.__file__).read_bytes()).hexdigest(),
    }, default=encode))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.output.name.endswith('_non_authoritative.json') or args.output.exists():
        parser.error('new *_non_authoritative.json output required')
    report = build_report(args.source_root)
    with args.output.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(report, stream, sort_keys=True, indent=2)
        stream.write('\n')
    print(json.dumps(report['model_scale'], sort_keys=True))


if __name__ == '__main__':
    main()
