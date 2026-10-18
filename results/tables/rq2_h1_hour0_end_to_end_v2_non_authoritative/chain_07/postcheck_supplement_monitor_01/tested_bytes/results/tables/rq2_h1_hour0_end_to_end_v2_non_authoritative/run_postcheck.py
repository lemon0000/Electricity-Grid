"""External byte-pinned launcher for a completed synthetic chain postcheck."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

evidence=Path(__file__).resolve().parent
root=evidence.parents[2]
label=sys.argv[1]
entry=evidence/'postcheck_complete.py'
def pin(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):
    with path.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
terminal=json.loads((evidence/label/'terminal.json').read_bytes())
assert terminal['exit_code']==0
launch=evidence/label/'postcheck_launch'
launch.mkdir(exist_ok=False)
pygments_file=Path(importlib.util.find_spec('pygments').origin).resolve()
before={str(path):pin(path) for path in (Path(__file__),entry,evidence/'replay_saved_with_fixture_v1.py',
    evidence/'preservation_check_02.json',
    root/'results/tables/rq2_v2_obligation_manifest_v1_non_authoritative/obligation_manifest_v2_final.json',
    root/'tests/h1_hour0_saved_replay_v2.py',*sorted(pygments_file.parent.rglob('*.py')))}
bootstrap=('import sys,runpy,importlib.util;'
    f'spec=importlib.util.spec_from_file_location("pygments",{str(pygments_file)!r},submodule_search_locations=[{str(pygments_file.parent)!r}]);'
    'module=importlib.util.module_from_spec(spec);sys.modules["pygments"]=module;spec.loader.exec_module(module);'
    f'sys.argv=[{str(entry)!r},{label!r}];runpy.run_path({str(entry)!r},run_name="__main__")')
command=[sys.executable,'-I','-B','-c',bootstrap]
save(launch/'request.json',dict(command=command,files_sha256=before,formal_result=False))
start=time.perf_counter()
with (launch/'stdout.log').open('xb') as out,(launch/'stderr.log').open('xb') as err:
    process=subprocess.Popen(command,cwd=root,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),stdout=out,stderr=err)
    save(launch/'started.json',dict(pid=process.pid))
    code=process.wait()
after={name:pin(Path(name)) for name in before}
result=dict(exit_code=code,pid=process.pid,elapsed_seconds=time.perf_counter()-start,
    files_sha256_before=before,files_sha256_after=after,unchanged=before==after,formal_result=False)
save(launch/'terminal.json',result)
print(json.dumps(result),flush=True)
assert before==after
sys.exit(code)
