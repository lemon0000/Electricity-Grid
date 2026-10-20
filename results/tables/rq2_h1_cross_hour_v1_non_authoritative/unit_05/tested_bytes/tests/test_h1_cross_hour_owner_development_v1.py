"""Connected synthetic two-hour prefix, real joins/replay/business/persistence.

Source/catalog and solver-shaped records are explicitly fabricated. Normal
workers run in actual bounded Windows Jobs. No native solver or formal result.
"""
from contextlib import closing
from dataclasses import asdict, dataclass, replace
from fractions import Fraction as Q
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace

import pytest
from pyomo.environ import Var, value
from pyomo.opt import SolverResults, SolverStatus, SolutionStatus, TerminationCondition
from pyomo.opt.results.problem import ProblemSense

from experiments import h1_cross_hour_owner_development_v1 as m
from tests.test_h1_saved_source_parent_development_v1 import environment
from tests.test_rq2_normal_h1_source_binding_v1 import supplied
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver, spec, saved
from tests.test_h1_attested_saved_hour_development_v1 import synthetic_reports
from tests import test_h1_exact_business_development_v1 as biz
from tests import test_h1_selector_replay_development_v1 as selectors
from tests.test_h1_persistent_owner_development_v1 import setup as legacy_setup, saved as saved_records
from tests.test_h1_phase_owner_development_v1 import setup as saved_setup


@pytest.fixture(scope='module')
def real():
    # Only the resolver/coordinate are used by the explicit synthetic binding.
    # Do not load the unrelated real RTS current used by the older fixture.
    resolver = m.normal.binding.open_manifest()
    axes = resolver.data()['catalog']['axes']['training_ub']
    point = {k: v[0] for k, v in axes.items()}
    point.update(power=axes['power'][8], workload=axes['workload'][17])
    return resolver, resolver.encode_coordinate('training_ub', point)


@pytest.fixture
def static_code_identities(tmp_path):
    from tests.h1_cross_hour_identity_fixture_v1 import immutable_code_identities
    with immutable_code_identities(tmp_path/'static_identity_bookends.json'):
        yield


def trace(root, label, **values):
    row = dict(label=label, monotonic=time.perf_counter(), **values)
    with (root/'cross_hour_timing.jsonl').open('a', encoding='utf-8') as out:
        out.write(json.dumps(row)+'\n')
    print(json.dumps(row), flush=True)


def install_rows(mp):
    source = m.saved.source.source
    original = source.windows.load_source_window
    def load(kind, split, start, hours, **kwargs):
        result = original(kind, split, start, hours, **kwargs)
        row = result['rows'][0]
        result['chain']['chain_id'] = 'test-only-cross-hour-'+kind
        if kind == 'power':
            row.update(block_id='synthetic', active_event_id='', active_component_type='', active_component_uid='',
                       cfe_call_fraction='0.6' if start == 0 else '0.2')
        else:
            row['workload_fraction'] = '0.1'
            result['chain']['trace_identity_basis'] = {'source': 'synthetic cross-hour fixture'}
        result.pop('window_identity')
        result['window_identity'] = source.windows._hash(result)
        return result
    mp.setattr(source.windows, 'load_source_window', load)
    return load


def install_registry(mp, env, load):
    _, _, origin, _ = env
    registry = m.saved.source.registry
    package = load('power', 'training', 0, 1, outage_seed=origin.outage_seed,
        expected_config_sha256=origin.config_sha256)['package_manifest_sha256']
    mp.setattr(registry.frozen, 'PACKAGE_SHA', package)
    mp.setattr(registry.catalog, 'CONFIG_SHA', origin.config_sha256)
    protocol = registry.events.DisclosureProtocol((registry.events.OutageComponent('generator', 'G1'),),
        'current_n1_outage_overlay_revealed_before_current_action',
        'complete_current_n1_outage_overlay__no_hidden_same_hour_replacement', 'mechanism_assumption')
    def context(split):
        rows = {h: load('power', split, h, 1, outage_seed=origin.outage_seed,
            expected_config_sha256=origin.config_sha256)['rows'][0] for h in (0, 1)}
        return dict(split=split, protocol=protocol, caps={'G1': Q(20)}, components=(),
            rows={origin.outage_seed: rows}, catalog_entries=[dict(source_start=0, observed_end_inclusive=1,
                outage_seed=origin.outage_seed, chain_id=f'power:{split}:outage_seed={origin.outage_seed}')],
            gaps=[dict(split=split, outage_seed=origin.outage_seed, raw_start=0)], identity='c'*64,
            split_hour=99, archive_member_sha256='d'*64, cap_table_sha256='e'*64)
    mp.setattr(registry, '_load', context)
    mp.setattr(registry.frozen, 'prefix_overlay', lambda *a: (('', '', ''),))


