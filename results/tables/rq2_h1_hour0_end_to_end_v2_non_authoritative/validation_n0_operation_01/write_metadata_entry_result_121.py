"""Composition cleanly closed, but no discovery fast path was actually used."""
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;D=HERE/'whole_workflow_optimization_01_non_authoritative'
plan_path=D/'metadata_entry_composition_plan_121.json';plan=json.loads(plan_path.read_text())
terminal_path=HERE/'metadata_entry_composition_121/terminal.json';terminal=json.loads(terminal_path.read_text())
base=Path('D:/h1_metadata_entry_121_non_authoritative');closed=base/'unit_code_read_lease_closed.json'
receipt=json.loads(closed.read_text());profile=next(base.glob('*/public_phase_runtime_profile.json'))
drift=[p for p,pin in plan['files_sha256'].items() if sha256(Path(p).read_bytes()).hexdigest()!=pin]
assert terminal['exit_code']==0 and not drift and terminal['observed_owned_processes_absent']
assert receipt['distribution_resolver_receipt']['fast_path_calls']==0
value=dict(schema='h1_metadata_entry_composition_result_121',status='CLEAN_COMPOSITION_FAST_PATH_UNUSED',
    plan_sha256=sha256(plan_path.read_bytes()).hexdigest(),terminal_sha256=sha256(terminal_path.read_bytes()).hexdigest(),
    closed_receipt_sha256=sha256(closed.read_bytes()).hexdigest(),profile_sha256=sha256(profile.read_bytes()).hexdigest(),
    terminal=terminal,planned_pins=len(plan['files_sha256']),pin_drift=drift,
    closed_receipt=receipt,components=json.loads(profile.read_text())['components'],
    interpretation='Parser reset took effect396 hits/0 misses. Resolver fast0/fallback388 means the intended discovery reuse was not exercised; do not call that optimization integrated or infer whole-workflow ROI.',
    next_question='Align the pytest import context with the resolver discovery context and record entry/test/exit sys.path; preserve native fallback behavior.',
    profiler_enabled=True,matched_unprofiled_runtime_comparison=False,whole_workflow_performance_review_complete=False,
    formal_result=False,resource_admission=False)
out=D/'metadata_entry_composition_result_121.json'
with out.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(path=str(out),sha256=sha256(out.read_bytes()).hexdigest())))
