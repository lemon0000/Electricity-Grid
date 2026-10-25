"""Frozen stdlib oracle for self-anchor tests; never import current ENTRY/helpers."""
import ast
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent
PRIOR=ROOT/'results/tables/staged_rts24_saved_fresh_successor_data_v1_non_authoritative/checks_01'
SOURCE_PATHS=('src/staged_rts24_saved_fresh_adoption_v1.py',
    'experiments/staged_rts24_saved_fresh_adoption_v1.py','tests/test_staged_rts24_saved_fresh_adoption_v1.py')
MUTABLE=set(SOURCE_PATHS[1:])
OUTPUT_PARENT=ROOT/'results/tables/staged_rts24_saved_fresh_adoption_v1_non_authoritative'

def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def canonical(value):return json.dumps(value,ensure_ascii=True,sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii')
def read(name):return json.loads((OUT/name).read_bytes())
def epoch(source):return sha256(canonical({n:source[n] for n in SOURCE_PATHS})).hexdigest()
def definitions(raw):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(raw).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}


def verify(require_current_navigation=False,require_current_sources=False):
    plan=read('group_admission_04.json');source=plan['source_pins'];baseline=read('baseline_sources.json');current=True
    proposals={n:read('group_admission'+suffix+'.json') for n,suffix in ((1,''),(2,'_02'),(3,'_03'),(4,'_04'))}
    assert len(source)==len(baseline)==49 and set(source)==set(baseline)
    assert epoch(baseline)==read('admission.json')['previous_source_epoch']
    assert len({epoch(baseline),*(p['source_epoch'] for p in proposals.values())})==5
    for proposal in proposals.values():assert epoch(proposal['source_pins'])==proposal['source_epoch']
    for name,expected in source.items():
        match=pin((ROOT/name).read_bytes())==expected
        if name not in MUTABLE:assert match and expected==baseline[name],name
        current &= match
    if require_current_sources:assert current,'current mutable sources differ from the tested epoch'
    preserved=read('preservation_inventory.json');assert len(preserved)==3649
    for name,expected in preserved.items():assert pin((ROOT/name).read_bytes())==expected,name
    for name,expected in read('support_pins.json').items():assert pin((ROOT/name).read_bytes())==expected,name
    records={p.name.removesuffix('.exit.json'):read(p.name) for p in OUT.glob('*.exit.json')}
    baseline_labels={'baseline_01','prepare_02'}
    first={'collection_03','admission_04'}
    second={'collection_14','admission_15','self_smoke_05'}
    third={'admission_17','admission_18','self_smoke_16','self_rest_06'}
    required=baseline_labels|first|second|third|{'admission_21','finalizer_22'}|set(plan['groups'])
    assert required<=set(records)<=required|{'saved_23','terminal_24'}
    failures={'self_smoke_05','self_rest_06','admission_17'};totals={'pytest':0.,'static':0.}
    for label,value in records.items():
        assert value['authority']=='DRAFT_NONAUTHORITATIVE' and not value['timed_out']
        assert value['exit_code']==(1 if label in failures else 0)
        assert 0<=value['wall_seconds']<=value['timeout_seconds']<=40
        totals[value['kind']]+=value['wall_seconds']
        expected=baseline if label in baseline_labels else proposals[1]['source_pins'] if label in first else \
            proposals[2]['source_pins'] if label in second else proposals[3]['source_pins'] if label in third else source
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
        stderr=(OUT/(label+'.stderr.log')).read_bytes();stdout=(OUT/(label+'.stdout.log')).read_bytes()
        if label=='admission_17':assert b'FileNotFoundError' in stderr and b'group_admission_03.json' in stderr
        else:assert stderr==b''
        if value['kind']=='pytest':
            test_plan=proposals[2] if label=='self_smoke_05' else proposals[3] if label in third else plan
            assert value['nodes']==test_plan['groups'][label] and value['timeout_seconds']==test_plan['caps'][label]
            if label=='self_smoke_05':assert b'1 failed in ' in stdout and b'Object of type bytes is not JSON serializable' in stdout
            elif label=='self_rest_06':assert b'1 failed, 22 passed in ' in stdout and b"'live' == 'closed'" in stdout
            else:assert re.search(rb'\b'+str(len(value['nodes'])).encode()+rb' passed in ',stdout)
            harness=read(label+'.harness.json')
            assert harness['counts']==dict(optional_Popen_attempts=1,blocked_lscpu=1,unexpected_process_attempts=0,
                native_owner_attempts=0,P1_write_attempts=0,actual_F_write_attempts=0)
            for flag in ('guards_installed_before_repository_import','numpy_SVE_forced_false',
                'native_constructor_guard_installed','native_constructor_original_restored','audit_hook_installed_until_process_exit'):
                assert harness[flag] is True
            for flag in ('audit_active_at_observation_end','production_policy_decided',
                'arbitrary_native_effects_proved_absent','actual_saved_F_execution'):assert harness[flag] is False
    assert totals['pytest']<=240 and totals['static']<=60 and sum(totals.values())<=300
    flat=[n for group in plan['groups'].values() for n in group]
    assert len(flat)==len(set(flat))==218 and sum('::test_saved_self_anchor_' in n for n in flat)==34
    assert sum(plan['caps'].values())==207
    previous_seconds=sum(records[n]['wall_seconds'] for n in ('self_smoke_05','self_smoke_16','self_rest_06'))
    assert previous_seconds+207<=220
    partial=re.search(rb'1 failed, (\d+) passed in ',(OUT/'self_rest_06.stdout.log').read_bytes())
    historical_passed=len(records['self_smoke_16']['nodes'])+int(partial.group(1))
    assert historical_passed==24
    old=json.loads((PRIOR/'group_admission_02.json').read_bytes())['groups']
    for here,there in (('data_smoke_07','successor_smoke_12'),('data_a_08','successor_a_13'),('data_b_09','successor_b_07'),
        ('source_expectation_10','source_expectation_08'),('expectation_a_11','expectation_a_09'),
        ('expectation_b_12','expectation_b_10'),('binding_13','binding_11')):assert plan['groups'][here]==old[there]
    # Reuse the exact collection only after proving the complete test bytes did
    # not change. The two subsequent corrections were confined to the ENTRY.
    collected=read('collection_14.exit.json')['source_pins'][SOURCE_PATHS[2]]
    assert collected==source[SOURCE_PATHS[2]]
    frozen=read('self_smoke_19.snapshot.json')['sources']
    for name,item in read('baseline_01.snapshot.json')['sources'].items():
        before=definitions((ROOT/item['snapshot']).read_bytes());after=definitions((ROOT/frozen[name]['snapshot']).read_bytes())
        assert all(after.get(key)==value for key,value in before.items()),name
    tree=ast.parse((ROOT/frozen[SOURCE_PATHS[1]]['snapshot']).read_bytes())
    factory=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='open_saved_self_anchor')
    image=next(n for n in ast.walk(factory) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)
        and n.func.id=='dict' and any(kw.arg=='schema' for kw in n.keywords))
    for kw in image.keywords:
        if kw.arg in ('role_bootstrap_verified','external_owner_verified','full_runtime_closure_verified',
            'full_P1_content_verified','run_authority','F_launch_admitted'):assert ast.literal_eval(kw.value) is False
    navigation_current=True
    for name,item in read('navigation_after.json').items():
        raw=(ROOT/name).read_bytes();header,separator,body=raw.partition(b'\n\n')
        assert separator and header.decode()==item['header'] and pin(body[-item['body']['bytes']:])==item['body']
        old_nav=read('navigation_before.json')[name];assert pin(raw[-old_nav['body']['bytes']:])==old_nav['body']
        navigation_current &= pin(raw)==item['full']
    if require_current_navigation:assert navigation_current
    documents=read('document_checks.json');assert documents['links_resolve'] is True
    for name,expected in documents['document_pins'].items():assert pin((ROOT/name).read_bytes())==expected,name
    loader=importlib.util.spec_from_file_location('previous_successor_data_self_anchor_audit',PRIOR/'saved_checks.py')
    previous=importlib.util.module_from_spec(loader);loader.loader.exec_module(previous);earlier=previous.verify()
    assert earlier['P1_unchanged_files']==683 and earlier['scientific_ENTRY_imported_by_oracle'] is False
    assert earlier['frozen_epoch_test_nodes']==184
    if require_current_sources:assert earlier['current_epoch_test_nodes']==0 and earlier['current_sources_match_frozen_epoch'] is False
    assert not OUTPUT_PARENT.exists()
    files=[p for p in OUT.rglob('*') if p.is_file()];size=sum(p.stat().st_size for p in files)
    assert len(files)<=192 and size<=12*1024**2
    return dict(authority='DRAFT_NONAUTHORITATIVE',source_epoch=plan['source_epoch'],
        current_sources_match_frozen_epoch=bool(current),frozen_epoch_test_nodes=218,current_epoch_test_nodes=218 if current else 0,
        new_self_anchor_nodes=34,regression_nodes=184,historical_other_epoch_partial_passed_nodes=historical_passed,
        preserved_failed_pytest_attempts=2,preserved_failed_static_attempts=1,all_attempt_pytest_seconds=totals['pytest'],
        observed_completed_static_seconds=totals['static'],observed_completed_check_seconds=sum(totals.values()),
        current_process_excluded_until_external_exit_record=True,pytest_cap_seconds=240,static_cap_seconds=60,total_cap_seconds=300,
        preservation_paths=3649,P1_unchanged_files=683,self_anchor_primitive_implemented=True,
        real_current_process_thread_query_tests=True,actual_role_bootstrap_verified=False,external_owner_verified=False,
        full_runtime_closure_verified=False,full_P1_content_verified=False,scientific_ENTRY_imported_by_oracle=False,
        production_import_probe_policy_decided=False,role_integration_complete=False,actual_saved_F_execution=False,
        F_launch_admitted=False,native_authorized=False,scientific_evidence_adopted=False,resource_admission=False,
        formal_result=False,public_P2_execution_enabled=False,navigation_current_whole_pins_match=bool(navigation_current),
        evidence_files=len(files),evidence_bytes=size)


if __name__=='__main__':
    sys.stdout.buffer.write((json.dumps(verify(require_current_navigation=True,require_current_sources=True),sort_keys=True,indent=2)+'\n').encode())
