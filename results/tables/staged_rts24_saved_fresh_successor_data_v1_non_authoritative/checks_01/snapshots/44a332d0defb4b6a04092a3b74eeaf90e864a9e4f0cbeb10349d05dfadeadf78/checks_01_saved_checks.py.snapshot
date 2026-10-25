"""Frozen stdlib-only evidence oracle; never import a current scientific ENTRY."""
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
PRIOR=ROOT/'results/tables/staged_rts24_saved_fresh_source_bytes_reuse_v1_non_authoritative/checks_01'
SOURCE_PATHS=('src/staged_rts24_saved_fresh_adoption_v1.py',
    'experiments/staged_rts24_saved_fresh_adoption_v1.py','tests/test_staged_rts24_saved_fresh_adoption_v1.py')
MUTABLE=set(SOURCE_PATHS[1:])
OUTPUT_PARENT=ROOT/'results/tables/staged_rts24_saved_fresh_adoption_v1_non_authoritative'
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def canonical(value):return json.dumps(value,ensure_ascii=True,sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii')
def read(name):return json.loads((OUT/name).read_bytes())


def verify(require_current_navigation=False):
    admission=read('admission.json');source=admission['source_pins'];current=True
    assert len(source)==49 and set(SOURCE_PATHS)<=set(source)
    for name,expected in source.items():
        match=pin((ROOT/name).read_bytes())==expected
        if name not in MUTABLE:assert match,name
        current &= match
    assert sha256(canonical({n:source[n] for n in SOURCE_PATHS})).hexdigest()==admission['source_epoch']
    preserved=read('preservation_inventory.json');assert len(preserved)==3390
    for name,expected in preserved.items():assert pin((ROOT/name).read_bytes())==expected,name
    seconds=0.;records={}
    for path in OUT.glob('*.exit.json'):
        value=read(path.name);label=path.name.removesuffix('.exit.json');records[label]=value
        seconds+=value['wall_seconds']
        assert not value['timed_out'] and value['wall_seconds']<=value['timeout_seconds']<=15
        assert value['exit_code']==(1 if label=='witness_05' else 0)
        assert value['source_pins']==source and value['source_epoch']==admission['source_epoch']
        assert value['source_pins_unchanged'] and value['helper_pins_unchanged']
        assert value['actual_saved_F_execution'] is value['F_launch_admitted'] is False
        manifest=read(value['snapshot_manifest'])
        assert set(manifest)=={'sources','helpers'} and set(manifest['sources'])==set(SOURCE_PATHS)
        assert set(manifest['helpers'])==set(value['helper_pins'])
        for category,items in manifest.items():
            for name,item in items.items():
                expected=(source if category=='sources' else value['helper_pins'])[name]
                assert pin((ROOT/item['snapshot']).read_bytes())==item['pin']==expected
        stderr=(OUT/(label+'.stderr.log')).read_bytes()
        if label=='witness_05':assert b'witness attempted process_launch_attempts' in stderr and b'check_support_sve' in stderr
        else:assert stderr==b''
    assert seconds<=90
    census=read('python_census_v2.json');assert census['source_pins']==source
    assert len(census['python_files'])==41 and len(census['production_candidate_files'])==37
    code=census['code_objects'];assert len(code)==1844 and len({(r['source'],r['code_path']) for r in code})==1844
    assert census['complete_reachable_call_graph'] is census['runtime_binding_verified'] is False
    roots=read('root_contracts_v2.json');assert len(roots['roots'])==33 and len(roots['direct_preparation_targets'])==10
    crosscheck=read('mechanical_crosscheck.json')
    assert crosscheck['v1_code_sha_differences']==946 and crosscheck['v2_is_current_census'] is True
    assert crosscheck['legacy_expectation_fields']==27 and crosscheck['successor_fields']==31
    witness=read('global_binding_witness_v2.json')
    assert witness['source_pins']==source and witness['failure'] is None
    assert witness['all_preregistered_acceptances_established'] is True
    expected_symbols={'codec.parse','adapter._replay','core.digest','adapter.HeldInput','adapter.METRIC_FIELDS'}
    assert {r['symbol'] for r in witness['cases']}==expected_symbols and len(witness['cases'])==5
    for row in witness['cases']:
        assert row['accepted'] is row['original_object_restored'] is row['module_globals_identity_unchanged'] is True
        assert row['replacement_called'] is False
    assert witness['declared_python_audit_P1_open_attempts']==0
    assert witness['declared_subprocess_Popen_attempts']==witness['blocked_lscpu_fallbacks']==1
    assert witness['replacement_import_profile_originals_restored'] is True
    assert witness['audit_hook_installed_until_process_exit'] is True and witness['audit_hook_active_at_observation_end'] is False
    assert witness['numpy_sve_support_forced_false_by_instrumentation'] is True
    assert set(witness['phase_counts'])==expected_symbols|{'repository_import','post_import','restoration'}
    for phase,counts in witness['phase_counts'].items():
        for name,value in counts.items():assert value==(1 if phase=='repository_import' and name=='process_launch_attempts' else 0)
    for flag in ('full_runtime_closure_proved','production_guard_bypassed','actual_saved_F_execution',
        'F_launch_admitted','scientific_evidence_adopted','resource_admission','formal_result'):
        assert witness[flag] is False
    external=read('external_source_snapshots.json');external_current=True
    for name,item in external.items():
        assert pin((ROOT/item['snapshot']).read_bytes())==item['pin']
        expected=witness['external_source_pins'].get(name,read('runtime_pin_v2.json')['pin'])
        assert expected==item['pin']
        external_current &= Path(name).is_file() and pin(Path(name).read_bytes())==item['pin']
    oracle=read('schema_cut_oracle_v3.json');spec=read('successor_context_spec_v3.json');dag=read('capability_edges_v3.json')
    assert len(spec['fields'])==len(set(spec['fields']))==oracle['context_fields']==31
    assert not set(spec['fields'])&{'context_sha','ack_sha','G0_verified','permit','run_authority','caller_core','caller_sha'}
    assert spec['first_and_only_context_publication_uses_this_schema'] is True
    assert spec['full_P1_content_verified'] is spec['production_validator_implemented'] is False
    assert spec['schema_contract_complete'] is True and set(spec['field_rules'])==set(spec['fields'])
    assert all(set(r)=={'type','constraint','provenance'} for r in spec['field_rules'].values())
    for key in ('runtime_binding_contract','deadline_contract','request_contract'):
        artifact=spec[key];raw=(ROOT/artifact['path']).read_bytes()
        assert pin(raw)==artifact['pin'] and canonical(json.loads(raw))==raw
    runtime_profile=json.loads((ROOT/spec['runtime_binding_contract']['path']).read_bytes())
    assert runtime_profile['admissible_for_production_execution'] is False
    assert runtime_profile['external_import_probe_policy']=='UNDECIDED_BLOCKING'
    request=json.loads((ROOT/spec['request_contract']['path']).read_bytes())
    assert len(request['fields'])==20 and set(request['field_rules'])==set(request['fields'])
    assert request['field_rules']['anchor_sha']['exact']==spec['field_rules']['anchor_sha']['constraint']['exact']
    for name,domain in dict(source_sha='source_pins',environment_sha='environment',input_pins_sha='input_files',
        caller_expectation_sha='caller_expectation_core').items():
        assert request['field_rules'][name]['equals']=='sha256(canonical(host.'+domain+'))'
    assert request['field_rules']['expectation_sha']['equals']=='sha256(host.canonical_expectation_envelope_bytes)'
    for name,key in (('runtime_binding_contract_sha','runtime_binding_contract'),('deadline_profile_sha','deadline_contract')):
        expected=spec[key]['pin']['sha256']
        assert request['field_rules'][name]['equals']==spec['field_rules'][name]['constraint']['equals']==expected
    expected_equalities={
        'context.source_pins = host.source_pins = broker independently checked selected file pins',
        'context.environment = host.environment = each role actual allowed environment',
        'context.input_files = host.input_files = SHA-fixed external anchor p1_files',
        'context.executable.pin = request.executable_pin = host held EXE pin = actual role executable pin',
        'canonical(context.caller_expectation_core) = canonical(host E) = canonical(broker independent E)',
        'context.caller_expectation_sha = request.caller_expectation_sha = sha256(canonical(host E))',
        'context.expectation_sha = request.expectation_sha = sha256(host canonical expectation envelope bytes)',
        'context.request_sha = sha256(canonical(externally held host request))',
        'context.runtime_binding_contract_sha = request.runtime_binding_contract_sha = fixed runtime artifact pin SHA',
        'context.deadline_profile_sha = request.deadline_profile_sha = fixed deadline artifact pin SHA',
        'context.invocation_started = request.invocation_started; context.deadline = request.deadline = start+180',
        'context.broker_identity = host held owner kernel identity = ready/START identity = controller verified kernel identity'}
    assert len(spec['cross_field_equalities'])==12 and set(spec['cross_field_equalities'])==expected_equalities
    assert oracle['design_oracle_only'] is oracle['acyclic'] is oracle['ACK_back_edge_rejected'] is oracle['cross_process_G0_capability_rejected'] is True
    assert len(dag['node_roles'])==38 and all(dag['node_roles'][a]==dag['node_roles'][b] for a,b in dag['same_process_capability_edges'])
    for n in ('broker_ACK_verified','controller_permit','controller_owner_constructed'):
        assert dag['node_roles'][n]=='broker'
    assert dag['node_roles']['parent_owner_constructed']==dag['node_roles']['controller_issuer']=='controller'
    assert dag['node_roles']['fresh_owner_constructed']=='parent'
    cap_edges={tuple(e) for e in dag['same_process_capability_edges']}
    assert {('G0','controller_issuer'),('controller_issuer','parent_permit'),
        ('parent_permit','parent_owner_constructed'),('parent_owner_constructed','parent_quiet'),
        ('fresh_permit','fresh_owner_constructed'),('fresh_owner_constructed','fresh_quiet')}<=cap_edges
    order_edges={tuple(e) for e in dag['data_order_edges']}
    for role in ('controller','parent','fresh'):
        assert (role+'_permit',role+'_owner_constructed') in order_edges
        assert (role+'_owner_constructed',role+'_bootstrap') in order_edges
    nodes=list(dag['node_roles']);degree={n:0 for n in nodes};children={n:[] for n in nodes}
    arcs=dag['data_order_edges']+dag['same_process_capability_edges']
    for a,b in arcs:degree[b]+=1;children[a].append(b)
    ready=[n for n in nodes if not degree[n]];visited=[]
    while ready:
        n=ready.pop();visited.append(n)
        for child in children[n]:
            degree[child]-=1
            if not degree[child]:ready.append(child)
    assert len(visited)==38
    assert dag['implemented'] is oracle['production_validator_implemented'] is oracle['actual_saved_F_execution'] is False
    navigation_current=True
    for name,item in read('navigation_after.json').items():
        raw=(ROOT/name).read_bytes();header,separator,body=raw.partition(b'\n\n')
        assert separator and header.decode()==item['header'] and pin(body[-item['body']['bytes']:])==item['body']
        old=read('navigation_before.json')[name];assert pin(raw[-old['body']['bytes']:])==old['body']
        navigation_current &= pin(raw)==item['full']
    if require_current_navigation:assert navigation_current
    docs=read('document_checks.json');assert docs['links_resolve'] is True
    for pins in (docs['document_pins'],read('support_pins.json')):
        for name,expected in pins.items():assert pin((ROOT/name).read_bytes())==expected,name
    # This predecessor is already a self-contained frozen stdlib oracle and is
    # hash-checked above; it does not execute a mutable current ENTRY or helper.
    specifier=importlib.util.spec_from_file_location('previous_source_reuse_runtime_audit',PRIOR/'saved_checks.py')
    previous=importlib.util.module_from_spec(specifier);specifier.loader.exec_module(previous);old=previous.verify()
    assert old['P1_unchanged_files']==683 and old['frozen_current_epoch_nodes']==63
    assert old['frozen_oracle_uses_current_ENTRY'] is False
    assert not OUTPUT_PARENT.exists()
    files=[p for p in OUT.rglob('*') if p.is_file()]
    assert len(files)<=128 and sum(p.stat().st_size for p in files)<=8*1024**2
    return dict(authority='DRAFT_NONAUTHORITATIVE',source_epoch=admission['source_epoch'],
        current_sources_match_frozen_epoch=bool(current),unchanged_epoch_unit_nodes=63 if current else 0,new_pytest_nodes=0,
        python_files=41,production_candidate_files=37,code_objects=1844,root_functions=33,
        direct_preparation_targets=10,controlled_counterexamples_established=5,
        blocked_optional_Popen_attempts=1,declared_python_audit_P1_open_attempts=0,
        runtime_probe_forced_numpy_sve_false=True,successor_context_fields=31,capability_DAG_nodes=38,
        schema_validator_implemented=False,external_current_bytes_match_observation=bool(external_current),
        preservation_paths=3390,P1_unchanged_files=683,observed_completed_check_seconds=seconds,
        current_process_excluded_until_external_exit_record=True,total_cap_seconds=90,
        navigation_current_whole_pins_match=bool(navigation_current),scientific_ENTRY_imported_by_oracle=False,
        transitive_global_binding_closed=False,role_integration_complete=False,actual_saved_F_execution=False,
        F_launch_admitted=False,scientific_evidence_adopted=False,resource_admission=False,formal_result=False)


if __name__=='__main__':
    sys.stdout.buffer.write((json.dumps(verify(require_current_navigation=True),sort_keys=True,indent=2)+'\n').encode())
