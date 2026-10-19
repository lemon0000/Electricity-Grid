"""Same saved four-build program, measuring only existing path-helper composition."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
D = HERE/'whole_workflow_optimization_01_non_authoritative'
previous = D/'saved137_n0_operation_diagnostic_plan_146.json'
value = json.loads(previous.read_bytes())
paths = {Path(p) for p in value['files_sha256']}
paths.update((Path(__file__), HERE/'run_unit_entry_v6.py', HERE/'run_unit_bounded_v19.py',
    HERE/'build_path_unit_entry_v6.py', ROOT/'tests/test_h1_canonical_path_unit_entry_development_v6.py'))
unit_path = HERE/'canonical_path_entry6_units_147/terminal.json'
unit = json.loads(unit_path.read_bytes())
assert unit['exit_code']==0 and unit['source_unchanged'] and unit['observed_owned_processes_absent']
base = Path('D:/h1_saved137_path_148_non_authoritative')
label = 'saved137_path_profile_148'
assert not base.exists() and not (HERE/label).exists()
value.update(schema='h1_saved137_path_diagnostic_plan_148',
    at_utc=datetime.now(timezone.utc).isoformat(),
    predecessor_plan_sha256=sha256(previous.read_bytes()).hexdigest(),
    command=[sys.executable,'-B',str(HERE/'run_unit_bounded_v19.py'),label,'180','1024','128','--',
        str(HERE/'run_unit_entry_v6.py'),'-s','-p','no:faulthandler','--basetemp',str(base),
        '--canonical-path-root','D:/h1_bootstrap5_n0_137_non_authoritative',
        'tests/test_h1_saved_n0_validation_operation_profile_development_v4.py'],
    question='Does the unchanged existing CanonicalPathLease reduce the saved verifier4 four-build read cost with identical science and counts?',
    optimization=dict(target='Only compose the existing path helper; entry4 body metadata resolver remains unchanged, no fixture scopes or new cached numerical results.',
        actual_baseline='146 complete,151.08s pytest /153.984s outer, prepare29.823+20.471+20.599+20.688s profiled. 101426 Path.stat and3486 episode_store._path per reused cycle.',
        invariants='Fresh leaf lstat and file bytes/stamps, per-call held-ancestor reparse/case attributes, original fallback for unsupported paths. Explicit REPO/testbase/saved137 roots,4096directory/16384path caps.',
        failure_semantics='entry6 records a failed resolver reader separately, preserves pytest body primary and returns nonzero;147 three child checks passed with all path/code/metadata resources restored.',
        whole_workflow_claim=False),
    entry6_units_terminal_sha256=sha256(unit_path.read_bytes()).hexdigest(),
    comparison='Same saved119 files and unchanged four-build cProfile test, same180s/1GiB/128MiB caps. Single fixed-order diagnostic comparison, not a repeated unprofiled speed estimate.',
    files_sha256={str(p):sha256(p.read_bytes()).hexdigest() for p in sorted(paths,key=str)})
target = D/'saved137_path_diagnostic_plan_148.json'
with target.open('x',encoding='utf-8',newline='\n') as stream:
    json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(path=str(target),sha256=sha256(target.read_bytes()).hexdigest(),pins=len(paths))))
