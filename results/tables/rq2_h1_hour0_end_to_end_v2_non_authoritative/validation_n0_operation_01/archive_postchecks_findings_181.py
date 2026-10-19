"""Record the independent non-authoritative audit of actual saved evidence."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

H=Path(__file__).resolve().parent
D=H/'whole_workflow_optimization_01_non_authoritative'
source=D/'bootstrap6_postchecks_pre_seal_input_181.json'
assert sha256(source.read_bytes()).hexdigest()=='b9e73d12642c1e7a276cc129c585399de23ea5627ca03c5565b5461033314330'
inputs=json.loads(source.read_bytes())
for name,pin in inputs['files_sha256'].items():
    assert sha256(Path(name).read_bytes()).hexdigest()==pin,name
value=dict(schema='h1_bootstrap6_postchecks_scoped_findings_181',
    status='NONAUTHORITATIVE_SCOPED_FINDINGS_RECORDED',reviewer='public_phase_review_118',
    at_utc=datetime.now(timezone.utc).isoformat(),input_sha256=sha256(source.read_bytes()).hexdigest(),
    provenance='Sole-writer transcription of final independent read-only PRE_SEAL findings; not an official review receipt.',
    additional_material_P1_P2_findings=[],
    evidence=dict(input_pins_verified=len(inputs['files_sha256']),producer_archive_files=139,
        oracle_archive_files=4,readonly_reopen_archive_files=5,
        actual_Bootstrap6_public_return_receipt_close_verified=True,
        original_saved_oracle_verified=True,readonly_numerical_constructor_inspect_close_verified=True,
        saved_file_names_and_bytes_unchanged_per_postcheck=154,
        successor_test_handler_cases=5),
    preserved_exceptions=[
        '174 invocation.module remains v5; its current_header_result_sha256 remains old136. Actual source/import/command/JUnit/return are v6.',
        'Exact planned invocation metadata and all plan provenance fields do not match;175 records both exceptions without rewriting174.',
        '174 v4 failure-reporting handler remains unchanged. Future test v5 guards secondary repr/add_note;180 validates five cases, no second N0.',
        '179 five test bodies passed but the outer entry failed because the base directory was absent. Its nonzero evidence is retained.'],
    boundaries=[
        '176 is an independent numerical observation in the original scientific algorithm family.',
        '177 exercises one Bootstrap6 owner lifecycle, not three independent arms or the whole optimized chain.',
        'No official verdict, review receipt, production seal, formal result or run authority is supplied.'],
    exact_planned_invocation_metadata_matched=False,all_plan_provenance_fields_current=False,
    full_optimized_workflow_accepted=False,whole_workflow_performance_review_complete=False,
    production_seal=False,official_review=False,review_receipt=False,
    formal_execution_ready=False,formal_run_authority=False,formal_result=False,
    resource_admission=False,native_execution_authorized=False)
target=D/'bootstrap6_postchecks_scoped_findings_181.json'
with target.open('x',encoding='utf-8',newline='\n') as stream:
    json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(path=str(target),sha256=sha256(target.read_bytes()).hexdigest(),pins=len(inputs['files_sha256']))))
