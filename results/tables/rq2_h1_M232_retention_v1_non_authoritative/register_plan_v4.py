"""New observation contract after a preserved diagnostic-only assertion failure."""
import ast
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def pin(path):return sha256(Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(Path(path).read_bytes())


def main():
    old=load(HERE/'plan_v3.json')
    pins=load(HERE/'packet_01/request.json')['sources_sha256']
    assert len(pins)==2919 and all(pin(path)==value for path,value in pins.items())
    failure=load(HERE/'packet_01/terminal.json')
    assert failure['exit_code']==1 and failure['changed_sources']==[]
    assert failure['reason'] is None and failure['observed_processes_remaining']==[]
    assert 'AssertionError' in failure['worker']['error'] and failure['worker']['audit_errors']==[]
    assert failure['worker']['opened_input_pins_changed']==[]
    support=load(HERE/'observer_checks_02/terminal.json')
    assert support['exit_code']==0 and support['changed']==[] and support['error'] is None
    assert all(pin(path)==value for path,value in support['source_after'].items())
    guard=load(HERE/'optimization_guard_02/terminal.json')
    assert guard['checks_passed']==2 and guard['source_before']==guard['source_after']
    assert all(pin(path)==value for path,value in guard['source_after'].items())
    plan=dict(old)
    for root in (HERE/'packet_01',HERE/'observer_checks_02',HERE/'optimization_guard_02',HERE/'dataclass_size_01'):
        for path in root.rglob('*'):
            if path.is_file():pins[str(path)]=pin(path)
    for path in HERE.glob('*.py'):
        ast.parse(path.read_text(encoding='utf-8'));pins[str(path)]=pin(path)
    pins[str(HERE/'observation_successor_design.md')]=pin(HERE/'observation_successor_design.md')
    plan.update(bindings=pins,scope='one real-source M232 origin packet; sequential accounting checkpoints, no cross-time equality gate',
        worker='packet_worker_v2.py',runner='run_packet_v2.py',prior_failed_attempt=str(HERE/'packet_01/terminal.json'),
        diagnostic_failure_reason='extra cross-time accounting equality assumption, not a source identity/128MiB gate',
        additional_top_level_retained_size_calls=14,additional_layout_walks=4,
        additional_post_source_full_packet_digest_calls=1,
        representation_observation_points=['before_all_packet_validation','after_all_packet_validation',
            'after_field_walks','after_source_revalidation'],
        accounting_stability_across_checkpoints_required=False,
        original_source_or_128MiB_contract_changed=False,
        per_attempt_budget_unchanged=True,prior_attempt_budget_extended=False,
        maximum_total_source_load_invocations_across_both_plans=4,
        inherited_registration={'path':str(HERE/'plan_v3.json'),'sha256':pin(HERE/'plan_v3.json')})
    with (HERE/'plan_v4.json').open('x',encoding='utf-8') as stream:json.dump(plan,stream,indent=2);stream.write('\n')
    print(json.dumps(dict(registered=True,bindings=len(pins),worker='v2',wall_seconds=60,
        domain_changed=False,prior_failure_preserved=True)))


if __name__=='__main__':main()
