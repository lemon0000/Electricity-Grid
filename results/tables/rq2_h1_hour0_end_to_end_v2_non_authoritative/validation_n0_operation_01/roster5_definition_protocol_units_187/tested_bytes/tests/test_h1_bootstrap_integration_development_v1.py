"""Pre-source bootstrap journal draft; no producer or native execution."""
from dataclasses import replace
import json
from pathlib import Path
from threading import Thread
from types import SimpleNamespace

import pytest
from experiments import h1_bootstrap_integration_development_v1 as m


@pytest.fixture(scope='module')
def example(tmp_path_factory):
    root=tmp_path_factory.mktemp('synthetic_bootstrap_config')
    from tests.test_rq2_continuous_grid_normal_v1 import fixture
    data=fixture(1).data;network=m.phase.binding.source_binding.h1.static_network(data)
    (root/'synthetic_upstream').mkdir()
    config_path=m.symbolic.ROOT/'configs/rq2_joint_deliverability_continuation_audit_v1.DRAFT.yaml'
    order=(('operating_cost',None),*(('commitment',g.uid) for g in network.data.generators if g.dispatch_mode=='committable'),
        *(('generation',g.uid) for g in network.data.generators))
    config=m.RunConfiguration(str(root/'synthetic_upstream'),str(config_path),
        m.phase.binding.SOURCE_CONFIG_PIN,network.identity,1,
        m.Rq2SolverSpec('gurobi','13.0.2',1,1e-8,1e-9,1e-9,1e-9,0,1.,False),
        m.phase.base.old.replay.H1HourReplayLimits(232,1000,2000),
        m.phase.base.old.process.TaskProcessBudget(300.,.05,512*1024**2,768*1024**2,2.),
        order)
    snapshot=m.symbolic.build(m.symbolic.StaticProfile(**config.declared_profile()))
    path=root/'synthetic_profile.json';path.write_bytes(snapshot.raw)
    pin=m.sha256(path.read_bytes()).hexdigest()
    return path,pin,m.symbolic.inspect(path,expected_sha256=pin),config,data


@pytest.fixture
def setup(tmp_path,example,monkeypatch):
    path,pin,snapshot,config,data=example
    implementation=m.implementation_identity()
    monkeypatch.setattr(m,'implementation_identity',lambda:implementation)
    def fresh(p,*,expected_sha256):
        assert Path(p)==path and expected_sha256==pin
        return snapshot
    monkeypatch.setattr(m.symbolic,'inspect',fresh)
    def denied(*a,**k):raise AssertionError('source/network/controller access forbidden in pre-source draft')
    monkeypatch.setattr(m.phase.binding.source_binding,'load_pinned_current',denied)
    monkeypatch.setattr(m.phase.binding.source_binding.rts,'load_rts_gmlc_chronological_data',denied)
    controller_init=m.phase.Controller.__init__
    monkeypatch.setattr(m.phase.Controller,'__init__',denied)
    continuation=m.BootstrapOwner._continue_bootstrap
    def prefix_stop(self):raise ValueError('owned bootstrap producer not implemented; test-only prefix seam')
    monkeypatch.setattr(m.BootstrapOwner,'_continue_bootstrap',prefix_stop)
    # Every network-only cell is unresolved, including original ordinal0.
    assert snapshot.resolve('training_ub',0)['kind']=='potential_N_slot'
    declaration=m.BootstrapDeclaration(str(tmp_path/'study_non_authoritative'),str(path),pin,'training_ub',0,12,65536,config)
    heads={}
    def retain(root,before,after):
        assert heads.get(str(root),before)==before
        heads[str(root)]=after
        return after
    def open_(create=True,create_study=True,**kw):
        d=kw.pop('declaration',declaration)
        return m.BootstrapOwner(d,create=create,create_study=create_study,
            retain_global_head=retain,retain_bootstrap_head=retain,**kw)
    return SimpleNamespace(declaration=declaration,heads=heads,retain=retain,open=open_,snapshot=snapshot,
        continuation=continuation,data=data,controller_init=controller_init)


def retained(o,s):
    return dict(global_head=s.heads.get(str(o._global.root),o._global.genesis),
        bootstrap_head=s.heads.get(str(o._bootstrap.root),o._bootstrap.genesis))


