"""Independent small primal/dual fixtures; no numeric backend or new journal."""
from dataclasses import asdict, replace
from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src import staged_rts24_saved_point_replay_v1 as d
from src.staged_rts24_causal_v1 import PointEvidence
from test_staged_rts24_numeric_interface_v1 import frame, raw_snapshot
from test_staged_rts24_p2_outer_observation_v2 import process as outer_process
from test_staged_rts24_p2_package_check_v1 import process as point_process


@pytest.fixture(autouse=True)
def deny_execution_and_publication(monkeypatch):
    import subprocess
    import pyomo.environ as pyo
    def denied(*a,**kw):pytest.fail('solver/spawn/publication requested by saved replay')
    for module,name in ((pyo,'SolverFactory'),(d.backend,'call_highs'),(d.backend,'make_model'),
            (d.codec,'publish'),(d.codec.EvidenceStore,'put'),(subprocess,'Popen')):
        monkeypatch.setattr(module,name,denied)


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(d.codec.canonical(value))


def balance_process(root):
    path=root/'process.json';record=json.loads(path.read_bytes())
    files=[p for p in root.rglob('*') if p.is_file() and p!=path]
    record.update(terminal_files=len(files),terminal_bytes=sum(p.stat().st_size for p in files))
    save(path,record)


def refresh(case):
    balance_process(case.root);case.files=d.mechanical.inventory(case.root)['pins']


def bundle(tmp_path,kind='economic',p2=False,numeric_failure=None):
    hour=frame(1)
    if kind=='economic':item=hour.reference
    elif kind=='child':item=hour.raw
    else:
        from experiments.staged_rts24_causal_examples_v1 import analytic_point
        q=replace(hour.reference.query.request,role='actual_P',meter_min=hour.reference.query.request.meter_min,
            meter_max=hour.reference.query.request.meter_max,anchor_id=hour.reference.query.request.identity)
        query=d.core.bind(q,hour.reference.query,hour.reference.point,hour.reference.economic)
        item=PointEvidence(query,analytic_point(query,q.meter_min))
    problem,snapshot=raw_snapshot(item)
    root=tmp_path/'point';(root/'cas/objects').mkdir(parents=True)
    (root/'native.log').write_bytes(b'analytic handwritten raw fixture; not a native run\n')
    log_pin=d.mechanical.pin((root/'native.log').read_bytes())
    options={**d.backend.options_for(problem),'log_file':str(root/'native.log')}
    info={name:0 for name in d.backend.INFO_FIELDS}
    info.update(valid=True,objective_function_value=snapshot.objective,primal_solution_status=2,dual_solution_status=2)
    native=dict(schema='staged_highs_raw_v1',problem_sha=problem.identity,problem=asdict(problem),options=options,
        version_expected=d.backend.VERSION,stage='returned',run_invoked=True,run_returned=True,cleanup_error=None,
        cleanup_status=dict(name='kOk',value=0),api_version=d.backend.VERSION,api_version_parts=[1,15,1],api_githash='analytic_fixture_only',
        model_status='kOptimal',model_status_value=7,solution=dict(primal_valid=True,dual_valid=snapshot.dual_valid,
            col_value=list(snapshot.column_value),row_value=list(snapshot.row_value),col_dual=list(snapshot.column_dual),row_dual=list(snapshot.row_dual)),
        info=info,native_run_seconds=0.,elapsed_seconds=0.,objective_value=snapshot.objective,log_pin=log_pin,
        api_calls=[dict(stage=stage,status='kOk',value=0) for name in options for stage in ('set_'+name,'get_'+name)]+
            [dict(stage='pass_model',status='kOk',value=0),dict(stage='run',status='kOk',value=0)])
    if numeric_failure=='warning':native['stage']='extract';native['api_calls'][-1].update(status='kWarning',value=1)
    elif numeric_failure=='time':native.update(model_status='kTimeLimit',model_status_value=13)
    elif numeric_failure=='dual':native['solution']['dual_valid']=False
    blobs={};query_ref,query_blobs=d.codec.pack(item.query);blobs.update(query_blobs)
    evidence_ref=None;error=None
    if numeric_failure:
        try:d.numeric.import_snapshot(item.query,problem,d.backend.snapshot_from_raw(problem,native))
        except d.numeric.UnresolvedNumeric as exc:error=dict(type=type(exc).__name__,message=str(exc))
        assert error is not None
    else:
        # The original writer stores importer output, including signed-zero
        # representation. Hand-specified evidence independently fixes the
        # numeric answer; its +/-0 spelling need not be the importer's spelling.
        imported=d.numeric.import_snapshot(item.query,problem,d.backend.snapshot_from_raw(problem,native))
        assert imported==item
        item=imported
        evidence_ref,evidence_blobs=d.codec.pack(item);blobs.update(evidence_blobs)
    for identity,raw in blobs.items():(root/'cas/objects'/(identity+'.json')).write_bytes(raw)
    expected=dict(ordinal=2 if p2 else 1,pins_sha='a'*64,registration_sha='b'*64,execution_binding=None)
    if p2:
        expected['execution_binding']=dict(ordinal=2,slot_sha='c'*64,request_sha=item.query.request.identity,bound_query_sha=item.query.identity,
            parent_slot=None if item.query.base_query is None else 1,
            parent_point_sha=None if item.query.base_point is None else d.core.digest(item.query.base_point),
            parent_economic_sha=None if item.query.base_economic is None else d.core.digest(item.query.base_economic),
            state_after_actual_slot=None,accepted_state_sha=None)
    request=dict(ordinal=expected['ordinal'],query_ref=query_ref,query_sha=item.query.identity,problem_sha=problem.identity,
        pins_sha=expected['pins_sha'],registration_sha=expected['registration_sha'],role=item.query.request.role,hour=item.query.request.hour)
    if p2:request['execution_binding']=expected['execution_binding']
    save(root/'request.json',request);save(root/'native.json',native)
    save(root/'result.json',dict(status='numeric_unresolved' if numeric_failure else 'imported',error=error,evidence_ref=evidence_ref,
        raw_pin=d.mechanical.pin((root/'native.json').read_bytes()),request_sha=d.mechanical.pin((root/'request.json').read_bytes())['sha256'],
        query_sha=item.query.identity,problem_sha=problem.identity,infeasibility_inferred=False))
    save(root/'process.json',point_process(1000,numeric=bool(numeric_failure)))
    save(root/'point_observations.json',dict(allow_native=True,counts={},inclusive_seconds={},
        missing_process_observations='unknown_not_zero',scope=d.OBSERVATION_SCOPE))
    for name in ('point.stdout.log','point.stderr.log'):(root/name).touch()
    balance_process(root)
    outer=outer_process();w=outer['quiescence_witness'];w['member_identities'].append(dict(pid=1000,creation_filetime=4561000))
    w['observed_unique_member_handles']=w['total_processes']=2
    return SimpleNamespace(root=root,item=item,frame=expected,outer=outer,native=native,
        files=d.mechanical.inventory(root)['pins'],sources=d.source_pins())


