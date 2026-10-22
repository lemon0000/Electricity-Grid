"""Verify both exact programs reject optimized Python before their work."""
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
    out=HERE/'optimization_guard_02';out.mkdir()
    paths=[Path(__file__),HERE/'packet_worker_v2.py',HERE/'run_packet_v2.py']
    before={str(path):pin(path) for path in paths}
    tested=out/'tested_bytes';tested.mkdir()
    for path in paths:(tested/path.name).write_bytes(path.read_bytes())
    rows=[];started=time.perf_counter()
    for path in paths[1:]:
        command=[sys.executable,'-O','-B',str(path)]
        result=subprocess.run(command,cwd=REPO,capture_output=True,timeout=5,
            env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'))
        (out/(path.stem+'.stdout.txt')).write_bytes(result.stdout)
        (out/(path.stem+'.stderr.txt')).write_bytes(result.stderr)
        assert result.returncode!=0 and b'diagnostic requires enabled Python assertions' in result.stderr
        rows.append(dict(command=command,exit_code=result.returncode,expected_refusal=True))
    after={str(path):pin(path) for path in paths};assert before==after
    terminal=dict(status='DRAFT_NONAUTHORITATIVE',exit_code=0,checks=rows,checks_passed=2,
        source_before=before,source_after=after,elapsed_seconds=time.perf_counter()-started,
        project_source_loader_invocations=0,Reader_invocations=0,model_builds=0,
        new_normal_jobs=0,real_native_solver_calls=0,formal_result=False)
    with (out/'terminal.json').open('x',encoding='utf-8') as stream:json.dump(terminal,stream,indent=2);stream.write('\n')
    print(json.dumps(dict(checks_passed=2,seconds=terminal['elapsed_seconds'],sources_unchanged=True)))


if __name__=='__main__':main()