def controller(root, env, manifest_fixture, mp):
    resolver, ordinal, *_ = manifest_fixture
    c = m.normal
    node = resolver.resolve('training_ub', ordinal)
    enrollment = dict(test_only_synthetic_source=True)
    mp.setattr(c.binding, 'open_manifest', lambda: resolver)
    mp.setattr(c.binding, 'precheck', lambda *a, **kw: node)
    mp.setattr(c.binding, 'prevalidate_enrollment', lambda *a, **kw: enrollment)
    def bind(resolver, declaration, **kw):
        owner = c.binding.snapshot.open_snapshot(declaration,
            expected_parent_identity=kw['expected_parent_identity'], expected_anchor_record=kw['expected_anchor_record'])
        try:
            item = owner.pending_input(**kw['pending_arguments'])
        finally:
            owner.close()
        item.validate(expected_receipt_sha256=kw['expected_pending_receipt_sha256'])
        request = dict(parent_declaration=declaration, pending_arguments=kw['pending_arguments'],
            input_receipt=json.loads(item.receipt), input_receipt_sha256=item.receipt_sha256, budget=asdict(kw['job_budget']))
        return c._historical_binding(item.packet, request, node, enrollment)
    mp.setattr(c.binding, 'bind', bind)
    upstream, config, origin, state = env
    return m.PhaseController(root, c.base.parent.source.static_network(state['data']),
        replace(spec(), time_limit_seconds=5.), c.base.old.replay.H1HourReplayLimits(3, 100, 500),
        resolver=resolver, family='training_ub', ordinal=ordinal, origin=origin,
        upstream_root=upstream, config_path=config, dc_bus=1, hours=192,
        budget=c.base.old.process.TaskProcessBudget(180., .05, 512*1024**2, 768*1024**2, 2.))


def normal_reports(templates, hour):
    # Fabricated values only. The worker rebuilds all model/export/science views.
    output = []
    for i, raw in enumerate(templates):
        report = json.loads(raw)
        assignment = dict(report['assignment'])
        assignment['generation[normal,0,G1]'] = float(45).hex()
        assignment.update({f'segment_power[0,G1,{i}]': float(number).hex()
                           for i, number in enumerate((30, 5, 0))})
        assignment['startup[0,G1]'] = float(hour == 0).hex()
        report['assignment'] = sorted(assignment.items())
        objective = float(1 if i == 1 else 45)
        provenance = report['provenance']
        for name in ('ObjVal', 'ObjBound', 'ObjBoundC'):
            provenance['native'][name] = dict(provenance['native'][name], hex=objective.hex())
        provenance['pyomo_lower_hex'] = provenance['pyomo_upper_hex'] = objective.hex()
        output.append(m.normal.io.encode(report))
    return output


def install_launcher(mp, root, reports, hour):
    from experiments import h1_timed_job_controller_development_v1 as timed
    raw_root = root/f'normal_templates_{hour}'
    raw_root.mkdir()
    for i, raw in enumerate(reports):
        (raw_root/f'{i:03d}.bin').write_bytes(raw)
    dependency = str(Path(importlib.util.find_spec('pygments').origin).parent.parent)
    code = (f'import sys;sys.path[:0]=[{str(Path.cwd())!r},{str(Path.cwd()/"tests")!r}];sys.path.append({dependency!r});'
        'from tests.test_h1_cross_hour_owner_development_v1 import child_main;'
        f'child_main({str(root)!r},{str(raw_root)!r},*sys.argv[1:])')
    wrapped = 'try:\n    '+code+'\nexcept BaseException:\n    import traceback\n    from pathlib import Path\n    (Path.cwd()/"error.txt").write_bytes(traceback.format_exc().encode()[:8192])\n    raise\n'
    mp.setattr(timed, '_argv', lambda path, pin: [sys.executable, '-I', '-B', '-c', wrapped, str(path), pin])


def child_main(base, raw_root, path, pin):
    from tests.test_h1_saved_job_development_v1 import install_child_source
    from tests.test_h1_timed_worker_hour_development_v1 import install
    patch = install_child_source(Path(base))
    no_solver.__wrapped__(patch)
    install_rows(patch)
    reports = [(Path(raw_root)/f'{i:03d}.bin').read_bytes() for i in range(3)]
    solvers = install(patch, Path(path).parent/'worker_non_authoritative', reports)
    m.normal.base.entry.execute(path, pin)
    assert [s.apply_calls for s in solvers] == [1, 1, 1]
    assert [s.close_calls for s in solvers] == [1, 1, 1]