def run(case,**changes):
    args=dict(point_root=case.root,expected_query=case.item.query,expected_frame=case.frame,expected_files=case.files,
        outer_record=case.outer,expected_sources=case.sources);args.update(changes)
    return d.replay_point(**args)


@pytest.mark.parametrize('kind',['economic','child','primal'])
@pytest.mark.parametrize('p2',[False,True])
def test_all_evidence_families_rebuild_without_backend(tmp_path,monkeypatch,kind,p2):
    case=bundle(tmp_path,kind,p2);built=[];original=d.core.build_point_model
    def build(query):built.append(query.identity);return original(query)
    monkeypatch.setattr(d.core,'build_point_model',build)
    result=run(case)
    assert len(built)==2 and result['evidence']==case.item and result['exact_typed_evidence_match']
    assert result['replay_state']=='imported_replay_matches_saved'
    assert result['evidence_family']==dict(economic='economic_kkt',child='child_lp_kkt',primal='primal_point')[kind]
    assert result['independent_audit'] is not None
    assert all(result[n] is False for n in ('scientific_evidence_adopted','journal_replayed','full_139_independently_verified',
        'fx_temporal_backing','rigorous_bound_certified','resource_admission','formal_result','expected_query_provenance_independently_verified'))


@pytest.mark.parametrize('failure',['warning','time','dual'])
def test_numeric_unresolved_is_reproduced_without_adoptable_evidence(tmp_path,failure):
    case=bundle(tmp_path,'economic',numeric_failure=failure);result=run(case)
    assert result['replay_state']=='numeric_unresolved_reproduced' and result['evidence'] is None
    assert result['evidence_ref'] is None and result['infeasibility_inferred'] is False


