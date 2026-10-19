"""Zero-execution numerical postcheck of152 saved controller bytes."""
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
D=HERE/'whole_workflow_optimization_01_non_authoritative'
old_path=D/'saved137_candidate_diagnostic_plan_138.json';value=json.loads(old_path.read_bytes())
old_root=Path('D:/h1_bootstrap5_n0_137_non_authoritative/nt_non_authoritative')
paths={Path(p) for p in value['files_sha256'] if not Path(p).is_relative_to(old_root)}
result_path=D/'bootstrap5_retained_n0_bounded_result_152.json';result=json.loads(result_path.read_bytes())
saved_root=Path('D:/h1_bootstrap5_retained_152_non_authoritative/nt_non_authoritative')
saved=[Path(row['source']) for row in result['archive_files'] if Path(row['source']).is_relative_to(saved_root)]
assert len(saved)==119 and len(result['externally_persisted_retention_records'])==8
assert result['terminal']['observed_owned_processes_absent'] and not result['terminal']['cleanup_errors']
paths.update(saved);paths.update((ROOT/'tests').glob('*h1*.py'))
paths.update((Path(__file__),HERE/'run_unit_entry_v6.py',HERE/'run_unit_bounded_v19.py'))
base=Path('D:/h1_saved152_oracle_153_non_authoritative');label='saved152_numerical_oracle_153'
assert not base.exists() and not (HERE/label).exists()
value.update(schema='h1_saved152_numerical_postcheck_plan_153',
    at_utc=datetime.now(timezone.utc).isoformat(),predecessor_plan_sha256=sha256(old_path.read_bytes()).hexdigest(),
    candidate_result_sha256=sha256(result_path.read_bytes()).hexdigest(),
    command=[sys.executable,'-B',str(HERE/'run_unit_bounded_v19.py'),label,'120','1024','128','--',
        str(HERE/'run_unit_entry_v6.py'),'-s','-p','no:faulthandler','--basetemp',str(base),
        '--canonical-path-root','D:/h1_bootstrap5_retained_152_non_authoritative',
        'tests/test_h1_saved_retained_n0_candidate_profile_development_v1.py'],
    question='Does the original numerical oracle match152 saved candidate without another Job or public owner?',
    candidate_files=len(saved),files_sha256={str(p):sha256(p.read_bytes()).hexdigest() for p in sorted(paths,key=str)})
value['optimization'].update(evidence='152 stopped at300.25s, all8 callback heads externally saved. Synthetic Job exited0/quiet49.281s,119files/1364source pins unchanged,10locks released. Public return still missing.',
    target='Reuse152 saved Job/controller for the same original numerical postcheck as138; unchanged entry6 path composition and original per-body resolver.',
    reuse='No public owner or new Job. External retention records are preserved; this numerical-only test does not authenticate an owner or adopt any suffix.')
value['budget'].update(basis='138 same numerical program83.50s test/86.484s outer;148 whole four-build diagnostic134.75s outer. One old oracle only,120s cap unchanged.',
    heartbeat='Fixture JSON and numerical oracle result; monitor PID+creation/RSS/storage. No automatic retry or extension.')
target=D/'saved152_numerical_postcheck_plan_153.json'
with target.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(path=str(target),sha256=sha256(target.read_bytes()).hexdigest(),pins=len(paths))))
