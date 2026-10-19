"""Bind the creator-thread repair, entry failure and explicit development route."""
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
D=HERE/'whole_workflow_optimization_01_non_authoritative'
prior=D/'public_phase_pre_seal_input_130.json';value=json.loads(prior.read_text())
paths=[ROOT/p for p in value['files_sha256']]
paths.extend((Path(__file__),ROOT/'tests/test_h1_roster4_live_header_development_v1.py',
    D/'roster4_header_probe_result_131.json'))
for label in ('phase_implementation_thread_isolation_132','phase_implementation_entry_faults_133',
              'phase_public_final_regression_134'):
    paths.extend(HERE/label/name for name in ('request.json','started.json','stdout.log','terminal.json'))
terminal=json.loads((HERE/'phase_public_final_regression_134/terminal.json').read_text())
assert terminal['exit_code']==0 and terminal['source_unchanged'] and terminal['observed_owned_processes_absent']
value.update(schema='h1_public_phase_fix_input_135',predecessor_input_sha256=sha256(prior.read_bytes()).hexdigest(),
    files_sha256={p.relative_to(ROOT).as_posix():sha256(p.read_bytes()).hexdigest() for p in paths},
    current_terminal=terminal,current_unit_bodies='116 passed in22.96s; outer26.125s',
    fixes_to_130=[dict(finding='P1 process-global implementation LIFO',
        repair='Private dictionary of separate(pid,thread_id) stacks; immediately delete empty stacks.',
        evidence='132/134 deterministic event barriers: legal A and B creator threads overlap, A exits while B remains active; normal and same-original body primary variants both clean and isolate memo counters.'),
        dict(finding='P2 first raw entry exception negative missing',repair='133/134 first entry throws before memo/window; receipt entry1/exit0, active frames0, no handles, outside raw unchanged.')],
    explicit_development_dispatch=dict(change='bootstrap(registered_development=True) selects the existing registered development continuation; exact bool required. Default retains the existing metadata-only route.',
        reason='The prior cold N0 fixture changed _continue_bootstrap after import; the new definition-bound successor must expose an explicit source-bound opt-in instead of changing a sealed callable.',
        authority='This draft method is not formal/native/resource authorization. Tests/diagnostics still use an explicit synthetic Job and source seams. No N0 launched by this change.',
        negatives='134 three non-bool inputs refused before phase handles; genuine header test also checks zero extra segments/writes.'),
    header131=dict(status='historical complete lifecycle before thread-map and opt-in source changes',
        outer_seconds=105.766,windows=6,raw=12,memo_hits=1304,
        current_source_byte_closure=False,execution_dispatch_verified=False,N0=0),
    scope='Current full targeted116-case regression plus exact source. Historical131 genuine zero-N0 public lifecycle is preserved; current-source header and positive N0 route still require diagnostics.',
    remaining=['independent review of thread/entry fixes and explicit development opt-in',
        'current-source genuine header and positive synthetic N0 numerical registration/close/reopen',
        'three-arm typed Common/Genesis/Parent/Handoff/paired/Post chain and whole-workflow budget',
        'all official/formal/native/resource gates'])
out=D/'public_phase_fix_input_135.json'
with out.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(path=str(out),sha256=sha256(out.read_bytes()).hexdigest())))
