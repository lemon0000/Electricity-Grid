"""Explicit continuation of the preserved compiler-elision unit failure."""
import ast
import base64
import copy
import importlib.util
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).absolute().parents[3]
OUT = Path(__file__).absolute().parent
EXE = 'D:/Miniconda3/envs/compute/python.exe'
TOOL = ROOT/'experiments/staged_rts24_saved_fresh_root_catalog_v1.py'
TEST = ROOT/'tests/test_staged_rts24_saved_fresh_root_catalog_v1.py'
REPAIR_SCOPE = ROOT/'docs/plan/staged_deliverability_c_saved_fresh_root_catalog_repair_scope_v1.md'


def canonical(v): return json.dumps(v, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('ascii')
def pin(raw):
    from hashlib import sha256
    return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())
def read(p): return json.loads(p.read_bytes())
def save(p,v):
    with p.open('xb') as stream: stream.write(canonical(v))
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path); module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module
def pins(paths): return {str(p):pin(p.read_bytes()) for p in paths}
def check(reg):
    for path,expected in reg['input_pins'].items(): assert pin(Path(path).read_bytes())==expected,path
def usage():
    files=[p for p in OUT.rglob('*') if p.is_file()]
    return dict(files=len(files),bytes=sum(p.stat().st_size for p in files))


def tool_delta(old_raw,new_raw):
    assert pin(old_raw)==dict(bytes=29830,sha256='dcd6a3c9fac38f324fc3494d33572e37f54255000865826f3078c9a344c23405')
    assert pin(new_raw)==dict(bytes=30330,sha256='68d5f11fcbe93e427671d49fbafe96c980199da3e4f1184487e05a0d1e311896')
    old,new=ast.parse(old_raw),ast.parse(new_raw); assert len(old.body)==len(new.body)
    changed=[]
    for before,after in zip(old.body,new.body):
        if isinstance(before,ast.ClassDef) and before.name in ('StaticModule','ReferenceGraph'):
            expected=copy.deepcopy(before); method='facts' if before.name=='StaticModule' else 'build'
            replacement=[n for n in after.body if isinstance(n,ast.FunctionDef) and n.name==method]
            assert len(replacement)==1
            for i,node in enumerate(expected.body):
                if isinstance(node,ast.FunctionDef) and node.name==method:
                    assert ast.dump(node)!=ast.dump(replacement[0]); expected.body[i]=replacement[0]; changed.append(before.name+'.'+method)
            assert ast.dump(expected)==ast.dump(after)
        else: assert ast.dump(before)==ast.dump(after)
    assert sorted(changed)==['ReferenceGraph.build','StaticModule.facts']
    return dict(before=pin(old_raw),after=pin(new_raw),changed_methods=changed,other_AST_identical=True)


def _register():
    started=time.perf_counter(); target=OUT/'revision_01.json'; assert not target.exists()
    original=read(OUT/'registration.json'); failed=read(OUT/'unittest.exit.json')
    assert original['accepted'] is True and failed['accepted'] is False and failed['label']=='unittest'
    assert failed['registration_pin']==pin((OUT/'registration.json').read_bytes())
    assert failed['helper_pins']==original['helper_pins'] and failed['report_pin']==pin((OUT/'unittest_report.json').read_bytes())
    report=read(OUT/'unittest_report.json'); assert report['tests_run']==28 and report['errors']==1 and report['failures']==report['skipped']==0
    inputs=dict(original['input_pins'])
    changed=[n for n,p in inputs.items() if pin(Path(n).read_bytes())!=p]
    assert changed==[str(TOOL)]
    # Each original helper generation is still available as exact content-addressed raw.
    old_snapshots={}
    for expected in original['helper_pins'].values():
        snapshot=OUT/('code_'+expected['sha256']+'.snapshot')
        assert pin(snapshot.read_bytes())==expected
        old_snapshots[str(snapshot)]=expected
    delta=tool_delta((OUT/('code_'+original['helper_pins'][str(TOOL)]['sha256']+'.snapshot')).read_bytes(),TOOL.read_bytes())
    held=[OUT/n for n in ('registration.json','unittest.exit.json','unittest_report.json','unittest_admission.json')]
    inputs.update(pins(held)); inputs.update(pins([TOOL,Path(__file__).absolute(),REPAIR_SCOPE])); inputs.update(old_snapshots)
    helpers=pins([TOOL,TEST,OUT/'driver.py',Path(__file__).absolute()])
    current_snapshots={}
    for path in (TOOL,Path(__file__).absolute()):
        raw=path.read_bytes()
        snapshot=OUT/('code_'+pin(raw)['sha256']+'.snapshot')
        with snapshot.open('xb') as stream: stream.write(raw)
        assert snapshot.read_bytes()==raw; current_snapshots[str(snapshot)]=pin(raw)
    inputs.update(current_snapshots)
    charged=time.perf_counter()-started
    reg=dict(original, input_pins=inputs, helper_pins=helpers,
        revision_registration_charged_seconds=charged,
        registration_charged_seconds=original['registration_charged_seconds']+charged,
        original_failure_pin=pin((OUT/'unittest.exit.json').read_bytes()), preserved_failure=True,
        old_snapshot_pins=old_snapshots,current_snapshot_pins=current_snapshots,reviewed_tool_transition=delta,
        repair_reason='CPython elides function code following unconditional module raise; retain AST-only compiler-elided open candidate',
        allowed_changes=['tool compiler_elided_definition with AST references and explicit dynamic_open edge',
            'new versioned controller consuming original failure without changing original helpers/records/tests'],
        accepted=original['registration_charged_seconds']+charged<=2)
    save(target,reg); print(canonical(dict(registered=reg['accepted'],charged_seconds=charged)).decode())
    if not reg['accepted']: raise SystemExit(1)