def manifest():
    business = m.saved.business
    configs = []
    for key, arm in [('cfe', business.arms.CFE), ('joint', business.arms.JOINT), ('network', business.arms.NETWORK)]:
        initial = biz.origin(arm, mechanism=business.Mechanism(Q(1, 2), Q(1, 2), Q(1, 10)))
        envelope = tuple(sorted(initial.cursor.initial.tracks[0][1].physical.envelope))
        configs.append(m.saved.LaneConfig(key, initial.cursor.spec, initial.mechanism, envelope))
    return m.saved.Manifest(tuple(configs), selectors.REF, selectors.ACT, selectors.SPEC,
        m.saved.selection.ReplayLimits(**asdict(selectors.LIMITS)),
        32, 1024**2, 32*1024**2, 'synthetic-two-hour-single-episode')


def install_selectors(mp):
    calls = []
    def create(specification):
        class Fake:
            def solve(self, model, **kwargs):
                vals = {v.name: 0. for v in model.component_data_objects(Var)}
                if hasattr(model, 'reference_power'):
                    power = 25.
                    vals['reference_power'] = power
                else:
                    # The balance row contains the exact prescribed business power.
                    balance = model.balance[1]
                    from pyomo.repn import generate_standard_repn
                    power = -float(generate_standard_repn(balance.body).constant)-20.
                vals['generation[G1]'] = 20.+power
                vals['selector_deviation[G1]'] = abs(power-25.)
                clone = model.clone()
                for name, number in vals.items():
                    clone.find_component(name).set_value(number, skip_validation=True)
                objective = float(value(clone.objective))
                out = SolverResults()
                out.solver.status = SolverStatus.ok
                out.solver.termination_condition = TerminationCondition.optimal
                out.problem.sense = ProblemSense.minimize
                out.problem.number_of_objectives = 1
                out.problem.lower_bound = out.problem.upper_bound = objective
                solution = out.solution.add()
                solution._cuid = False
                solution.status = SolutionStatus.optimal
                solution.variable.update({k: {'Value': v} for k, v in vals.items()})
                solution.objective['objective'] = {'Value': objective}
                calls.append(dict(reference=hasattr(model, 'reference_power'), power=power))
                return out
        return Fake(), m.saved.selection.native.capture.solver_options(specification)
    mp.setattr(m.saved.selection.native.capture, 'create_solver', create)
    return calls


def restore(owner):
    with closing(owner._connect()) as db:
        rows = owner._rows(db)
    return owner._restore(rows), rows


def producer_budget(**changes):
    return replace(selectors.BUDGET, purpose=m.SELECTOR_PURPOSE, **changes)


@pytest.fixture
def saved_owner(saved_setup, monkeypatch, tmp_path):
    """Explicit saved-source seam for fault tests; no normal producer or Job."""
    s = saved_setup
    holder = m.saved.tickets.TicketHolder(tmp_path/'fault_holder_non_authoritative', owner_root=s.root,
        max_tickets=s.manifest.max_events, max_ticket_bytes=s.manifest.max_event_bytes,
        max_total_ticket_bytes=s.manifest.max_archive_bytes, create=True, retain_head=lambda *a: a[2])
    owner = m.DevelopmentOwner(s.root, s.manifest, s.binding, holder=holder, create=True)
    try:
        def consume(actual=True):
            records = saved_records(monkeypatch, s, m.saved._initial(s.manifest, s.currents[0]), 0, actual=actual)
            # Only this fixture imports saved bootstrap; live public entries remain disabled.
            return m.saved.DevelopmentOwner.advance(owner, expected_heads=owner.heads,
                terminal_sha256=s.binding.genesis_terminal_sha256,
                reference_records=records[0], actual_records=records[1])
        yield s, owner, consume
    finally:
        owner.close()
        holder.close()


def test_need_requires_producer_before_attempt_or_next_source(saved_owner, monkeypatch):
    _, owner, consume = saved_owner
    consume()
    before = owner.heads
    hours = []
    original = m.saved._fresh
    monkeypatch.setattr(m.saved, '_fresh', lambda binding, hour, terminal: (
        hours.append(hour) or original(binding, hour, terminal)))
    with pytest.raises(ValueError, match='exact phase selector'):
        owner.run_next_development(expected_heads=before)
    assert owner.heads == before and set(hours) == {0}