def test_unknown_outer_quiet_rejects_before_any_file_or_source_read(tmp_path,monkeypatch):
    record=outer_process();record['job_quiet_confirmed']=False
    monkeypatch.setattr(d.codec,'read_bytes',lambda *a,**kw:pytest.fail('unknown quiet read disk'))
    with pytest.raises(ValueError,match='quiet required'):d.replay_point(tmp_path,None,None,None,record,None)


@pytest.mark.parametrize('fault',['query','frame','source','inventory','outside_member'])
def test_external_expectation_and_process_bindings_are_required(tmp_path,fault):
    case=bundle(tmp_path)
    if fault=='query':case.item=replace(case.item,query=replace(case.item.query,request=replace(case.item.query.request,hour=12)))
    elif fault=='frame':case.frame['pins_sha']='d'*64
    elif fault=='source':case.sources[d.SOURCES[0]]['sha256']='f'*64
    elif fault=='inventory':case.files['native.log']['sha256']='f'*64
    else:case.outer['quiescence_witness']['member_identities']=case.outer['quiescence_witness']['member_identities'][:1];case.outer['quiescence_witness']['total_processes']=case.outer['quiescence_witness']['observed_unique_member_handles']=1
    with pytest.raises(ValueError):run(case)


@pytest.mark.parametrize('fault',['row','objective','cleanup','options','evidence','orphan'])
def test_self_consistent_file_hashes_do_not_replace_numeric_reconstruction(tmp_path,fault):
    case=bundle(tmp_path,'child');raw=json.loads((case.root/'native.json').read_bytes())
    if fault=='row':raw['solution']['row_value'][0]+=1
    elif fault=='objective':raw['objective_value']+=1
    elif fault=='cleanup':raw['cleanup_error']=dict(type='OSError',message='failed')
    elif fault=='options':raw['options']['primal_feasibility_tolerance']=1e-3
    elif fault=='evidence':
        result=json.loads((case.root/'result.json').read_bytes());result['evidence_ref']=json.loads((case.root/'request.json').read_bytes())['query_ref'];save(case.root/'result.json',result)
    else:
        identity,blobs=d.codec.pack('unreferenced')
        for key,value in blobs.items():(case.root/'cas/objects'/(key+'.json')).write_bytes(value)
    if fault in ('row','objective','cleanup','options'):
        save(case.root/'native.json',raw);result=json.loads((case.root/'result.json').read_bytes())
        result['raw_pin']=d.mechanical.pin((case.root/'native.json').read_bytes());save(case.root/'result.json',result)
    refresh(case)
    with pytest.raises(ValueError):run(case)


def test_inventory_bookend_detects_late_drift(tmp_path,monkeypatch):
    case=bundle(tmp_path);original=d.numeric.import_snapshot
    def changed(*args):
        result=original(*args);(case.root/'native.log').write_bytes(b'late drift');return result
    monkeypatch.setattr(d.numeric,'import_snapshot',changed)
    with pytest.raises(ValueError,match='inventory bookend'):run(case)


def test_numeric_equal_signed_zero_substitution_is_rejected_by_typed_sha(tmp_path):
    case=bundle(tmp_path,'primal')
    angles=tuple((i,-value if value==0. else value) for i,value in case.item.point.angles_rad)
    changed=replace(case.item,point=replace(case.item.point,angles_rad=angles))
    assert changed==case.item
    identity,blobs=d.codec.pack(changed)
    assert identity!=d.codec.pack(case.item)[0]
    for key,value in blobs.items():(case.root/'cas/objects'/(key+'.json')).write_bytes(value)
    result=json.loads((case.root/'result.json').read_bytes());result['evidence_ref']=identity;save(case.root/'result.json',result)
    refresh(case)
    with pytest.raises(ValueError,match='exact evidence differs'):run(case)


def test_primal_only_does_not_promote_invalid_native_dual_arrays(tmp_path):
    case=bundle(tmp_path,'primal');raw=json.loads((case.root/'native.json').read_bytes())
    raw['solution'].update(dual_valid=False,col_dual=['not usable duals'],row_dual=['not usable duals'])
    save(case.root/'native.json',raw);result=json.loads((case.root/'result.json').read_bytes())
    result['raw_pin']=d.mechanical.pin((case.root/'native.json').read_bytes());save(case.root/'result.json',result)
    refresh(case)
    replay=run(case)
    assert replay['evidence_family']=='primal_point' and replay['evidence'].economic is replay['evidence'].child_lp is None