def test_attempt_then_claim_and_reopen_never_runs_source(setup):
    s=setup;o=s.open()
    try:
        assert o.inspect()['state']=='new'
        with pytest.raises(ValueError,match='producer not implemented'):o.bootstrap()
        assert o.poisoned
        attempt=json.loads((o._bootstrap.root/'00000000000000000001.json').read_bytes())
        claim=json.loads((o._global.root/'00000000000000000001.json').read_bytes())
        assert claim['body']['bootstrap_attempt_head']==m.sha256(m.encode(attempt)).hexdigest()
        assert claim['body']['claim_proposal_id']==attempt['body']['claim_proposal_id']
        heads=retained(o,s)
    finally:o.close()
    reopened=s.open(create=False,create_study=False,**heads)
    try:
        assert reopened.inspect()['state']=='claimed_pre_source'
        with pytest.raises(ValueError,match='no automatic retry'):reopened.bootstrap()
    finally:reopened.close()


@pytest.mark.parametrize('where',['bootstrap_before','bootstrap_after','global_before','global_after'])
def test_write_failure_preserves_artifacts_and_retained_head(setup,monkeypatch,where):
    s=setup;o=s.open();write=m.storage._new
    target=o._bootstrap.root if where.startswith('bootstrap') else o._global.root
    def fault(path,raw):
        if path.parent==target and path.name=='00000000000000000001.json':
            if where.endswith('after'):write(path,raw)
            raise OSError('injected journal write')
        return write(path,raw)
    monkeypatch.setattr(m.storage,'_new',fault)
    try:
        with pytest.raises(OSError,match='injected'):o.bootstrap()
        assert o.poisoned
        heads=retained(o,s)
        bootstrap_files=list(o._bootstrap.root.glob('[0-9]*.json'))
        global_files=list(o._global.root.glob('[0-9]*.json'))
    finally:o.close()
    assert len(bootstrap_files)==(0 if where=='bootstrap_before' else 1)
    assert len(global_files)==(1 if where=='global_after' else 0)
    if where.endswith('after'):
        with pytest.raises(ValueError,match='retained journal head'):
            s.open(create=False,create_study=False,**heads)
    else:
        o=s.open(create=False,create_study=False,**heads)
        try:assert o.inspect()['state']==('new' if where=='bootstrap_before' else 'attempt_without_claim')
        finally:o.close()


@pytest.mark.parametrize('capacity',[3,4,5])
def test_declared_capacity_checked_before_attempt(setup,capacity):
    s=setup;o=s.open(declaration=replace(s.declaration,max_global_events=capacity))
    try:
        with pytest.raises(ValueError,match='producer not implemented'):o.bootstrap()
        heads=retained(o,s)
    finally:o.close()
    # Next capacity coordinate is a separate unresolved obligation with same
    # candidate N class, but it must not receive a resource/reuse discount.
    other=replace(s.declaration,ordinal=1,max_global_events=capacity)
    o=s.open(create=True,create_study=False,declaration=other,global_head=heads['global_head'])
    try:
        with pytest.raises(ValueError,match='complete journal branch'):o.bootstrap()
        assert not list(o._bootstrap.root.glob('[0-9]*.json'))
    finally:o.close()


@pytest.mark.parametrize('field',['extra','missing','digest','attempt','study','profile','roots','ordinal','genesis'])
def test_foreign_episode_claim_requires_full_correspondence(setup,field):
    s=setup;o=s.open()
    try:
        with pytest.raises(ValueError,match='producer not implemented'):o.bootstrap()
        path=o._global.root/'00000000000000000001.json'
        value=json.loads(path.read_bytes());body=value['body'];proposal=body['proposal']
        if field=='extra':body['extra']=False
        elif field=='missing':del body['bootstrap_attempt_head']
        elif field=='digest':body['claim_proposal_id']='0'*64
        elif field=='attempt':body['bootstrap_attempt_head']='0'*64
        elif field=='study':proposal['study']['symbolic_path']+='-other'
        elif field=='profile':proposal['profile']['network_sha256']='0'*64
        elif field=='roots':proposal['roots']['owner']+='-other'
        elif field=='ordinal':proposal['ordinal']=True
        else:proposal['bootstrap_genesis']='0'*64
        raw=m.encode(value);path.write_bytes(raw);head=m.sha256(raw).hexdigest()
    finally:o.close()
    # A matching externally retained hash does not certify semantic validity.
    with pytest.raises(ValueError,match='global claim'):
        s.open(create=True,create_study=False,declaration=replace(s.declaration,ordinal=1),global_head=head)
    assert len(list(Path(s.declaration.study_root).glob('episodes/*/bootstrap_non_authoritative/[0-9]*.json')))==1


