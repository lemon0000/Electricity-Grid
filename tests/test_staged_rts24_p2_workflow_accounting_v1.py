"""Expanded event/AST oracles and immutable metadata; no scientific execution."""
import ast
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys

import pytest

from experiments import staged_rts24_p2_workflow_accounting_v1 as d


def packet():return json.loads((d.ROOT/d.PACKET/'packet.json').read_bytes())


def expanded_writer_and_two_readers(t):
    events=[];root_reads=[];cas=[];audit_rows=[];prepare=[]
    def scan_root(entries):root_reads.extend(range(entries+1))
    def check(k):
        events.extend(('runtime','runtime'));scan_root(k)
        root_reads.extend(('genesis','head'));root_reads.extend(range(k));cas.append('accepted_'+str(k))
        events.append('check')
    def append(k,terminal=False):
        check(k);scan_root(k)
        cas.extend(('accepted_'+str(k),('terminal_payload' if terminal else 'payload_'+str(k+1))))
        cas.extend((('terminal_payload' if terminal else 'payload_'+str(k+1)),('final' if terminal else 'accepted_'+str(k+1))))
        cas.extend([('final' if terminal else 'accepted_'+str(k+1))]*2)
        scan_root(k+1);root_reads.append('published_entry');events.append('runtime')
    events.extend(['runtime']*2);scan_root(0)
    cas.extend(['empty','fixture','fixture']+['accepted_0']*7)
    for k in range(t):
        check(k);check(k);check(k);append(k)
    check(t);append(t,True)
    for _ in range(2):
        events.extend(['runtime']*2);scan_root(t+1);scan_root(t+1)
        root_reads.extend(['genesis']+list(range(t+1)));cas.extend(['final']*4)
    for _ in range(3):
        for k in range(t):
            prepare.extend([k]*2)
            audit_rows.extend(range(k));audit_rows.extend(range(k));audit_rows.extend(range(k+1))
        audit_rows.extend(range(t));audit_rows.extend(range(t))
    return Counter(events),root_reads,Counter(cas),Counter(audit_rows),prepare


@pytest.mark.parametrize('t',[0,1,2,5,10])
def test_formula_agrees_with_expanded_operation_events_and_prefix_rows(t):
    events,roots,scans,rows,prepares=expanded_writer_and_two_readers(t);value=d.prefix_accounting(t)
    assert value['writer_checks']==events['check']
    assert value['journal_runtime_including_two_reopens']==events['runtime']
    assert value['direct_journal_root_reads_excluding_codec_publication']==len(roots)
    assert sum(value[n] for n in ('root_inventory_file_hash_reads','check_chain_entry_reads','check_genesis_and_head_reads',
        'reopen_sequential_entry_reads','append_published_entry_readbacks','reopen_genesis_reads'))==len(roots)
    assert value['CAS_inventory_epoch_weights']==dict(scans) and value['CAS_inventory_calls']==sum(scans.values())
    assert value['audit_prefix_row_visits']==sum(rows.values()) and value['prepare_hour']==len(prepares)
    assert [rows[i] for i in range(t)]==[9*(t-i) for i in range(t)]


def function_calls(path,name):
    tree=ast.parse((d.ROOT/path).read_text(encoding='utf-8-sig'))
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
    return Counter(n.func.id if isinstance(n.func,ast.Name) else n.func.attr for n in ast.walk(fn)
        if isinstance(n,ast.Call) and isinstance(n.func,(ast.Name,ast.Attribute)))


def test_expansion_sites_match_unchanged_journal_and_codec_AST():
    journal='src/staged_rts24_journal_v2.py';codec='src/staged_rts24_evidence_store_v1.py'
    assert function_calls(journal,'begin_step')['_check']==2
    assert function_calls(journal,'commit_step')['_check']==1
    assert function_calls(journal,'finish')['_check']==1
    assert function_calls(journal,'_append')['_check']==1
    assert function_calls(journal,'_check')['runtime_identity']==2
    assert function_calls(journal,'_append')['runtime_identity']==1
    assert function_calls(journal,'create_session')['runtime_identity']==2
    assert function_calls(journal,'reopen')['runtime_identity']==2
    tree=ast.parse((d.ROOT/codec).read_text(encoding='utf-8'));cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='EvidenceStore')
    put=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='put')
    assert sum(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='inventory' for n in ast.walk(put))==2
    assert d.ast_counts((d.ROOT/journal).read_bytes())==dict(SOURCE_PATHS=28,EXTERNAL_MODULES=10)


