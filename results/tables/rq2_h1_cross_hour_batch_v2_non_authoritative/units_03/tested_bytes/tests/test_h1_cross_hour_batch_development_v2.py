"""Batch successor tests plus unchanged predecessor guard regression."""
from tests.test_h1_cross_hour_owner_development_v1 import *
from tests import test_h1_cross_hour_owner_development_v1 as predecessor_tests
from experiments import h1_cross_hour_owner_development_v2 as m

del test_two_hour_three_lane_connected_chain


@pytest.mark.parametrize('pins,selected', [({},None), ({True:'a'*64},None), ({1:'a'*64},None),
    ({0:'a'*64, 2:'b'*64},None), ({0:'bad'},None), ({192:'a'*64},None),
    ({0:'a'*64},(1,)), ({0:'a'*64},(0,0)), ({0:'a'*64},(False,))])
def test_batch_invalid_map_rejected_before_reader(monkeypatch, pins, selected):
    with pytest.raises(ValueError):
        m.batch_source.prepare_many('unused', expected_binding_sha256='c'*64,
            expected_registry_identity='d'*64, expected_terminals=pins, selected_hours=selected)


def test_prefix_evidence_excludes_future_hashes():
    api = m.batch_source.historical
    evidence = {'obligation_non_authoritative/binding.json':'a'*64,
        'obligation_non_authoritative/000.terminal.json':'b'*64,
        'job_000_non_authoritative/request.json':'c'*64,
        'clock_bridge_non_authoritative/000/terminal.json':'d'*64,
        'obligation_non_authoritative/001.terminal.json':'e'*64,
        'job_001_non_authoritative/request.json':'f'*64,
        'clock_bridge_non_authoritative/001/terminal.json':'1'*64}
    old = api.prefix_evidence(evidence, 0)
    changed = {name:pin if '/000' in name or 'job_000' in name or name.endswith('/binding.json') else '2'*64
               for name,pin in evidence.items()}
    assert api.prefix_evidence(changed, 0) == old
    assert api.prefix_evidence(changed, 1) != api.prefix_evidence(evidence, 1)
    assert len(old) == 4


def test_batch_retained_byte_limit(monkeypatch):
    api = m.batch_source.historical
    monkeypatch.setattr(api, 'MAX_RETAINED_BYTES', 32)
    with pytest.raises(ValueError, match='byte cap'):
        api.retained_size({'payload':b'x'*64})


def test_successor_uses_own_request_contract(saved_setup, monkeypatch):
    s = saved_setup
    current = s.currents[0]
    initial = m.saved._initial(s.manifest, current)
    assert m._request(s.manifest, initial, current) != m.saved._request(s.manifest, initial, current)
    records = saved_records(monkeypatch, s, initial, 0)
    records = m.saved._unpack_records(s.manifest,m.saved._pack_records(s.manifest,*records))
    _, projection = m._transition(s.manifest, initial, current, records)
    projected = json.loads(projection)
    assert projected['request_contract'] == m.SCHEMA
    assert projected['request_key'] == m._request(s.manifest, initial, current)


def test_owner_rejects_replaced_source_before_call(monkeypatch):
    calls=[]
    def forbidden(*a, **kw):
        calls.append(True)
        raise AssertionError('replacement source called')
    monkeypatch.setattr(m.batch_source, 'prepare_many', forbidden)
    with pytest.raises(ValueError, match='original batch source'):
        m.DevelopmentOwner._currents(object(), [])
    assert calls == []


@pytest.mark.parametrize('entry', ['source','reader'])
def test_owner_constructor_rejects_entry_drift_before_root(tmp_path,monkeypatch,entry):
    calls=[]
    def replacement(*a,**kw):calls.append(True)
    module,name=(m.batch_source,'prepare_many') if entry=='source' else (m.batch_source.historical,'replay_prefixes')
    monkeypatch.setattr(module,name,replacement)
    root=tmp_path/'untouched_owner'
    with pytest.raises(ValueError,match='original batch'):
        m.DevelopmentOwner(root,object(),object(),create=True)
    assert not root.exists() and calls==[]


