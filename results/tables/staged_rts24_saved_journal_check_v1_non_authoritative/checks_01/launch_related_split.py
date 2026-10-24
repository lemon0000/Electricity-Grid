"""Run the two frozen, disjoint ordinary regression groups sequentially."""
import json
from pathlib import Path
import subprocess
import sys

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[3]
groups=json.loads((OUT/'related_split_nodes.json').read_bytes())
assert set(groups)=={'related_02a','related_02b'}
flat=[n for group in groups.values() for n in group]
assert len(flat)==len(set(flat))==24 and all(len(g)==12 for g in groups.values())
assert all(n.startswith('tests/test_staged_rts24_journal_v2.py::') for n in flat)
for label,nodes in groups.items():
    run=subprocess.run([sys.executable,'-B',str(OUT/'run_checks.py'),label,*nodes],cwd=ROOT,
        capture_output=True,timeout=105)
    (OUT/(label+'.launcher.stdout.log')).write_bytes(run.stdout)
    (OUT/(label+'.launcher.stderr.log')).write_bytes(run.stderr)
    record=json.loads((OUT/(label+'.exit.json')).read_bytes())
    print(json.dumps(dict(label=label,exit_code=record['exit_code'],wall_seconds=record['wall_seconds'])),flush=True)
    assert run.returncode==0 and record['exit_code']==0 and record['timed_out'] is False