def test_current_packet_reconciles_compiler_layers_and_Journal_multipliers():
    value=d.accounting(packet());assert value['points']['model_builds']==1276
    assert value['journal']['journal_runtime_including_two_reopens']==101
    assert value['journal']['root_inventory_file_hash_reads']==434
    assert value['journal']['direct_journal_root_reads_excluding_codec_publication']==753
    assert value['journal']['CAS_inventory_calls']==126 and value['point_CAS_inventory_calls']==2552
    assert value['journal_and_P2_fingerprint_runtime_calls']==1382 and value['selected_runtime_file_reads']==53898
    compiler=value['compiler_descriptions']
    assert compiler['selective_calls']==575 and compiler['selective_descriptions']==1796
    assert compiler['full_calls']==4 and compiler['full_descriptions']==570 and compiler['total_descriptions']==2366
    assert compiler['selective_roles']==dict(reference_base_P0=575,reference_raw_need=71,recovery_min_meter=575,recovery_max_meter=575)
    assert value['unknown']['wall_estimate_seconds'] is value['unknown']['CAS_bytes'] is None
    assert value['deferred_cache']['implemented'] is False and value['deferred_cache']['fingerprint_checks_removed']==0


@pytest.mark.parametrize('fault',['horizon','role','ordinal','qp','schedule_sha'])
def test_different_scope_cannot_inherit_P2_accounting(fault):
    value=packet()
    if fault=='horizon':value['observation_end']=9
    elif fault=='role':value['schedule'][0]['role']='normal_contract_C'
    elif fault=='ordinal':value['schedule'][5]['ordinal']=1
    elif fault=='qp':value['schedule'][0]['objective']='min_meter'
    else:value['schedule_sha']='0'*64
    if fault!='schedule_sha':value['schedule_sha']=d.digest(value['schedule'])
    with pytest.raises(ValueError):d.accounting(value)


def test_CAS_work_is_inventory_weighted_instead_of_scan_count_times_final_size():
    weights=d.prefix_accounting(2)['CAS_inventory_epoch_weights']
    sizes=dict(empty=0,fixture=3,accepted_0=5,payload_1=8,accepted_1=10,payload_2=12,accepted_2=15,terminal_payload=18,final=18)
    expected=2*3+12*5+2*8+8*10+2*12+6*15+2*18+11*18
    assert d.inventory_object_visits(weights,sizes)==expected
    assert expected!=sum(weights.values())*sizes['final']
    for bad in ({},dict(sizes,final=True),dict(sizes,empty=1)):
        with pytest.raises(ValueError):d.inventory_object_visits(weights,bad)


@pytest.mark.parametrize('t',[-1,11,True,1.0])
def test_prefix_scope_and_exact_types_are_closed(t):
    with pytest.raises(ValueError):d.prefix_accounting(t)


def test_real_saved_metadata_audit_does_not_create_audit_or_P2_outputs():
    assert not d.OUT.exists()
    value=d.audit()
    assert value['source_and_artifact_bookends'] is True and value['new_scientific_calls']==value['new_native_calls']==0
    assert value['input_reads']<=1800 and value['input_bytes']<=12*1024**2 and not d.OUT.exists()
    assert value['accounting']['resource_admission'] is False and value['official_verdict'] is None


def test_both_budget_modules_only_import_stdlib_and_the_frozen_reader():
    for path in (Path(d.__file__),d.ROOT/d.READER):
        tree=ast.parse(path.read_text(encoding='utf-8'))
        for n in ast.walk(tree):
            if isinstance(n,ast.Import):assert all(x.name.split('.')[0] in d.sys.stdlib_module_names for x in n.names)
            elif isinstance(n,ast.ImportFrom):
                assert n.module.split('.')[0] in d.sys.stdlib_module_names or (
                    n.module=='experiments' and [(v.name,v.asname) for v in n.names]==[('staged_c_workflow_budget_v1','retained')])


def test_output_exists_rejected_before_audit(tmp_path,monkeypatch):
    output=tmp_path/'existing';output.mkdir();monkeypatch.setattr(d,'OUT',output)
    monkeypatch.setattr(d,'audit',lambda:pytest.fail('existing output was re-audited'))
    # Flags/loaded-src are ordinary pytest context; test the same create-only admission in isolation.
    monkeypatch.setattr(d.sys,'flags',type('Flags',(),dict(no_user_site=True))())
    monkeypatch.setattr(d.sys,'dont_write_bytecode',True)
    with monkeypatch.context() as isolated:
        isolated.setattr(d.sys,'modules',{n:v for n,v in d.sys.modules.items() if n!='src' and not n.startswith('src.')})
        with pytest.raises(ValueError,match='output exists'):d.main()


def test_wire_grammar_distinguishes_literal_ref_strings_from_references():
    key='a'*64
    wire=['dict',[['actual',['ref',key]],['literal',['list',['ref',key]]]]]
    assert d.wire_refs(wire)=={key}
    assert d.wire_refs(['list',['ref',key]])==set()
    assert d.wire_refs(['list',[['ref',key],['ref',key]]])=={key}


@pytest.mark.parametrize('wire',[
    ['ref','short'],['foreign',[]],['dict',[['x',None],['x',None]]],['list',{}],
    ['float','nan'],['Q',2,4],['Q',True,1],['class',None,[]]])