def test_owner_diagnostic_cap_rejects_before_source():
    owner=object.__new__(m.DevelopmentOwner)
    owner.batch_observations=[None]*m.MAX_BATCH_OBSERVATIONS
    with pytest.raises(ValueError,match='observations exhausted'):owner._currents([])


def test_source_rejects_replaced_reader_before_path_read(monkeypatch):
    calls=[]
    def forbidden(*a, **kw):
        calls.append(True)
        raise AssertionError('replacement reader called')
    monkeypatch.setattr(m.batch_source.historical, 'replay_prefixes', forbidden)
    with pytest.raises(ValueError, match='original batch historical'):
        m.batch_source.prepare_many('unused', expected_binding_sha256='c'*64,
            expected_registry_identity='d'*64, expected_terminals={0:'a'*64})
    assert calls == []


def test_owner_rejects_predecessor_current_contract(saved_setup):
    s=saved_setup
    metrics=tuple(dict(completed_hours=1, selected_hours=[0], parent_inspect_traversals=2,
                       observation_token=str(i)*32) for i in (1,2))
    value=m.batch_source.CurrentBatch({0:s.currents[0]}, metrics)
    with pytest.raises(ValueError):
        m._validate_batch(value,s.binding,{0:s.binding.genesis_terminal_sha256},(0,),'a'*64)


@pytest.mark.parametrize('primary_exists', [True,False])
@pytest.mark.parametrize('failed', ['reader','lease'])
def test_close_failure_clears_captured_and_attempts_all(primary_exists, failed):
    api=m.batch_source.historical
    calls=[]
    failure=RuntimeError('injected '+failed+' close failure')
    primary=ValueError('primary failure') if primary_exists else None
    class Resource:
        def __init__(self,name):self.name=name
        def close(self):
            calls.append(self.name)
            if self.name==failed:raise failure
    captured={0:object()}
    if primary is None:
        with pytest.raises(RuntimeError) as caught:
            api._close_replay(Resource('reader'),[Resource('last'),Resource('lease')],captured,True,None)
        assert caught.value is failure
    else:
        api._close_replay(Resource('reader'),[Resource('last'),Resource('lease')],captured,True,primary)
        assert 'cleanup also failed' in primary.__notes__[0]
    assert captured=={} and calls==['reader','lease','last']


def test_restore_releases_batch_on_reducer_error(monkeypatch):
    currents={0:object()}
    owner=object.__new__(m.DevelopmentOwner)
    owner._currents=lambda *a:currents
    def fail(*a):raise RuntimeError('reducer failure')
    owner._reduce_saved=fail
    with pytest.raises(RuntimeError,match='reducer failure'):owner._restore([])
    assert currents=={}


def _saved_environment(environment, real, monkeypatch):
    load = predecessor_tests.install_rows(monkeypatch)
    predecessor_tests.install_registry(monkeypatch, environment, load)
    resolver, ordinal = real
    binding = m.normal.binding
    node = resolver.resolve('training_ub', ordinal)
    monkeypatch.setattr(binding, 'open_manifest', lambda:resolver)
    monkeypatch.setattr(binding, 'precheck', lambda *a, **kw:node)
    monkeypatch.setattr(binding, 'prevalidate_enrollment', lambda *a, **kw:dict(test_only_synthetic_source=True))
    monkeypatch.setattr(m.saved.source.historical, '_source_paths', lambda d:(
        {Path(d['config_path']), Path(d['upstream_root'])/'SHA256SUMS'}, {Path(d['upstream_root'])}))


