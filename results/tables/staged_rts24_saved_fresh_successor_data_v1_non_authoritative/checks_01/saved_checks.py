"""Frozen stdlib evidence oracle; does not import the current ENTRY or validator."""
import ast
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
PRIOR=ROOT/'results/tables/staged_rts24_saved_fresh_runtime_binding_v1_non_authoritative/checks_01'
SOURCE_PATHS=('src/staged_rts24_saved_fresh_adoption_v1.py',
    'experiments/staged_rts24_saved_fresh_adoption_v1.py','tests/test_staged_rts24_saved_fresh_adoption_v1.py')
MUTABLE=set(SOURCE_PATHS[1:])
OUTPUT_PARENT=ROOT/'results/tables/staged_rts24_saved_fresh_adoption_v1_non_authoritative'
SPEC_PIN=(18167,'b151876e286f24dca3571134e4506e55978f0fe1dee949b76005f3e3c24b2f90')
CONTRACT_PINS=((2777,'767b0119ee6de14f720099897eafb158803433b4291529a786a4e3e281ed148d'),
    (776,'ecffb262d87b6595e4d66451768ada7780c73e6e2ea0fc0e5b88834aadb32343'),
    (3301,'fbb536393e7246487f3b91af0b691da317f1dbb238f5fdd40f770c286ce3dc1e'))

def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def canonical(value):return json.dumps(value,ensure_ascii=True,sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii')
def read(name):return json.loads((OUT/name).read_bytes())
def epoch(source):return sha256(canonical({n:source[n] for n in SOURCE_PATHS})).hexdigest()
def definitions(raw):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(raw).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}


