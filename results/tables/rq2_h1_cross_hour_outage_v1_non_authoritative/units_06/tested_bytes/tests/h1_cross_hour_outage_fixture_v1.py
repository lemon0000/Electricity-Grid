"""Explicit two-generator toy inputs and fake candidates; no run authority."""
from copy import deepcopy
from dataclasses import asdict, replace
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys

import pytest
from pyomo.environ import Var, value
from pyomo.opt import SolverResults, SolverStatus, SolutionStatus, TerminationCondition
from pyomo.opt.results.problem import ProblemSense
from pyomo.repn import generate_standard_repn

from experiments import h1_cross_hour_owner_development_v2 as m
from tests import test_h1_cross_hour_owner_development_v1 as prior
from tests.test_rq2_continuous_grid_normal_v1 import fixture

Q=prior.Q
HOURS=3
CAP=Q(24)


def producer_budget():
    # Per-hour complete roster: four Rref stages plus three for each lane.
    return prior.producer_budget(max_solver_calls=13,max_total_solver_seconds=13.)


def install_case(env, patch):
    """N has both units; the disclosed G1 outage affects only Rref/Actual."""
    upstream, config, origin, state=env
    data=fixture(HOURS).data
    first=replace(data.generators[0],p_max_mw=30.,ramp_mw_per_minute=.4,ramp_mw_per_hour=24.,
        cost_breakpoints_mw=(10.,20.,25.,30.),cost_values_usd_per_hour=(10.,20.,25.,30.))
    second=replace(data.generators[0],uid='G2',p_max_mw=40.,
        cost_breakpoints_mw=(10.,20.,30.,40.),cost_values_usd_per_hour=(20.,40.,60.,80.))
    assert CAP==min(Q(str(first.p_max_mw)),60*Q(str(first.ramp_mw_per_minute)))==Q(str(first.ramp_mw_per_hour))
    points=tuple(replace(p,generator_min_mw={'G1':10.,'G2':10.},
                         generator_max_mw={'G1':30.,'G2':40.}) for p in data.hourly_points)
    state['data']=replace(data,generators=(first,second),hourly_points=points)
    source=m.saved.source.source
    original=source.windows.load_source_window
    def load(kind,split,start,hours,**kwargs):
        if not 0<=start<len(state['data'].hourly_points):
            raise ValueError('window not contained in one verified same-split source chain')
        result=original(kind,split,start,hours,**kwargs)
        result['chain']['chain_id']='test-only-outage-chain-'+kind
        row=result['rows'][0]
        if kind=='power':
            active=start<2
            row.update(block_id='synthetic',active_event_id='toy-G1-outage' if active else '',
                active_component_type='generator' if active else '',active_component_uid='G1' if active else '',
                cfe_call_fraction='0.6' if active else '0.2')
        else:
            row['workload_fraction']='0.1'
            result['chain']['trace_identity_basis']={'source':'synthetic outage continuation fixture'}
        result.pop('window_identity')
        result['window_identity']=source.windows._hash(result)
        return result
    patch.setattr(source.windows,'load_source_window',load)
    registry=m.saved.source.registry
    package=load('power','training',0,1,outage_seed=origin.outage_seed,
                 expected_config_sha256=origin.config_sha256)['package_manifest_sha256']
    patch.setattr(registry.frozen,'PACKAGE_SHA',package)
    patch.setattr(registry.catalog,'CONFIG_SHA',origin.config_sha256)
    protocol=registry.events.DisclosureProtocol((registry.events.OutageComponent('generator','G1'),),
        'current_n1_outage_overlay_revealed_before_current_action',
        'complete_current_n1_outage_overlay__no_hidden_same_hour_replacement','mechanism_assumption')
    def context(split):
        rows={h:load('power',split,h,1,outage_seed=origin.outage_seed,
                     expected_config_sha256=origin.config_sha256)['rows'][0] for h in range(HOURS)}
        return dict(split=split,protocol=protocol,caps={'G1':CAP},components=(),
            rows={origin.outage_seed:rows},catalog_entries=[dict(source_start=0,observed_end_inclusive=HOURS-1,
                outage_seed=origin.outage_seed,chain_id=f'power:{split}:outage_seed={origin.outage_seed}')],
            gaps=[dict(split=split,outage_seed=origin.outage_seed,raw_start=0)],identity='c'*64,
            split_hour=99,archive_member_sha256='d'*64,cap_table_sha256='e'*64)
    patch.setattr(registry,'_load',context)
    patch.setattr(registry.frozen,'prefix_overlay',lambda *a:(('toy-G1-outage','generator','G1'),))
    patch.setattr(m.saved.source.historical,'_source_paths',lambda d:(
        {Path(d['config_path']),Path(d['upstream_root'])/'SHA256SUMS'},{Path(d['upstream_root'])}))
    return env


