"""Fixed zero-execution saved-candidate diagnostic, preserving137 input bytes."""
from datetime import datetime,timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
D=HERE/'whole_workflow_optimization_01_non_authoritative'
old=json.loads((D/'bootstrap5_n0_bounded_plan_137.json').read_bytes())
paths={Path(name) for name in old['files_sha256']};paths.add(Path(__file__))
paths.update((ROOT/'tests').glob('*h1*.py'))
saved=Path('D:/h1_bootstrap5_n0_137_non_authoritative/nt_non_authoritative')
pending=[saved];candidate_paths=[]
while pending:
    directory=pending.pop()
    for row in os.scandir(directory):
        info=row.stat(follow_symlinks=False);assert not info.st_file_attributes&0x400
        if row.is_dir(follow_symlinks=False):
            if row.name!='scratch_non_authoritative':pending.append(Path(row.path))
        else:candidate_paths.append(Path(row.path))
    assert len(candidate_paths)<=1024
assert sum(p.stat().st_size for p in candidate_paths)<128*1024**2
paths.update(candidate_paths)
base=Path('D:/h1_saved137_oracle_138_non_authoritative');label='saved137_numerical_oracle_138'
assert not base.exists() and not (HERE/label).exists()
value=dict(schema='h1_saved137_candidate_diagnostic_plan_138',status='BOUNDED_DIAGNOSTIC_PLAN_NONAUTHORITATIVE',
    risk='R3',at_utc=datetime.now(timezone.utc).isoformat(),
    command=[sys.executable,'-B',str(HERE/'run_unit_bounded_v17.py'),label,'120','1024','128','--',
        str(HERE/'run_unit_entry_v4.py'),'-s','-p','no:faulthandler','--basetemp',str(base),
        'tests/test_h1_saved_bootstrap5_n0_candidate_profile_development_v1.py'],
    question='Can the saved137 controller numerical candidate match the predecessor oracle, and what remaining reader CPU cost dominates?',
    scale=dict(public_owners=0,new_N0_Jobs=0,native_calls=0,saved_candidates=1,
        predecessor_oracles=1,concurrency=1,retries=0),
    dag=['Recreate only explicit synthetic input/source seams in a fresh temporary fixture; do not create a Bootstrap owner or run a Job.',
        'Read one saved local normal_terminal row only as untrusted candidate data; compare lexical controller path.',
        'Run original predecessor numerical oracle against saved controller binding/terminal under solver_calls_forbidden, with cProfile.',
        'Require full audit payload hash equal to the candidate row; save profile and data-only limitations.',
        'Close entry code/metadata/resolver, verify saved candidate and source hashes, observed PIDs and artifacts.'],
    optimization=dict(evidence='137 Job exit0/quiet51.125s and8 retentions; public return/oracle/close/JUnit missing at300.453s. Its10 locks released and1355pins unchanged.',
        reuse='Reuse saved controller and Job bytes; no new source Job, no suffix adoption, no owner resume without external retained heads.',
        target='Profile actual saved numerical reader before selecting full entry14 static-input/repair/canonical-path composition.',
        limitations='137 journal head authority is unavailable. Numerical candidate equality cannot authenticate a registered owner or complete the missing public return.'),
    budget=dict(wall_seconds=120,sampled_rss_bytes=1024**3,observed_storage_bytes=128*1024**2,
        basis='One original oracle only; existing fixture setup35s in137. Actual reader cost is unknown and is the measured question.',
        heartbeat='Fixture/import and final oracle JSON, monitor PID+creation/RSS/storage. Fixed120s cap, no extension or retry.',
        stop='Preserve exact observed-process cleanup and all failed output on any cap/observer/error.'),
    candidate_files=len(candidate_paths),scratch_contents_enumerated=False,
    acceptance=['exit0, complete predecessor numerical audit equals local candidate SHA',
        'all pinned saved files unchanged; no owner credentials or new Jobs; aliases/handles clean, observed PIDs absent',
        'profile is attribution only; registered/public/whole-workflow/formal gates remain open'],
    files_sha256={str(p):sha256(p.read_bytes()).hexdigest() for p in sorted(paths,key=str)},
    bounded_diagnostic_self_review_complete=True,whole_workflow_performance_review_complete=False,
    full_optimized_workflow_accepted=False,formal_result=False,formal_execution_ready=False,
    resource_admission=False,native_execution_authorized=False)
out=D/'saved137_candidate_diagnostic_plan_138.json'
with out.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(path=str(out),sha256=sha256(out.read_bytes()).hexdigest(),candidate_files=len(candidate_paths))))
