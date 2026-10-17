"""Serial counterbalanced comparisons of the fixed zero-native package."""
from hashlib import sha256
import json
from pathlib import Path
import statistics
import subprocess
import sys
from time import perf_counter

HERE=Path(__file__).resolve().parent
EXPECTED_LAUNCHER='13333f85abe556fbcfffe35c611149a937076de3422bde6c7f3b471f71242415'
EXPECTED_MANIFEST='0cd4511072ee11cc89a942b3eb76a3a91de4390ca1af5febe0981c216976a59a'
out=HERE/'current_entry_pair_01';out.mkdir(exist_ok=False)
assert sha256((HERE/'launch_validation.py').read_bytes()).hexdigest()==EXPECTED_LAUNCHER
assert sha256((HERE/'package_manifest_v1.json').read_bytes()).hexdigest()==EXPECTED_MANIFEST
order=[('plain','final'),('parse','final')]
request=dict(launcher_sha256=EXPECTED_LAUNCHER,manifest_sha256=EXPECTED_MANIFEST,
    serial_order=order,per_member_timeout_seconds=120,real_native_calls=0,formal_result=False)
(out/'request.json').write_text(json.dumps(request,indent=2),encoding='utf-8')
bootstrap="from hashlib import sha256;from pathlib import Path;import sys;p=Path(sys.argv.pop(1));pin=sys.argv.pop(1);raw=p.read_bytes();assert sha256(raw).hexdigest()==pin;sys.argv[0]=str(p);exec(compile(raw,str(p),'exec'),{'__name__':'__main__','__file__':str(p)})"
rows=[];start=perf_counter()
try:
    for mode,pair in order:
        label='fixed_pair_'+pair+'_'+mode
        completed=subprocess.run([sys.executable,'-B','-c',bootstrap,str(HERE/'launch_validation.py'),
            EXPECTED_LAUNCHER,'arm',mode,label],capture_output=True,timeout=120)
        (out/(label+'.stdout.log')).write_bytes(completed.stdout)
        (out/(label+'.stderr.log')).write_bytes(completed.stderr)
        terminal=json.loads((HERE/label/'terminal.json').read_bytes())
        if completed.returncode!=0 or terminal['exit_code']!=0:raise RuntimeError('member failed: '+label)
        assert terminal['candidate_bytes_unchanged'] and terminal['repository_test_closure_unchanged'] and terminal['repository_code_unchanged']
        rows.append(dict(label=label,mode=mode,pair=pair,arm_seconds=terminal['arm_seconds'],
            total_seconds=terminal['elapsed_seconds'],
            science_sha256=sha256((HERE/label/'scientific.json').read_bytes()).hexdigest(),
            full_audit_sha256=sha256((HERE/label/'audit.json').read_bytes()).hexdigest()))
        print(json.dumps(rows[-1]),flush=True)
    assert len({row['science_sha256'] for row in rows})==1
    assert len({row['full_audit_sha256'] for row in rows})==1
    plain=statistics.median(row['arm_seconds'] for row in rows if row['mode']=='plain')
    parsed=statistics.median(row['arm_seconds'] for row in rows if row['mode']=='parse')
    terminal=dict(exit_code=0,rows=rows,plain_median_seconds=plain,parse_median_seconds=parsed,
        reduction_percent=100*(plain-parsed)/plain,science_and_full_audit_equal=True,
        full_chain_passed=False,formal_result=False)
except BaseException as error:
    terminal=dict(exit_code=1,rows=rows,error=repr(error),full_chain_passed=False,formal_result=False)
terminal['elapsed_seconds']=perf_counter()-start
(out/'terminal.json').write_text(json.dumps(terminal,indent=2),encoding='utf-8')
print(json.dumps(terminal),flush=True)
sys.exit(terminal['exit_code'])
