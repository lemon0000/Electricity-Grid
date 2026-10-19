"""Bind actual Bootstrap6 observations, preserved metadata exception and fixes."""
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path

H=Path(__file__).resolve().parent;R=H.parents[3];D=H/'whole_workflow_optimization_01_non_authoritative'
paths={Path(__file__),H/'collect_saved174_postcheck_178.py',H/'write_retained_n0_result_174.py',
    H/'create_saved174_postchecks_175.py',H/'write_saved174_postcheck_plans_175.py'}
for name in ('bootstrap6_retained_n0_bounded_plan_174.json','bootstrap6_retained_n0_bounded_result_174.json',
        'bootstrap6_plan_metadata_mismatch_175.json','saved174_postcheck_plan_176.json','saved174_postcheck_plan_177.json',
        'saved174_postcheck_result_176.json','saved174_postcheck_result_177.json','consumer_scoped_findings_173.json'):
    paths.add(D/name)
producer=json.loads((D/'bootstrap6_retained_n0_bounded_result_174.json').read_bytes())
assert producer['public_development_N0_return_and_close_verified']
for row in producer['archive_files']:
    p=Path(row['saved']);assert sha256(p.read_bytes()).hexdigest()==row['sha256'];paths.add(p)
for number in ('176','177'):
    v=json.loads((D/('saved174_postcheck_result_'+number+'.json')).read_bytes())
    assert v['terminal']['exit_code']==0 and v['terminal']['observed_owned_processes_absent'] and not v['pin_drift']
    assert v['saved_file_names_and_bytes_unchanged']==154
    for row in v['archive_files']:
        p=Path(row['saved']);assert sha256(p.read_bytes()).hexdigest()==row['sha256'];paths.add(p)
labels=('bootstrap6_retained_n0_174','saved174_numerical_oracle_176','saved174_readonly_reopen_177',
    'n0_diagnostic_primary_successor_units_179','n0_diagnostic_primary_successor_units_180')
for label in labels:
    for name in ('request.json','started.json','terminal.json','stdout.log'):paths.add(H/label/name)
base=Path('D:/h1_n0_primary_successor_180_non_authoritative')
terminal=json.loads((H/labels[-1]/'terminal.json').read_bytes())
assert terminal['exit_code']==0 and terminal['source_unchanged'] and terminal['observed_owned_processes_absent']
assert not terminal['cleanup_errors'] and not terminal['storage_read_errors']
closed=base/'unit_code_read_lease_closed.json';entry=json.loads(closed.read_bytes())
assert entry['all_code_handles_closed'] and entry['original_read_alias_restored']
archive=D/'primary_test5_180_preserved_non_authoritative';archive.mkdir(exist_ok=False)
units=list(base.glob('*/primary_handler_observation.json'));assert len(units)==5
for source in [closed,*units]:
    target=archive/source.parent.name/source.name;target.parent.mkdir(parents=True,exist_ok=True)
    raw=source.read_bytes()
    with target.open('xb') as stream:stream.write(raw)
    assert target.read_bytes()==source.read_bytes()==raw;paths.add(target)
for name in ('test_h1_registry_validation_retained_n0_development_v4.py','test_h1_registry_validation_retained_n0_development_v5.py',
        'test_h1_saved_bootstrap6_n0_candidate_profile_development_v1.py',
        'test_h1_retained_n0_readonly_reopen_development_v6.py',
        'test_h1_n0_diagnostic_primary_handler_development_v5.py'):
    paths.add(R/'tests'/name)
prior=json.loads((D/'consumer_pre_seal_input_173.json').read_bytes())
for name in ('h1_bootstrap_integration_development_v6.py','h1_owned_bootstrap_controller_development_v6.py',
        'h1_historical_n0_verifier_development_v5.py'):
    path=R/'experiments'/name;assert sha256(path.read_bytes()).hexdigest()==prior['files_sha256'][str(path)]
    paths.add(path)
value=dict(schema='h1_bootstrap6_postchecks_input_181',status='PRE_SEAL_AUDIT_NONAUTHORITATIVE',
    at_utc=datetime.now(timezone.utc).isoformat(),root_sole_writer=True,risk='R3',
    scope='Actual versioned synthetic Bootstrap6 public N0 return/close, original saved oracle and genuine numerical public read reopen; preserve174 planning exception.',
    known_exception=['174 invocation.module retainsv5 and current_header_result_sha256 retains136.175 records both; exact planned invocation/provenance match remainsfalse. Original174 plan/result are preserved.',
        '174 v4 test failure reporting does not guard repr/add_note failure. Its successful N0 run did not enter that branch. Future test5 changes only handler reporting, validated by five AST faults/success tests; no second Job.',
        '179 logic5passed but entry failed because no tmp_path created its --basetemp; nonzero/cleanup-read failure retained.180 adds per-case tmp artifacts and entry exits0.'],
    actual_evidence=['174 literaltrue/public v6 invocation,8external retention5/3 heads,4full28fresh64contexts,17phase segments closed,producer/constructor records retired,entry restored,10locks released.',
        '176 original numerical oracle matches174 actual candidate audit; independent observation, same scientific algorithm family.',
        '177 actual constructor/inspect each has independent source-bound scope:4full12fresh32contexts each; complete pending_post_N/close,154 saved file names andbytes unchanged.',
        'No new Jobs in176/177/180; source6/owned6/verifier5 bytes unchanged from173.'],
    acceptance=['Verify source/plan/result/archive hashes and actual invocation/heads/receipt/closure evidence.',
        'Preserve plan metadata exception and failed179 evidence; distinguish fixed future template from immutable successful174 v4.',
        'Scope findings only; no official verdict/receipt,production seal,formal/resource/native or full-chain gate.'],
    open=['Roster5 authenticated consumer/callback borrow integration and three independent arms.',
        'Connected typed Common/Genesis/Parent/Handoff/paired/Post/reopen and whole performance/resource budget.',
        'Separate formal readiness and formal-run authority.'],
    production_seal=False,official_review=False,review_receipt=False,full_optimized_workflow_accepted=False,
    whole_workflow_performance_review_complete=False,formal_execution_ready=False,formal_run_authority=False,
    formal_result=False,resource_admission=False,native_execution_authorized=False,
    files_sha256={str(p):sha256(p.read_bytes()).hexdigest() for p in sorted(paths,key=str)})
out=D/'bootstrap6_postchecks_pre_seal_input_181.json'
with out.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(path=str(out),sha256=sha256(out.read_bytes()).hexdigest(),pins=len(paths),primary_test_cases=len(units))))
