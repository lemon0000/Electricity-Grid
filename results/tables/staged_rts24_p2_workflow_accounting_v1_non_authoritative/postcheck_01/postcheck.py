"""Independent saved-accounting/byte verification, stdlib only."""
import ast
from hashlib import sha256
import json
from pathlib import Path
import re
import stat

ROOT=Path(__file__).resolve().parents[4]
BASE=Path(__file__).resolve().parent.parent
POST=BASE/'postcheck_01'


def require(value,message):
    if not value:raise ValueError(message)


def read(path):return json.loads(path.read_bytes())


def stamp(path):
    info=path.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink==1 and not getattr(info,'st_file_attributes',0)&0x400,'nonordinary repository file')
    raw=path.read_bytes();return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def main():
    checks=BASE/'development_checks_01';units=read(checks/'units_06.exit.json');related=read(checks/'related_02.exit.json')
    require(units['exit_code']==related['exit_code']==0 and units['source_pins_unchanged'] is related['source_pins_unchanged'] is True,'ordinary check terminal')
    for label,count in (('units_06',40),('related_02',41)):
        require(re.search(rb'\b'+str(count).encode()+rb' passed in\b',(checks/(label+'.stdout.log')).read_bytes())
            and (checks/(label+'.stderr.log')).read_bytes()==b'','ordinary check summary')
    require(all(stamp(ROOT/n)==v for n,v in units['source_pins'].items()),'final three inputs drifted')
    dependency=read(POST/'related_dependency_pins.json')
    require(all(stamp(ROOT/n)==v for n,v in dependency.items()),'frozen related code changed')
    require(read(checks/'prereview_01.json')['remaining_high_medium']==[],'prereview finding remains')
    obs=BASE/'execution_observations_01';command=read(obs/'command_01.exit.json');terminal=read(obs/'command_01.stdout.json')
    require(command['exit_code']==0 and command['source_pins_unchanged'] is True
        and command['source_pins']==units['source_pins'] and (obs/'command_01.stderr.log').read_bytes()==b'','metadata command terminal')
    path=BASE/'audit_01/audit.json';require({p.name for p in path.parent.iterdir()}=={'audit.json'},'audit output set')
    require(stamp(path)==terminal['output_pin'] and terminal['output_readback_reads']==1
        and terminal['output_readback_bytes']==stamp(path)['bytes']<=512*1024,'export pin/readback')
    audit=read(path);pins=audit['input_pins']
    require(len(pins)==264 and all(stamp(ROOT/n)==v for n,v in pins.items()),'input pins drifted')
    duplicates=['experiments/__init__.py','src/staged_rts24_journal_v2.py',
        *['results/tables/staged_rts24_p2_input_cost_v1_non_authoritative/measure_01/'+n+'.json' for n in ('start','report','launcher')]]
    require(audit['bounded_reader_input_reads']==2*len(pins)+len(duplicates)==533
        and audit['bounded_reader_input_bytes']==2*sum(v['bytes'] for v in pins.values())+sum(pins[n]['bytes'] for n in duplicates)==5046716,'Reader ledger reconstruction')
    bootstrap=audit['bootstrap_identity_pins']
    require(set(bootstrap)=={'experiments/__init__.py','experiments/staged_c_workflow_budget_v1.py'}
        and all(stamp(ROOT/n)==v for n,v in bootstrap.items()) and audit['bootstrap_identity_reads']==3
        and audit['bootstrap_identity_bytes']==bootstrap['experiments/__init__.py']['bytes']+2*bootstrap['experiments/staged_c_workflow_budget_v1.py']['bytes']==29094,'bootstrap identity ledger')
    require(audit['input_reads']==terminal['input_reads']==536 and audit['input_bytes']==terminal['input_bytes']==5075810
        and 0<=audit['bounded_reader_wall_seconds']<=20,'total bounded metadata ledger')
    value=audit['accounting'];journal=value['journal'];compiler=value['compiler_descriptions']
    wanted=dict(accepted_hours=10,writer_checks=42,writer_runtime=97,journal_runtime_including_two_reopens=101,
        root_inventory_calls=69,CAS_inventory_calls=126,root_inventory_file_hash_reads=434,check_chain_entry_reads=200,
        check_genesis_and_head_reads=84,reopen_sequential_entry_reads=22,append_published_entry_readbacks=11,reopen_genesis_reads=2,
        direct_journal_root_reads_excluding_codec_publication=753,prepare_hour=60,propose_hour=60,accept_hour=30,
        execution_summary=3,audit_execution=97,audit_execution_context=64,audit_prefix_row_visits=495,
        selective_calls_three_journal_passes=555)
    require(all(type(journal[n]) is int and journal[n]==v for n,v in wanted.items()),'conditional journal accounting')
    require(sum(journal[n] for n in ('root_inventory_file_hash_reads','check_chain_entry_reads','check_genesis_and_head_reads',
        'reopen_sequential_entry_reads','append_published_entry_readbacks','reopen_genesis_reads'))==753,'root read decomposition')
    require(compiler['selective_calls']==sum(compiler['selective_call_sources'].values())==575
        and compiler['selective_descriptions']==sum(compiler['selective_roles'].values())==1796
        and compiler['full_calls']==sum(compiler['full_call_sources'].values())==4
        and compiler['full_descriptions']==570 and compiler['total_descriptions']==2366,'compiler layer accounting')
    require(value['input_checks']['fingerprints']==1281 and value['input_checks']['load_packet']==960
        and value['input_checks']['preserve']==3 and value['input_checks']['preparation_total_logical_bytes']==2345752302,'input check accounting')
    require(value['journal_and_P2_fingerprint_runtime_calls']==1382 and value['selected_runtime_file_reads']==53898
        and value['point_CAS_inventory_calls']==2552 and value['all_internal_CAS_inventory_calls']==2678,'inner runtime/CAS accounting')
    require(value['deferred_cache']['implemented'] is False and value['deferred_cache']['fingerprint_checks_removed']==0
        and all(v is None for v in value['unknown'].values()),'unknown scope changed')
    projection=audit['saved_P1_CAS_projection']
    require(projection['accepted_hours']==5 and projection['CAS_files']==130 and projection['inventory_calls']==76
        and projection['inventory_object_read_instances']==5376 and projection['inventory_logical_bytes']==17465962,'P1 saved epoch projection')
    require([projection['epoch_object_counts']['accepted_'+str(i)] for i in range(6)]==[4,28,52,76,105,129]
        and projection['epoch_object_counts']['final']==130 and projection['epoch_bytes']['final']==381174,'P1 epoch shape')
    independently=read(POST/'independent_P1_epoch_projection.json')
    require(independently['epoch_object_counts']==projection['epoch_object_counts']
        and independently['epoch_bytes']==projection['epoch_bytes']
        and independently['inventory_object_read_instances']==5376 and independently['inventory_logical_bytes']==17465962,'independent wire metadata oracle differs')
    for name in ('new_scientific_calls','new_native_calls','new_scientific_replays'):require(audit[name]==0,'scientific execution claim')
    require(audit['source_and_artifact_bookends'] is True and audit['environment_revalidated'] is False
        and audit['resource_admission'] is audit['formal_result'] is False
        and all(audit[n] is None for n in ('official_verdict','receipt','seal')),'audit authority scope')
    prior=read(POST/'prior_preservation_inventory.json')
    require(len(prior)==351 and all(stamp(ROOT/n)==v for n,v in prior.items()),'prior publication drift')
    for label,anchor in (('P1_and_prior','results/tables/staged_rts24_native_v1_non_authoritative/p1_execution_review_01/postcheck_03.stdout.json'),
        ('input_cost','results/tables/staged_rts24_p2_input_cost_v1_non_authoritative/postcheck_01/saved_01.stdout.json')):
        record=read(POST/(label+'.exit.json'))
        require(record['exit_code']==0 and record['exact_prior_stdout'] is True and stamp(POST/(label+'.stdout.json'))==stamp(ROOT/anchor)
            and (POST/(label+'.stderr.log')).read_bytes()==b'','prior postcheck reproduction')
    native=ROOT/'results/tables/staged_rts24_p2_native_v1_non_authoritative'
    require(not (native/'p2_01').exists() and not (native/'registration_v1.json').exists(),'P2 execution state exists')
    for name in units['source_pins']:
        if name.endswith('.py'):ast.parse((ROOT/name).read_text(encoding='utf-8-sig'),filename=name)
    require(all(stamp(ROOT/n)==v for n,v in pins.items()) and stamp(path)==terminal['output_pin'],'final inputs/output drift')
    return dict(authority='DRAFT_NONAUTHORITATIVE',script=stamp(Path(__file__)),targeted_passed=40,related_passed=41,
        input_files_unchanged=264,total_logical_input_reads=536,total_logical_input_bytes=5075810,
        audit_output=stamp(path),conditional_T10_journal_runtime=101,conditional_T10_all_CAS_inventories=2678,
        original_P1_CAS_files=130,original_P1_weighted_inventory_instances=5376,original_P1_weighted_inventory_bytes=17465962,
        prior_published_paths_unchanged=351,P1_files_unchanged=683,B1_B3_saved_files_unchanged=118,prior_checkpoint_paths_unchanged=685,
        new_scientific_calls_by_postcheck=0,new_native_calls=0,resource_admission=False,formal_result=False,
        C_overall_performance_review_complete=False,scope='saved metadata/bytes and independent wire oracle only')


if __name__=='__main__':print(json.dumps(main(),sort_keys=True,indent=2,allow_nan=False))
