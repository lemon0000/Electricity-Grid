"""Bind support checks to the precise fault-worker bytes before a launch."""
from hashlib import sha256
import json
from pathlib import Path
import os
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
out=HERE/sys.argv[1]
out.mkdir()
paths=[HERE/'fault_worker_v1.py',HERE/'test_probe_support_v1.py',Path(__file__),
    HERE/'run_faults_v1.py',
    REPO/'experiments/h1_phase_historical_batch_development_v3.py',
    REPO/'experiments/h1_historical_parent_prefix_development_v1.py']
before={str(path):sha256(path.read_bytes()).hexdigest() for path in paths}
for path in paths:
    target=out/'tested_bytes'/path.relative_to(REPO)
    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(path.read_bytes())
command=[sys.executable,'-B','-m','pytest','-q','--disable-warnings',
    str(HERE/'test_probe_support_v1.py'),'--junitxml='+str(out/'pytest.xml')]
(out/'request.json').write_text(json.dumps(dict(command=command,source_before=before),indent=2)+'\n',encoding='utf-8')
began=time.perf_counter()
with (out/'stdout.txt').open('wb') as stdout,(out/'stderr.txt').open('wb') as stderr:
    result=subprocess.run(command,cwd=REPO,stdout=stdout,stderr=stderr,
        env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'))
after={str(path):sha256(path.read_bytes()).hexdigest() for path in paths}
terminal=dict(exit_code=result.returncode,outer_seconds=time.perf_counter()-began,
    source_before=before,source_after=after,changed=[name for name in before if before[name]!=after[name]],
    snapshots=len(paths),saved_Reader_invocations=0,new_normal_jobs=0,real_native_calls=0,formal_result=False)
(out/'terminal.json').write_text(json.dumps(terminal,indent=2)+'\n',encoding='utf-8')
print((out/'stdout.txt').read_text(encoding='utf-8'))
print(json.dumps(dict(exit_code=result.returncode,outer_seconds=terminal['outer_seconds'],changed=terminal['changed'])))
sys.exit(result.returncode if result.returncode else bool(terminal['changed']))
