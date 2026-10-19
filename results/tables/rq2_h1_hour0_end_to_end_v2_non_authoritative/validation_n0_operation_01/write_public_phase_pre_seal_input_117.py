"""Exact provisional public coordinator and monitor review input."""
from hashlib import sha256
import difflib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
D=HERE/'whole_workflow_optimization_01_non_authoritative'
sources=[
 'experiments/h1_bootstrap_integration_development_v5.py',
 'experiments/h1_owned_bootstrap_controller_development_v5.py',
 'experiments/h1_group_execution_roster_development_v4.py',
 'experiments/h1_historical_n0_verifier_development_v4.py',
 'experiments/h1_bootstrap_integration_development_v4.py',
 'experiments/h1_owned_bootstrap_controller_development_v4.py',
 'experiments/h1_group_execution_roster_development_v3.py',
 'experiments/h1_historical_n0_verifier_development_v3.py',
 'experiments/h1_phase_manifest_validation_operation_development_v1.py',
 'tests/test_h1_bootstrap_phase_segments_development_v5.py',
 'tests/test_h1_phase_manifest_segment_faults_development_v1.py',
 'tests/test_h1_unit_storage_observer_development_v16.py',
]
for name in ('run_unit_bounded_v15.py','run_unit_bounded_v16.py','run_unit_entry_v3.py'):
    sources.append((HERE/name).relative_to(ROOT).as_posix())
for name in ('request.json','started.json','terminal.json','stdout.log'):
    sources.append((HERE/'monitor_public_phase_units_117'/name).relative_to(ROOT).as_posix())
terminal=json.loads((HERE/'monitor_public_phase_units_117/terminal.json').read_text())
assert terminal['exit_code']==0 and terminal['source_unchanged'] and terminal['observed_owned_processes_absent']
assert not terminal['cleanup_errors'] and not terminal['storage_read_errors']
assert terminal['storage_path_ABA_covered'] is False
value=dict(schema='h1_public_phase_pre_seal_input_117',status='DRAFT_NONAUTHORITATIVE',root_is_sole_writer=True,
    original_request='Finish missing experiment work and optimize bottlenecks in the complete workflow.',
    files_sha256={name:sha256((ROOT/name).read_bytes()).hexdigest() for name in sources},
    independent_pre_seal_findings_only=True,
    acceptance=[
      'New Bootstrap5/Owned5/Roster4 and retained verifier4 use exact new namespaces; predecessor files and headers are not taken over.',
      'Verifier4 is an exact mechanical copy of verifier3 except its active name and exact Bootstrap5 binding; protected predecessor science schema is unchanged.',
      'Retained local fields change only verifier schema/contract; global terminal-body digest honestly changes to bind the new local bytes.',
      'The private creator-bound per-owner coordinator uses exact configuration/declaration/guard/route identities and cannot accept detached caller receipts.',
      'Internal phase checks/candidate/replay borrow an active window; pure phase science only is cached. Every candidate cache hit is compared with the held projection.',
      'Constructors may write only under the complete declared disjoint study root. All Journal retain callbacks, Roster external retain and the complete external Owned Job close the current window and reacquire afterward.',
      'Private synchronous frames allow internal reads inside a callback only via a separate complete child scope. No active original kernel spans callback entry.',
      'Body/callback/configuration/CloseHandle failures remain sticky, preserve primary error and retain pending scopes for bounded explicit cleanup.',
      'Instances may not shadow definition-bound owner methods; class/source/module and original shared class methods are fixed by runtime2.',
      'Public receipts are detached diagnostic lifecycle data with consumer_bound=false; no formal or ABA/per-call freshness claim is made.',
    ],
    tested_scope='Original coordinator extracted by AST into explicit unit owner protocol; tiny science with actual Windows handles. Seven public-namespace/coordinator bodies plus seven monitor bodies. No genuine public owner lifecycle or N0 executed.',
    prior_scope_review=dict(input='shared_phase_scope_pre_seal_input_114.json',
        scope112_named_findings_closed=True,official_review=False),
    monitor_fixes=[
      'Root and each queued directory are statted without following immediately before scandir; reject reparse and non-directory roots/routes.',
      'Only the exact basetemp may be missing at startup sampling. Final observation requires both roots.',
      'Actual root cycle/broken/external junction negatives, queued-directory replacement negative and missing-final-root checks added.',
      'Contract narrowed to observed_entries_nonfollow_with_directory_rechecks; storage_path_ABA_covered=false.',
    ],
    monitor_diff=''.join(difflib.unified_diff((HERE/'run_unit_bounded_v15.py').read_text().splitlines(True),
        (HERE/'run_unit_bounded_v16.py').read_text().splitlines(True),fromfile='runner15',tofile='runner16')),
    terminal=terminal,unit_bodies='14 passed in 6.38s',
    failures_preserved=['111 storage traversal cycle','113 dangling-junction storage error',
        '115 incorrect test expectation that new local body has old global digest; first-test temp root missing'],
    remaining_open=['Independent named review','Genuine Bootstrap5/Roster4 header create/inspect/close/reopen',
        'Genuine synthetic N0 and independent complete oracle','Fresh three-arm typed Common/Genesis/Handoff/paired/reopen',
        'Whole-workflow measured resource budget','All official/formal gates'],
    formal_result=False,formal_execution_ready=False,resource_admission=False,native_execution_authorized=False,
    official_review=False,formal_run_authorized=False)
out=D/'public_phase_pre_seal_input_117.json'
with out.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(path=str(out),sha256=sha256(out.read_bytes()).hexdigest())))