def test_genesis_and_head_mutation_precedes_any_write(setup):
    o=setup.open();root=o._bootstrap.root
    try:
        o._bootstrap.genesis=o._bootstrap.head='0'*64
        with pytest.raises(ValueError,match='configuration changed'):o.bootstrap()
        assert not list(root.glob('[0-9]*.json'))
    finally:o.close()


@pytest.mark.parametrize('change',['missing','dc_bus','budget','limits','specification','network','order'])
def test_concrete_configuration_must_match_profile_before_attempt(setup,change):
    s=setup;config=s.declaration.run_configuration
    if change=='missing':config=None
    elif change=='dc_bus':config=replace(config,dc_bus=2)
    elif change=='budget':config=replace(config,budget=replace(config.budget,max_elapsed_seconds=299.))
    elif change=='limits':config=replace(config,limits=replace(config.limits,max_variables=1001))
    elif change=='specification':config=replace(config,specification=replace(config.specification,time_limit_seconds=2.))
    elif change=='network':config=replace(config,network_sha256='2'*64)
    else:config=replace(config,stage_order=(('operating_cost',None),('generation','other')))
    o=s.open(declaration=replace(s.declaration,run_configuration=config))
    try:
        with pytest.raises(ValueError,match='configuration/profile correspondence'):o.bootstrap()
        assert not list(o._bootstrap.root.glob('[0-9]*.json'))
        assert not list(o._global.root.glob('[0-9]*.json'))
    finally:o.close()


def test_original_synthetic_example_is_not_a_concrete_profile(setup,monkeypatch):
    s=setup;path=m.symbolic.ROOT/'results/tables/rq2_h1_symbolic_normal_manifest_v1_non_authoritative/symbolic_manifest.synthetic_profile_example.json'
    profile=json.loads(path.read_bytes())['declared_static_profile']
    snapshot=m.symbolic.build(m.symbolic.StaticProfile(**profile))
    monkeypatch.setattr(m.symbolic,'inspect',lambda *a,**k:snapshot)
    o=s.open()
    try:
        with pytest.raises(ValueError,match='configuration/profile correspondence'):o.bootstrap()
        assert not list(o._bootstrap.root.glob('[0-9]*.json'))
    finally:o.close()


@pytest.mark.parametrize('where',['before','after','wrong_ack','readback'])
def test_retention_failure_reopen_uses_only_external_head(setup,monkeypatch,where):
    s=setup;original=s.retain;armed=[]
    def retain(root,before,after):
        if root.name=='bootstrap_non_authoritative':
            if where=='before':raise OSError('retention failure')
            original(root,before,after)
            if where=='after':raise OSError('retention failure')
            if where=='wrong_ack':return before
            armed.append(True)
        return original(root,before,after) if root.name!='bootstrap_non_authoritative' else after
    o=m.BootstrapOwner(s.declaration,create=True,create_study=True,
        retain_global_head=original,retain_bootstrap_head=retain)
    read=m.storage._read
    def fail_read(path,cap):
        if armed and path.parent==o._bootstrap.root:raise OSError('readback failure')
        return read(path,cap)
    monkeypatch.setattr(m.storage,'_read',fail_read)
    try:
        with pytest.raises((OSError,ValueError),match='retention|readback'):o.bootstrap()
        assert o.poisoned and o._bootstrap.poisoned
        assert len(list(o._bootstrap.root.glob('[0-9]*.json')))==1
        heads=retained(o,s)
    finally:o.close()
    monkeypatch.setattr(m.storage,'_read',read)
    if where=='before':
        with pytest.raises(ValueError,match='retained journal head'):s.open(create=False,create_study=False,**heads)
    else:
        o=s.open(create=False,create_study=False,**heads)
        try:assert o.inspect()['state']=='attempt_without_claim'
        finally:o.close()


@pytest.mark.parametrize('target',['pid','thread','root','retainer','journal','header'])
def test_live_owner_mutation_rejected_before_write(setup,monkeypatch,target):
    o=setup.open();root=o._bootstrap.root
    try:
        with monkeypatch.context() as patch:
            if target=='pid':patch.setattr(m.os,'getpid',lambda:o._pid+1)
            elif target=='thread':patch.setattr(m,'get_ident',lambda:o._thread+1)
            elif target=='root':patch.setattr(o._bootstrap,'root',root.parent/'other_non_authoritative')
            elif target=='retainer':patch.setattr(o._bootstrap,'_retain',lambda *args:args[-1])
            elif target=='journal':patch.setattr(o,'_bootstrap',o._global)
            else:
                path=root/'header.json';raw=path.read_bytes()
                path.rename(root/'old_header_preserved.json');path.write_bytes(raw)
            with pytest.raises(ValueError,match='changed'):o.bootstrap()
        assert not list(root.glob('[0-9]*.json'))
    finally:o.close()


