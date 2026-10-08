"""Zero-solver reproduction of saved synthetic assignment audits, not a certificate."""
from dataclasses import asdict
from fractions import Fraction
from pathlib import Path
import argparse
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))

from pyomo.environ import Var
from test_rq2_continuous_planner_open_activity_native_v1 import contract, scenario, SPEC, p, a


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encode(item):
    if isinstance(item, Fraction):
        return {'numerator': str(item.numerator), 'denominator': str(item.denominator)}
    raise TypeError(type(item).__name__)


def verify():
    directory = ROOT / 'results/tables/rq2_continuous_planner_open_activity_native_v1_non_authoritative'
    inventory = json.loads((directory / 'inventory.json').read_text(encoding='utf-8'))
    checks = json.loads((directory / 'development_checks.json').read_text(encoding='utf-8'))
    for name, expected in checks['development_sha256'].items():
        if sha(ROOT / name) != expected:
            raise ValueError('development dependency drift: ' + name)
    if sha(directory / 'inventory.json') != checks['evidence_inventory_sha256']:
        raise ValueError('inventory drift')
    comparisons = []
    for row in inventory['rows']:
        path = ROOT / row['path']
        if sha(path) != row['sha256'] or path.stat().st_size != row['bytes']:
            raise ValueError('snapshot drift: ' + row['arm'])
        saved = json.loads(path.read_text(encoding='utf-8'))['snapshot']
        config = contract(scenario(g=(.25, 0.), c=(.125, 0.), due=(2, None)))
        model = p.build_continuous_planning_model(config, row['arm'])
        values = dict(saved['assignment']['snapshot'])
        for variable in model.component_data_objects(Var):
            variable.set_value(values[variable.name]['number'], skip_validation=True)
        audit = a.audit_planner_assignment(config, row['arm'], model, SPEC)
        decoded = json.loads(json.dumps(asdict(audit), default=encode, allow_nan=False))
        if decoded != saved['assignment'] or saved['native_values'] != saved['assignment']['snapshot']:
            raise ValueError('assignment replay differs: ' + row['arm'])
        def digest(obj):
            return hashlib.sha256(json.dumps(obj, sort_keys=True, allow_nan=False).encode()).hexdigest()
        comparisons.append({'arm': row['arm'], 'assignment_id': audit.assignment_id,
            'saved_assignment_sha256': digest(saved['assignment']),
            'recomputed_assignment_sha256': digest(decoded), 'native_values_match': True})
    names = [Path(__file__).relative_to(ROOT).as_posix(),
        'tests/test_rq2_continuous_planner_open_activity_native_v1.py',
        'tests/test_rq2_continuous_planner_open_activity_v1.py',
        'tests/test_rq2_continuous_planner_v1.py',
        'tests/test_rq2_continuous_planner_short_solve_v1.py']
    return {'schema': 'rq2_open_activity_saved_assignment_replay_v2',
        'status': 'DRAFT_NONAUTHORITATIVE', 'inventory_sha256': sha(directory / 'inventory.json'),
        'checker_and_fixture_sha256': {name: sha(ROOT / name) for name in names},
        'comparisons': comparisons, 'solver_calls': 0, 'synthetic_fixture_reconstruction': True,
        'native_history_authenticated': False, 'complete_capacity_certificate': None, 'formal_result': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = verify()
    report['command'] = 'D:/Miniconda3/envs/compute/python.exe -B ' + Path(__file__).relative_to(ROOT).as_posix() + ' --output ' + args.output.as_posix()
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print('Verified saved synthetic assignments:', len(report['comparisons']))
