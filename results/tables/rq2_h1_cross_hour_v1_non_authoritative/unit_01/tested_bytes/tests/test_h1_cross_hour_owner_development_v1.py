"""Connected synthetic two-hour prefix, real joins/replay/business/persistence.

Source/catalog and solver-shaped records are explicitly fabricated. Normal
workers run in actual bounded Windows Jobs. No native solver or formal result.
"""
from contextlib import closing
from dataclasses import asdict, replace
from fractions import Fraction as Q
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

import pytest
from pyomo.environ import Var, value
from pyomo.opt import SolverResults, SolverStatus, SolutionStatus, TerminationCondition
from pyomo.opt.results.problem import ProblemSense

from experiments import h1_cross_hour_owner_development_v1 as m
from tests.test_h1_saved_source_parent_development_v1 import environment
from tests.test_rq2_normal_h1_source_binding_v1 import supplied
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver, spec, saved
from tests.test_h1_attested_saved_hour_development_v1 import synthetic_reports
from tests.test_rq2_v2_normal_obligation_controller_development_v1 import real
from tests import test_h1_exact_business_development_v1 as biz
from tests import test_h1_selector_replay_development_v1 as selectors


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
        assignment['generation[0,G1]'] = float(45).hex()
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
    code = (f'import sys;sys.path.insert(0,{str(Path.cwd())!r});sys.path.append({dependency!r});'
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
        selectors.LIMITS, 32, 1024**2, 32*1024**2, 'synthetic-two-hour-single-episode')


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


def test_detached_entries_reject_before_state_access():
    with pytest.raises(ValueError, match='detached'):
        m.PhaseController._step_development(object(), expected_source_identity='a'*64)
    for method in ('advance', 'prepare_next', 'complete_saved'):
        with pytest.raises(ValueError, match='atomic'):
            getattr(m.DevelopmentOwner, method)(object())


def test_two_hour_three_lane_connected_chain(tmp_path, environment, real, synthetic_reports, monkeypatch):
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
        producer = m.PhaseSelectorProducer(selectors.BUDGET)
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
        for key in ('cfe', 'joint'):
            assert lanes0[key].business.identity != lanes1[key].business.identity
            records = lanes1[key].business.cursor.records
            a0, a1 = (r.response.action for r in records)
            q0, q1 = a0.grid_served+a0.cfe_served, a1.grid_served+a1.cfe_served
            assert q0 == Q(1, 50) and a0.recovery == 0 and q1 == 0 and a1.recovery > 0
            assert q0+a0.recovery <= Q(1, 2) and q1+a1.recovery <= Q(1, 2)
            ledger = lanes1[key].business.cursor.execution.tracks[0][1].ledger
            assert ledger.debt == q0-Q(85, 100)*a1.recovery
        assert lanes1['network'].actual.identity != lanes1['cfe'].actual.identity
        assert final_state.reference.identity not in (lane.actual.identity for _, lane in final_state.lanes)
        heads, holder_head = owner.heads, holder.head
        scientific = final_state.scientific
        owner_timings = list(owner.stage_timings)
        last_terminal = normal.last_obligation_observation.terminal_sha256
        declaration = normal._parent._declaration
        parent_identity = normal._parent.identity
        anchor = normal._parent._anchor.inspect().record_sha256
        owner.close(); owner = None
        holder.close(); holder = None
        normal.close()
        trace(tmp_path, 'closed_before_reopen')
        holder = m.saved.tickets.TicketHolder(holder_root, expected_head=holder_head, **holder_args)
        owner = m.DevelopmentOwner(owner_root, cfg, binding, holder=holder, expected_heads=heads)
        replayed = owner.inspect(expected_heads=heads)
        assert replayed.completed_hours == 2 and owner.last_candidate_state.scientific == scientific
        proof = historical.inspect(binding.root, expected_binding_sha256=binding.binding_sha256,
            expected_terminal_sha256=last_terminal, completed_hours=2)
        assert proof['historical_job_clock_prefix_verified']
        snapshot = m.normal.binding.snapshot.open_snapshot(declaration, expected_parent_identity=parent_identity,
            expected_anchor_record=anchor)
        try:
            assert snapshot.inspect().completed_hours == 2
        finally:
            snapshot.close()
        result = dict(schema=m.SCHEMA, status='DRAFT_NONAUTHORITATIVE', synthetic_hours=2, lanes=3,
            normal_jobs=2, selector_stages=len(calls), real_native_calls=0,
            source_adapter_replaced=False, historical_reader_replaced=False,
            exact_business_replaced=False, numerical_replay_replaced=False,
            source_calls=source_calls, owner_stage_timings=owner_timings,
            outcome_head=heads[0], registry_head=heads[1], holder_head=holder_head,
            state=scientific, reopen_scientific_match=True, formal_result=False,
            full_192_hour_execution_verified=False, writer_rehydration_implemented=False,
            persisted_atomic_live_join_authenticated=False)
        (tmp_path/'cross_hour_result.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
        trace(tmp_path, 'reopen_verified')
    finally:
        if owner is not None:
            owner.close()
        if holder is not None:
            holder.close()
        if normal._lease is not None:
            normal.close()