def test_duplicate_root_cannot_replace_existing_attempt(setup):
    s=setup;o=s.open()
    try:
        with pytest.raises(ValueError,match='producer not implemented'):o.bootstrap()
        heads=retained(o,s);path=o._bootstrap.root/'00000000000000000001.json';raw=path.read_bytes()
    finally:o.close()
    with pytest.raises(FileExistsError):s.open(create=True,create_study=False,global_head=heads['global_head'])
    assert path.read_bytes()==raw


@pytest.mark.parametrize('create',[1,'yes'])
def test_exact_create_flags_precede_directory_creation(setup,create):
    with pytest.raises(ValueError,match='exact create'):setup.open(create=create)
    assert not Path(setup.declaration.study_root).exists()


def test_foreign_thread_close_does_not_release_owner(setup):
    s=setup;o=s.open();errors=[]
    def close():
        try:o.close()
        except ValueError as e:errors.append(str(e))
    t=Thread(target=close);t.start();t.join()
    assert errors and not o.closed
    try:assert o.inspect()['state']=='new'
    finally:o.close();o.close()


def test_configuration_drift_rejected_before_attempt(setup):
    o=setup.open()
    try:
        o._profile['network_sha256']='0'*64
        with pytest.raises(ValueError,match='configuration changed'):o.bootstrap()
        assert not list(o._bootstrap.root.glob('[0-9]*.json'))
    finally:o.close()


def test_journal_capacity_mutation_is_not_a_reservation(setup):
    o=setup.open()
    try:
        o._global.max_events+=1
        with pytest.raises(ValueError,match='configuration changed'):o.bootstrap()
        assert not list(o._bootstrap.root.glob('[0-9]*.json'))
    finally:o.close()


def test_replay_rechecks_earlier_event_after_read(setup,monkeypatch):
    s=setup;o=s.open()
    try:
        with pytest.raises(ValueError,match='producer not implemented'):o.bootstrap()
        heads=retained(o,s)
    finally:o.close()
    o=s.open(create=False,create_study=False,**heads)
    try:
        path=o._global.root/'00000000000000000001.json';read=m.storage._read;changed=[]
        def mutate_after_read(p,cap):
            result=read(p,cap)
            if p==path and not changed:
                changed.append(True);p.write_bytes(result[0]+b' ')
            return result
        monkeypatch.setattr(m.storage,'_read',mutate_after_read)
        with pytest.raises(ValueError,match='changed during replay'):o.inspect()
    finally:o.close()


def enable_post_claim(s,monkeypatch,*,config=None):
    """Synthetic static inventory seam; actual controller construction, zero Job."""
    d=s.declaration
    if config is not None:
        snapshot=m.symbolic.build(m.symbolic.StaticProfile(**config.declared_profile()))
        path=Path(d.study_root).parent/'post_claim_manifest.json';path.write_bytes(snapshot.raw)
        d=replace(d,run_configuration=config,symbolic_path=str(path),symbolic_sha256=m.sha256(snapshot.raw).hexdigest())
        def fresh(p,*,expected_sha256):
            assert str(p)==str(path) and expected_sha256==d.symbolic_sha256
            return snapshot
        monkeypatch.setattr(m.symbolic,'inspect',fresh)
    monkeypatch.setattr(m.BootstrapOwner,'_continue_bootstrap',s.continuation)
    monkeypatch.setattr(m.phase.Controller,'__init__',s.controller_init)
    events=[];binding=m.phase.binding.source_binding
    def manifest(root):
        events.append('manifest');return binding.rts.RTS_GMLC_MANIFEST_SHA256
    class FuturePoison:
        def __iter__(self):raise AssertionError('future rows iterated')
        def __len__(self):raise AssertionError('future rows counted')
        def __deepcopy__(self,memo):raise AssertionError('future rows copied')
    def static(root):
        study=Path(d.study_root)
        assert len(list(study.glob('episodes/*/bootstrap_non_authoritative/[0-9]*.json')))==1
        assert len(list((study/'global_claims_non_authoritative').glob('[0-9]*.json')))==1
        assert len(s.heads)==2
        events.append('static_load')
        return replace(s.data,hourly_points=FuturePoison())
    monkeypatch.setattr(binding.rts,'_source',manifest)
    monkeypatch.setattr(binding.rts,'load_rts_gmlc_chronological_data',static)
    return d,events


