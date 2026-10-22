"""Thirty-second support check; no source loads, Readers or solver calls."""
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]


def pin(path):return sha256(Path(path).read_bytes()).hexdigest()


def main():
    out=HERE/'observer_checks_01';out.mkdir()
    paths=[Path(__file__),HERE/'test_accounting_observer_v1.py',HERE/'packet_worker_v2.py',
        REPO/'experiments/h1_phase_historical_batch_development_v1.py']
    before={str(path):pin(path) for path in paths}
    tested=out/'tested_bytes';tested.mkdir()
    for path in paths:(tested/path.name).write_bytes(path.read_bytes())
    command=[sys.executable,'-B','-m','pytest','-q',str(HERE/'test_accounting_observer_v1.py'),
        '--junitxml='+str(out/'pytest.xml')]
    (out/'request.json').write_text(json.dumps(dict(command=command,timeout_seconds=30,source_before=before),indent=2)+'\n',encoding='utf-8')
    started=time.perf_counter();error=None;exit_code=None
    with (out/'stdout.txt').open('wb') as stdout,(out/'stderr.txt').open('wb') as stderr:
        try:
            result=subprocess.run(command,cwd=REPO,stdout=stdout,stderr=stderr,timeout=30,
                env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'))
            exit_code=result.returncode
        except subprocess.TimeoutExpired as caught:error=repr(caught)
    after={str(path):pin(path) for path in paths}
    terminal=dict(status='DRAFT_NONAUTHORITATIVE',exit_code=exit_code,error=error,
        outer_seconds=time.perf_counter()-started,source_before=before,source_after=after,
        changed=[name for name in before if before[name]!=after[name]],
        source_loader_invocations=0,model_builds=0,Reader_invocations=0,new_normal_jobs=0,
        real_native_solver_calls=0,formal_result=False)
    with (out/'terminal.json').open('x',encoding='utf-8') as stream:json.dump(terminal,stream,indent=2);stream.write('\n')
    print((out/'stdout.txt').read_text(encoding='utf-8'))
    print(json.dumps(dict(exit_code=exit_code,seconds=terminal['outer_seconds'],changed=terminal['changed'])))
    return 0 if exit_code==0 and not error and before==after else 1


if __name__=='__main__':raise SystemExit(main())
