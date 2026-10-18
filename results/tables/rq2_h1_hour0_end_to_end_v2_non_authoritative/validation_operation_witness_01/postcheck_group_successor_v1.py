"""Pin scoped draft checks and distinguish them from numerical integration."""
from hashlib import sha256
import json
from pathlib import Path
import re

import psutil

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
def read(path):return json.loads(path.read_bytes())
def digest(path):return sha256(path.read_bytes()).hexdigest()
def require(value,message):
    if not value:raise ValueError(message)
pins={};checks={}
def bind(path):
    pins[path.relative_to(REPO).as_posix()]=digest(path)

expected=None
for label,count in (('group_unit_05',48),('bridge_unit_07',50),('cold_route_definition_01',None)):
    root=HERE/label
    request=read(root/'request.json');terminal=read(root/'terminal.json');started=read(root/'started.json')
    require(terminal['exit_code']==0 and terminal['stop_reason'] is None
        and terminal['source_unchanged'],label+' terminal is incomplete')
    try:
        process=psutil.Process(started['pid'])
        require(process.create_time()!=started['creation_time'] or not process.is_running(),label+' owned PID remains')
    except psutil.NoSuchProcess:pass
    sources=request['source_sha256']
    for name,pin in sources.items():
        path=Path(name)
        require(digest(path)==pin,label+' current source differs: '+name)
        require(digest(root/'tested_bytes'/path.relative_to(REPO))==pin,label+' tested source differs')
        bind(path)
    if expected is None:expected=sources
    # Extra launcher scripts differ; the same four candidate files and three
    # unit tests are pinned in all three actual attempts.
    shared={name:pin for name,pin in sources.items() if '/experiments/' in name.replace('\\','/')
        or '/tests/' in name.replace('\\','/')}
    require(all(expected.get(name)==pin for name,pin in shared.items()),label+' shared draft drift')
    log=(root/'stdout.log').read_text(encoding='utf-8')
    if count is not None:require(re.search(r'\b'+str(count)+r' passed\b',log),label+' pass count differs')
    for filename in ('request.json','terminal.json','started.json','stdout.log'):bind(root/filename)
    checks[label]=dict(tests_passed=count,terminal=terminal,started=started,
        observed_direct_pid_absent=True,process_scope='recorded direct PID plus creation time; these unit/definition entries spawn no workers')

cold=read(HERE/'cold_route_definition_01_result.json')
require(cold['all_final_guards_passed'] and not cold['lease_issued']
    and not cold['handoff_token_issued'] and not cold['historical_numerical_replay']
    and not cold['actual_common_slice'],'cold definition scope differs')
for row in cold['route_sources']:require(digest(Path(row['path']))==row['sha256'],'real route source differs')
bind(HERE/'cold_route_definition_01_result.json')

# All old long-attempt inputs remain untouched; no run-state conclusion follows.
chain=HERE.parent/'chain_07';old=read(chain/'request.json')['before']
for name,pin in old.items():require(digest(Path(name))==pin,'old chain input changed: '+name)
bind(chain/'request.json')
for filename in ('review_fix_checks_plan_01.json','cold_route_definition_plan_01.json',
        'group_unit_04/request.json','group_unit_04/terminal.json','group_unit_04/stdout.log'):
    bind(HERE/filename)
bind(Path(__file__))
result=dict(status='SCOPED_DRAFT_CHECKS_COMPLETE_PENDING_PRESEAL_REVIEW',
    checks=checks,real_cold_route_definition=cold,old_chain_inputs_unchanged=len(old),
    files_sha256=pins,scoped_tests_passed=98,
    failed_attempt_preserved='group_unit_04: 41 passed, 1 failure, 1 teardown error; original owner/session detection and expected-corruption fixture teardown repaired',
    inherited_source_composition_evidence=dict(label='source_unit_02',tests_passed=6,
        scope='historical source/registry unit composition with mock witness; unchanged source v3/test; not a full dependency closure claim'),
    actual_three_arm_common_slice=False,numerical_performance_gain_measured=False,
    full_hour0_chain_passed=False,full_192_hour_verified=False,
    full_chain_performance_review_complete=False,official_review_verdict=None,
    formal_execution_ready=False,formal_result=False,resource_admission=False,
    native_execution_authorized=False)
out=HERE/'group_successor_checks_01.json'
with out.open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
print(json.dumps(dict(output=str(out),sha256=digest(out),pins=len(pins),scoped_tests_passed=98)),flush=True)