def packets(env):
    upstream,config,origin,_=env
    source=m.saved.source.source
    before=None
    result=[]
    for hour in range(HOURS):
        declaration=replace(origin,power_raw_hour=hour,workload_raw_hour=hour)
        observed=source.load_pinned_current(declaration,upstream,config_path=config)
        packet=source.assemble_pinned_current(observed,upstream,expected_identity=observed.identity,
            relative_hour=hour,dc_bus=1,config_path=config,before=before)
        before=source.h1._owned(source.h1.H1NormalBoundary,network_identity=packet.network.identity,
            completed_hours=hour+1,units=(('G1',True,30.,hour+1),('G2',True,15.,hour+1)),
            evidence_role='numerical_lex_candidate')
        result.append((packet,before))
    return tuple(result)


def normal_reports(packet,templates):
    """Fabricated solver values; the actual worker regenerates export/provenance."""
    api=m.normal.base.old.replay.native.model_api
    locks=()
    reports=[]
    for kind,uid in api.stage_order(packet.inputs):
        request=api.H1StageRequest(packet.inputs,locks)
        model=api.build_h1_stage_model(request,expected_identity=api.h1_stage_identity(request))
        vals={v.name:0. for v in model.component_data_objects(Var)}
        for unit,power,parts in (('G1',30.,(10.,5.,5.)),('G2',15.,(5.,0.,0.))):
            vals[f'commitment[0,{unit}]']=1.
            vals[f'startup[0,{unit}]']=float(packet.relative_hour==0)
            vals[f'generation[normal,0,{unit}]']=power
            for i,number in enumerate(parts):vals[f'segment_power[0,{unit},{i}]']=number
        for name,number in vals.items():model.find_component(name).set_value(number,skip_validation=True)
        objective=float(value(model.objective))
        expected=60. if kind=='operating_cost' else 1. if kind=='commitment' else {'G1':30.,'G2':15.}[uid]
        assert objective==expected
        record=deepcopy(json.loads(templates[0 if kind=='operating_cost' else 1 if kind=='commitment' else 2]))
        record['assignment']=sorted((name,float(number).hex()) for name,number in vals.items())
        provenance=record['provenance']
        for field in ('ObjVal','ObjBound','ObjBoundC'):
            provenance['native'][field]['hex']=objective.hex()
        provenance['pyomo_lower_hex']=provenance['pyomo_upper_hex']=objective.hex()
        reports.append(m.normal.io.encode(record));locks+=(objective,)
    assert locks==(60.,1.,1.,30.,15.)
    return tuple(reports)


def controller(root,env,real,patch):
    resolver,ordinal=real
    c=m.normal
    node=resolver.resolve('training_ub',ordinal)
    enrollment=dict(test_only_synthetic_source=True)
    patch.setattr(c.binding,'open_manifest',lambda:resolver)
    patch.setattr(c.binding,'precheck',lambda *a,**kw:node)
    patch.setattr(c.binding,'prevalidate_enrollment',lambda *a,**kw:enrollment)
    def bind(resolver,declaration,**kw):
        opened=c.binding.snapshot.open_snapshot(declaration,
            expected_parent_identity=kw['expected_parent_identity'],expected_anchor_record=kw['expected_anchor_record'])
        try:item=opened.pending_input(**kw['pending_arguments'])
        finally:opened.close()
        item.validate(expected_receipt_sha256=kw['expected_pending_receipt_sha256'])
        request=dict(parent_declaration=declaration,pending_arguments=kw['pending_arguments'],
            input_receipt=json.loads(item.receipt),input_receipt_sha256=item.receipt_sha256,budget=asdict(kw['job_budget']))
        return c._historical_binding(item.packet,request,node,enrollment)
    patch.setattr(c.binding,'bind',bind)
    upstream,config,origin,state=env
    return m.PhaseController(root,c.base.parent.source.static_network(state['data']),
        replace(prior.spec(),time_limit_seconds=5.),c.base.old.replay.H1HourReplayLimits(5,100,500),
        resolver=resolver,family='training_ub',ordinal=ordinal,origin=origin,upstream_root=upstream,
        config_path=config,dc_bus=1,hours=192,
        budget=c.base.old.process.TaskProcessBudget(240.,.05,512*1024**2,768*1024**2,2.))