def register():
    started=time.perf_counter(); assert not (OUT/'revision_01.json').exists() and not (OUT/'revision_registration_failure.json').exists()
    try: _register()
    except BaseException as error:
        if not (OUT/'revision_01.json').exists():
            save(OUT/'revision_registration_failure.json',dict(accepted=False,kind='static',phase='revision_registration',
                charged_seconds=time.perf_counter()-started,error=type(error).__name__,driver_pin=pin(Path(__file__).read_bytes()),
                prior_usage=usage(),process_observation=None,predecessor_cumulative_verified=False,
                actual_F=False,formal_result=False,resource_admission=False,run_authority=False,production_seal=False))
        raise


def predecessors(label,reg):
    accepted=dict(unittest_repair=[],catalog=['unittest_repair'],saved=['unittest_repair','catalog'])[label]
    assert sorted(p.name for p in OUT.glob('*.exit.json'))==sorted(['unittest.exit.json']+[n+'.exit.json' for n in accepted])
    assert pin((OUT/'unittest.exit.json').read_bytes())==reg['original_failure_pin']
    assert read(OUT/'unittest.exit.json')['accepted'] is False
    result=pins([OUT/'unittest.exit.json'])
    for name in accepted:
        path=OUT/(name+'.exit.json'); record=read(path)
        assert record['accepted'] is True and record['label']==name and record['source_epoch']==reg['source_epoch']
        assert record['kind']==('unittest' if name=='unittest_repair' else 'static')
        assert record['revision_pin']==pin((OUT/'revision_01.json').read_bytes()) and record['helper_pins']==reg['helper_pins']
        report=OUT/(name+'_report.json'); assert record['report_pin']==pin(report.read_bytes()) and read(report)['accepted'] is True
        result.update(pins([path,report]))
    return result


def spent(reg):
    records=[read(p) for p in OUT.glob('*.exit.json')]
    result={k:sum(r['charged_seconds'] for r in records if r['kind']==k) for k in ('static','unittest')}
    result['static']+=reg['registration_charged_seconds']; return result


def child(label):
    reg=read(OUT/'revision_01.json'); check(reg); held=predecessors(label,reg)
    if label=='unittest_repair':
        import unittest
        module=load(TEST,'catalog_tests'); suite=unittest.defaultTestLoader.loadTestsFromModule(module)
        def nodes(s): return [n for child in s for n in nodes(child)] if isinstance(s,unittest.TestSuite) else [s.id()]
        selected=sorted(nodes(suite)); assert selected==reg['unit_nodes']
        save(OUT/'unittest_repair_admission.json',dict(nodes=selected,helper_pins=reg['helper_pins'],source_epoch=reg['source_epoch'],before_test_calls=True))
        admission=pin((OUT/'unittest_repair_admission.json').read_bytes())
        result=unittest.TextTestRunner(verbosity=1).run(suite)
        assert admission==pin((OUT/'unittest_repair_admission.json').read_bytes())
        report=dict(accepted=result.wasSuccessful() and result.testsRun==len(selected) and not result.skipped,
            nodes=selected,tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),admission_pin=admission)
    else:
        tool=load(TOOL,'catalog_tool'); result=tool.build_catalog(ROOT); raw=canonical(result)
        assert all(result[k] is False for k in tool.FALSE_GATES)
        if label=='catalog':
            with (OUT/'catalog.json').open('xb') as stream: stream.write(raw)
            graph=result['reference_graph']
            report=dict(accepted=True,catalog_pin=pin(raw),current_roots=len(result['current_roots']),legacy_roots=len(result['legacy33_disposition']),
                symbols=len(graph['nodes']),edges=len(graph['edges']),recursive_components=len(graph['recursive_components']),
                edge_disposition_counts=graph['edge_disposition_counts'],evidence_nodes=len(result['required_evidence_dag']['nodes']))
        else:
            assert label=='saved' and raw==(OUT/'catalog.json').read_bytes()
            report=dict(accepted=True,canonical_reopen_equal=True,catalog_pin=pin(raw),predecessor_pins=held,all_capabilities_verified=False)
    check(reg); assert held==predecessors(label,reg)
    save(OUT/(label+'_report.json'),report)
    if not report['accepted']: raise AssertionError('repair check failed; preserved')
    print(canonical(dict(accepted=True,action=label)).decode())