def test_current_predecessor_sources_are_bound_and_network_oversize_never_builds(tmp_path,monkeypatch):
    case=bundle(tmp_path)
    data=case.item.query.request.data
    oversized=replace(case.item.query,request=replace(case.item.query.request,
        data=replace(data,buses=data.buses+tuple(replace(data.buses[0],index=100+i) for i in range(22)))))
    monkeypatch.setattr(d.numeric,'compile_problem',lambda *a:pytest.fail('oversized query compiled'))
    with pytest.raises(ValueError,match='network exceeds'):run(case,expected_query=oversized)


def test_saved_P1_first_three_points_use_independently_built_queries_and_raw():
    from src.staged_rts24_reference_queries_v1 import reference_requests
    root=Path(__file__).resolve().parents[1]
    p1=root/'results/tables/staged_rts24_native_v1_non_authoritative/p1_01'
    anchor=p1.parent/'p1_execution_review_01/postcheck_03.stdout.json'
    raw_anchor=anchor.read_bytes();assert sha256(raw_anchor).hexdigest()=='c6a25cd96c8a4a2cf293d41fe51bc7905db63fbc35253076f97e9239a4f22473'
    files=json.loads(raw_anchor)['p1_files'];assert len(files)==683
    def preserve():
        assert all(d.mechanical.pin((p1/name).read_bytes())==value for name,value in files.items())
    preserve()
    start=json.loads((p1/'start.json').read_bytes());outer=json.loads((p1/'launcher.json').read_bytes())
    fixture=d.core.load_fixture();group=reference_requests(fixture,'on_time','early','full_temporal',-2)
    requests={q.role:q for q in group['requests']}
    source=d.source_pins();parent_evidence=None;reports=[]
    roles=('reference_base_P0','recovery_min_meter','recovery_max_meter')
    for ordinal,role in enumerate(roles,1):
        request=requests[role]
        query=d.core.bind(request) if parent_evidence is None else d.core.bind(request,
            parent_evidence.query,parent_evidence.point,parent_evidence.economic)
        prefix=f'points/point_{ordinal:04d}/'
        held={name[len(prefix):]:value for name,value in files.items() if name.startswith(prefix)}
        # Registration SHA comes from the independently pinned start record,
        # not from the point request currently being audited.
        frame_expected=dict(ordinal=ordinal,pins_sha=d.core.digest(start['pins']),registration_sha=start['registration_sha'],execution_binding=None)
        replay=d.replay_point(p1/prefix,query,frame_expected,held,outer,source)
        if ordinal==1:parent_evidence=replay['evidence']
        reports.append(dict(ordinal=ordinal,family=replay['evidence_family'],evidence_ref=replay['evidence_ref']))
        assert replay['replay_state']=='imported_replay_matches_saved' and replay['outer_monitor_schema']=='legacy_guard'
        assert replay['scientific_evidence_adopted'] is False
    preserve();assert anchor.read_bytes()==raw_anchor
    print(json.dumps(dict(saved_P1_points_replayed_once=reports,new_native_calls=0,P1_683_files_unchanged=True)))


@pytest.mark.parametrize('field',['terminal_files','terminal_bytes'])
def test_package_counters_cannot_be_smaller_than_local_point(tmp_path,field):
    case=bundle(tmp_path);record=json.loads((case.root/'process.json').read_bytes());record[field]=0
    save(case.root/'process.json',record);case.files=d.mechanical.inventory(case.root)['pins']
    with pytest.raises(ValueError,match='below local point'):run(case)


def test_point_resource_stop_rejects_before_numeric_model_build(tmp_path,monkeypatch):
    case=bundle(tmp_path);record=json.loads((case.root/'process.json').read_bytes());record['outer_seconds']=10.01
    save(case.root/'process.json',record);case.files=d.mechanical.inventory(case.root)['pins']
    monkeypatch.setattr(d.numeric,'compile_problem',lambda *a:pytest.fail('over-cap point was compiled'))
    with pytest.raises(ValueError,match='process protocol'):run(case)


