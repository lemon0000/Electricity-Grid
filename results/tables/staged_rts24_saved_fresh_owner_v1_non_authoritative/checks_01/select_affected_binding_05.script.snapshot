"""Select existing binding tests directly affected by owner-input refactoring."""
import json
from capture_checks import OUT, save

plan = json.loads((OUT/'group_admission_04.json').read_bytes())
all_binding = plan['groups']['binding_regression_01']+plan['groups']['binding_regression_02']
nodes = [n for n in all_binding if any(t in n for t in ('owner', 'reservation', 'constructor', 'data_only', 'consume'))]
assert len(nodes) == len(set(nodes)) == 18
spent = sum(json.loads(p.read_bytes())['wall_seconds'] for p in OUT.glob('*.exit.json')
    if json.loads(p.read_bytes()).get('nodes'))
save('group_admission_06.json', dict(authority='DRAFT_NONAUTHORITATIVE',
    groups=dict(binding_affected_01=nodes), caps=dict(binding_affected_01=25),
    previous_pytest_seconds=spent, pytest_total_seconds=240, static_total_seconds=60, whole_development_seconds=300,
    automatic_actor_retries=0, actual_saved_F_execution=False, F_launch_admitted=False,
    selection='existing owner inputs, store/reservation binding, final consume bookend',
    full_frozen_binding_77_rerun=False))
print(json.dumps(dict(selected_nodes=len(nodes), previous_pytest_seconds=spent)))
