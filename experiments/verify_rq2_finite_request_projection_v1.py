"""Replay retained raw-source counterexamples through the existing numeric interfaces."""
from fractions import Fraction as Q
from hashlib import sha256
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.rq2_joint_deliverability_boundary_v1.workload_projection import project_workload_power
from src.scenarios.rq2_joint_deliverability import raw_cfe_request
from src.rq2_joint_deliverability_boundary_v1.four_arm_replay import _effective_call


def verify():
    source = ROOT/'results/tables/rq2_finite_request_feasibility_v1_non_authoritative/necessary_conflicts_verified.json'
    if sha256(source.read_bytes()).hexdigest() != 'bd498113d2342da1237c6433c976b6fb4d963885f83515ca47f56544d635cafa':
        raise ValueError('independent counterexample report differs')
    report = json.loads(source.read_bytes())
    paths = [source, Path(__file__),
        ROOT/'src/rq2_joint_deliverability_boundary_v1/source_pair.py',
        ROOT/'src/rq2_joint_deliverability_boundary_v1/workload_projection.py',
        ROOT/'src/rq2_joint_deliverability_boundary_v1/four_arm_replay.py',
        ROOT/'src/rq2_joint_deliverability_boundary_v1/boundary.py',
        ROOT/'src/scenarios/rq2_joint_deliverability.py']
    pins = {p.relative_to(ROOT).as_posix(): sha256(p.read_bytes()).hexdigest() for p in paths}
    rows = []
    for witness in report['witnesses']:
        projection = project_workload_power(witness['workload_row']['workload_fraction'], '250', decimal_places=12)
        if projection['status'] != 'projected':
            raise ValueError('counterexample does not reach the declared numeric interface')
        amount = raw_cfe_request(float(witness['power_row']['cfe_call_fraction']), float(witness['alpha']))
        q = _effective_call(0., amount)
        w = Q(str(projection['workload_occupancy']))
        available = Q(str(witness['flexible_fraction']))*w
        if not q > w or not q > available:
            raise ValueError('counterexample lost after actual interface projection')
        rows.append(dict(cell_id=witness['cell_id'], projection=projection,
            raw_cfe_request=amount, raw_cfe_request_float_hex=amount.hex(),
            effective_cfe_request=str(q), available_flexibility=str(available),
            baseline_excess=str(q-w), flexibility_excess=str(q-available)))
    if len(rows) != 46 or len({r['cell_id'] for r in rows}) != 46:
        raise ValueError('46 unique replayed counterexamples required')
    if any(sha256((ROOT/p).read_bytes()).hexdigest() != h for p,h in pins.items()):
        raise ValueError('replay inputs changed')
    return dict(status='DRAFT_NONAUTHORITATIVE', formal_result=False, solver_calls=0,
        scope='retained counterexamples through projection and request interfaces; not full-window staging',
        normalized_unit_mw='250', decimal_places=12, assumptions_are_registered=False,
        source_sha256=pins, rows=rows, replayed_conflicts=len(rows),
        minimum_baseline_excess=str(min(Q(r['baseline_excess']) for r in rows)),
        minimum_flexibility_excess=str(min(Q(r['flexibility_excess']) for r in rows)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = verify()
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(result['replayed_conflicts'], 'projected conflicts; zero solves')
