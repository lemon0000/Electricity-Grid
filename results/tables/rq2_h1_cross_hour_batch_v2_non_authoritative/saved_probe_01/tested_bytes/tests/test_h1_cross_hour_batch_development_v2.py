"""Versioned batch reader/owner: inherited guards, saved-data oracle, tiny chain."""
from tests.test_h1_cross_hour_owner_development_v1 import *
from tests import test_h1_cross_hour_owner_development_v1 as predecessor_tests
from experiments import h1_cross_hour_owner_development_v2 as m

del test_two_hour_three_lane_connected_chain


@pytest.fixture(autouse=True)
def successor_helpers(monkeypatch):
    # Reuse the exact previous guard tests and explicitly synthetic helpers.
    # No predecessor source bytes or production dispatch is modified.
    monkeypatch.setattr(predecessor_tests, 'm', m)


@pytest.fixture
def saved_owner(saved_setup, monkeypatch, tmp_path):
    """Fault-test source seam; original scientific transition/replay stays live."""
    s = saved_setup
    def currents(root, *, expected_binding_sha256, expected_terminals, expected_registry_identity, selected_hours=None):
        selected = tuple(expected_terminals) if selected_hours is None else selected_hours
        return {hour:m.saved._fresh(s.binding, hour, expected_terminals[hour]) for hour in selected}
    monkeypatch.setattr(m.batch_source, 'prepare_many', currents)
    holder = m.saved.tickets.TicketHolder(tmp_path/'fault_holder_non_authoritative', owner_root=s.root,
        max_tickets=s.manifest.max_events, max_ticket_bytes=s.manifest.max_event_bytes,
        max_total_ticket_bytes=s.manifest.max_archive_bytes, create=True, retain_head=lambda *a:a[2])
    owner = m.DevelopmentOwner(s.root, s.manifest, s.binding, holder=holder, create=True)
    try:
        def consume(actual=True):
            current = s.currents[0]
            before = m.saved._initial(s.manifest, current)
            records = saved_records(monkeypatch, s, before, 0, actual=actual)
            packed = m.saved._pack_records(s.manifest, records[0], records[1])
            key = m._request(s.manifest, before, current)
            # Explicit saved bootstrap seam for fault tests, no normal Job.
            with owner._operation:
                rows, _, _ = owner._ready_replay(owner.heads)
                owner._reserve_check(rows, bootstrap=True)
                rows = owner._append('intent', dict(hour=0, terminal=s.binding.genesis_terminal_sha256, key=key,
                    source_audit=json.loads(current.source_projection_audit_payload), records=packed,
                    alternate=False, before_heads=owner.heads), rows)
                _, projection = m._transition(s.manifest, before, current, m.saved._unpack_records(s.manifest, packed))
                owner._append('outcome', dict(intent_head=rows[-1][4], key=key,
                    projection=json.loads(projection), projection_sha256=sha256(projection).hexdigest()), rows)
                return owner._inspect(expected_heads=owner.heads)
        yield s, owner, consume
    finally:
        owner.close()
        holder.close()


@pytest.mark.parametrize('pins,selected', [({},None), ({True:'a'*64},None), ({1:'a'*64},None),
    ({0:'a'*64, 2:'b'*64},None), ({0:'bad'},None), ({192:'a'*64},None),
    ({0:'a'*64},(1,)), ({0:'a'*64},(0,0)), ({0:'a'*64},(False,))])
def test_batch_invalid_map_rejected_before_reader(monkeypatch, pins, selected):
    def forbidden(*a, **kw):
        raise AssertionError('invalid map reached reader')
    monkeypatch.setattr(m.batch_source.historical, 'replay_prefixes', forbidden)
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


def test_successor_uses_own_request_contract(saved_owner):
    s, owner, consume = saved_owner
    initial = m.saved._initial(s.manifest, s.currents[0])
    assert m._request(s.manifest, initial, s.currents[0]) != m.saved._request(s.manifest, initial, s.currents[0])
    consume()
    with closing(owner._connect()) as db:
        outcome = json.loads(db.execute("SELECT body FROM events WHERE kind='outcome'").fetchone()[0])
    assert outcome['projection']['request_contract'] == m.SCHEMA
    assert outcome['projection']['request_key'] == outcome['key']


def test_restore_releases_batch_on_reducer_error(saved_owner, monkeypatch):
    _, owner, _ = saved_owner
    observed = []
    original = m.batch_source.prepare_many
    def record(*a, **kw):
        value = original(*a, **kw)
        observed.append(value)
        return value
    def fail(*a):
        raise RuntimeError('reducer failure')
    monkeypatch.setattr(m.batch_source, 'prepare_many', record)
    monkeypatch.setattr(owner, '_reduce_saved', fail)
    with owner._operation, pytest.raises(RuntimeError, match='reducer failure'):
        owner._restore([])
    assert len(observed) == 1 and observed[0] == {}


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
    oracle = {h:m.saved.source.prepare(root, expected_binding_sha256=binding,
        expected_terminal_sha256=terminals[h], completed_hours=h+1, expected_registry_identity='c'*64) for h in range(2)}
    calls = []
    original = m.batch_source.historical.replay_prefixes
    def observe(*a, **kw):
        calls.append(dict(hours=kw['completed_hours'], selected=list(kw['selected_hours'])))
        return original(*a, **kw)
    monkeypatch.setattr(m.batch_source.historical, 'replay_prefixes', observe)
    single = m.batch_source.prepare_many(root, expected_binding_sha256=binding,
        expected_registry_identity='c'*64, expected_terminals={0:terminals[0]})
    together = m.batch_source.prepare_many(root, expected_binding_sha256=binding,
        expected_registry_identity='c'*64, expected_terminals=terminals)
    assert single[0].source_projection_audit_payload == together[0].source_projection_audit_payload
    assert [row['hours'] for row in calls] == [1,1,2,2]
    for hour in range(2):
        old, new = oracle[hour], together[hour]
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
    calls = []
    original = m.batch_source.historical.replay_prefixes
    def observe(*a, **kw):
        if kw['completed_hours'] == 2:
            with closing(sqlite3.connect(tmp_path/'owner_non_authoritative/owner.sqlite')) as db:
                assert db.execute("SELECT COUNT(*) FROM events WHERE kind='attempt'").fetchone()[0] == 1
        calls.append(dict(hours=kw['completed_hours'], selected=list(kw['selected_hours'])))
        return original(*a, **kw)
    import sqlite3
    monkeypatch.setattr(m.batch_source.historical, 'replay_prefixes', observe)
    predecessor_tests.test_two_hour_three_lane_connected_chain(tmp_path, environment, real, synthetic_reports,
                                                               monkeypatch, static_code_identities)
    assert len(calls) == 20 and sum(row['hours'] for row in calls) == 28
    assert calls[-2:] == [dict(hours=2, selected=[0,1])]*2
    (tmp_path/'batch_replay_counts.json').write_text(json.dumps(dict(
        calls=calls, historical_prefix_hour_weight=28, batch_historical_calls=20,
        cross_call_cache_used=False, formal_result=False), indent=2)+'\n', encoding='utf-8')
