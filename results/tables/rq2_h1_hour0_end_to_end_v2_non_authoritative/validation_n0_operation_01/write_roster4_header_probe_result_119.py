"""Preserve the bounded incomplete public-header diagnostic and pin readback."""
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
D=HERE/'whole_workflow_optimization_01_non_authoritative'
plan_path=D/'roster4_header_probe_plan_119.json';plan=json.loads(plan_path.read_text())
terminal_path=HERE/'workflow_roster4_header_119/terminal.json';terminal=json.loads(terminal_path.read_text())
stages=[]
for line in (HERE/'workflow_roster4_header_119/stdout.log').read_text().splitlines():
    try:item=json.loads(line)
    except json.JSONDecodeError:continue
    if type(item) is dict and 'stage' in item:stages.append(item)
drift=[]
for name,pin in plan['files_sha256'].items():
    try:
        if sha256(Path(name).read_bytes()).hexdigest()!=pin:drift.append(name)
    except OSError:drift.append(name)
value=dict(schema='h1_roster4_header_probe_result_119',status='INCOMPLETE_BOUNDED_DIAGNOSTIC',
    plan_sha256=sha256(plan_path.read_bytes()).hexdigest(),terminal_sha256=sha256(terminal_path.read_bytes()).hexdigest(),
    stages=stages,terminal=terminal,planned_pins=len(plan['files_sha256']),pin_drift=drift,
    Bootstrap5_create_interval_seconds=stages[1]['elapsed_seconds']-stages[0]['elapsed_seconds'],
    Roster4_create_returned=False,complete_header_lifecycle=False,closed_internal_receipts_observed=False,
    internal_graceful_cleanup_proven=False,OS_owned_process_cleanup_observed=terminal['observed_owned_processes_absent'],
    scope='Header only with predefinition execution denials;0 completed N0/Job/native. Missing final counters are not a passed zero-execution oracle.',
    interpretation='No completion or mathematical infeasibility claim. Do not extend or repeat this unchanged expensive prefix; profile runtime-seal/check composition with0 owners.',
    full_optimized_workflow_accepted=False,whole_workflow_performance_review_complete=False,
    formal_result=False,formal_execution_ready=False,resource_admission=False,native_execution_authorized=False)
out=D/'roster4_header_probe_result_119.json'
with out.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(path=str(out),sha256=sha256(out.read_bytes()).hexdigest(),stages=stages,pin_drift=len(drift))))