def verify(require_current_navigation=False,require_current_sources=False):
    plan=read('group_admission_02.json');old_plan=read('group_admission.json');source=plan['source_pins']
    baseline=read('baseline_sources.json');current=True
    assert len(source)==len(baseline)==49 and set(source)==set(baseline)
    assert epoch(source)==plan['source_epoch'] and epoch(baseline)==read('admission.json')['previous_source_epoch']
    assert epoch(old_plan['source_pins'])==old_plan['source_epoch']
    assert len({epoch(baseline),old_plan['source_epoch'],plan['source_epoch']})==3
    for name,expected in source.items():
        match=pin((ROOT/name).read_bytes())==expected
        if name not in MUTABLE:assert match and expected==baseline[name],name
        current &= match
    if require_current_sources:assert current,'current mutable sources differ from the tested epoch'
    preserved=read('preservation_inventory.json');assert len(preserved)==3518
    for name,expected in preserved.items():assert pin((ROOT/name).read_bytes())==expected,name
    for name,expected in read('support_pins.json').items():assert pin((ROOT/name).read_bytes())==expected,name
    records={p.name.removesuffix('.exit.json'):read(p.name) for p in OUT.glob('*.exit.json')}
    required={'baseline_01','prepare_02','collection_03','admission_04','admission_12',
        'successor_smoke_05','successor_a_06','finalizer_14','finalizer_17'}|set(plan['groups'])
    assert required<=set(records)<=required|{'saved_15','terminal_16'}
    totals={'static':0.,'pytest':0.}
    initial={'baseline_01','prepare_02'}
    middle={'collection_03','admission_04','successor_smoke_05','successor_a_06'}
    for label,value in records.items():
        assert value['authority']=='DRAFT_NONAUTHORITATIVE'
        if label=='finalizer_14':
            assert value['kind']=='static' and value['timed_out'] is True and value['exit_code'] is None
            assert value['timeout_seconds']==4 and 4<=value['wall_seconds']<=4.1
        else:
            assert value['exit_code']==0 and not value['timed_out']
            assert 0<=value['wall_seconds']<=value['timeout_seconds']<=40
        totals[value['kind']]+=value['wall_seconds']
        expected=baseline if label in initial else old_plan['source_pins'] if label in middle else source
        assert value['source_pins']==expected and value['source_epoch']==epoch(expected)
        assert value['source_pins_unchanged'] and value['helper_pins_unchanged']
        assert value['actual_saved_F_execution'] is value['F_launch_admitted'] is False
        manifest=read(value['snapshot_manifest'])
        assert set(manifest)=={'sources','helpers'} and set(manifest['sources'])==set(SOURCE_PATHS)
        assert set(manifest['helpers'])==set(value['helper_pins'])
        for category,items in manifest.items():
            for name,item in items.items():
                wanted=(expected if category=='sources' else value['helper_pins'])[name]
                assert pin((ROOT/item['snapshot']).read_bytes())==item['pin']==wanted
        assert (OUT/(label+'.stderr.log')).read_bytes()==b''
        if value['kind']=='pytest':
            node_plan=old_plan if label in middle else plan
            assert value['nodes']==node_plan['groups'][label]
            assert value['timeout_seconds']==node_plan['caps'][label]
            assert re.search(rb'\b'+str(len(value['nodes'])).encode()+rb' passed in ',(OUT/(label+'.stdout.log')).read_bytes())
            harness=read(label+'.harness.json')
            assert harness['counts']==dict(optional_Popen_attempts=1,blocked_lscpu=1,unexpected_process_attempts=0,
                native_owner_attempts=0,P1_write_attempts=0,actual_F_write_attempts=0)
            for flag in ('guards_installed_before_repository_import','numpy_SVE_forced_false',
                'native_constructor_guard_installed','native_constructor_original_restored','audit_hook_installed_until_process_exit'):
                assert harness[flag] is True
            for flag in ('audit_active_at_observation_end','production_policy_decided',
                'arbitrary_native_effects_proved_absent','actual_saved_F_execution'):assert harness[flag] is False
    assert totals['static']<=40 and totals['pytest']<=200 and sum(totals.values())<=240
    groups=plan['groups'];flat=[n for g in groups.values() for n in g]
    assert len(flat)==len(set(flat))==184
    assert sum('::test_saved_successor_' in n for n in flat)==121
    assert sum(plan['caps'].values())==178 and plan['previous_pytest_seconds']+178<=200
    assert abs(plan['previous_pytest_seconds']-sum(records[n]['wall_seconds'] for n in ('successor_smoke_05','successor_a_06')))<1e-8
    historical_nodes=sum(len(records[n]['nodes']) for n in ('successor_smoke_05','successor_a_06'))
    assert historical_nodes==61
    reused=ROOT/'results/tables/staged_rts24_saved_fresh_source_bytes_reuse_v1_non_authoritative/checks_01/group_admission_02.json'
    earlier=json.loads(reused.read_bytes())['groups']
    for here,there in (('source_expectation_08','source_bytes_and_smoke_09'),('expectation_a_09','expectation_rest_05'),
        ('expectation_b_10','expectation_rest_06'),('binding_11','binding_regression_07')):assert groups[here]==earlier[there]
    frozen=read('successor_smoke_12.snapshot.json')['sources']
    for name,item in read('baseline_01.snapshot.json')['sources'].items():
        before=definitions((ROOT/item['snapshot']).read_bytes());after=definitions((ROOT/frozen[name]['snapshot']).read_bytes())
        assert all(after.get(key)==value for key,value in before.items()),name
    tree=ast.parse((ROOT/frozen[SOURCE_PATHS[1]]['snapshot']).read_bytes())
    assignments={n.targets[0].id:ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
        and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in {'SUCCESSOR_SPEC_PIN','SUCCESSOR_CONTRACT_PINS'}}
    assert assignments==dict(SUCCESSOR_SPEC_PIN=SPEC_PIN,SUCCESSOR_CONTRACT_PINS=CONTRACT_PINS)
    spec_raw=(PRIOR/'successor_context_spec_v3.json').read_bytes();assert pin(spec_raw)==dict(zip(('bytes','sha256'),SPEC_PIN))
    spec=json.loads(spec_raw);assert len(spec['fields'])==31 and len(spec['cross_field_equalities'])==12
    for key,wanted in zip(('runtime_binding_contract','deadline_contract','request_contract'),CONTRACT_PINS):
        artifact=spec[key];assert pin((ROOT/artifact['path']).read_bytes())==artifact['pin']==dict(zip(('bytes','sha256'),wanted))
    runtime=json.loads((ROOT/spec['runtime_binding_contract']['path']).read_bytes())
    deadline=json.loads((ROOT/spec['deadline_contract']['path']).read_bytes())
    assert runtime['external_import_probe_policy']=='UNDECIDED_BLOCKING' and runtime['admissible_for_production_execution'] is False
    assert deadline['actual_enforcement_implemented'] is False
    result_class=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='SavedSuccessorDataCheck')
    status=next(n for n in result_class.body if isinstance(n,ast.FunctionDef) and n.name=='status_raw')
    literal=next(n for n in ast.walk(status) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='dict')
    status_values={kw.arg:ast.literal_eval(kw.value) for kw in literal.keywords}
    assert status_values['data_only'] is status_values['declared_time_consistent'] is True
    assert all(v is False for k,v in status_values.items() if k not in ('schema','data_only','declared_time_consistent'))
    navigation_current=True
    for name,item in read('navigation_after.json').items():
        raw=(ROOT/name).read_bytes();header,separator,body=raw.partition(b'\n\n')
        assert separator and header.decode()==item['header'] and pin(body[-item['body']['bytes']:])==item['body']
        old=read('navigation_before.json')[name];assert pin(raw[-old['body']['bytes']:])==old['body']
        navigation_current &= pin(raw)==item['full']
    if require_current_navigation:assert navigation_current
    for name,item in read('finalizer_14_document_snapshots.json').items():
        assert pin((ROOT/item['snapshot']).read_bytes())==item['pin']==read('document_checks.json')['document_pins'][name]
    documents=read('document_checks_v2.json');assert documents['links_resolve'] is True
    for name,expected in documents['document_pins'].items():assert pin((ROOT/name).read_bytes())==expected,name
    # The predecessor's frozen stdlib oracle is hash-checked in preservation;
    # its verifier never imports the mutable current ENTRY or its helpers.
    loader=importlib.util.spec_from_file_location('previous_runtime_successor_data_audit',PRIOR/'saved_checks.py')
    previous=importlib.util.module_from_spec(loader);loader.loader.exec_module(previous);old=previous.verify()
    assert old['P1_unchanged_files']==683 and old['scientific_ENTRY_imported_by_oracle'] is False
    assert old['unchanged_epoch_unit_nodes']==(63 if old['current_sources_match_frozen_epoch'] else 0)
    if require_current_sources:assert old['current_sources_match_frozen_epoch'] is False
    assert not OUTPUT_PARENT.exists()
    files=[p for p in OUT.rglob('*') if p.is_file()];size=sum(p.stat().st_size for p in files)
    assert len(files)<=192 and size<=12*1024**2
    return dict(authority='DRAFT_NONAUTHORITATIVE',source_epoch=plan['source_epoch'],
        current_sources_match_frozen_epoch=bool(current),frozen_epoch_test_nodes=184,
        current_epoch_test_nodes=184 if current else 0,new_data_nodes=121,regression_nodes=63,
        historical_other_epoch_passed_nodes=historical_nodes,all_attempt_pytest_seconds=totals['pytest'],
        preserved_timed_out_static_attempts=1,successor_finalizer_completed=True,
        observed_completed_static_seconds=totals['static'],observed_completed_check_seconds=sum(totals.values()),
        current_process_excluded_until_external_exit_record=True,pytest_cap_seconds=200,static_cap_seconds=40,total_cap_seconds=240,
        preservation_paths=3518,P1_unchanged_files=683,successor_fields=31,request_fields=20,
        static_data_validator_implemented=True,declared_time_consistency_only=True,
        kernel_identity_observed_by_validator=False,filesystem_observed_by_validator=False,
        clock_observed_by_validator=False,scientific_ENTRY_imported_by_oracle=False,
        production_validator_or_role_integration_complete=False,transitive_runtime_binding_closed=False,
        production_import_probe_policy_decided=False,deadline_enforced=False,full_P1_content_verified=False,
        actual_saved_F_execution=False,F_launch_admitted=False,native_authorized=False,
        scientific_evidence_adopted=False,resource_admission=False,formal_result=False,public_P2_execution_enabled=False,
        navigation_current_whole_pins_match=bool(navigation_current),evidence_files=len(files),evidence_bytes=size)


if __name__=='__main__':
    sys.stdout.buffer.write((json.dumps(verify(require_current_navigation=True,require_current_sources=True),sort_keys=True,indent=2)+'\n').encode())
