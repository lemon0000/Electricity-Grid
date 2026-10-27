"""Preserve a semantically equivalent candidate with no actual-ENTRY hash benefit."""
import base64
from hashlib import sha256
import json
from pathlib import Path
import time
OUT=Path(__file__).absolute().parent
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def main():
    started=time.perf_counter();reg=json.loads((OUT/'registration.json').read_bytes());row=json.loads((OUT/'unittest.exit.json').read_bytes());report=json.loads((OUT/'unittest_report.json').read_bytes())
    assert not row['accepted'] and row['streams']['returncode']==1 and row['streams']['error'] is None
    raw=base64.b64decode(row['streams']['stderr_raw_base64'],validate=True);assert pin(raw)==row['streams']['stderr_pin']
    assert b'696 not less than 696' in raw and report['tests_run']==34 and report['failures']==1 and report['errors']==report['skipped']==0
    assert row['streams']['process_observation']['handle_closed'] and not row['streams']['process_observation']['cleanup']
    for path,value in reg['input_pins'].items():assert pin(Path(path).read_bytes())==value,path
    for path,encoded in json.loads((OUT/'helper_snapshots.json').read_bytes()).items():assert base64.b64decode(encoded,validate=True)==Path(path).read_bytes()
    elapsed=time.perf_counter()-started;assert elapsed<=2
    cumulative={**row['all_cumulative_charged_seconds']};cumulative['static']+=elapsed
    result=dict(authority='DRAFT_NONAUTHORITATIVE',accepted=True,acceptance_scope='failure_preservation_and_cost_decision_only',kind='static',charged_seconds=elapsed,cap_seconds=2,
        candidate_adopted=False,cold_launch_admitted=False,actual_entry_old_hash_calls=696,actual_entry_new_hash_calls=696,
        actual_count_source='captured failing assert after the old/new image and objects checks',unit_complete=34,unit_failures=1,unit_errors=0,synthetic_shared_dag_hash_calls=[5,3],
        unit_exit_pin=pin((OUT/'unittest.exit.json').read_bytes()),raw_stderr_pin=pin(raw),source_epoch=reg['source_epoch'],
        prior_not_accepted_count=21,all_cumulative_charged_seconds=cumulative,actual_F=False,run_authority=False,formal_result=False,resource_admission=False)
    with (OUT/'rejection_snapshot.json').open('xb') as f:f.write(canonical(result))
    print(canonical(dict(accepted=True,candidate_adopted=False,charge=elapsed,cumulative=cumulative)).decode())
if __name__=='__main__':main()
