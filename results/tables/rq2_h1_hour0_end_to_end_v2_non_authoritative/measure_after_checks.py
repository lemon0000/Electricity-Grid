"""Wait for the current scoped regression terminal, then measure serially."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

E=Path(__file__).resolve().parent
terminal=E/'exact_source_routing_checks_02/terminal.json'
start=time.monotonic()
print('Waiting for scoped regression terminal before serial timing',flush=True)
while not terminal.exists():
    if time.monotonic()-start>7200:raise TimeoutError('Measurement observer deadline; tests left untouched')
    time.sleep(2)
for trial in range(30):
    try:
        checked=json.loads(terminal.read_bytes());break
    except json.JSONDecodeError:
        if trial==29:raise
        time.sleep(1)
assert checked['exit_code']==0 and checked['before']==checked['after']
assert all(hashlib.sha256((E.parents[2]/name).read_bytes()).hexdigest()==pin
           for name,pin in checked['after'].items())
print('Regression exit0 and current source pins verified; starting serial timing',flush=True)
sys.exit(subprocess.run([sys.executable,'-B',str(E/'measure_exact_source_pairs.py'),
                        'exact_source_timing_pairs_02'],timeout=1900).returncode)