def test_post_claim_static_profile_and_owned_empty_controller(setup,monkeypatch):
    s=setup;d,events=enable_post_claim(s,monkeypatch)
    captured=[];callbacks=[];children=[];init=m._BootstrapController.__init__
    def capture(controller,*args,**kwargs):
        init(controller,*args,**kwargs)
        with pytest.raises(ValueError,match='release/capability'):controller._check()
        captured.append(controller)
    def child(*a,**k):
        children.append(True);raise AssertionError('child entry reached')
    monkeypatch.setattr(m._BootstrapController,'__init__',capture)
    monkeypatch.setattr(m.phase.base.old.process,'normal_task_child',child)
    def retain(root,before,after):
        if captured:
            controller=captured[0]
            assert o._controller is None and o._original_controller is None
            assert controller._lease is controller._clock_lease is controller._obligation_lease is None
            files={p.relative_to(Path(o.roots['controller'])) for p in Path(o.roots['controller']).rglob('*')}
            for cls,name in ((m._BootstrapController,'_step_development'),(m.phase.Controller,'step'),
                    (m.phase.Controller,'_step_development'),(m.phase.bridge.Controller,'step'),(m.phase.base.Controller,'step')):
                with pytest.raises(ValueError):
                    getattr(cls,name)(controller,expected_source_identity='0'*64,expected_head='0'*64)
            for cls in (m.phase.Controller,m.phase.bridge.Controller):
                with pytest.raises(ValueError):cls._job(controller,0,None,None,None)
            with pytest.raises(AttributeError,match='root'):
                m.phase.base.Controller._job(controller,0,None,None,None)
            assert files=={p.relative_to(Path(o.roots['controller'])) for p in Path(o.roots['controller']).rglob('*')}
            assert children==[]
            callbacks.append(True)
        return s.retain(root,before,after)
    o=m.BootstrapOwner(d,create=True,create_study=True,retain_global_head=s.retain,retain_bootstrap_head=retain)
    try:
        with pytest.raises(ValueError,match='release/capability entry not implemented'):o.bootstrap()
        assert events==['manifest','static_load','manifest']
        assert o._network.data.hourly_points==()
        assert o._controller is o._original_controller is None
        assert captured[0]._parent._declaration==o._parent_declaration()
        assert captured[0]._parent._origin==o._origin()
        assert callbacks==[True] and children==[]
        assert not list(Path(o.roots['controller']).glob('job_*'))
        heads=retained(o,s)
    finally:o.close()
    o=s.open(create=False,create_study=False,declaration=d,**heads)
    try:
        assert o.inspect()['state']=='controller_genesis_retained'
        assert o.inspect()['live_controller_retained'] is False
        with pytest.raises(ValueError,match='no automatic retry'):o.bootstrap()
        assert events==['manifest','static_load','manifest']
    finally:o.close()


@pytest.mark.parametrize('field',['network','dc_bus','stage_order'])
def test_loaded_profile_mismatch_retains_typed_unresolved(setup,monkeypatch,field):
    s=setup;config=s.declaration.run_configuration
    if field=='network':config=replace(config,network_sha256='3'*64)
    elif field=='dc_bus':config=replace(config,dc_bus=99999)
    else:config=replace(config,stage_order=(('operating_cost',None),('generation',config.stage_order[-1][1])))
    d,events=enable_post_claim(s,monkeypatch,config=config);o=s.open(declaration=d)
    try:
        with pytest.raises(ValueError,match='loaded network/DC/stage profile differs'):o.bootstrap()
        assert events==['manifest','static_load']
        assert not Path(o.roots['controller']).exists()
        heads=retained(o,s)
    finally:o.close()
    o=s.open(create=False,create_study=False,declaration=d,**heads)
    try:
        assert o.inspect()['state']=='pre_release_unresolved'
        assert o._bootstrap.rows()[-1][1]['stage']=='profile'
    finally:o.close()


@pytest.mark.parametrize('where',['config_before','config_after','source_after'])
def test_profile_source_change_stops_before_controller(setup,monkeypatch,where):
    s=setup;d,events=enable_post_claim(s,monkeypatch);o=s.open(declaration=d)
    read=m.storage._read;counts=[];source=m.phase.binding.source_binding.rts
    def config_read(path,cap):
        view=read(path,cap)
        if path==Path(d.run_configuration.config_path):
            counts.append(True)
            if where=='config_before' or where=='config_after' and len(counts)>1:return view[0]+b' ',view[1]
        return view
    monkeypatch.setattr(m.storage,'_read',config_read)
    if where=='source_after':
        def source_read(root):
            counts.append(True);return source.RTS_GMLC_MANIFEST_SHA256 if len(counts)==2 else '4'*64
        monkeypatch.setattr(source,'_source',source_read)
    try:
        with pytest.raises(ValueError,match='configuration content differs|static source changed'):o.bootstrap()
        assert o._controller is None
        assert len(list(o._bootstrap.root.glob('[0-9]*.json')))==2
    finally:o.close()


