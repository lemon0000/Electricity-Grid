"""Repartition the timed-out unit group; preserve the original attempt and cap."""
import json
from capture_checks import OUT, save

prior = json.loads((OUT/'group_admission_04.json').read_bytes())
nodes = [n for name, group in prior['groups'].items() if name.startswith('owner_complete_') for n in group]
assert len(nodes) == len(set(nodes)) == 56
groups = {f'owner_bounded_{i//10+1:02d}': nodes[i:i+10] for i in range(0, len(nodes), 10)}
spent = sum(json.loads(p.read_bytes())['wall_seconds'] for p in OUT.glob('*.exit.json')
    if json.loads(p.read_bytes()).get('nodes'))
caps = {label:30 for label in groups}
assert spent+sum(caps.values()) <= 240
save('group_admission_05.json', dict(authority='DRAFT_NONAUTHORITATIVE', groups=groups, caps=caps,
    previous_pytest_seconds=spent, pytest_total_seconds=240, static_total_seconds=60, whole_development_seconds=300,
    automatic_actor_retries=0, actual_saved_F_execution=False, F_launch_admitted=False,
    deferred_regressions=['stage_regression_01', 'guard_regression_01', 'binding_regression_01', 'binding_regression_02']))
print(json.dumps(dict(groups={k:len(v) for k,v in groups.items()}, previous_pytest_seconds=spent)))