def test_wire_topology_rejects_invalid_tags_and_shapes(wire):
    with pytest.raises((ValueError,TypeError)):d.wire_refs(wire)


def test_ref_closure_rejects_missing_and_cyclic_edges():
    a,b='a'*64,'b'*64
    envelope=lambda payload:dict(schema='staged_rts24_typed_cas_v1',kind='dict',payload=payload)
    with pytest.raises(ValueError):d.closures({a:envelope(['ref',b])})
    with pytest.raises(ValueError):d.closures({a:envelope(['ref',b]),b:envelope(['ref',a])})
    assert d.closures({a:envelope(['list',[['ref',b],['ref',b]]]),b:envelope(None)})[a]=={a,b}


def test_saved_P1_epoch_projection_is_bound_and_keeps_five_hour_scope():
    value=d.saved_P1_projection(d.Reader(d.ROOT))
    assert value['accepted_hours']==5 and value['CAS_files']==130 and value['inventory_calls']==76
    assert value['epoch_object_counts']['final']==130 and value['inventory_object_read_instances']>130
    assert value['inventory_logical_bytes']>value['epoch_bytes']['final']
    assert value['saved_process_observer_crosscheck']['journal_runtime_identity_attempts']==185


@pytest.mark.parametrize('fault',['after_keys','swap','orphan'])
def test_retained_epoch_projection_rejects_bad_graph_adoption(fault):
    reader=d.Reader(d.ROOT);anchor=reader.json(d.P1_ANCHOR,d.P1_ANCHOR_SHA);pins=anchor['p1_files']
    values={n:reader.json(d.P1+n,pins[n]) for n in pins if n.startswith('journal/')}
    genesis=values['journal/genesis.json'];entries=[values['journal/entry_'+str(i).zfill(6)+'.json'] for i in range(1,7)]
    objects={n.removeprefix('journal/objects/').removesuffix('.json'):v for n,v in values.items() if n.startswith('journal/objects/')}
    sizes={k:pins['journal/objects/'+k+'.json']['bytes'] for k in objects}
    if fault=='after_keys':entries[2]['after_cas_keys'].pop()
    elif fault=='swap':entries[0]['payload_ref'],entries[0]['state_ref']=entries[0]['state_ref'],entries[0]['payload_ref']
    else:objects['0'*64]=dict(schema='staged_rts24_typed_cas_v1',kind='dict',payload=None);sizes['0'*64]=1
    with pytest.raises(ValueError):d.retained_epochs(genesis,entries,objects,sizes)


@pytest.mark.parametrize('fault',['method','require_alias'])
def test_loaded_Reader_code_and_alias_must_match_frozen_source(monkeypatch,fault):
    if fault=='method':monkeypatch.setattr(d.Reader,'read',lambda *a,**k:b'{}')
    else:monkeypatch.setattr(d,'require',lambda *a:None)
    with pytest.raises(ValueError,match='Reader'):d.reader_identity()


def test_CLI_rejects_preloaded_package_before_importing_Reader():
    script=str(Path(d.__file__))
    code="import sys,types,runpy; sys.modules['experiments']=types.ModuleType('experiments'); runpy.run_path(sys.argv[1],run_name='__main__')"
    result=subprocess.run([sys.executable,'-B','-s','-c',code,script],cwd=d.ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=15)
    assert result.returncode!=0 and b'before Reader import' in result.stderr and not d.OUT.exists()


def test_export_is_create_only_and_verified_after_close(tmp_path):
    path=tmp_path/'audit.json';raw=b'{"value":1}\n'
    assert d.publish_audit(path,raw)==dict(bytes=len(raw),sha256=d.sha256(raw).hexdigest())
    with pytest.raises(FileExistsError):d.publish_audit(path,raw)


def test_partial_write_is_retained_and_not_adopted(tmp_path,monkeypatch):
    path=tmp_path/'audit.json';original=Path.open
    class Short:
        def __init__(self,stream):self.stream=stream
        def __enter__(self):self.stream.__enter__();return self
        def __exit__(self,*args):return self.stream.__exit__(*args)
        def fileno(self):return self.stream.fileno()
        def write(self,raw):return self.stream.write(raw[:3])
    def opened(self,*args,**kwargs):
        stream=original(self,*args,**kwargs)
        return Short(stream) if self==path and args==('xb',) else stream
    monkeypatch.setattr(Path,'open',opened)
    with pytest.raises(ValueError,match='short audit write'):d.publish_audit(path,b'1234567')
    assert path.read_bytes()==b'123'


def test_postclose_output_drift_prevents_adoption(tmp_path,monkeypatch):
    path=tmp_path/'audit.json';original=Path.open
    def opened(self,*args,**kwargs):
        if self==path and args==('rb',):
            with original(self,'wb') as stream:stream.write(b'changed')
        return original(self,*args,**kwargs)
    monkeypatch.setattr(Path,'open',opened)
    with pytest.raises(ValueError,match='readback'):d.publish_audit(path,b'1234567')
