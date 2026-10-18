"""One admission wrapper: bind the exact input postcheck before the old monitor."""
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
plan_pin,pre_pin=sys.argv[1:]
raw=(HERE/'source_reader_input_postcheck_plan_01.json').read_bytes()
if sha256(raw).hexdigest()!=plan_pin:raise ValueError('fixed additive plan differs')
plan=json.loads(raw)
for name,pin in plan['implementation_sha256'].items():
    if sha256(Path(name).read_bytes()).hexdigest()!=pin:raise ValueError('fixed wrapper or diagnostic differs')
pre_raw=(HERE/'source_reader_input_postcheck_01_baseline_non_authoritative/terminal.json').read_bytes()
pre=json.loads(pre_raw)
if (sha256(pre_raw).hexdigest()!=pre_pin or pre['exit_code']!=0 or pre['phase']!='baseline'
        or pre['plan_sha256']!=plan_pin or pre['relative_files_sha256']!=plan['relative_files_sha256']
        or pre['regular_input_files']!=134 or pre['locked_and_released']!=plan['relative_locks']):
    raise ValueError('exact successful pre-candidate input check required')
out=HERE/'candidate_after_input_postcheck_01_non_authoritative';out.mkdir(exist_ok=False)
command=[sys.executable,'-B',str(HERE/'run_fresh_source_reader_bounded_v1.py'),'candidate',plan['candidate_plan_sha256']]
with (out/'request.json').open('x',encoding='utf-8') as stream:
    json.dump(dict(plan_sha256=plan_pin,pre_input_postcheck_sha256=pre_pin,
        command=command,formal_result=False,resource_admission=False),stream,indent=2)
status=subprocess.run(command,cwd=HERE.parents[3]).returncode
with (out/'terminal.json').open('x',encoding='utf-8') as stream:
    json.dump(dict(exit_code=status,pre_input_postcheck_sha256=pre_pin,formal_result=False),stream,indent=2)
raise SystemExit(status)