@pytest.mark.parametrize('readback_failure', [False, True])
def test_no_need_with_no_producer_and_terminal_failure_freezes(saved_owner, monkeypatch, readback_failure):
    _, owner, consume = saved_owner
    consume(actual=False)
    before = owner.heads
    if readback_failure:
        def fail(**kwargs):
            raise OSError('terminal readback failed')
        monkeypatch.setattr(owner, '_inspect', fail)
        with pytest.raises(OSError, match='readback'):
            owner.run_next_development(expected_heads=before)
        assert owner.poisoned
    else:
        report = owner.run_next_development(expected_heads=before)
        assert report.episode_terminal and report.completed_hours == 1
    # Inspect canonical SQLite directly even if the live handle is frozen.
    import sqlite3
    with closing(sqlite3.connect(owner.path)) as db:
        assert db.execute('SELECT kind FROM events ORDER BY seq').fetchall() == [
            ('intent',), ('outcome',), ('episode_terminal',)]


@dataclass(frozen=True)
class StubObservation:
    terminal_sha256: str
    outcome_head: str


@pytest.fixture
def pending_capability(saved_owner):
    _, owner, consume = saved_owner
    consume()
    with owner._operation:
        rows, _, state = owner._ready_replay(owner.heads)
        owner._reserve_check(rows)
        rows = owner._append('attempt', owner._attempt_body(state, rows), rows)
        controller = SimpleNamespace(_phase_owner=owner, _clock_index=1, _clock_previous='4'*64,
            _clock_last=100, _obligation_previous=json.loads(rows[-1][3])['previous_normal_terminal'],
            _phase_job_intent=None, _clock_pending=None, _active_request=None, _phase_scope=None,
            last_observation=StubObservation('4'*64, '5'*64),
            last_obligation_observation=StubObservation('6'*64, '5'*64))
        controller._parent = SimpleNamespace(_journal=SimpleNamespace(head='5'*64),
            _root=owner.root, _anchor=SimpleNamespace(inspect=lambda: SimpleNamespace(record_sha256='7'*64)))
        controller._phase_check = controller._clock_check = lambda: None
        owner._live_controller = controller
        owner._phase_nonce = object()
        cap = m._Capability(owner, controller, owner._operation, owner._phase_nonce, (os.getpid(), m.get_ident()),
            1, owner.heads, rows[-1][4], controller._obligation_previous, '5'*64, '4'*64, 100)
        owner._phase_capability = cap
        controller._phase_scope = cap
        try:
            yield owner, controller, cap, rows
        finally:
            owner._phase_nonce = owner._phase_capability = None


@pytest.mark.parametrize('field', ['_clock_index', '_clock_previous', '_obligation_previous', '_clock_last', 'parent_head', 'nonce'])
def test_pre_normal_drift_rejects_before_job(pending_capability, field):
    owner, controller, cap, _ = pending_capability
    m.PhaseController._scope_check(controller)
    if field == 'parent_head':
        controller._parent._journal.head = '8'*64
    elif field == 'nonce':
        owner._phase_nonce = object()
    else:
        setattr(controller, field, 999 if field in ('_clock_index', '_clock_last') else '8'*64)
    with pytest.raises(ValueError):
        m.PhaseController._scope_check(controller)


def test_wrong_parent_intent_anchor_rejects_before_job(pending_capability, monkeypatch):
    _, controller, _, _ = pending_capability
    monkeypatch.setattr(m.normal.base.entry, 'read', lambda *a: ({'previous_registry_head': '8'*64}, None))
    with pytest.raises(ValueError, match='intent'):
        m.PhaseController._job(controller, 1, None, {'expected_head': '5'*64}, '7'*64)


@pytest.mark.parametrize('field', ['_clock_last', '_clock_pending', '_active_request', '_phase_scope', '_phase_job_intent', 'equal_observation'])
def test_post_normal_drift_rejects(pending_capability, field):
    owner, controller, cap, rows = pending_capability
    controller._phase_scope = None
    controller._clock_index = 2
    owner._post_normal = owner._normal_token()
    owner._post_observations = (controller.last_observation, controller.last_obligation_observation)
    owner._post_check(cap, rows)
    if field == 'equal_observation':
        controller.last_observation = replace(controller.last_observation)
    else:
        setattr(controller, field, 101 if field == '_clock_last' else object())
    with pytest.raises(ValueError):
        owner._post_check(cap, rows)