def test_controller_construction_failure_keeps_partial_files(setup,monkeypatch):
    s=setup;d,_=enable_post_claim(s,monkeypatch);o=s.open(declaration=d)
    path=Path(o.roots['controller'])/'source_parent_non_authoritative'/'parent_events_non_authoritative'/'header.json'
    def fail(owner,network):
        assert owner._replay()=='profile_verified'
        path.parent.mkdir(parents=True);path.write_bytes(b'partial controller evidence')
        raise OSError('controller construction failure')
    monkeypatch.setattr(m,'_BootstrapController',fail)
    try:
        with pytest.raises(OSError,match='construction failure'):o.bootstrap()
        assert path.read_bytes()==b'partial controller evidence'
        heads=retained(o,s)
    finally:o.close()
    o=s.open(create=False,create_study=False,declaration=d,**heads)
    try:
        assert o.inspect()['state']=='pre_release_unresolved'
        assert o.inspect()['recovery_required'] is True
        assert o._bootstrap.rows()[-1][1]['stage']=='controller'
        assert path.exists()
        read=m.storage._read;changed=[]
        def mutate(target,cap):
            result=read(target,cap)
            if target==path and not changed:
                changed.append(True);path.write_bytes(b'changed partial evidence')
            return result
        monkeypatch.setattr(m.storage,'_read',mutate)
        with pytest.raises(ValueError,match='partial controller artifacts changed'):o.inspect()
    finally:o.close()


@pytest.mark.parametrize('sequence',[2,3])
@pytest.mark.parametrize('timing',['before','after'])
def test_profile_and_controller_record_write_windows(setup,monkeypatch,sequence,timing):
    s=setup;d,_=enable_post_claim(s,monkeypatch);o=s.open(declaration=d);write=m.storage._new
    target=o._bootstrap.root/f'{sequence:020d}.json'
    def fail(path,raw):
        if path==target:
            if timing=='after':write(path,raw)
            raise OSError('profile publication fault')
        return write(path,raw)
    monkeypatch.setattr(m.storage,'_new',fail)
    try:
        with pytest.raises(OSError,match='publication fault'):o.bootstrap()
        heads=retained(o,s)
        assert target.exists()==(timing=='after')
        assert Path(o.roots['controller']).exists()==(sequence==3)
    finally:o.close()
    if timing=='after':
        with pytest.raises(ValueError,match='retained journal head'):s.open(create=False,create_study=False,declaration=d,**heads)
    else:
        o=s.open(create=False,create_study=False,declaration=d,**heads)
        try:
            assert o.inspect()['state']==('claimed_pre_source' if sequence==2 else 'controller_artifacts_uncommitted')
            assert o.inspect()['recovery_required']==(sequence==3)
        finally:o.close()


@pytest.mark.parametrize('suffix',['job_000_non_authoritative','clock_bridge_non_authoritative/000',
    'source_parent_non_authoritative/parent_events_non_authoritative/000001.json'])
def test_uncommitted_controller_suffix_cannot_hide_behind_profile(setup,monkeypatch,suffix):
    s=setup;d,_=enable_post_claim(s,monkeypatch);o=s.open(declaration=d);write=m.storage._new
    target=o._bootstrap.root/'00000000000000000003.json'
    def fail(path,raw):
        if path==target:raise OSError('ready write-before')
        return write(path,raw)
    monkeypatch.setattr(m.storage,'_new',fail)
    try:
        with pytest.raises(OSError,match='ready write-before'):o.bootstrap()
        heads=retained(o,s);root=Path(o.roots['controller'])
        assert o._controller is None
    finally:o.close()
    (root/suffix).mkdir()
    with pytest.raises(ValueError,match='partial controller suffix'):
        s.open(create=False,create_study=False,declaration=d,**heads)


def test_controller_suffix_cannot_be_reported_unreleased(setup,monkeypatch):
    s=setup;d,_=enable_post_claim(s,monkeypatch);o=s.open(declaration=d)
    try:
        with pytest.raises(ValueError,match='release/capability entry'):o.bootstrap()
        heads=retained(o,s);root=Path(o.roots['controller'])
    finally:o.close()
    (root/'job_000_non_authoritative').mkdir()
    with pytest.raises(ValueError):s.open(create=False,create_study=False,declaration=d,**heads)


