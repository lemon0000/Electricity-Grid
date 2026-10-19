"""Record the complete genuine zero-N0 header lifecycle without a speed claim."""
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;D=HERE/'whole_workflow_optimization_01_non_authoritative'
plan_path=D/'roster4_header_probe_plan_131.json';plan=json.loads(plan_path.read_text())
terminal_path=HERE/'workflow_roster4_header_131/terminal.json';terminal=json.loads(terminal_path.read_text())
base=Path('D:/h1_roster4_header_131_non_authoritative')
observation_path=next(base.glob('*/roster4_live_header_observation.json'))
closed_path=base/'unit_code_read_lease_closed.json'
observation=json.loads(observation_path.read_bytes());closed=json.loads(closed_path.read_bytes())
drift=[name for name,pin in plan['files_sha256'].items() if sha256(Path(name).read_bytes()).hexdigest()!=pin]
assert terminal['exit_code']==0 and terminal['source_unchanged'] and not drift
assert terminal['observed_owned_processes_absent'] and not terminal['cleanup_errors']
assert not any(observation['execution_denial_calls'].values())
segments=observation['original_receipt']['segments']+observation['reopened_receipt']['segments']
assert len(segments)==6
assert all(s['receipt']['lifecycle_complete'] and s['receipt']['cached_science_cleared']
    and s['receipt']['phase_kernel_receipt']['all_handles_closed']
    and s['implementation_observation']['entry_exit_equal'] for s in segments)
value=dict(schema='h1_roster4_header_probe_result_131',status='COMPLETE_HEADER_DIAGNOSTIC_NONAUTHORITATIVE',
    plan_sha256=sha256(plan_path.read_bytes()).hexdigest(),terminal_sha256=sha256(terminal_path.read_bytes()).hexdigest(),
    observation_sha256=sha256(observation_path.read_bytes()).hexdigest(),
    closed_receipt_sha256=sha256(closed_path.read_bytes()).hexdigest(),
    terminal=terminal,planned_pins=len(plan['files_sha256']),pin_drift=drift,observation=observation,
    entry_closed_receipt=closed,
    summary=dict(complete_header_lifecycle=True,exact_public_class=True,phase_windows=6,
        raw_implementation_observations=sum(s['implementation_observation']['entry_raw_attempts']+
            s['implementation_observation']['exit_raw_attempts'] for s in segments),
        cached_implementation_calls=sum(s['implementation_observation']['cached_calls'] for s in segments),
        all_phase_handles_closed=True,all_phase_science_caches_cleared=True,
        all_phase_guards_released=True,completed_N0=0,new_N0_Jobs=0,real_native_calls=0),
    limitations=['Nine pre-definition execution denials are explicit; execution dispatch and N0/Job not validated.',
        '119 was incomplete and used a different entry. Do not report a matched percentage speedup.',
        'Implementation/source observation is segment entry/exit only; no per-call or transient ABA claim.',
        'No three-arm, Common/Genesis/Parent/Handoff/paired/Post integration or whole-workflow budget follows.'],
    complete_header_lifecycle=True,full_optimized_workflow_accepted=False,
    whole_workflow_performance_review_complete=False,formal_result=False,formal_execution_ready=False,
    resource_admission=False,native_execution_authorized=False)
out=D/'roster4_header_probe_result_131.json'
with out.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(path=str(out),sha256=sha256(out.read_bytes()).hexdigest(),summary=value['summary'],pin_drift=drift)))
