"""Retain exact development test bytes and terminal status for each invocation."""
from pathlib import Path
from hashlib import sha256
import json
import os
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
label=sys.argv[1]
if not label.replace('_','').isalnum():raise ValueError('fresh label required')
out=HERE/label
out.mkdir()
tests=[
    'tests/test_h1_source_post_validation_development_v3.py',
    'tests/test_h1_constructor_inspection_capture_development_v1.py',
    'tests/test_h1_constructor_rejection_support_development_v1.py',
    'tests/test_h1_source_callable_gap_development_v1.py',
]
paths=[Path(__file__),*map(lambda name:REPO/name,tests)]
paths += [REPO/name for name in (
    'experiments/h1_constructor_runtime_guard_development_v1.py',
    'experiments/h1_phase_historical_batch_development_v3.py',
    'experiments/h1_phase_exact_source_batch_development_v3.py',
    'experiments/h1_constructor_source_batch_validation_development_v2.py',
    'experiments/h1_phase_historical_batch_development_v2.py',
    'experiments/h1_phase_historical_batch_development_v1.py',
    'experiments/h1_constructor_inspection_capture_development_v1.py',
    'experiments/h1_constructor_rejection_support_development_v1.py',
    'src/rq2_joint_deliverability_boundary_v1/continuous_grid_normal.py',
    'src/rq2_joint_deliverability_boundary_v1/normal_h1_source.py',
    'tests/test_rq2_normal_h1_source_v1.py',
    'tests/test_rq2_normal_h1_hour_archive_v1.py',
    'tests/test_rq2_continuous_grid_normal_v1.py',
)]
before={str(path):sha256(path.read_bytes()).hexdigest() for path in paths}
for path in paths:
    target=out/'tested_bytes'/path.relative_to(REPO)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(path.read_bytes())
command=[sys.executable,'-B','-m','pytest','-q','--disable-warnings',*tests,'--junitxml='+str(out/'pytest.xml')]
(out/'request.json').write_text(json.dumps(dict(command=command,source_before=before,
    status='DRAFT_NONAUTHORITATIVE',new_normal_jobs=0,real_native_calls=0),indent=2)+'\n',encoding='utf-8')
began=time.perf_counter()
with (out/'stdout.txt').open('wb') as stdout,(out/'stderr.txt').open('wb') as stderr:
    result=subprocess.run(command,cwd=REPO,stdout=stdout,stderr=stderr,
        env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'))
after={str(path):sha256(path.read_bytes()).hexdigest() for path in paths}
terminal=dict(exit_code=result.returncode,outer_seconds=time.perf_counter()-began,
    source_before=before,source_after=after,changed=[name for name in before if before[name]!=after[name]],
    snapshots=len(paths),new_normal_jobs=0,real_native_calls=0,formal_result=False)
(out/'terminal.json').write_text(json.dumps(terminal,indent=2)+'\n',encoding='utf-8')
print(json.dumps({key:terminal[key] for key in ('exit_code','outer_seconds','changed','snapshots')}))
print((out/'stdout.txt').read_text(encoding='utf-8')[-12000:])
sys.exit(result.returncode if result.returncode else bool(terminal['changed']))