def test_profile_record_mutation_during_controller_replay_is_detected(setup,monkeypatch):
    s=setup;d,_=enable_post_claim(s,monkeypatch);o=s.open(declaration=d)
    try:
        with pytest.raises(ValueError,match='release/capability entry'):o.bootstrap()
        heads=retained(o,s)
    finally:o.close()
    o=s.open(create=False,create_study=False,declaration=d,**heads)
    target=o._bootstrap.root/'00000000000000000002.json';read=m.storage._read;changed=[]
    def mutate(path,cap):
        result=read(path,cap)
        if path==Path(o.roots['controller'])/'clock_bridge_non_authoritative'/'binding.json' and not changed:
            changed.append(True);target.write_bytes(target.read_bytes()+b' ')
        return result
    monkeypatch.setattr(m.storage,'_read',mutate)
    try:
        with pytest.raises(ValueError,match='journal chain|event replaced'):o.inspect()
    finally:o.close()


def test_unrepresentable_failure_type_does_not_publish_invalid_stop(setup,monkeypatch):
    s=setup;d,_=enable_post_claim(s,monkeypatch);o=s.open(declaration=d)
    def fail(*a):raise type('invalid error name',(Exception,),{})()
    monkeypatch.setattr(m.phase.binding.source_binding.rts,'_source',fail)
    try:
        with pytest.raises(ValueError,match='unrepresentable failure type'):o.bootstrap()
        assert len(list(o._bootstrap.root.glob('[0-9]*.json')))==1
        heads=retained(o,s)
    finally:o.close()
    o=s.open(create=False,create_study=False,declaration=d,**heads)
    try:assert o.inspect()['state']=='claimed_pre_source'
    finally:o.close()


def enable_release_prefix(s,monkeypatch,*,capacity=12):
    d,events=enable_post_claim(s,monkeypatch)
    d=replace(d,max_global_events=capacity)
    continuation=m.BootstrapOwner._continue_bootstrap
    def release(owner):
        try:continuation(owner)
        except ValueError as error:
            if str(error)!='bootstrap release/capability entry not implemented; controller genesis retained':raise
        else:raise AssertionError('expected metadata-only stop')
        owner._record_release()
        with pytest.raises(ValueError,match='fresh unreleased genesis'):owner._record_release()
        raise ValueError('test-only released prefix stop')
    monkeypatch.setattr(m.BootstrapOwner,'_continue_bootstrap',release)
    return d,events


def test_release_prefix_is_indeterminate_and_not_a_capability(setup,monkeypatch):
    s=setup;d,events=enable_release_prefix(s,monkeypatch,capacity=6);o=s.open(declaration=d)
    try:
        with pytest.raises(ValueError,match='test-only released prefix'):o.bootstrap()
        assert o._controller is None and o._operation_nonce is None
        assert events==['manifest','static_load','manifest']
        heads=retained(o,s);root=Path(o.roots['controller'])
        assert not list(root.glob('job_*'))
    finally:o.close()
    # Preserve a possible interrupted execution suffix. It is not a terminal.
    suffix=root/'job_000_non_authoritative';suffix.mkdir();(suffix/'unresolved.bin').write_bytes(b'unknown execution')
    o=s.open(create=False,create_study=False,declaration=d,**heads)
    try:
        observed=o.inspect()
        assert observed['state']=='execution_indeterminate' and observed['recovery_required']
        assert observed['execution_artifacts_audited'] is observed['retry_authorized'] is False
        assert o._remaining_global_records()==1
        o._operation.acquire()
        try:
            with pytest.raises(ValueError,match='active bootstrap operation'):o._record_release()
        finally:o._operation.release()
        assert suffix.joinpath('unresolved.bin').read_bytes()==b'unknown execution'
    finally:o.close()
    # Reconstruct the foreign release while opening the next episode. Remaining
    # capacity is exactly released(1) + a new claim/release/terminal(3).
    def stop(owner):raise ValueError('test-only second episode prefix')
    monkeypatch.setattr(m.BootstrapOwner,'_continue_bootstrap',stop)
    o=s.open(create=True,create_study=False,declaration=replace(d,ordinal=1),global_head=heads['global_head'])
    try:
        with pytest.raises(ValueError,match='second episode prefix'):o.bootstrap()
        assert len(list(o._bootstrap.root.glob('[0-9]*.json')))==1
        next_heads=retained(o,s)
    finally:o.close()
    read=m.storage._read;changed=[]
    released_row=root.parent/'bootstrap_non_authoritative'/'00000000000000000004.json'
    clock=root/'clock_bridge_non_authoritative'/'binding.json'
    def mutate(path,cap):
        result=read(path,cap)
        if path==released_row and not changed:
            changed.append(True);clock.write_bytes(clock.read_bytes()+b' ')
        return result
    monkeypatch.setattr(m.storage,'_read',mutate)
    with pytest.raises(ValueError,match='release genesis changed during cross-replay'):
        s.open(create=False,create_study=False,declaration=replace(d,ordinal=1),**next_heads)