def action(label):
    started=time.perf_counter(); target=OUT/(label+'.exit.json'); assert not target.exists()
    reg=read(OUT/'revision_01.json'); cap=reg['phase_caps'][label]; kind='unittest' if label.startswith('unittest') else 'static'
    code=None; stdout=stderr=b''; error=None; observation=None; held=None; accepted=False
    revision_pin=pin((OUT/'revision_01.json').read_bytes())
    try:
        assert reg['accepted'] is True; check(reg); held=predecessors(label,reg)
        before=spent(reg); assert before[kind]+cap<=reg['caps'][kind] and sum(before.values())+cap<=50
        reserve=4*1024**2+131072 if label=='catalog' else 131072
        assert usage()['files']+4<=32 and usage()['bytes']+reserve<=8*1024**2
        capture=load(OUT.parent/'staged_rts24_saved_fresh_machinery_transition_v1_non_authoritative/checks_01/capture.py','fixed_repair_capture')
        code,stdout,stderr,error,observation=capture.bounded([EXE,'-B','-s',str(Path(__file__).absolute()),'child',label],cap-(time.perf_counter()-started)-0.7)
        check(reg); assert revision_pin==pin((OUT/'revision_01.json').read_bytes()) and held==predecessors(label,reg)
        drain=observation['bounded_drain']
        assert code==0 and error is None and observation['handle_closed'] and not observation['cleanup']
        assert drain['pipes_closed'] and drain['reader_threads_terminal'] and not drain['reader_errors'] and not drain['cleanup']
        assert not drain['killed'] and not drain['stdout_truncated'] and not drain['stderr_truncated']
        assert json.loads(stdout)==dict(accepted=True,action=label)
        report=read(OUT/(label+'_report.json')); assert report['accepted'] is True
        if kind=='unittest': assert report['tests_run']==28 and report['failures']==report['errors']==report['skipped']==0
        if label=='saved': assert report['canonical_reopen_equal'] is True
        accepted=True
    except BaseException as caught: error=type(caught).__name__+(':'+str(error) if error else '')
    charged=time.perf_counter()-started; total=spent(reg); total[kind]+=charged
    accepted=accepted and charged<=cap and total[kind]<=reg['caps'][kind] and sum(total.values())<=50
    report_path=OUT/(label+'_report.json')
    record=dict(accepted=accepted,label=label,kind=kind,charged_seconds=charged,cap_seconds=cap,charged_seconds_by_kind=total,
        all_cumulative_charged_seconds=dict(static=reg['predecessor_charged_seconds']['static']+total['static'],
            pytest=reg['predecessor_charged_seconds']['pytest'],unittest=total['unittest']),
        source_epoch=reg['source_epoch'],revision_pin=revision_pin,helper_pins=reg['helper_pins'],predecessor_pins=held,
        returncode=code,error=error,process_observation=observation,report_pin=pin(report_path.read_bytes()) if report_path.exists() else None,
        stdout_pin=pin(stdout),stderr_pin=pin(stderr),stdout_raw_base64=base64.b64encode(stdout).decode(),stderr_raw_base64=base64.b64encode(stderr).decode(),
        original_unit_failure_preserved=True,charge_scope='preparation through parent postcheck; final exit serialization/editor/review/Git excluded; target tail0.7s',
        actual_F=False,run_authority=False,resource_admission=False,formal_result=False,production_seal=False,
        storage_before_exit=usage(),storage_cap_satisfied=True)
    projected=len(canonical(record))+2
    storage_ok=usage()['files']+1<=32 and usage()['bytes']+projected<=8*1024**2
    record['storage_cap_satisfied']=storage_ok; record['accepted']=accepted=accepted and storage_ok
    save(target,record); print(canonical(dict(accepted=accepted,charged_seconds=charged,kind=kind)).decode())
    if not accepted: raise SystemExit(1)


if __name__=='__main__':
    if sys.argv[1:]==['register']: register()
    elif len(sys.argv)==3 and sys.argv[1]=='child': child(sys.argv[2])
    elif len(sys.argv)==2 and sys.argv[1] in ('unittest_repair','catalog','saved'): action(sys.argv[1])
    else: raise SystemExit('explicit static repair actions only')
