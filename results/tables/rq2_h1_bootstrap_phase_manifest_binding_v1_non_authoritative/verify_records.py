"""Read back completed development evidence and frozen predecessors."""
from pathlib import Path
import hashlib
import json
import subprocess

p=Path(__file__).parent
def sha(f):return hashlib.sha256(Path(f).read_bytes()).hexdigest()
def read(f):return json.loads(Path(f).read_text(encoding='utf-8'))
checks=read(p/'development_checks.json')
drift=[f for f,h in checks['files_sha256'].items() if not Path(f).is_file() or sha(f)!=h]
evidence_drift=[f for f,h in checks['evidence_sha256'].items() if sha(p/f)!=h]
trace=read(p/'append_trace_01.json')
assert trace['development_checks_sha256']==sha(p/'development_checks.json')
assert sha(trace['draft_state_path'])==trace['draft_state_sha256']
assert all(sha(f)==v['sha256']==sha(v['snapshot']) for f,v in checks['reviewed_open_assembly'].items())
assert all(sha(x['path'])==x['after_sha256'] for x in trace['documents'])
frozen={}
retained=read(p/'frozen_retention_01.json')['frozen']
for n in (2,3):
    outer=Path(f'configs/rq2_normal_h1_calibration_v{n}.OUTER.SHA256SUMS.json')
    assert sha(outer)==retained[str(n)]['outer_sha256']
    data=read(outer)
    bad=[f for f,h in data['members'].items() if not Path(f).is_file() or sha(f)!=h]
    old=read(f'results/tables/rq2_normal_h1_full_job_v{n}_non_authoritative/calibration_v{n}.postrun_inventory.json')
    run_bad=[f for f,v in old['members'].items() if not (Path(old['root'])/f).is_file()
        or sha(Path(old['root'])/f)!=v['sha256'] or (Path(old['root'])/f).stat().st_size!=v['bytes']]
    frozen[str(n)]=dict(outer_sha256=sha(outer),members=len(data['members']),member_drift=bad,
                        run_files=len(old['members']),run_drift=run_bad)
diff=subprocess.run(['git','diff','--check'],capture_output=True,text=True)
status=subprocess.run(['git','status','--porcelain'],capture_output=True,text=True)
result=dict(pin_count=len(checks['files_sha256']),pin_drift=drift,
    evidence_count=len(checks['evidence_sha256']),evidence_drift=evidence_drift,
    reviewed_open_assembly_unchanged=True,documents_verified=True,draft_state_verified=True,
    frozen=frozen,git_diff_check_exit_code=diff.returncode,
    git_diff_check_output=diff.stdout+diff.stderr,git_status_exit_code=status.returncode,
    git_status_entries=len(status.stdout.splitlines()),formal_result=False,formal_execution_ready=False)
with (p/'final_verification_01.json').open('x',encoding='utf-8') as out:json.dump(result,out,indent=2)
print(json.dumps(result))
assert not drift and not evidence_drift and diff.returncode==status.returncode==0
assert all(not x['member_drift'] and not x['run_drift'] for x in frozen.values())