@pytest.mark.parametrize('changes', [dict(max_solver_calls=8), dict(max_total_solver_seconds=8.)])
def test_aggregate_budget_rejects_before_any_capture(saved_setup, changes):
    cfg = manifest()
    current = saved_setup.currents[0]
    state = m.saved._initial(cfg, current)
    owner = SimpleNamespace(manifest=cfg, stage_timings=[], _selector_scope_check=lambda *a: None)
    producer = m.PhaseSelectorProducer(producer_budget(**changes))
    with pytest.raises(ValueError, match='aggregate'):
        producer.produce(owner, None, state, current)
    assert owner.stage_timings == []


def test_selector_callable_replacement_rejects(monkeypatch):
    producer = m.PhaseSelectorProducer(producer_budget())
    monkeypatch.setattr(m.saved.selection.native.capture, '_solve', lambda *a: None)
    with pytest.raises(ValueError, match='callable'):
        producer._check()


def test_selector_dispatch_replacement_rejects_before_callback(saved_owner):
    _, owner, consume = saved_owner
    consume()
    called = []
    producer = m.PhaseSelectorProducer(producer_budget())
    producer.produce = lambda *a: called.append(True)
    with pytest.raises(ValueError, match='callable'):
        owner.run_next_development(expected_heads=owner.heads, selector_producer=producer)
    assert not called


@pytest.mark.parametrize('hour', [0, 1])
def test_normal_reports_match_canonical_model_without_job(synthetic_reports, hour):
    from tests.test_rq2_normal_h1_source_v1 import packet
    p = packet(raw_workload='0.1')
    api = m.normal.base.old.replay.native.model_api
    if hour:
        source = m.normal.base.parent.source
        before = source._owned(type(p.before), network_identity=p.network.identity, completed_hours=1,
            units=(('G1', True, 45., 1),), evidence_role='numerical_lex_candidate')
        p = packet(raw_workload='0.1', relative_hour=1, before=before)
    locks = ()
    for report_raw in normal_reports(synthetic_reports, hour):
        request = api.H1StageRequest(p.inputs, locks)
        model = api.build_h1_stage_model(request, expected_identity=api.h1_stage_identity(request))
        assignment = {name: float.fromhex(number) for name, number in json.loads(report_raw)['assignment']}
        assert set(assignment) == {v.name for v in model.component_data_objects(Var)}
        for name, number in assignment.items():
            model.find_component(name).set_value(number, skip_validation=True)
        audit = m.saved.selection.native.capture
        assert audit._constraint_violation(model) <= 1e-9
        assert audit._integrality_violation(model) <= 1e-9
        objective = float(value(model.objective))
        expected = float(1 if len(locks) == 1 else 45)
        assert objective == expected
        locks += (objective,)


def test_selector_purpose_is_explicit():
    with pytest.raises(ValueError, match='purpose'):
        m.PhaseSelectorProducer(selectors.BUDGET)


def test_static_identity_cache_bookends_and_leaves_dynamic_functions(tmp_path, monkeypatch):
    from tests.h1_cross_hour_identity_fixture_v1 import immutable_code_identities
    calls = []
    def original():
        calls.append(True)
        return 'a'*64
    monkeypatch.setattr(m.saved.source, 'implementation_identity', original)
    dynamic = (m.saved._fresh, m.saved.source.prepare, m.saved.source.historical._replay_prefix,
               m.saved.source.registry.prepare, m.saved.source.source.load_pinned_current,
               m.saved.selection.input_identity, m.saved.selection.physical.development_step_identity)
    path = tmp_path/'memo.json'
    with immutable_code_identities(path):
        assert m.saved.source.implementation_identity() == m.saved.source.implementation_identity() == 'a'*64
        assert len(calls) == 1
        assert dynamic == (m.saved._fresh, m.saved.source.prepare, m.saved.source.historical._replay_prefix,
            m.saved.source.registry.prepare, m.saved.source.source.load_pinned_current,
            m.saved.selection.input_identity, m.saved.selection.physical.development_step_identity)
    assert m.saved.source.implementation_identity is original and len(calls) == 2
    receipt = json.loads(path.read_bytes())
    assert not receipt['errors'] and not receipt['production_overhead_measured']
    assert all(row['original_callable_restored'] for row in receipt['functions'])


def test_static_identity_cache_detects_dependency_drift_and_restores(tmp_path, monkeypatch):
    from tests.h1_cross_hour_identity_fixture_v1 import immutable_code_identities
    dependency = ['a'*64]
    def original():
        return dependency[0]
    monkeypatch.setattr(m.saved.source, 'implementation_identity', original)
    with pytest.raises(ValueError, match='bookend'):
        with immutable_code_identities(tmp_path/'drift.json'):
            assert m.saved.source.implementation_identity() == 'a'*64
            dependency[0] = 'b'*64
    assert m.saved.source.implementation_identity is original