def install_launcher(patch,base,reports,hour):
    from experiments import h1_timed_job_controller_development_v1 as timed
    raw_root=base/f'normal_templates_{hour}';raw_root.mkdir()
    for i,raw in enumerate(reports):(raw_root/f'{i:03d}.bin').write_bytes(raw)
    dependency=str(Path(importlib.util.find_spec('pygments').origin).parent.parent)
    code=(f'import sys;sys.path[:0]=[{str(Path.cwd())!r},{str(Path.cwd()/"tests")!r}];sys.path.append({dependency!r});'
        'from tests.h1_cross_hour_outage_fixture_v1 import child_main;'
        f'child_main({str(base)!r},{str(raw_root)!r},*sys.argv[1:])')
    wrapped='try:\n    '+code+'\nexcept BaseException:\n    import traceback\n    from pathlib import Path\n    (Path.cwd()/"error.txt").write_bytes(traceback.format_exc().encode()[:8192])\n    raise\n'
    patch.setattr(timed,'_argv',lambda path,pin:[sys.executable,'-I','-B','-c',wrapped,str(path),pin])


def child_main(base,raw_root,path,pin):
    from tests.test_rq2_normal_h1_source_binding_v1 import supplied
    from tests.test_h1_saved_source_parent_development_v1 import environment
    from tests.test_h1_timed_worker_hour_development_v1 import install
    base=Path(base);patch=pytest.MonkeyPatch()
    mkdir,write=Path.mkdir,Path.write_bytes
    expected={base/'upstream/SHA256SUMS':b'synthetic-current-source\n',base/'source.yaml':b'{}'}
    with pytest.MonkeyPatch.context() as temporary:
        def same_mkdir(path,*a,**kw):
            if path==base/'upstream':assert path.is_dir();return None
            return mkdir(path,*a,**kw)
        def same_write(path,data):
            if path in expected:assert path.read_bytes()==data==expected[path];return len(data)
            return write(path,data)
        temporary.setattr(Path,'mkdir',same_mkdir);temporary.setattr(Path,'write_bytes',same_write)
        env=supplied.__wrapped__(base,patch)
    environment.__wrapped__(env,patch)
    install_case(env,patch)
    prior.no_solver.__wrapped__(patch)
    reports=[p.read_bytes() for p in sorted(Path(raw_root).glob('*.bin'))]
    assert len(reports)==5
    solvers=install(patch,Path(path).parent/'worker_non_authoritative',reports)
    m.normal.base.entry.execute(path,pin)
    assert [s.apply_calls for s in solvers]==[1]*5 and [s.close_calls for s in solvers]==[1]*5


def install_selectors(patch,*,timeout_call=17):
    calls=[]
    def create(specification):
        class Fake:
            def solve(self,model,**kwargs):
                index=len(calls)
                vals={v.name:0. for v in model.component_data_objects(Var)}
                reference=hasattr(model,'reference_power')
                # In this three-hour toy, outage bounds give zero at h0/h1;
                # at h2 the 24 MW return limit is an actual_ramp constraint.
                cap=min(float(model.generation['G1'].ub),float(CAP))
                if reference:
                    power=min(25.,cap+float(model.generation['G2'].ub)-20.)
                    vals['reference_power']=power
                else:power=-float(generate_standard_repn(model.balance[1].body).constant)-20.
                g1=min(30.,cap,20.+power-float(model.generation['G2'].lb))
                g2=20.+power-g1
                vals.update({'generation[G1]':g1,'generation[G2]':g2,
                    'selector_deviation[G1]':abs(g1-30.),'selector_deviation[G2]':abs(g2-15.)})
                clone=model.clone()
                for name,number in vals.items():clone.find_component(name).set_value(number,skip_validation=True)
                objective=float(value(clone.objective))
                result=SolverResults();result.solver.status=SolverStatus.ok
                result.solver.termination_condition=TerminationCondition.maxTimeLimit if index==timeout_call else TerminationCondition.optimal
                result.problem.sense=ProblemSense.minimize;result.problem.number_of_objectives=1
                result.problem.lower_bound=result.problem.upper_bound=objective
                solution=result.solution.add();solution._cuid=False
                solution.status=SolutionStatus.feasible if index==timeout_call else SolutionStatus.optimal
                solution.variable.update({k:{'Value':v} for k,v in vals.items()})
                solution.objective['objective']={'Value':objective}
                calls.append(dict(index=index,reference=reference,power=power,generation=[g1,g2],
                    repair_or_available_cap=cap,timeout=index==timeout_call))
                return result
        return Fake(),m.saved.selection.native.capture.solver_options(specification)
    patch.setattr(m.saved.selection.native.capture,'create_solver',create)
    return calls
