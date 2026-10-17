"""Local synthetic validation recorder. Never invokes an experiment runner."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

root=Path(__file__).resolve().parents[3]
evidence=Path(__file__).resolve().parent
label=sys.argv[1]
attempt=evidence/label
attempt.mkdir(exist_ok=False)
files=[Path(row['successor']) for row in json.loads((evidence/'successor_origin.json').read_bytes())]
files+=list(Path('tests').glob('*h1*_*v2.py'))
files += [Path('experiments')/name for name in (
    'h1_historical_hour_witness_development_v1.py','h1_historical_n0_verifier_development_v1.py',
    'h1_phase_exact_source_current_development_v2.py','h1_phase_owner_development_v2.py',
    'h1_selector_phase_consumption_development_v2.py')]
files += [Path(__file__).resolve().relative_to(root)]
files += [Path('tests/test_h1_historical_hour_witness_development_v1.py')]
def hashes():return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
before=hashes()
snapshot=attempt/'tested_bytes';snapshot.mkdir()
for path in files:
    target=snapshot/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(path.read_bytes())
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',
    H1_E2E_TIMING_FILE=str(attempt/'timing.jsonl'))
command=[sys.executable,'-B','-m','pytest','-q','-s','-p','no:cacheprovider',
    '--basetemp',str(Path('D:/')/('h1_'+label+'_non_authoritative')), *sys.argv[2:]]
assert not Path(command[command.index('--basetemp')+1]).exists(), 'fresh basetemp required'
(attempt/'request.json').write_text(json.dumps(dict(command=command,before=before,formal_result=False),indent=2)+'\n',encoding='utf-8')
start=time.perf_counter()
with (attempt/'stdout.log').open('wb') as out,(attempt/'stderr.log').open('wb') as err:
    process=subprocess.Popen(command,cwd=root,env=env,stdout=out,stderr=err)
    (attempt/'started.json').write_text(json.dumps(dict(pid=process.pid),indent=2)+'\n',encoding='utf-8')
    code=process.wait()
result=dict(command=command,pid=process.pid,exit_code=code,elapsed_seconds=time.perf_counter()-start,
    before=before,after=hashes(),formal_result=False)
(attempt/'terminal.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:result[k] for k in ('exit_code','elapsed_seconds')}),flush=True)
sys.exit(code)
