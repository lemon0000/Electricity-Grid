"""Small independent diagnostic archive, not a production import-policy verdict."""
import time
STARTED=time.perf_counter()
from hashlib import sha256
import json
from pathlib import Path
OUT=Path(__file__).resolve().parent;BASE=OUT.parent;ROOT=BASE.parents[2]
def raw(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(v):return dict(bytes=len(v),sha256=sha256(v).hexdigest())
def read(p):return json.loads(p.read_bytes())
def names(paths):return {p.relative_to(ROOT).as_posix():pin(p.read_bytes()) for p in paths}
output=OUT/'checkpoint.json';assert not output.exists()
admission=probe=None
report=dict(authority='DRAFT_NONAUTHORITATIVE',label='machinery_diagnostic_archive',kind='static',cap_seconds=4,
    diagnostic_capture_accepted=False,
    predecessor_combined_resource_admission=False,policy_resource_admission=False,cold_acceptance=False,
    actual_F=False,run_authority=False,resource_admission=False,formal_result=False,official_verdict=None,production_seal=False)
step='source_and_controls'
try:
    admission=read(OUT/'admission.json');probe=read(OUT/'probe.exit.json')
    report['predecessor_charged_seconds']=admission['predecessor_charged_seconds']
    assert admission['caps']==dict(registration=2,probe=12,archive=4,total_static=18,pytest=0)
    registration=read(OUT/'registration.json')
    assert registration['accepted'] and registration['charged_seconds']==admission['registration_charged_seconds']
    assert pin((OUT/'registration.json').read_bytes())==admission['registration_pin']==probe['registration_pin']==probe['after_registration_pin']
    prepared={k:v for k,v in admission.items() if k not in ('registration_charged_seconds','registration_tail_reserve_seconds','registration_accepted','registration_pin')}
    assert registration['prepared_controls_pin']==pin(raw(prepared))
    assert registration['git_query']==admission['registration_git_query'] and registration['git_query']['returncode']==0
    source=names(ROOT/n for n in admission['source_pins']);assert len(source)==49 and source==admission['source_pins']==probe['source_pins']==probe['after_source_pins']
    epoch=sha256(raw(source)).hexdigest();assert epoch==admission['source_epoch']
    helpers=names(ROOT/n for n in admission['helper_pins']);assert len(helpers)==4 and helpers==admission['helper_pins']==probe['helper_pins']==probe['after_helper_pins']
    assert names(ROOT/n for n in admission['reference_pins'])==admission['reference_pins']==probe['reference_pins']==probe['after_reference_pins']
    assert {n:pin(Path(n).read_bytes()) for n in admission['external_pins']}==admission['external_pins']==probe['external_pins']==probe['after_external_pins']
    assert probe['admission_pin']==probe['after_admission_pin']==pin((OUT/'admission.json').read_bytes())
    assert probe['postcheck_pins_match'] and probe['accepted'] and probe['diagnostic_capture_accepted'] and probe['returncode']==0 and probe['error'] is None and probe['parent_exact_launch_events']==1
    for suffix in ('stdout','stderr'):assert pin((OUT/('probe.'+suffix+'.log')).read_bytes())==probe[suffix+'_pin']
    assert not (OUT/'probe.stderr.log').read_bytes()
    assert pin((OUT/'result.json').read_bytes())==probe['result_pin']
    result=read(OUT/'result.json');assert result==read(OUT/'probe.stdout.log')
    step='observation_and_cleanup'
    assert result['diagnostic_capture_accepted'] and result['before_snapshot_matches_boundary']
    assert result['boundary'] is not None and not result['boundary']['hook_active']
    assert result['error_type']=='SavedSuccessorImportUnresolved' and not result['loader_returned'] and result['source49_raw_recorded'] and result['boundary']['phase']=='FAULTED'
    assert all(result['counts'][n]==0 for n in ('P1_open','actual_F_open','write_attempts','mutation_attempts','unexpected_process'))
    assert result['counts']['optional_seen']==1
    comparison=result['comparison'];assert set(comparison)=={'meta_path','path_hooks','path','path_importer_cache','modules'}
    for name in ('meta_path','path_hooks'):
        row=comparison[name];assert len(row['before'])==row['before_length'] and len(row['after'])==row['after_length']
        for item in row['before']+row['after']:
            assert item['descriptor_sha']==sha256(raw(item['descriptor'])).hexdigest() and item['identity_sha']==sha256(item['identity_token'].encode('ascii')).hexdigest()
        left=[i['identity_sha'] for i in row['before']];right=[i['identity_sha'] for i in row['after']]
        assert row['equal']==(left==right)
        expected=next((i for i,(a,b) in enumerate(zip(left,right)) if a!=b),min(len(left),len(right)) if len(left)!=len(right) else None)
        assert row['first_difference_index']==expected
        assert row['added_indices']==[i for i,v in enumerate(right) if v not in left] and row['removed_indices']==[i for i,v in enumerate(left) if v not in right]
    assert any(not comparison[n]['equal'] for n in ('meta_path','path_hooks','path')) or any(not comparison[n]['container_identity_same'] for n in ('path_importer_cache','modules'))
    state=probe['bounded_drain'];assert state['reader_threads_terminal'] and state['pipes_closed'] and not state['cleanup']
    assert probe['handle_closed'] and not probe['process_cleanup_errors'] and probe['peak_working_set_bytes'] is not None and probe['RAM_hard_cap_enforced'] is False
    step='failure_lineage_and_costs'
    previous=read(ROOT/admission['predecessor_checkpoint_path'])
    assert previous['accepted'] is False and previous['failed_check']=='resource_caps_and_binding'
    assert previous['cumulative_charged_seconds']==admission['predecessor_charged_seconds']
    assert len(admission['failed_record_pins'])==9 and names(ROOT/n for n in admission['failed_record_pins'])==admission['failed_record_pins']
    assert all(read(ROOT/n)['accepted'] is False for n in admission['failed_record_pins'])
    assert 0<=admission['registration_charged_seconds']<=2 and 0<=probe['charged_seconds']<=12
    expected=dict(static=admission['registration_charged_seconds']+probe['charged_seconds'],pytest=0)
    assert probe['successor_charged_seconds']==expected
    assert probe['all_cumulative_charged_seconds']=={k:admission['predecessor_charged_seconds'][k]+expected[k] for k in expected}
    assert all(probe[n] is result[n] is False for n in ('predecessor_combined_resource_admission','policy_resource_admission','cold_acceptance','actual_F','run_authority','resource_admission','formal_result'))
    step='small_archive_and_review'
    review=read(OUT/'pre_seal_review.json');assert review['official_verdict'] is None and review['production_seal'] is False and review['scope']=='machinery_difference_diagnostic_only'
    assert review['remaining_production_findings']
    files=[p for p in BASE.rglob('*') if p.is_file()];assert len(files)+1<=16 and sum(p.stat().st_size for p in files)+65000<=512*1024
    report.update(source_epoch=epoch,diagnostic_capture_accepted=True,comparison=comparison,
        bound_files=names(files+[ROOT/admission['scope_path']]),files_before_checkpoint=len(files),bytes_before_checkpoint=sum(p.stat().st_size for p in files),
        predecessor_resource_observation=admission['predecessor_resource_observation'],predecessor_filesystem_full_rescan_performed=False,
        peak_working_set_bytes=probe['peak_working_set_bytes'],verification_completed=True)
except BaseException as error:report.update(verification_completed=False,failed_check=step,error_type=type(error).__name__)
charged=time.perf_counter()-STARTED+.5;report['charged_seconds']=charged;report['tail_reserve_seconds']=.5
def known_cost(container,key):
    value=container.get(key) if type(container) is dict else None
    return value if type(value) in (int,float) and 0<=value<=10000 else None
registered=known_cost(admission,'registration_charged_seconds');observed=known_cost(probe,'charged_seconds')
successor=dict(static=(registered or 0)+(observed or 0)+charged,pytest=0)
report.update(successor_charged_seconds=successor,cost_lineage_complete=registered is not None and observed is not None)
previous=admission.get('predecessor_charged_seconds') if type(admission) is dict else None
if type(previous) is dict and all(known_cost(previous,k) is not None for k in successor):report['all_cumulative_charged_seconds']={k:previous[k]+successor[k] for k in successor}
report['accepted']=report.get('verification_completed',False) and charged<=4 and successor['static']<=18
with output.open('xb') as stream:stream.write(raw(report))
print(json.dumps(dict(accepted=report['accepted'],failed_check=report.get('failed_check'),charged_seconds=charged,successor_charged_seconds=successor),sort_keys=True))
if not report['accepted']:raise SystemExit(1)
