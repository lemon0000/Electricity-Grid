"""Bind an explicit build-only normal declaration to a verified power window."""
import argparse
from dataclasses import asdict
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path

from src.evaluation import ChronologicalFlexibilityEnvelope
from src.grid.chronological_dispatch import ChronologicalDispatchRequest
from src.grid.rts_gmlc_scuc import RtsGmlcInitialState
from src.rq2_joint_deliverability_boundary_v1.grid_carry import GridCarry, GridIdentity, UnitLimits, UnitPoint
from src.rq2_joint_deliverability_boundary_v1 import source_normal, source_window
from src.rq2_joint_deliverability_boundary_v1.power_normal_binding import bind_power_normal


def declared_inputs(record, window):
    """Interpret a supplied record as a mechanism declaration, not a checkpoint."""
    request = dict(record['request'])
    request['timestamps'] = tuple(datetime.fromisoformat(t) for t in request['timestamps'])
    request['system_demand_by_bus_mw'] = tuple({int(k): v for k,v in row.items()}
        for row in request['system_demand_by_bus_mw'])
    request['flexibility_envelope'] = ChronologicalFlexibilityEnvelope(**request['flexibility_envelope'])
    request['completed_periods'] = frozenset(request['completed_periods'])
    for key, value in request.items():
        if type(value) is list:
            request[key] = tuple(value)
    initial = RtsGmlcInitialState(**record['initial'])
    original = record['carry']
    # This is a new explicit mechanism scenario attached to the source chain;
    # it does not upgrade the old initial state into an observed history.
    identity = GridIdentity(window['split'], window['chain']['chain_id'], window['outage_seed'],
        record['source_manifest_sha256'])
    carry = GridCarry(identity, original['source_hour'],
        tuple(UnitLimits(**x) for x in original['limits']), tuple(UnitPoint(**x) for x in original['points']),
        tuple(original['elapsed_state_hours']), 'mechanism_assumption')
    return ChronologicalDispatchRequest(**request), initial, carry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--declaration', type=Path, required=True)
    parser.add_argument('--expected-declaration-sha256', required=True)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--split', choices=('training','holdout'), required=True)
    parser.add_argument('--raw-start', type=int, required=True)
    parser.add_argument('--hours', type=int, required=True)
    parser.add_argument('--outage-seed', type=int, required=True)
    parser.add_argument('--expected-window-identity', required=True)
    parser.add_argument('--expected-assembly-identity', required=True)
    parser.add_argument('--expected-config-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or not args.output.name.endswith('_non_authoritative.json'):
        parser.error('new *_non_authoritative.json output required')
    source_window._sha(args.expected_declaration_sha256)
    source_window._sha(args.expected_assembly_identity)
    raw = args.declaration.read_bytes()
    if sha256(raw).hexdigest() != args.expected_declaration_sha256:
        raise ValueError('normal declaration hash mismatch')
    record = json.loads(raw)
    window = source_window.load_source_window('power',args.split,args.raw_start,args.hours,
        outage_seed=args.outage_seed,expected_config_sha256=args.expected_config_sha256)
    source_window._sha(args.expected_window_identity)
    if window['window_identity'] != args.expected_window_identity:
        raise ValueError('power window identity mismatch')
    request, initial, carry = declared_inputs(record,window)
    assembly = source_normal.assemble_source_normal(args.source_root,tuple(range(args.raw_start,args.raw_start+args.hours)),
        request,initial,carry,source_time_basis=record['source_time_basis'])
    report = bind_power_normal(assembly,args.source_root,expected_assembly_identity=args.expected_assembly_identity,
        expected_window_identity=args.expected_window_identity,expected_config_sha256=args.expected_config_sha256)
    output = {'binding':report,'declaration_sha256':args.expected_declaration_sha256,
        'expected_assembly_identity':args.expected_assembly_identity,
        'declaration_role':'explicit_mechanism_input_not_executable_checkpoint',
        'initial':asdict(initial),'carry':asdict(carry),
        'original_carry_identity':record['carry']['identity'],
        'runner_sha256':sha256(Path(__file__).read_bytes()).hexdigest()}
    with args.output.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(output,stream,sort_keys=True,indent=2,allow_nan=False)
        stream.write('\n')
    print(json.dumps({'binding_identity':report['binding_identity'],
        'maximum_system_load_residual_mw':report['maximum_system_load_residual_mw']}))


if __name__ == '__main__':
    main()
