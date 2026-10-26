"""Current Source42 unit verification; no actual cold closure claim."""
import time
STARTED=time.perf_counter()
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3]
spec=importlib.util.spec_from_file_location('frozen_diagnostic_capture',OUT/'capture.py');parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
raw=parent.raw;pin=parent.pin;names=parent.names
admission_raw=(OUT/'regression_admission.json').read_bytes();admission=json.loads(admission_raw)
assert names(ROOT/n for n in admission['preserved'])==admission['preserved']
before_source=parent.sources();before_helpers=names(ROOT/n for n in admission['helper_pins']);assert before_helpers==admission['helper_pins']
before_fixed=pin(raw(admission['preserved']));prior=parent.records();spent={k:sum(r['charged_seconds'] for r in prior.values() if r['kind']==k) for k in ('static','pytest')}
cap=15.;assert spent['pytest']+cap<=420 and sum(spent.values())+cap<=540
assert before_source==admission['source_pins']
for n in {*before_source,*before_helpers}:parent.snapshot((ROOT/n).read_bytes())
parent.storage(3,500000)
controls={(OUT/'regression_admission.json').relative_to(ROOT).as_posix():pin(admission_raw)}
preparation=time.perf_counter()-STARTED;timeout=cap-1.5-preparation
argv=[sys.executable,'-B',str(OUT/'pytest_regression.py'),'regression_admission.json','pytest_regression'];started=time.perf_counter()
if timeout>0:code,stdout,stderr,error,state=parent.capture.spawn_and_drain(argv,timeout)
else:code,stdout,stderr,error,state=None,b'',b'','preparation_exhausted_no_child',None
target_seconds=time.perf_counter()-started
harness_path=OUT/'pytest_regression.harness.json'
produced=names([harness_path]) if harness_path.exists() else {}
missing=[] if produced else [harness_path.relative_to(ROOT).as_posix()]
after_source=parent.sources();after_helpers=names(ROOT/n for n in before_helpers);after_fixed=pin(raw(names(ROOT/n for n in admission['preserved'])));after_controls=names(ROOT/n for n in controls)
post_ok=before_source==after_source and before_helpers==after_helpers and before_fixed==after_fixed and controls==after_controls and names(ROOT/n for n in admission['preserved'])==admission['preserved']
charged=time.perf_counter()-STARTED+.5
value=dict(authority='DRAFT_NONAUTHORITATIVE',label='pytest_regression',kind='pytest',argv=argv,returncode=code,error=error,
    accepted=error is None and code==0 and not missing and post_ok and charged<=cap,component_acceptance=False,
    child_artifact_pins=produced,missing_child_artifacts=missing,source_pins=before_source,after_source_pins=after_source,
    helper_pins=before_helpers,after_helper_pins=after_helpers,controls_pins=controls,after_controls_pins=after_controls,
    postcheck_pins_match=post_ok,fixed_before=before_fixed,fixed_after=after_fixed,source_epoch=sha256(raw(before_source)).hexdigest(),
    stdout_pin=pin(stdout),stderr_pin=pin(stderr),bounded_drain=state,charged_seconds=charged,tail_reserve_seconds=.5,
    preparation_seconds=preparation,target_seconds=target_seconds,target_timeout_seconds=timeout,cap_seconds=cap,
    prior_record_pins={n:pin((ROOT/n).read_bytes()) for n in prior},previous_charged_seconds=spent,
    actual_F=False,scientific_evidence_adopted=False,resource_admission=False,formal_result=False)
payload=raw(value);parent.storage(3,len(stdout)+len(stderr)+len(payload))
for suffix,data in (('stdout.log',stdout),('stderr.log',stderr),('exit.json',payload)):
    with (OUT/('pytest_regression.'+suffix)).open('xb') as stream:stream.write(data)
print(json.dumps(dict(accepted=value['accepted'],component_acceptance=False,returncode=code,charged_seconds=charged),sort_keys=True))
if not value['accepted']:raise SystemExit(1)
