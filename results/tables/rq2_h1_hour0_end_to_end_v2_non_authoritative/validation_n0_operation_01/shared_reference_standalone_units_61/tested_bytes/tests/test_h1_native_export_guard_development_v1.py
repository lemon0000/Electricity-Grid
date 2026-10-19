from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sqlite3

import pytest
from pyomo.environ import ConcreteModel, Objective, Var

from experiments import h1_native_export_guard_development_v1 as api
from experiments import h1_raw_ingress_development_v1 as ingress
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver

ROOT=Path(__file__).resolve().parents[1]


class Expression:
    def __init__(self, terms, constant=1.): self.terms,self.constant=terms,constant
    def size(self):return len(self.terms)
    def getVar(self,i):return self.terms[i][0]
    def getCoeff(self,i):return self.terms[i][1]
    def getConstant(self):return self.constant


def live_case():
    m=ConcreteModel()
    m.x=Var();m.y=Var()
    m.obj=Objective(expr=3*m.x+1)
    x,y=object(),object()
    arguments=dict(forward_pairs=((m.x,x),(m.y,y)),reverse_pairs=((x,m.x),(y,m.y)),
        native_variables=(x,y),native_expression=Expression([(x,3.)]),native_model_sense=1)
    return m,arguments


def test_live_map_exact_inverse_and_canonical_algebra_without_solver():
    model,args=live_case()
    result=api.live_export(model,**args)
    assert result['live_map_correspondence_checked']
    assert not result['native_execution_authenticated'] and not result['native_export_coverage']


@pytest.mark.parametrize('sense',[-1,True,1.,None])
def test_native_sense_must_be_exact_minimization(sense):
    model,args=live_case()
    args['native_model_sense']=sense
    with pytest.raises(api.ExportUnresolved,match='minimization sense'):
        api.live_export(model,**args)


@pytest.mark.parametrize('bad',['reverse','foreign_pyomo','missing','duplicate_variable','unmapped_term',
    'duplicate_term','coefficient','constant','many_terms','nan','quadratic'])
def test_live_guard_rejects_counterexamples(bad):
    m,args=live_case()
    x,y=args['native_variables']
    if bad=='reverse':args['reverse_pairs']=((x,m.y),(y,m.x))
    elif bad=='foreign_pyomo':args['reverse_pairs']=((x,m.clone().x),(y,m.y))
    elif bad=='missing':args['forward_pairs']=args['forward_pairs'][:1]
    elif bad=='duplicate_variable':args['native_variables']=(x,x)
    elif bad=='unmapped_term':args['native_expression']=Expression([(object(),3.)])
    elif bad=='duplicate_term':args['native_expression']=Expression([(x,1.5),(x,1.5)])
    elif bad=='coefficient':args['native_expression']=Expression([(x,4.)])
    elif bad=='constant':args['native_expression']=Expression([(x,3.)],2.)
    elif bad=='many_terms':args['native_expression']=Expression([(x,0.)]*363)
    elif bad=='nan':args['native_expression']=Expression([(x,float('nan'))])
    else:m.obj.set_value(m.x**2)
    with pytest.raises(api.ExportUnresolved):api.live_export(m,**args)


@pytest.fixture(scope='module')
def saved_origin():
    from src.rq2_joint_deliverability_boundary_v1 import normal_h1_full_job_v3 as job
    _,request=job.gates.verify_package(ROOT/'configs/rq2_normal_h1_calibration_v3.OUTER.SHA256SUMS.json',
        'e3acc7a6de1c1863ab64a8c1ae67ded9676e01c564a3d4ef2d0be29252f0edcf')
    packet=job._packet(request)  # Read-only origin binding, no Job execution.
    path=ROOT/'results/tables/rq2_normal_h1_origin_calibration_v3_non_authoritative/collector_non_authoritative/stages_non_authoritative/h1_chunk_journal.sqlite3'
    reports=[]
    with sqlite3.connect(path.as_uri()+'?mode=ro&immutable=1',uri=True) as db:
        for seq,metadata,size,pin in db.execute('SELECT seq,metadata,payload_bytes,payload_sha FROM events WHERE payload_bytes>0 ORDER BY seq'):
            raw=b''.join(row[0] for row in db.execute('SELECT payload FROM chunks WHERE event_seq=? ORDER BY chunk_index',(seq,)))
            assert len(raw)==size and sha256(raw).hexdigest()==pin
            reports.append((json.loads(metadata),raw))
    assert len(reports)==232
    return job.source.h1.model_api,packet,reports


