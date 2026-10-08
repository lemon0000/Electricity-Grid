"""Reproduce saved synthetic assignments with zero solves; no native-history claim."""
from dataclasses import asdict
from fractions import Fraction
from hashlib import sha256
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'tests'))

from pyomo.environ import Var
from test_rq2_bidirectional_capacity_v1 import contract, scenario, SPEC, p, a
from test_rq2_continuous_planner_v1 import assign
from src.rq2_joint_deliverability_boundary_v1.four_arm_replay import NETWORK, CFE, JOINT, B6

DIRECTORY = ROOT/'results/tables/rq2_bidirectional_capacity_v1_non_authoritative'


def fixtures():
    for arm in (NETWORK, CFE, JOINT, B6):
        yield 'four_arm_'+arm, arm, contract(scenario(g=(.25, 0.), c=(.125, 0.), due=(2, None)))
    for hours in (2, 3):
        yield 'analytic_'+str(hours), JOINT, contract(scenario(g=(.4,)+(0.,)*(hours-1),
            due=(hours,)+(None,)*(hours-1)))


def encode(item):
    if isinstance(item, Fraction):
        return {'numerator': str(item.numerator), 'denominator': str(item.denominator)}
    raise TypeError(type(item).__name__)


def verify():
    inventory = json.loads((DIRECTORY/'inventory.json').read_text(encoding='utf-8'))
    expected = list(fixtures())
    if [row['case'] for row in inventory['rows']] != [name for name, _, _ in expected]:
        raise ValueError('synthetic fixture inventory differs')
    comparisons = []
    for row, (name, arm, config) in zip(inventory['rows'], expected, strict=True):
        path = DIRECTORY/(name+'.json')
        data = path.read_bytes()
        if sha256(data).hexdigest() != row['sha256'] or len(data) != row['bytes']:
            raise ValueError('saved snapshot drift: '+name)
        saved = json.loads(data)['snapshot']
        model = p.build_continuous_planning_model(config, arm)
        values = dict(saved['assignment']['snapshot'])
        for variable in model.component_data_objects(Var):
            variable.set_value(values[variable.name]['number'], skip_validation=True)
        audit = a.audit_planner_assignment(config, arm, model, SPEC)
        decoded = json.loads(json.dumps(asdict(audit), default=encode, allow_nan=False))
        if decoded != saved['assignment'] or saved['native_values'] != saved['assignment']['snapshot']:
            raise ValueError('full assignment/witness replay differs: '+name)
        comparisons.append(dict(case=name, assignment_id=audit.assignment_id,
            numerical_accepted=audit.numerical_assignment_accepted, exact_witness_accepted=audit.exact_witness_accepted))
    exact_data = (DIRECTORY/'analytic_exact_witnesses.json').read_bytes()
    if sha256(exact_data).hexdigest() != inventory['analytic_exact_witnesses_sha256']:
        raise ValueError('exact synthetic witness artifact drift')
    saved_exact = json.loads(exact_data)['rows']
    expected_exact = []
    for hours, capacity in ((2, .5), (3, .4)):
        config = contract(scenario(g=(.4,)+(0.,)*(hours-1), due=(hours,)+(None,)*(hours-1)))
        model = p.build_continuous_planning_model(config, JOINT)
        assign(model, recovery={('s', 'shared', t): .5/(hours-1) for t in range(1, hours)},
            allocations={('s', 'shared', 0, t): .4/(hours-1) for t in range(1, hours)}, capacity=capacity)
        audit = a.audit_planner_assignment(config, JOINT, model, SPEC)
        if not audit.exact_witness_accepted:
            raise ValueError('exact analytic witness rejected')
        expected_exact.append(dict(hours=hours,
            lower_bound_reason='max(call .4, total physical recovery .4/.8 divided by idle hours)',
            capacity=capacity, assignment=asdict(audit)))
    if json.loads(json.dumps(expected_exact, default=encode, allow_nan=False)) != saved_exact:
        raise ValueError('exact synthetic witness replay differs')
    return dict(schema='rq2_bidirectional_saved_assignment_replay_v1', status='DRAFT_NONAUTHORITATIVE',
        inventory_sha256=sha256((DIRECTORY/'inventory.json').read_bytes()).hexdigest(),
        comparisons=comparisons, exact_analytic_witnesses_reproduced=2,
        solver_calls=0, native_history_authenticated=False,
        complete_capacity_certificate=None, formal_result=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = verify()
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print('Verified synthetic bidirectional assignments:', len(report['comparisons']))
