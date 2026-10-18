"""Real genesis journals and selector replay over explicit synthetic source seams."""
from dataclasses import replace
from fractions import Fraction as Q
from importlib.metadata import version
import json
from types import SimpleNamespace

import pytest

from experiments import h1_selector_input_snapshot_development_v1 as m
from tests.test_h1_common_owner_genesis_development_v1 import case,create
from tests.test_h1_phase_owner_development_v1 import setup
from tests.test_h1_persistent_owner_development_v1 import setup as legacy_setup
from tests import test_h1_selector_raw_science_development_v1 as producer
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver


@pytest.fixture
def context(case,setup,monkeypatch,no_solver,request):
    s=setup
    spec=replace(s.manifest.solver_specification,name='gurobi',expected_package_version=version('gurobipy'))
    s.manifest=replace(s.manifest,solver_specification=spec)
    if getattr(request,'param',None)=='business_unresolved':
        lane=s.manifest.lanes[0]
        lane=replace(lane,mechanism=replace(lane.mechanism,flexible_fraction=Q(1,2)))
        s.manifest=replace(s.manifest,lanes=(lane,))
    f=s.currents[0].prepared_current.frame
    budget=m.sequence.configuration_api.process.TaskProcessBudget(300,.05,512*1024**2,768*1024**2,2)
    config=m.sequence.configuration_api.SelectorRunConfiguration(f.normal_network_identity,
        tuple(g.uid for g in f.info.network.units),s.manifest.reference_selector,s.manifest.actual_selector,
        spec,s.manifest.replay_limits,budget,budget,2,2)
    # Cache only identities of unchanged dependencies; persistence/science run normally.
    for module in (m.common,m.sequence.stage,m.sequence.bridge,m.sequence.configuration_api):
        pin=module.implementation_identity()
        monkeypatch.setattr(module,'implementation_identity',lambda pin=pin:pin)
    with create(case) as owner:
        yield SimpleNamespace(owner=owner,config=config,s=s,case=case,cap=2**30)


def reference(c):return m.capture_reference(c.owner,c.config,max_archive_bytes=c.cap)
def rebuild(raw):return m.rebuild(raw,expected_sha256=m.io.digest(raw))
def altered(raw,change):
    doc=json.loads(raw);change(doc);return m.encode(doc)


def archive(c,monkeypatch,tmp_path,*,fractional=False):
    raw=reference(c);item=rebuild(raw)
    original=m.sequence.bridge._run_stage
    def run(path,*args,**kw):
        with monkeypatch.context() as patch:
            producer.install(patch,path,m.phase.RREF)
            if fractional:
                direct=m.sequence.bridge.capture.GurobiDirect
                presolve=direct._presolve
                def fractional_presolve(self,*a,**k):
                    presolve(self,*a,**k)
                    values={'reference_power':10.25,'generation[G1]':30.25,'selector_deviation[G1]':14.75}
                    for v in self.native.variables:
                        if v.VarName in values:v.X=values[v.VarName]
                    objective=self.native.objective.constant+sum(c*v.X for v,c in self.native.objective.terms)
                    self.native.ObjVal=self.native.ObjBound=self.native.ObjBoundC=objective
                    self.result.problem.lower_bound=self.result.problem.upper_bound=objective
                    for name,value in values.items():self.result.solution[0].variable[name]['Value']=value
                patch.setattr(direct,'_presolve',fractional_presolve)
            return original(path,*args,**kw)
    monkeypatch.setattr(m.sequence.bridge,'_run_stage',run)
    root=tmp_path/'reference_sequence_non_authoritative'
    owner=m.sequence.OwnedSelectorSequence(root,item.frame,item.disclosure,item.before,
        max_archive_bytes=c.cap,run_configuration=c.config,**item.arguments)
    receipt=owner.run();owner.validate_completion(receipt)
    return dict(reference_root=root,reference_terminal_sha256=receipt.terminal_sha256,
                reference_request_sha256=receipt.request_sha256,reference_max_archive_bytes=c.cap)


