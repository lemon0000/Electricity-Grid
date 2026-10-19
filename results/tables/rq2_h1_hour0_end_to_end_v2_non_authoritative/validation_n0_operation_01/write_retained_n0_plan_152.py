"""Plan one fresh public development N0 after the path bottleneck diagnostic."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
D=HERE/'whole_workflow_optimization_01_non_authoritative'
previous=D/'bootstrap5_n0_bounded_plan_137.json';value=json.loads(previous.read_bytes())
paths={Path(p) for p in value['files_sha256']}
paths.update((ROOT/'tests').glob('*h1*.py'))
paths.update((HERE/'run_unit_entry_v6.py',HERE/'run_unit_bounded_v19.py',Path(__file__),
    HERE/'create_bootstrap5_retained_n0_diagnostic_v3.py'))
closure_path=D/'canonical_path_entry6_scoped_findings_151.json'
closure=json.loads(closure_path.read_bytes())
assert closure['named_findings_closed'] is True and closure['official_review'] is False
base=Path('D:/h1_bootstrap5_retained_152_non_authoritative');label='bootstrap5_retained_n0_152'
assert not base.exists() and not (HERE/label).exists()
value.update(schema='h1_bootstrap5_retained_n0_bounded_plan_152',
    at_utc=datetime.now(timezone.utc).isoformat(),
    predecessor_plan_sha256=sha256(previous.read_bytes()).hexdigest(),
    command=[sys.executable,'-B',str(HERE/'run_unit_bounded_v19.py'),label,'300','1024','128','--',
        str(HERE/'run_unit_entry_v6.py'),'-s','-p','no:faulthandler','--basetemp',str(base),
        '--junitxml',str(base/'registered_development_true.xml'),'-o','junit_family=legacy',
        'tests/test_h1_registry_validation_retained_n0_development_v3.py::test_cold_bootstrap5_retained_n0_registration_and_close'],
    question='Can the unchanged public Bootstrap5/Owned5 development route return a complete registered N0 and close within the same300s cap after path composition, with externally persisted callback heads?',
    dag=['Reuse explicit synthetic input/source/Job seams and original identity callables; cold-import exact Bootstrap5.',
        'Build one current symbolic declaration and a new study/owner; preserve the existing foreign-thread registry-scope refusal.',
        'Call literal bootstrap(registered_development=True). Each of8 external retention callbacks CAS-checks original memory heads, saves a canonical chained record by flush/fsync and fresh-name rename before acknowledging.',
        'Execute exactly one short synthetic Windows Job; keep phase/implementation handles closed across callbacks and Job.',
        'Original4 registry builds with4full/28fresh/64contexts. Immediately save the actual successful public return and exact execution-receipt bytes.',
        'Save returned heads/report, close owner, require complete phase/implementation lifecycle and zero active/orphan counters, then close path/code/metadata leases.',
        'Save terminal/JUnit/pin/process/resource observations. Run the predecessor saved-data oracle and reopen in separate bounded postchecks; never rerun this Job for postchecks.'],
    files_sha256={str(p):sha256(p.read_bytes()).hexdigest() for p in sorted(paths,key=str)},
    path_scoped_findings_sha256=sha256(closure_path.read_bytes()).hexdigest(),
    numerical_oracle_is_separate_postcheck=True,
    externally_persisted_retention_protocol='File flush/fsync and fresh-name rename before callback acknowledgement; hash-linked records and full known heads. No power-loss durability guarantee or automatic suffix adoption.',
    matched_whole_workflow_comparison=False)
value['scale']['independent_predecessor_oracles']=0
value['optimization'].update(reused_evidence=[
    'Legacy chain07 and postcheck04 completed; do not rerun.',
    '135 scoped named closure,134116 cases,136 current real header complete.',
    '137 failed public registration at300.453s; saved Job exit0/quiet51.125s. No external heads; do not resume/adopt its suffix.',
    '138 saved candidate oracle equal;146 original four-build diagnostic4full/28fresh/64contexts complete.',
    '148 same saved program plus unchanged CanonicalPathLease: outer153.984 to134.75s, identical decision/audit/counts, all aliases/handles closed. Single profiled fixed-order comparison.',
    '150 ten entry6 child failures/CLI checks passed;151 independent named findings closed.'],
    changes_since137='Existing CanonicalPathLease composition; improved diagnostic failure persistence; external retention saves; separate numerical postcheck after public return. Original scientific code/config/thresholds unchanged.',
    callback_counts='Expected8 external head retentions plus1 Job; observe actual phase windows rather than infer counts.',
    limitations='No consumer foreign-registry reuse or full typed chain; path/implementation ABA and whole-tree process absence unproved. Separate oracle/reopen remain required after this diagnostic.')
value['budget'].update(basis='Same300s cap as137, not extended. 137 costs and146/148 attribution justify the path composition. Completion remains unknown; saved records/return permit separate postchecks without another Job.',
    heartbeat='Import/owner-open/every retention and final public return/close. Persist retention bytes before acknowledgement; monitor PID+creation/RSS/storage.',
    no_progress='No automatic retry, cap extension or deadlock inference from a quiet interval.')
value['acceptance']=[
    'exit0, exactly1 synthetic N0 Job, Job exit0/whole Job quiescent,0 real native calls',
    'literal True public call, invocation+JUnit and saved successful return; four registry builds/4full/28fresh/64contexts complete',
    'external retention records hash-linked and heads CAS-consistent before callback acknowledgement; no derived suffix adopted',
    'phase/implementation lifecycle complete, active/orphan0, path/code/metadata aliases and handles closed',
    'pins unchanged, observed PIDs absent and no cleanup errors; independent predecessor oracle/reopen not claimed here',
    'formal/native/resource and full-chain gates remain false']
target=D/'bootstrap5_retained_n0_bounded_plan_152.json'
with target.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(path=str(target),sha256=sha256(target.read_bytes()).hexdigest(),pins=len(paths))))