def test_static_identity_cache_preserves_primary_error(tmp_path, monkeypatch):
    from tests.h1_cross_hour_identity_fixture_v1 import immutable_code_identities
    dependency = ['a'*64]
    def original():
        return dependency[0]
    monkeypatch.setattr(m.saved.source, 'implementation_identity', original)
    primary = RuntimeError('primary failure')
    with pytest.raises(RuntimeError, match='primary failure') as caught:
        with immutable_code_identities(tmp_path/'primary.json'):
            m.saved.source.implementation_identity()
            dependency[0] = 'b'*64
            raise primary
    assert caught.value is primary and m.saved.source.implementation_identity is original


def stub_normal(owner):
    """Fault-injection object only; it cannot construct or launch a Job."""
    controller = object.__new__(m.PhaseController)
    controller._phase_owner = owner
    controller._phase_check = lambda: None
    controller._clock_index, controller._clock_last = 1, 100
    controller._clock_previous = '4'*64
    controller._parent = SimpleNamespace(_journal=SimpleNamespace(head='5'*64))
    owner._live_controller = controller
    return controller


def test_normal_failure_retains_attempt_and_blocks_retry(saved_owner):
    _, owner, consume = saved_owner
    consume()
    controller = stub_normal(owner)
    def fail(*args):
        raise ValueError('injected normal failure')
    controller._run_owned = fail
    producer = m.PhaseSelectorProducer(producer_budget())
    with pytest.raises(ValueError, match='normal failure'):
        owner.run_next_development(expected_heads=owner.heads, selector_producer=producer)
    assert owner.poisoned and owner._phase_nonce is None and owner._phase_capability is None
    import sqlite3
    with closing(sqlite3.connect(owner.path)) as db:
        assert db.execute('SELECT kind FROM events ORDER BY seq').fetchall() == [('intent',), ('outcome',), ('attempt',)]
    with pytest.raises(ValueError, match='poisoned'):
        owner.run_next_development(expected_heads=owner.heads, selector_producer=producer)


def test_reference_failure_keeps_intent_and_runs_no_actual(saved_owner, monkeypatch):
    _, owner, _ = saved_owner
    stub_normal(owner)
    calls = selectors.install(monkeypatch, selectors.R, 'timeout')
    producer = m.PhaseSelectorProducer(producer_budget())
    with pytest.raises(ValueError, match='reference unresolved'):
        owner.run_next_development(expected_heads=owner.heads, selector_producer=producer)
    assert len(calls) == 2 and owner.poisoned
    import sqlite3
    with closing(sqlite3.connect(owner.path)) as db:
        rows = db.execute('SELECT kind,body FROM events ORDER BY seq').fetchall()
    assert len(rows) == 1 and rows[0][0] == 'intent'
    packed = json.loads(rows[0][1])['records']
    assert len(packed['reference']) == 2 and all(not records for records in packed['actual'].values())


@pytest.mark.parametrize('approved', [True, False])
def test_business_unresolved_semantics_preserved(saved_owner, monkeypatch, approved):
    _, owner, _ = saved_owner
    stub_normal(owner)
    selectors.install(monkeypatch, selectors.R)
    producer = m.PhaseSelectorProducer(producer_budget())
    def fail(**kwargs):
        raise ValueError('exact interface unresolved: no lossless decimal built-in' if approved else 'unexpected business failure')
    monkeypatch.setattr(m.saved.business, 'current', fail)
    if approved:
        report = owner.run_next_development(expected_heads=owner.heads, selector_producer=producer)
        assert report.completed_hours == 1 and not owner.poisoned
        lane = owner.last_candidate_state.lanes[0][1]
        assert lane.halted and lane.reason == 'business_input_unresolved'
        assert lane.business.cursor.records == () and lane.actual.physical_carry.completed_hours == 0
    else:
        with pytest.raises(ValueError, match='unexpected business failure'):
            owner.run_next_development(expected_heads=owner.heads, selector_producer=producer)
        assert owner.poisoned


def test_detached_entries_reject_before_state_access():
    with pytest.raises(ValueError, match='detached'):
        m.PhaseController._step_development(object(), expected_source_identity='a'*64)
    for method in ('advance', 'prepare_next', 'complete_saved'):
        with pytest.raises(ValueError, match='atomic'):
            getattr(m.DevelopmentOwner, method)(object())