def test_reference_roundtrip_uses_fresh_source_and_leaves_genesis_empty(context):
    c=context;before=c.owner.inspect();calls=len(c.s.calls)
    raw=reference(c);first=rebuild(raw);second=rebuild(raw)
    assert first.before.identity==second.before.identity
    assert first.arguments['lane']==m.phase.RREF and first.arguments['power'] is None
    assert first.frame.info.relative_hour==0 and len(c.s.calls)>calls
    assert c.owner.inspect()==before and c.owner._holder.inspect()==()
    assert not any(v for _,v in first.authority_flags)
    assert not any(json.loads(raw)[k] for k in m.FLAGS)
    with pytest.raises(ValueError,match='exact live common owner'):
        m.capture_reference(json.loads(raw),c.config,max_archive_bytes=c.cap)


@pytest.mark.parametrize('fault',['hour','role','extra','power','source_pin','network','uid','manifest',
    'holder_head','owner_head','scope','implementation','projection','fraction','config_extra',
    'max_events','max_event_bytes','max_archive_bytes','capacity_label','relative_root','noncanonical_root'])
def test_snapshot_mutations_rejected(context,fault):
    raw=reference(context)
    def change(doc):
        d=doc['declaration']
        if fault=='hour':d['hour']=1
        elif fault=='role':d['role']='N'
        elif fault=='extra':d['surprise']=True
        elif fault=='power':d['power']=5
        elif fault=='source_pin':d['source_binding']['binding_sha256']='0'*64
        elif fault=='network':d['run_configuration']['network_sha256']='0'*64
        elif fault=='uid':d['run_configuration']['generation_uids']=['G2']
        elif fault=='manifest':d['manifest']['accounting_period_id']='different'
        elif fault=='holder_head':d['provenance']['holder_receipt']['head']='0'*64
        elif fault=='owner_head':d['provenance']['owner_receipt']['heads'][0]='0'*64
        elif fault=='scope':doc['owner_consumption_authorized']=True
        elif fault=='implementation':doc['implementation']='0'*64
        elif fault=='projection':doc['projection']['before_identity']='0'*64
        elif fault=='fraction':d['manifest']['lanes'][0]['mechanism']['alpha']={'numerator':'2','denominator':'4'}
        elif fault in ('max_events','max_event_bytes','max_archive_bytes'):d['manifest'][fault]+=1
        elif fault=='capacity_label':d['manifest']['lanes'][0]['policy']['capacity_declaration_id']='other'
        elif fault=='relative_root':d['provenance']['root']='relative_non_authoritative'
        elif fault=='noncanonical_root':d['provenance']['root']+='/'
        else:d['run_configuration']['extra']=1
    with pytest.raises((ValueError,AssertionError)):rebuild(altered(raw,change))


@pytest.mark.parametrize('fault',['external_pin','duplicate','noncanonical','oversize','mutable'])
def test_snapshot_byte_envelope(context,fault):
    raw=reference(context);pin=m.io.digest(raw)
    if fault=='external_pin':pin='0'*64
    elif fault=='duplicate':raw=raw[:-2]+b',"formal_result":false}\n';pin=m.io.digest(raw)
    elif fault=='noncanonical':raw=b' '+raw;pin=m.io.digest(raw)
    elif fault=='oversize':raw=b' '*(m.CAP+1);pin=m.io.digest(raw)
    else:raw=bytearray(raw)
    with pytest.raises(ValueError):m.rebuild(raw,expected_sha256=pin)


