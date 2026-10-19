"""Preserve terminal/profile evidence before changing the current DRAFT."""
from hashlib import sha256
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEST = HERE / 'whole_workflow_optimization_01_non_authoritative'
plan_path = DEST / 'public_implementation_identity_cost_plan_125.json'
terminal_path = HERE / 'public_implementation_identity_cost_125/terminal.json'
base = Path('D:/h1_implementation_identity_125_non_authoritative')
closed_path = base / 'unit_code_read_lease_closed.json'
profile_path = next(base.glob('*/public_implementation_identity_profile.json'))
plan = json.loads(plan_path.read_text())
terminal = json.loads(terminal_path.read_text())
drift = [name for name, pin in plan['files_sha256'].items()
         if sha256(Path(name).read_bytes()).hexdigest() != pin]
assert terminal['exit_code'] == 0 and terminal['source_unchanged'] and not drift
assert terminal['observed_owned_processes_absent'] and not terminal['cleanup_errors']
value = dict(
    schema='h1_public_implementation_identity_cost_result_125',
    status='BOUNDED_PROFILE_COMPLETE_NONAUTHORITATIVE',
    plan_sha256=sha256(plan_path.read_bytes()).hexdigest(),
    terminal_sha256=sha256(terminal_path.read_bytes()).hexdigest(),
    profile_sha256=sha256(profile_path.read_bytes()).hexdigest(),
    closed_receipt_sha256=sha256(closed_path.read_bytes()).hexdigest(),
    terminal=terminal, planned_pins=len(plan['files_sha256']), pin_drift=drift,
    profile=json.loads(profile_path.read_text()), closed_receipt=json.loads(closed_path.read_text()),
    interpretation='Recursive implementation identity recomputation is the next measured bottleneck. '
        'The public Bootstrap5 formula repeatedly traverses unchanged dependency subgraphs. '
        'This is profiled attribution only; no public owner, data window, N0, or native call ran.',
    next_question='Optimize repeated immutable implementation identity observation with explicit '
        'freshness and failure boundaries, then validate genuine public construction/close/reopen.',
    profiler_enabled=True, matched_unprofiled_runtime_comparison=False,
    whole_workflow_performance_review_complete=False, formal_result=False,
    formal_execution_ready=False, resource_admission=False)
out = DEST / 'public_implementation_identity_cost_result_125.json'
with out.open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(value, stream, indent=2)
    stream.write('\n')
print(json.dumps(dict(path=str(out), sha256=sha256(out.read_bytes()).hexdigest(),
                     planned_pins=value['planned_pins'], pin_drift=drift)))
