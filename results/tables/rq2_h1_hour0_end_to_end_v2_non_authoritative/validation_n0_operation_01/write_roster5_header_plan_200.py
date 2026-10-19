"""Fix an eight-window empty-header diagnostic from current bytes and metadata."""
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

H=Path(__file__).resolve().parent;R=H.parents[3]
D=H/'whole_workflow_optimization_01_non_authoritative'
prior=D/'bootstrap6_live_header_plan_170.json'
# Reuse only the known dependency file set, never predecessor metadata scalars.
paths={Path(path) for path in json.loads(prior.read_bytes())['files_sha256']}
paths.update((R/'tests').glob('*h1*.py'));paths.update((R/'experiments').glob('h1_*.py'))
paths.update((Path(__file__),H/'archive_roster_evidence_200.py',H/'run_unit_entry_v6.py',H/'run_unit_bounded_v19.py'))
base=Path('D:/h1_roster5_header_200_non_authoritative');label='roster5_live_header_200'
assert not base.exists() and not (H/label).exists()
command=[sys.executable,'-B',str(H/'run_unit_bounded_v19.py'),label,'210','1024','128','--',
    str(H/'run_unit_entry_v6.py'),'-s','-p','no:faulthandler','--basetemp',str(base),
    'tests/test_h1_roster5_live_header_development_v1.py']
value=dict(schema='h1_roster5_live_header_plan_200',at_utc=datetime.now(timezone.utc).isoformat(),
    question='Do original Bootstrap7/Roster5 headers create, inspect, close and reopen with real phase and empty registry scopes?',
    source_modules=dict(bootstrap='experiments.h1_bootstrap_integration_development_v7',
        owned='experiments.h1_owned_bootstrap_controller_development_v7',
        roster='experiments.h1_group_execution_roster_development_v5',
        verifier='experiments.h1_historical_n0_verifier_development_v6',
        phase_binding='experiments.h1_phase_manifest_binding_development_v4',
        phase_kernel='experiments.h1_phase_dependency_validation_operation_development_v2',
        phase_operation='experiments.h1_phase_manifest_validation_operation_development_v2'),
    command=command,environment=dict(python=sys.executable,platform=sys.platform),
    task_DAG=['predefinition execution denial','typed configuration/profile/selector/archive',
        'Bootstrap7 create and inspect','Roster5 create and inspect','close both and release guards',
        'Bootstrap7 reopen and inspect from exact saved heads','Roster5 reopen and inspect from exact saved head',
        'close both','check detached receipts and released handles','persist terminal and source hashes'],
    counts=dict(attempts=1,bootstrap_owners=2,rosters=2,phase_windows=8,
        bootstrap_read_scopes=4,roster_read_scopes=6,numerical_roots=0,new_N0_Jobs=0,native_calls=0,
        callbacks=0,concurrency=1),
    reuse=dict(earlier_170_empty_header_seconds=90.078,earlier_136_six_window_seconds=97.031,
        current_199_protocol_cases=36,current_199_outer_seconds=57.094,
        dependency_file_set_source_sha256=sha256(prior.read_bytes()).hexdigest(),
        scientific_N0_replay_avoided=True,predecessor_scalar_metadata_inherited=False),
    optimization=dict(entry='code leases plus bounded canonical path and metadata leases',
        lifetime='current method phase bookends; each Roster route has a distinct scope',
        numerical_evidence_cache_across_methods=False,
        rationale='Exercise real metadata/guard/handle plumbing without repeating a saved synthetic N0 Job.',
        remaining_unknown=['numerical Roster public path','Common bridge and witness integration',
            'optimized full chain','resource budget and formal acceptance']),
    budget=dict(expected_seconds=[100,170],uncertainty='No prior exact eight-window successor measurement.',
        wall_seconds_cap=210,rss_bytes_cap=1024**3,storage_bytes_cap=128*1024**2,
        heartbeat='stdout stage trace plus bounded monitor observed PID/RSS/storage sampling',
        no_progress='before cap use stage trace and process samples; hard cap stops attempt',
        overrun='stop and retain terminal; no cap extension or unchanged retry',
        cleanup='bounded observer process cleanup plus original phase/registry close and guard release',
        saved_terminal='request/started/stdout/terminal, source snapshot, entry close receipt'),
    acceptance=['one pytest pass and zero execution denial calls','eight closed phase windows',
        'ten distinct closed empty registry scopes','no pending registry record',
        'inspection equality after exact-head reopen','original guards free and nonce absent',
        'all actual code/metadata/path/kernel handles closed','source hashes unchanged','observed owned PIDs absent'],
    files_sha256={str(path):sha256(path.read_bytes()).hexdigest() for path in sorted(paths,key=str)},
    whole_workflow_performance_review_complete=False,numerical_roster_read_accepted=False,
    full_optimized_workflow_accepted=False,production_seal=False,official_review=False,
    formal_execution_ready=False,formal_run_authority=False,formal_result=False,
    native_execution_authorized=False,resource_admission=False)
out=D/'roster5_live_header_plan_200.json'
with out.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(path=str(out),sha256=sha256(out.read_bytes()).hexdigest(),pins=len(paths),command=command)))