@pytest.mark.parametrize('fault',['source','global','guard','configuration'])
def test_capture_bookends_reject_drift(context,monkeypatch,fault):
    c=context;original=m._build;calls=[]
    def change(d):
        out=original(d);calls.append(True)
        if len(calls)==1:
            if fault=='source':
                current=c.s.currents[0]
                object.__setattr__(current,'source_projection_audit_payload',current.source_projection_audit_payload+b' ')
            elif fault=='global':
                c.case.global_.head='d'*64;c.case.global_.history.append(('d'*64,{}))
            elif fault=='guard':c.owner._operation=object()
            else:object.__setattr__(c.config,'actual_non_solver_seconds',3)
        return out
    monkeypatch.setattr(m,'_build',change)
    with pytest.raises(ValueError):reference(c)
    assert not c.case.guard.locked()


def test_actual_derives_exact_power_and_rechecks_reference(context,monkeypatch,tmp_path):
    c=context;ref=archive(c,monkeypatch,tmp_path)
    raw=m.capture_actual(c.owner,c.config,max_archive_bytes=c.cap,lane_id='joint',**ref)
    item=rebuild(raw);d=json.loads(raw);p=d['projection']['dependency']
    # Independent analytic fixture: B=25MW, Rref P=10MW -> grid request=15MW.
    # CFE request=5MW, combined served=20MW, so actual DC power=5MW.
    assert m._fraction(p['reference_request_exact'])==Q(15)
    assert m._fraction(p['actual_power_exact'])==Q(5)
    assert item.arguments['power']==m.selection.physical.RelativeDcPower(0,'5','1','mechanism_assumption')
    assert item.before.identity==m.phase._initial(c.s.manifest,c.s.currents[0]).lanes[0][1].actual.identity
    assert not any(v for _,v in item.authority_flags)
    for change in (lambda doc:doc['declaration'].update(lane_id='absent'),
                   lambda doc:doc['declaration']['reference'].update(request_sha256='0'*64),
                   lambda doc:doc['projection']['dependency'].update(actual_power_exact={'numerator':'6','denominator':'1'})):
        with pytest.raises(ValueError):rebuild(altered(raw,change))
    terminal=ref['reference_root']/'terminal.json';terminal.write_bytes(terminal.read_bytes()+b' ')
    with pytest.raises(ValueError):rebuild(raw)


def test_actual_incomplete_reference_rejected(context,tmp_path):
    root=tmp_path/'incomplete_non_authoritative';root.mkdir()
    with pytest.raises((ValueError,FileNotFoundError)):
        m.capture_actual(context.owner,context.config,max_archive_bytes=context.cap,lane_id='joint',
            reference_root=root,reference_terminal_sha256='0'*64,reference_request_sha256='0'*64,
            reference_max_archive_bytes=context.cap)
    assert not list(root.iterdir())


def test_fractional_reference_and_actual_power_oracle(context,monkeypatch,tmp_path):
    c=context;ref=archive(c,monkeypatch,tmp_path,fractional=True)
    raw=m.capture_actual(c.owner,c.config,max_archive_bytes=c.cap,lane_id='joint',**ref)
    item=rebuild(raw);projection=json.loads(raw)['projection']['dependency']
    # B=25, P_ref=10.25 -> g=59/4. CFE=5, so P_actual=25-59/4-5=21/4.
    assert m._fraction(projection['reference_request_exact'])==Q(59,4)
    assert m._fraction(projection['actual_power_exact'])==Q(21,4)
    assert item.arguments['power']==m.selection.physical.RelativeDcPower(0,'21','4','mechanism_assumption')


@pytest.mark.parametrize('context',['business_unresolved'],indirect=True)
def test_real_business_rule_unresolved_has_no_actual_snapshot(context,monkeypatch,tmp_path):
    c=context;ref=archive(c,monkeypatch,tmp_path)
    before=c.owner.inspect()
    with pytest.raises(ValueError,match='business candidate unresolved'):
        m.capture_actual(c.owner,c.config,max_archive_bytes=c.cap,lane_id='joint',**ref)
    assert c.owner.inspect()==before and c.owner._holder.inspect()==()