def test_two_hour_three_lane_connected_chain(tmp_path, environment, real, synthetic_reports, monkeypatch, static_code_identities):
    trace(tmp_path, 'start', synthetic_hours=2, lanes=3, formal_result=False)
    load = install_rows(monkeypatch)
    install_registry(monkeypatch, environment, load)
    historical = m.saved.source.historical
    monkeypatch.setattr(historical, '_source_paths', lambda d: (
        {Path(d['config_path']), Path(d['upstream_root'])/'SHA256SUMS'}, {Path(d['upstream_root'])}))
    normal = controller(tmp_path/'normal_non_authoritative', environment, real, monkeypatch)
    holder = owner = None
    original_fresh = m.saved._fresh
    source_calls = []
    def fresh(binding, hour, terminal):
        source_calls.append(hour)
        if hour == 1:
            import sqlite3
            if owner is not None and owner._live_controller is not None:
                assert owner._operation.locked()
            with closing(sqlite3.connect(owner_root/'owner.sqlite')) as db:
                attempts = db.execute("SELECT body FROM events WHERE kind='attempt'").fetchall()
            assert any(json.loads(raw)['hour'] == 1 for (raw,) in attempts)
        return original_fresh(binding, hour, terminal)
    monkeypatch.setattr(m.saved, '_fresh', fresh)
    try:
        install_launcher(monkeypatch, tmp_path, normal_reports(synthetic_reports, 0), 0)
        assert normal.bootstrap_development().completed_hours == 1
        trace(tmp_path, 'N0_terminal')
        first = normal.last_obligation_observation
        cfg = manifest()
        binding = m.saved.SourceBinding(str(normal._lease.root), first.header_sha256, 'c'*64, first.terminal_sha256)
        owner_root = tmp_path/'owner_non_authoritative'
        holder_root = tmp_path/'holder_non_authoritative'
        retained_heads = []
        holder_args = dict(owner_root=owner_root, max_tickets=cfg.max_events, max_ticket_bytes=cfg.max_event_bytes,
                           max_total_ticket_bytes=cfg.max_archive_bytes, retain_head=lambda *a: retained_heads.append(a[2]) or a[2])
        holder = m.saved.tickets.TicketHolder(holder_root, create=True, **holder_args)
        owner = m.DevelopmentOwner(owner_root, cfg, binding, holder=holder, create=True, controller=normal)
        calls = install_selectors(monkeypatch)
        producer = m.PhaseSelectorProducer(producer_budget())
        one = owner.run_next_development(expected_heads=owner.heads, selector_producer=producer)
        assert one.completed_hours == 1 and all(status == 'active' for _, status in one.lane_status)
        first_state = owner.last_candidate_state
        assert first_state.reference.physical_carry.completed_hours == 1
        trace(tmp_path, 'hour0_paired')
        with pytest.raises(ValueError, match='retained owner heads'):
            owner.run_next_development(expected_heads=('a'*64, 'b'*64), selector_producer=producer)
        assert normal._clock_index == 1
        install_launcher(monkeypatch, tmp_path, normal_reports(synthetic_reports, 1), 1)
        two = owner.run_next_development(expected_heads=owner.heads, selector_producer=producer)
        assert two.completed_hours == 2 and two.continuation_available
        assert not two.pending_attempt and not two.pending_intent
        assert all(status == 'active' for _, status in two.lane_status)
        final_state = owner.last_candidate_state
        with closing(owner._connect()) as db:
            rows = owner._rows(db)
        assert [row[2] for row in rows] == ['intent', 'outcome', 'attempt', 'intent', 'outcome']
        assert normal._clock_index == final_state.hour == 2
        assert len(calls) == 18 and sum(v['reference'] for v in calls) == 6
        trace(tmp_path, 'hour1_paired', owner_timings=owner.stage_timings, source_calls=source_calls)
        # An independent exact ledger check; no replacement of business code.
        lanes0, lanes1 = dict(first_state.lanes), dict(final_state.lanes)
        expected_recovery = Q((Q(1, 50)/Q(85, 100)*10**12).__floor__(), 10**12)
        for key in ('cfe', 'joint'):
            assert lanes0[key].business.identity != lanes1[key].business.identity
            records = lanes1[key].business.cursor.records
            a0, a1 = (r.response.action for r in records)
            q0, q1 = a0.grid_served+a0.cfe_served, a1.grid_served+a1.cfe_served
            assert q0 == Q(1, 50) and a0.recovery == 0 and q1 == 0 and a1.recovery == expected_recovery
            assert q0+a0.recovery <= Q(1, 2) and q1+a1.recovery <= Q(1, 2)
            ledger = lanes1[key].business.cursor.execution.tracks[0][1].ledger
            assert ledger.debt == q0-Q(85, 100)*a1.recovery
        for key in lanes1:
            for record in lanes1[key].business.cursor.records:
                action = record.response.action
                assert action.grid_served+action.cfe_served+action.recovery <= min(Q(1, 2), Q(1, 20))
        assert lanes1['network'].actual.identity != lanes1['cfe'].actual.identity
        assert final_state.reference.identity not in (lane.actual.identity for _, lane in final_state.lanes)
        heads, holder_head = owner.heads, holder.head
        scientific = final_state.scientific
        owner_timings = list(owner.stage_timings)
        last_terminal = normal.last_obligation_observation.terminal_sha256
        declaration = normal._parent._declaration
        parent_identity = normal._parent.identity
        anchor = normal._parent._anchor.inspect().record_sha256
        jobs = []
        for hour in range(2):
            job_root = normal._lease.root/f'job_{hour:03d}_non_authoritative'
            observed = json.loads((job_root/'observation.json').read_bytes())
            assert observed['exit_code'] == 0 and observed['whole_job_quiescent']
            jobs.append(observed)
        assert len({record['pid'] for record in jobs}) == 2
        leases = (normal._lease, normal._clock_lease, normal._obligation_lease,
            normal._parent._root_lease, normal._parent._journal._lease, normal._parent._anchor._lease,
            owner._lease_object, holder._lease_object)
        streams = tuple(lease.stream for lease in leases)
        def saved_bytes():
            roots = [Path(binding.root), owner_root, holder_root]
            return {str(path): sha256(path.read_bytes()).hexdigest() for root in roots
                    for path in root.rglob('*') if path.is_file()}
        before_reopen = saved_bytes()
        owner.close(); owner = None
        holder.close(); holder = None
        normal.close()
        assert all(stream.closed for stream in streams)
        assert all(lease.stream is None and not lease.locked for lease in leases)
        trace(tmp_path, 'closed_before_reopen')
        holder = m.saved.tickets.TicketHolder(holder_root, expected_head=holder_head, **holder_args)
        owner = m.DevelopmentOwner(owner_root, cfg, binding, holder=holder, expected_heads=heads)
        replayed = owner.inspect(expected_heads=heads)
        assert replayed.completed_hours == 2 and owner.last_candidate_state.scientific == scientific
        with pytest.raises(ValueError, match='read-only reopen'):
            owner.run_next_development(expected_heads=heads, selector_producer=producer)
        proof = historical.inspect(binding.root, expected_binding_sha256=binding.binding_sha256,
            expected_terminal_sha256=last_terminal, completed_hours=2)
        assert proof['historical_job_clock_prefix_verified']
        snapshot = m.normal.binding.snapshot.open_snapshot(declaration, expected_parent_identity=parent_identity,
            expected_anchor_record=anchor)
        try:
            assert snapshot.inspect().completed_hours == 2
        finally:
            snapshot.close()
        assert saved_bytes() == before_reopen
        reopen_leases = (owner._lease_object, holder._lease_object)
        reopen_streams = tuple(lease.stream for lease in reopen_leases)
        owner.close(); owner = None
        holder.close(); holder = None
        assert all(stream.closed for stream in (*streams, *reopen_streams))
        assert all(lease.stream is None and not lease.locked for lease in (*leases, *reopen_leases))
        result = dict(schema=m.SCHEMA, status='DRAFT_NONAUTHORITATIVE', synthetic_hours=2, lanes=3,
            normal_jobs=2, selector_stages=len(calls), real_native_calls=0,
            normal_job_observations=jobs, all_owned_lease_handles_closed=True,
            saved_file_count=len(before_reopen), reopen_all_saved_bytes_match=True,
            saved_files_sha256=before_reopen,
            phase_exact_source_prepare_replaced=False, historical_reader_replaced=False,
            source_window_loader_replaced=True, registry_context_replaced=True,
            normal_binding_fixture_replaced=True, historical_source_paths_replaced=True,
            exact_business_replaced=False, numerical_replay_replaced=False,
            phase_fresh_hours=source_calls, owner_stage_timings=owner_timings,
            outcome_head=heads[0], registry_head=heads[1], holder_head=holder_head,
            state=scientific, reopen_scientific_match=True, formal_result=False,
            full_192_hour_execution_verified=False, writer_rehydration_implemented=False,
            persisted_atomic_live_join_authenticated=False)
        result.update(test_only_static_identity_memo=True, production_overhead_measured=False,
            dynamic_source_or_history_or_state_cached=False)
        (tmp_path/'cross_hour_result.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
        trace(tmp_path, 'reopen_verified')
    finally:
        if owner is not None:
            owner.close()
        if holder is not None:
            holder.close()
        if normal._lease is not None:
            normal.close()