@pytest.mark.parametrize('where',['local_before','local_after','global_before','global_after'])
def test_release_two_journal_write_windows(setup,monkeypatch,where):
    s=setup;d,_=enable_release_prefix(s,monkeypatch);o=s.open(declaration=d);write=m.storage._new
    target=(o._bootstrap.root/'00000000000000000004.json' if where.startswith('local')
        else o._global.root/'00000000000000000002.json')
    def fail(path,raw):
        if path==target:
            if where.endswith('after'):write(path,raw)
            raise OSError('release write fault')
        return write(path,raw)
    monkeypatch.setattr(m.storage,'_new',fail)
    try:
        with pytest.raises(OSError,match='release write fault'):o.bootstrap()
        heads=retained(o,s);root=Path(o.roots['controller'])
        assert target.exists()==where.endswith('after')
        assert not list(root.glob('job_*'))
    finally:o.close()
    if where.endswith('after'):
        with pytest.raises(ValueError,match='retained journal head'):s.open(create=False,create_study=False,declaration=d,**heads)
    else:
        o=s.open(create=False,create_study=False,declaration=d,**heads)
        try:
            assert o.inspect()['state']==('controller_genesis_retained' if where=='local_before' else 'release_metadata_uncommitted')
            assert o._remaining_global_records()==2
        finally:o.close()
        # No global release means no execution suffix may be adopted.
        (root/'job_000_non_authoritative').mkdir()
        with pytest.raises(ValueError):s.open(create=False,create_study=False,declaration=d,**heads)


@pytest.mark.parametrize('mutation',['digest','journal_suffix'])
def test_foreign_release_digest_cannot_be_forged_with_matching_head(setup,monkeypatch,mutation):
    s=setup;d,_=enable_release_prefix(s,monkeypatch);o=s.open(declaration=d)
    try:
        with pytest.raises(ValueError,match='test-only released prefix'):o.bootstrap()
        path=o._global.root/'00000000000000000002.json'
        journal=o._bootstrap.root;global_head=o._global.head
    finally:o.close()
    if mutation=='digest':
        value=json.loads(path.read_bytes());value['body']['bootstrap_release_body_sha256']='0'*64
        raw=m.encode(value);path.write_bytes(raw);global_head=m.sha256(raw).hexdigest()
    else:
        previous=m.sha256((journal/'00000000000000000004.json').read_bytes()).hexdigest()
        (journal/'00000000000000000005.json').write_bytes(m.encode(dict(sequence=5,previous=previous,body=dict(kind='terminal'))))
    with pytest.raises(ValueError,match='global release binding|hour directory entry cap'):
        s.open(create=True,create_study=False,declaration=replace(d,ordinal=1),global_head=global_head)


@pytest.mark.parametrize('lane',['local','global'])
def test_release_retain_callback_cannot_replace_operation_nonce(setup,monkeypatch,lane):
    s=setup;d,_=enable_release_prefix(s,monkeypatch);changed=[]
    def retain(root,before,after):
        result=s.retain(root,before,after)
        sequence=4 if lane=='local' else 2
        if ((Path(root)/f'{sequence:020d}.json').exists()
                and Path(root)==(o._bootstrap.root if lane=='local' else o._global.root)):
            o._operation_nonce=object();changed.append(True)
        return result
    o=m.BootstrapOwner(d,create=True,create_study=True,retain_global_head=retain,retain_bootstrap_head=retain)
    try:
        with pytest.raises(ValueError,match='release operation changed'):o.bootstrap()
        assert changed==[True] and len(list(o._global.root.glob('[0-9]*.json')))==(1 if lane=='local' else 2)
        heads=retained(o,s)
    finally:o.close()
    o=s.open(create=False,create_study=False,declaration=d,**heads)
    try:assert o.inspect()['state']==('release_metadata_uncommitted' if lane=='local' else 'execution_indeterminate')
    finally:o.close()