def test_failed_but_quiet_outer_only_allows_local_diagnostic_not_package_adoption(tmp_path):
    case=bundle(tmp_path);case.outer.update(exit_code=2,stop_reason='child_exit_nonzero')
    result=run(case)
    assert result['replay_state']=='imported_replay_matches_saved'
    assert result['scientific_evidence_adopted'] is result['resource_admission'] is result['formal_result'] is False


@pytest.mark.parametrize('module_name',['src.staged_rts24_causal_v1','src.staged_rts24_p2_outer_observation_v1',
    'src.staged_rts24_process_guard_v3','src.grid.rts24','src.rq2_joint_deliverability_boundary_v1.debt_cohorts'])
def test_loaded_type_and_process_modules_cannot_come_from_other_paths(tmp_path,monkeypatch,module_name):
    import sys
    case=bundle(tmp_path);module=sys.modules[module_name];copy=tmp_path/'different.py';copy.write_bytes(Path(module.__file__).read_bytes())
    monkeypatch.setattr(module,'__file__',str(copy))
    with pytest.raises(ValueError,match='loaded replay module path'):run(case)


@pytest.mark.parametrize('name',['native.json','point_observations.json'])
@pytest.mark.parametrize('field',['formal_result','scientific_evidence_adopted','authority','extra'])
def test_self_consistent_extra_authority_fields_are_rejected(tmp_path,name,field):
    case=bundle(tmp_path);record=json.loads((case.root/name).read_bytes());record[field]=True;save(case.root/name,record)
    if name=='native.json':
        result=json.loads((case.root/'result.json').read_bytes());result['raw_pin']=d.mechanical.pin((case.root/name).read_bytes());save(case.root/'result.json',result)
    refresh(case)
    with pytest.raises(ValueError,match='(raw record fields|closed fields)'):run(case)


def test_P2_registration_cannot_be_null_even_with_new_matching_file_hashes(tmp_path):
    case=bundle(tmp_path,p2=True);case.frame['registration_sha']=None
    request=json.loads((case.root/'request.json').read_bytes());request['registration_sha']=None;save(case.root/'request.json',request)
    result=json.loads((case.root/'result.json').read_bytes());result['request_sha']=d.mechanical.pin((case.root/'request.json').read_bytes())['sha256'];save(case.root/'result.json',result)
    refresh(case)
    with pytest.raises(ValueError,match='SHA'):run(case)


def test_noncanonical_absolute_historical_log_path_is_rejected(tmp_path):
    case=bundle(tmp_path);raw=json.loads((case.root/'native.json').read_bytes());raw['options']['log_file']=str(case.root/'native.log').replace('\\','/')
    assert raw['options']['log_file']!=str(Path(raw['options']['log_file']).absolute())
    save(case.root/'native.json',raw);result=json.loads((case.root/'result.json').read_bytes());result['raw_pin']=d.mechanical.pin((case.root/'native.json').read_bytes());save(case.root/'result.json',result)
    refresh(case)
    with pytest.raises(ValueError,match='log path'):run(case)


@pytest.mark.parametrize('failure',[None,'warning'])
def test_full_logical_read_and_pack_accounting_is_observed(tmp_path,monkeypatch,failure):
    case=bundle(tmp_path,numeric_failure=failure);calls=dict(source=0,point=0,pack=0)
    original_read=d.codec.read_bytes;original_bounded=d.mechanical.bounded_file_bytes;original_pack=d.codec.pack
    def read(path,*a,**kw):
        calls['point' if Path(path).is_relative_to(case.root) else 'source']+=1
        return original_read(path,*a,**kw)
    def bounded(path,*a,**kw):
        assert Path(path).is_relative_to(case.root)
        calls['point']+=1
        return original_bounded(path,*a,**kw)
    def pack(*a,**kw):calls['pack']+=1;return original_pack(*a,**kw)
    monkeypatch.setattr(d.codec,'read_bytes',read);monkeypatch.setattr(d.mechanical,'bounded_file_bytes',bounded);monkeypatch.setattr(d.codec,'pack',pack)
    result=run(case)
    objects=sum(name.startswith('cas/objects/') for name in case.files)
    assert calls==dict(source=86,point=6*objects+16,pack=5 if failure is None else 3)
    assert (result['evidence'] is None) is (failure is not None)
    print(json.dumps(dict(oracle='single_point_logical_reads',numeric_failure=failure,cas_objects=objects,**calls)))
