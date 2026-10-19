"""Same saved oracle, now measure metadata reuse during heavy fixture setup."""
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent;D=HERE/'whole_workflow_optimization_01_non_authoritative'
old=D/'saved137_candidate_diagnostic_plan_138.json';value=json.loads(old.read_bytes())
paths={Path(p) for p in value['files_sha256']}
paths.update((HERE/'run_unit_bounded_v18.py',HERE/'run_unit_entry_v5.py',Path(__file__)))
base=Path('D:/h1_saved137_fixture_145_non_authoritative');label='saved137_fixture_metadata_145'
assert not base.exists() and not (HERE/label).exists()
value.update(schema='h1_saved137_fixture_diagnostic_plan_145',at_utc=datetime.now(timezone.utc).isoformat(),
    predecessor_plan_sha256=sha256(old.read_bytes()).hexdigest(),
    question='Do four heavy fixture-body resolver scopes actually hit the original fast path while preserving saved137 numerical audit and all cleanup?',
    command=[sys.executable,'-B',str(HERE/'run_unit_bounded_v18.py'),label,'120','1024','128','--',
        str(HERE/'run_unit_entry_v5.py'),'-s','-p','no:faulthandler','--basetemp',str(base),
        'tests/test_h1_saved_bootstrap5_n0_candidate_profile_development_v1.py'],
    files_sha256={str(p):sha256(p.read_bytes()).hexdigest() for p in sorted(paths,key=str)},
    entry_pre_seal_input_sha256=sha256((D/'fixture_metadata_entry5_pre_seal_input_144.json').read_bytes()).hexdigest(),
    expected_discovery_scopes='example/setup/numerical/prepared plus body; nested dynamic fixtures borrow rather than nest.',
    comparison='Same saved137119 files, same original cProfile oracle/test, same120s cap; entry changes only metadata observation windows and failed-receipt persistence. Profile time is not an unprofiled whole-workflow comparison.')
value['optimization']['target']='Cover previously unoptimized fixture metadata discovery using unchanged original resolver helper; no new permanent metadata cache or relaxed source freshness.'
value['optimization']['evidence']+='138 separate numerical observation passed83.50s test/86.484s outer, actual oracle28.093s, all119 candidates unchanged.143 four fixture-window cleanup/fallback tests passed.'
out=D/'saved137_fixture_diagnostic_plan_145.json'
with out.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(path=str(out),sha256=sha256(out.read_bytes()).hexdigest(),pins=len(paths))))