def stage_model(saved_origin,index):
    model_api,packet,reports=saved_origin
    locks=tuple(float.fromhex(meta['lock_hex']) for meta,_ in reports[:index])
    request=model_api.H1StageRequest(packet.inputs,locks)
    return model_api.build_h1_stage_model(request,expected_identity=model_api.h1_stage_identity(request))


def test_all_232_saved_origin_reports_match_actual_stage_algebra(saved_origin):
    for index,(_,raw) in enumerate(saved_origin[2]):
        result=api.saved_report(raw,stage_model(saved_origin,index))
        assert result['raw_sha256']==sha256(raw).hexdigest()
        assert result['conditional_bound_bytes']==929218
        assert result['report_shape_and_objective_correspondence_checked']
        assert result['full_scientific_replay_required']
        assert not result['live_reverse_map_checked'] and not result['native_export_coverage']
        assert not result['scientific_acceptance'] and not result['resource_admission']


@pytest.mark.parametrize('bad',['missing_variable','duplicate_variable','foreign_variable','native_coefficient',
    'canonical_coefficient','reference','algebra','exact','flag','constraints','no_provenance','duplicate_terms'])
def test_report_rejects_model_and_provenance_mismatch(saved_origin,bad):
    # Stage 1 has one objective term; duplicate halves preserve exact algebra.
    raw=saved_origin[2][1][1]
    report=json.loads(raw)
    p=report['provenance']
    if bad=='missing_variable':report['assignment'].pop()
    elif bad=='duplicate_variable':report['assignment'][1]=deepcopy(report['assignment'][0])
    elif bad=='foreign_variable':report['assignment'][0][0]='other'
    elif bad=='native_coefficient':p['ordered_native_objective_terms'][0][1]=(2.).hex()
    elif bad=='canonical_coefficient':p['ordered_objective_terms'][0][1]=(2.).hex()
    elif bad=='reference':p['referenced_assignment'][0][1]=(2.).hex()
    elif bad=='algebra':p['canonical_objective_algebra'][0]='1'
    elif bad=='exact':p['native_exact_objective']['numerator']='2'
    elif bad=='flag':p['native_algebra_equals_canonical_algebra']=False
    elif bad=='constraints':report['constraints']+=1
    elif bad=='no_provenance':report['provenance']=None
    else:
        term=deepcopy(p['ordered_native_objective_terms'][0]);term[1]=(0.5).hex()
        p['ordered_native_objective_terms']=[term,deepcopy(term)]
    with pytest.raises(api.ExportUnresolved):api.saved_report(api.syntax.encode(report),stage_model(saved_origin,1))


@pytest.mark.parametrize('bad',['foreign_assignment','variable_cap','constraint_cap','term_cap'])
def test_guard_failure_after_ingress_preserves_exact_raw_and_stops(tmp_path,saved_origin,bad):
    report=json.loads(saved_origin[2][0][1])
    if bad=='foreign_assignment':report['assignment'][0][0]='foreign'
    elif bad=='variable_cap':report['variables']=892
    elif bad=='constraint_cap':report['constraints']=1273
    else:
        report['provenance']['ordered_native_objective_terms'] += [deepcopy(report['provenance']['ordered_native_objective_terms'][0])]
        assert len(report['provenance']['ordered_native_objective_terms'])==363
    raw=api.syntax.encode(report)
    model=stage_model(saved_origin,0)
    writer=ingress.Ingress(tmp_path/'ingress_non_authoritative','a'*64,stages=232)
    with pytest.raises(api.ExportUnresolved):
        writer.deliver(0,lambda:raw,lambda saved:api.saved_report(saved,model))
    assert (writer.root/'000/raw.bin').read_bytes()==raw
    assert (writer.root/'000/raw_receipt.json').exists()
    assert not (writer.root/'000/outcome.json').exists()
    with pytest.raises(ValueError,match='poisoned'):
        writer.deliver(0,lambda:pytest.fail('retry'),lambda x:x)