def test_saved_two_hour_batch_matches_independent_prefix_oracle(tmp_path, environment, real, monkeypatch, static_code_identities):
    _saved_environment(environment, real, monkeypatch)
    root = Path('D:/h1_cross_connected_06_non_authoritative/test_two_hour_three_lane_conne0/normal_non_authoritative')
    def saved_bytes():
        return {str(p):sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
    before = saved_bytes()
    binding = sha256((root/'obligation_non_authoritative/binding.json').read_bytes()).hexdigest()
    terminals = {h:sha256((root/f'obligation_non_authoritative/{h:03d}.terminal.json').read_bytes()).hexdigest() for h in range(2)}
    oracle={}
    for h in range(2):
        oracle[h]=m.saved.source.prepare(root, expected_binding_sha256=binding,
            expected_terminal_sha256=terminals[h], completed_hours=h+1, expected_registry_identity='c'*64)
        trace(tmp_path,'oracle_hour_'+str(h))
    single = m.batch_source.prepare_many(root, expected_binding_sha256=binding,
        expected_registry_identity='c'*64, expected_terminals={0:terminals[0]})
    trace(tmp_path,'single_batch_done')
    together = m.batch_source.prepare_many(root, expected_binding_sha256=binding,
        expected_registry_identity='c'*64, expected_terminals=terminals)
    trace(tmp_path,'two_hour_batch_done')
    calls=list(single.observations+together.observations)
    assert single.currents[0].source_projection_audit_payload == together.currents[0].source_projection_audit_payload
    assert [row['completed_hours'] for row in calls] == [1,1,2,2]
    assert all(row['parent_inspect_traversals']==2 for row in calls)
    assert len({row['observation_token'] for row in calls})==4
    source_binding=m.saved.SourceBinding(str(root),binding,'c'*64,terminals[0])
    m._validate_batch(together,source_binding,terminals,(0,1),m.batch_source.implementation_identity())
    for hour in range(2):
        old, new = oracle[hour], together.currents[hour]
        assert old.exogenous_scientific_payload == new.exogenous_scientific_payload
        assert old.workload_exact == new.workload_exact and old.source_cfe_at_alpha_one_exact == new.source_cfe_at_alpha_one_exact
        a, b = old.prepared_current, new.prepared_current
        assert a.decision.decision_bytes == b.decision.decision_bytes
        for name in ('frame', 'source_origin', 'source_action'):
            assert m.saved.source.physical._digest(getattr(a,name)) == m.saved.source.physical._digest(getattr(b,name))
        assert json.loads(new.source_projection_audit_payload)['schema'] == m.batch_source.SCHEMA
        old_proof = json.loads(old.source_projection_audit_payload)['historical_controller']
        new_proof = json.loads(new.source_projection_audit_payload)['historical_controller']
        assert old_proof['evidence_identity'] == new_proof['evidence_identity']
    valid=together.currents[0]
    for key,replacement in [('schema',m.saved.source.SCHEMA),('implementation_identity','1'*64),
            ('controller_binding_sha256','2'*64),('controller_terminal_sha256','3'*64),
            ('registry_identity','4'*64),('completed_hours',2),('replay_contract','old'),('formal_result',True)]:
        audit=json.loads(valid.source_projection_audit_payload);audit[key]=replacement
        raw=m.batch_source.io.encode(audit)
        prepared=m.saved.source.normal._owned(type(valid.prepared_current),
            **{**vars(valid.prepared_current),'audit_payload':raw})
        altered=m.saved.source.normal._owned(type(valid),
            **{**vars(valid),'prepared_current':prepared,'source_projection_audit_payload':raw})
        bundle=m.batch_source.CurrentBatch({0:altered,1:together.currents[1]},together.observations)
        with pytest.raises(ValueError):
            m._validate_batch(bundle,source_binding,terminals,(0,1),m.batch_source.implementation_identity())
    invalid_maps = [dict(enumerate(reversed(tuple(terminals.values())))),
                   {0:binding, 1:terminals[1]}, {0:terminals[0], 1:terminals[0]},
                   {0:terminals[0], 2:terminals[1]}]
    for invalid in invalid_maps:
        with pytest.raises(ValueError):
            m.batch_source.prepare_many(root, expected_binding_sha256=binding,
                expected_registry_identity='c'*64, expected_terminals=invalid)
    assert saved_bytes() == before
    (tmp_path/'saved_prefix_batch_oracle.json').write_text(json.dumps(dict(
        status='DRAFT_NONAUTHORITATIVE', baseline_normal_root=str(root), saved_files=before,
        complete_hour0_audit_standalone_vs_batch_equal=True, scientific_slices_equal_to_predecessor=True,
        observed_batch_calls=calls, invalid_terminal_maps_rejected=len(invalid_maps),
        real_native_calls=0, new_normal_jobs=0, formal_result=False), indent=2)+'\n', encoding='utf-8')


def test_two_hour_three_lane_batch_chain(tmp_path, environment, real, synthetic_reports, monkeypatch, static_code_identities):
    monkeypatch.setattr(predecessor_tests, 'm', m)
    trace(tmp_path, 'start', synthetic_hours=2, lanes=3, formal_result=False)
    load = install_rows(monkeypatch)
    install_registry(monkeypatch, environment, load)
    historical = m.saved.source.historical
    monkeypatch.setattr(historical, '_source_paths', lambda d: (
        {Path(d['config_path']), Path(d['upstream_root'])/'SHA256SUMS'}, {Path(d['upstream_root'])}))
    normal = controller(tmp_path/'normal_non_authoritative', environment, real, monkeypatch)
    holder = owner = None
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
        trace(tmp_path, 'hour1_paired', owner_timings=owner.stage_timings, batch_observations=owner.batch_observations)
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
        batch_observations = list(owner.batch_observations)
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
        owner.close(); owner = None
        holder.close(); holder = None
        normal.close()
        assert all(stream.closed for stream in streams)
        assert all(lease.stream is None and not lease.locked for lease in leases)
        before_reopen = saved_bytes()
        trace(tmp_path, 'closed_before_reopen')
        holder = m.saved.tickets.TicketHolder(holder_root, expected_head=holder_head, **holder_args)
        owner = m.DevelopmentOwner(owner_root, cfg, binding, holder=holder, expected_heads=heads)
        # Construction performs the full inspect/replay. Check its output
        # directly rather than repeating the same complete historical replay.
        assert owner.last_candidate_state.hour == 2 and owner.last_candidate_state.scientific == scientific
        batch_observations.extend(owner.batch_observations)
        assert len(batch_observations)==20
        assert sum(row['completed_hours'] for row in batch_observations)==28
        assert sum(row['parent_inspect_traversals'] for row in batch_observations)==40
        assert len({row['observation_token'] for row in batch_observations})==20
        proof = historical.inspect(binding.root, expected_binding_sha256=binding.binding_sha256,
            expected_terminal_sha256=last_terminal, completed_hours=2)
        assert proof['historical_job_clock_prefix_verified']
        snapshot = m.normal.binding.snapshot.open_snapshot(declaration, expected_parent_identity=parent_identity,
            expected_anchor_record=anchor)
        try:
            assert snapshot.inspect().completed_hours == 2
        finally:
            snapshot.close()
        reopen_leases = (owner._lease_object, holder._lease_object)
        reopen_streams = tuple(lease.stream for lease in reopen_leases)
        owner.close(); owner = None
        holder.close(); holder = None
        assert all(stream.closed for stream in (*streams, *reopen_streams))
        assert all(lease.stream is None and not lease.locked for lease in (*leases, *reopen_leases))
        assert saved_bytes() == before_reopen
        result = dict(schema=m.SCHEMA, status='DRAFT_NONAUTHORITATIVE', synthetic_hours=2, lanes=3,
            normal_jobs=2, selector_stages=len(calls), real_native_calls=0,
            normal_job_observations=jobs, all_owned_lease_handles_closed=True,
            saved_file_count=len(before_reopen), reopen_all_saved_bytes_match=True,
            saved_files_sha256=before_reopen,
            source_route=m.batch_source.SCHEMA, historical_reader_route=m.batch_source.historical.SCHEMA,
            predecessor_source_and_reader_bytes_preserved=True,
            source_window_loader_replaced=True, registry_context_replaced=True,
            normal_binding_fixture_replaced=True, historical_source_paths_replaced=True,
            exact_business_replaced=False, numerical_replay_replaced=False,
            batch_observations=batch_observations, owner_stage_timings=owner_timings,
            batch_historical_calls=20, historical_prefix_hour_weight=28,
            parent_inspect_traversals=40, parent_inspect_prefix_hour_weight=56,
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
