"""Saved F adapter/protocol checks; no new five-hour fresh execution."""
from copy import deepcopy
from hashlib import sha256
from functools import lru_cache
import json
from pathlib import Path
import sys
import time

import pytest

from src import staged_rts24_saved_fresh_adoption_v1 as f
from experiments import staged_rts24_saved_fresh_adoption_v1 as cli


@pytest.fixture
def deny_scientific_effects(monkeypatch):
    import highspy
    import pyomo.environ as pyo
    import subprocess
    def denied(*args, **kwargs): pytest.fail('saved adapter requested native/spawn/journal/publication')
    for module, name in ((pyo, 'SolverFactory'), (highspy, 'Highs'), (subprocess, 'Popen'),
            (f.prefix.point.backend, 'make_model'), (f.prefix.point.backend, 'call_highs'),
            (f.codec.EvidenceStore, 'put'), (f.codec, 'publish'), (f.journal, 'publish')):
        monkeypatch.setattr(module, name, denied)
    for name in ('create_session', 'begin_step', 'commit_step', 'finish'):
        monkeypatch.setattr(f.journal, name, denied)


@pytest.fixture
def payload():
    prior = f.ROOT/'results/tables/staged_rts24_saved_journal_check_v1_non_authoritative/checks_01'
    observed = json.loads((prior/'saved_journal_observation.json').read_bytes())
    frozen = _comparison_arguments()
    value = dict(schema=f.SCHEMA, authority='DRAFT_NONAUTHORITATIVE', scope=f.SCOPE,
        context_sha='a'*64, caller_sha=frozen['caller_sha'], source_sha=frozen['source_sha'], input_pins_sha=frozen['input_pins_sha'],
        metrics=json.loads((f.P1/'fresh.json').read_bytes())['metrics'], evidence_refs=observed['evidence_refs'],
        prefix_bindings=[json.loads((f.P1/f'trusted_prefixes/prefix_{n:06d}.json').read_bytes()) for n in range(6)],
        trusted_binding=json.loads((f.P1/'trusted_binding.json').read_bytes()), **f.GATES)
    f.validate_payload(value)
    return value


@lru_cache(maxsize=1)
def _test_caller_image():
    return f.capture(cli.source_pins()).image


def _comparison_arguments():
    image = _test_caller_image(); core = f.codec.parse(image)
    return dict(context_sha='a'*64, caller_sha=sha256(image).hexdigest(), source_sha=f.digest(core['source']),
        input_pins_sha=f.digest(core['files']), caller_image=image)


def compare(left, right):
    return f.compare_payloads(f.codec.canonical(left), f.codec.canonical(right), **_comparison_arguments())


def test_complete_metrics_comparison_retains_missing_input_and_closed_gates(payload):
    result = compare(payload, deepcopy(payload))
    assert result['payload_byte_equality_verified'] is True and result['point_references'] == 21
    assert result['saved_P1_fresh_process_verified'] is result['saved_P1_parent_adoption_verified'] is False
    assert all(result[k] is False for k in f.GATES)
    assert payload['metrics']['summary']['coverage_complete'] is False
    assert payload['metrics']['summary']['method_conditions_satisfied'] is None
    assert set(payload['metrics']) == set(f.METRIC_FIELDS) and len(f.METRIC_FIELDS) == 19


@pytest.mark.parametrize('field', f.METRIC_FIELDS)
def test_any_complete_metric_drift_blocks_comparison(payload, field):
    changed = deepcopy(payload)
    original = changed['metrics'][field]
    if original is None: changed['metrics'][field] = 'changed'
    elif type(original) is bool: changed['metrics'][field] = not original
    elif type(original) is int: changed['metrics'][field] = original+1
    elif type(original) is list: changed['metrics'][field] = ['changed']
    elif type(original) is dict: changed['metrics'][field]['changed'] = True
    else: changed['metrics'][field] = '0'*64
    with pytest.raises(ValueError): compare(payload, changed)


@pytest.mark.parametrize('field', ['context_sha', 'source_sha', 'input_pins_sha', 'caller_sha', 'evidence_refs', 'prefix_bindings', 'trusted_binding'])
def test_common_payload_binding_and_evidence_drift_blocks_comparison(payload, field):
    changed = deepcopy(payload)
    if field == 'evidence_refs': changed[field][20]['evidence_ref'] = '0'*64
    elif field == 'prefix_bindings': changed[field][5]['known_state_sha'] = '0'*64
    elif field == 'trusted_binding': changed[field]['closed'] = False
    else: changed[field] = '0'*64
    with pytest.raises(ValueError): compare(payload, changed)


@pytest.mark.parametrize('fault', ['extra', 'missing', 'duplicate', 'nonfinite', 'pretty'])
def test_payload_parsing_requires_closed_canonical_json(payload, fault):
    value = deepcopy(payload)
    if fault == 'extra': value['extra'] = True
    elif fault == 'missing': del value['metrics']['independent_audit']
    if fault == 'duplicate': raw = b'{"x":1,"x":2}'
    elif fault == 'nonfinite': raw = b'{"x":NaN}'
    elif fault == 'pretty': raw = json.dumps(value, indent=2).encode()
    else: raw = f.codec.canonical(value)
    with pytest.raises(ValueError): f.compare_payloads(raw, raw, **_comparison_arguments())


def test_bootstrap_parser_matches_original_codec_for_saved_payload(payload):
    raw = f.codec.canonical(payload)
    assert cli.parse(raw) == f.codec.parse(raw) == payload
    assert cli.canonical(payload) == raw


@pytest.mark.parametrize('raw', [b'{"x":1,"x":2}', b'{"x":NaN}', b'{}\n', b'['*257+b']'*257])
def test_bootstrap_parser_rejects_invalid_images_before_scientific_imports(raw):
    with pytest.raises(ValueError): cli.parse(raw)


def test_frozen_source_inventory_and_planned_set_are_exact():
    assert cli.source_names() == f.SOURCES and len(f.E_SOURCES) == 45 and len(f.SOURCES) == 49
    assert len(cli.TARGETS) == 17 and len(set(cli.TARGETS)) == 17
    assert len(cli.RECORDS) == 4 and 4*cli.CAPS['record_bytes'] == 524288
    assert sum(cli.STAGE_SECONDS.values()) == cli.CAPS['wall_seconds'] == 180


def test_source_inventory_is_independently_pinned(tmp_path, monkeypatch):
    changed = tmp_path/'inherited.json'
    data = json.loads(cli.INHERITED.read_bytes())
    old = next(iter(data)); data['src/forged.py'] = data.pop(old)
    changed.write_bytes(json.dumps(data).encode())
    monkeypatch.setattr(cli, 'INHERITED', changed)
    with pytest.raises(ValueError, match='frozen inherited'): cli.source_names()


@pytest.fixture
def context(tmp_path):
    raw = cli.make_context(tmp_path/'output', started=time.monotonic())
    return cli.parse(raw)


def safety(context, root):
    raw = cli.canonical(context)
    return cli.safety_accounting(cli.hold_context(raw, sha256(raw).hexdigest()), root)


def test_context_binds_actual_compute_executable_inputs_sources_and_budget(context):
    raw = cli.canonical(context)
    assert cli.check_context(raw, sha256(raw).hexdigest()) == context
    assert context['executable']['path'] == str(Path(sys.executable).absolute())
    assert context['input_files'] == json.loads(cli.read(f.ANCHOR))['p1_files']
    assert all(context[k] is False for k in cli.GATES)
    for role in ('supervise', 'parent', 'fresh'):
        argv = cli.argv_for(role, raw, sha256(raw).hexdigest())
        assert argv[:4] == [str(cli.EXE), '-B', '-s', str(cli.ROOT/cli.NEW_SOURCES[1])]
        assert '--'+role in argv
    assert cli.argv_for('fresh', raw, sha256(raw).hexdigest())[-1] == str(Path(context['output_root'])/'worker/fresh')


@pytest.mark.parametrize('fault', ['source', 'exe', 'environment', 'input_map', 'budget', 'expired', 'extra', 'overlap'])
def test_context_drift_or_wrong_binding_is_rejected(context, fault):
    value = deepcopy(context)
    if fault == 'source': value['source_pins'][cli.NEW_SOURCES[0]]['sha256'] = '0'*64
    elif fault == 'exe': value['executable']['pin']['sha256'] = '0'*64
    elif fault == 'environment': value['environment']['PYTHONHASHSEED'] = 'changed'
    elif fault == 'input_map': value['input_files']['fresh.json']['sha256'] = '0'*64
    elif fault == 'budget': value['limits']['wall_seconds'] = 181
    elif fault == 'expired': value['deadline'] = 1.0
    elif fault == 'extra': value['grant'] = True
    else: value['output_root'] = str(cli.P1/'output')
    raw = cli.canonical(value)
    with pytest.raises(ValueError): cli.check_context(raw, sha256(raw).hexdigest())


def test_unknown_quiet_safety_accounting_reads_metadata_only(context, monkeypatch):
    root = Path(context['output_root'])
    target = root/'worker/fresh/stdout.log'; target.parent.mkdir(parents=True); target.write_bytes(b'log')
    # Construct the validated token before blocking all subsequent content reads.
    raw = cli.canonical(context); held = cli.hold_context(raw, sha256(raw).hexdigest())
    monkeypatch.setattr(cli, 'read', lambda *a, **k: pytest.fail('safety accounting read artifact content'))
    result = cli.safety_accounting(held, root)
    assert result['bytes'] == 3 and result['files'] == 1
    assert result['remaining_reserved_bytes'] == 524288 and result['remaining_reserved_files'] == 4
    assert result['safety_only'] is True and result['worker_accounting'] == 'unknown' and result['content_read'] is False


@pytest.mark.parametrize('fault', ['extra', 'extra_dir', 'oversized_record', 'record_conflict', 'hardlink', 'storage'])
def test_safety_accounting_rejects_unbounded_or_unexpected_outputs(context, fault):
    tmp_path = Path(context['output_root']); tmp_path.mkdir()
    if fault == 'extra': (tmp_path/'extra').write_bytes(b'x')
    elif fault == 'extra_dir': (tmp_path/'extra').mkdir()
    elif fault == 'hardlink':
        import os
        first = tmp_path/'worker/parent.stdout.log'; first.parent.mkdir(); first.write_bytes(b'x')
        os.link(first, first.with_name('parent.stderr.log'))
    else:
        target = tmp_path/'worker/launcher.json'; target.parent.mkdir()
        if fault == 'record_conflict':
            target.write_bytes(b'{}'); target.with_name(target.name+'.pending').write_bytes(b'{}')
        elif fault == 'oversized_record': target.write_bytes(b'x'*131073)
        else: target.with_name('parent.stdout.log').write_bytes(b'x'*(cli.CAPS['output_bytes']-524288+1))
    with pytest.raises(ValueError): safety(context, tmp_path)


def test_record_pending_consumes_one_slot_without_double_charging(context):
    root = Path(context['output_root'])
    target = root/'worker/fresh_parent/parent_observation.json.pending'
    target.parent.mkdir(parents=True); target.write_bytes(b'x'*100)
    result = safety(context, root)
    assert result['remaining_reserved_bytes'] == 524188 and result['remaining_reserved_files'] == 3
    assert result['bytes']+result['remaining_reserved_bytes'] == 524288


def test_one_saved_parent_adapter_matches_all_original_metrics_without_effects(deny_scientific_effects, context):
    held = f.hold(context['source_pins'], cli.canonical(context['caller_core']))
    before = {name: f.mechanical.pin((f.P1/name).read_bytes()) for name in held.files}
    result = f.replay(held, 'a'*64)
    assert result['metrics'] == json.loads((f.P1/'fresh.json').read_bytes())['metrics']
    assert len(result['evidence_refs']) == 21 and len(result['prefix_bindings']) == 6
    assert all(result[k] is False for k in f.GATES)
    assert before == {name: f.mechanical.pin((f.P1/name).read_bytes()) for name in held.files}


@pytest.mark.parametrize('field', ['files', 'source', 'fixture', 'anchor_identity', 'expectations', 'trusted'])
def test_adapter_caller_image_rejects_late_expectation_mutation(deny_scientific_effects, field):
    held = f.capture(cli.source_pins())
    if field == 'files': held.files[next(iter(held.files))]['sha256'] = '0'*64
    elif field == 'source': held.source[next(iter(held.source))]['sha256'] = '0'*64
    elif field == 'fixture': object.__setattr__(held.fixture, 'source_identity', '0'*64)
    elif field == 'anchor_identity': object.__setattr__(held, 'anchor_identity', (0, 0, 0, 0))
    elif field == 'expectations': held.expectations['registration_sha'] = '0'*64
    else: held.trusted['known_state_sha'] = '0'*64
    with pytest.raises(ValueError, match='caller expectation'): f.bookend(held, inventory=False)


def test_both_payloads_cannot_replace_the_external_caller_digest(payload):
    changed = deepcopy(payload); changed['caller_sha'] = '0'*64
    with pytest.raises(ValueError, match='held parent/fresh binding'): compare(changed, changed)


@pytest.mark.parametrize('domain', ['summary', 'audit', 'evidence', 'prefix', 'trusted'])
def test_same_corruption_on_both_sides_cannot_keep_the_original_caller_label(payload, domain):
    changed = deepcopy(payload)
    if domain == 'summary': changed['metrics']['summary']['fx_contract_status'] = 'forged'
    elif domain == 'audit': changed['metrics']['independent_audit']['record_consistency_satisfied'] = False
    elif domain == 'evidence': changed['evidence_refs'][20]['query_sha'] = '0'*64
    elif domain == 'prefix': changed['prefix_bindings'][5]['known_state_sha'] = '0'*64
    else: changed['trusted_binding']['known_cas_keys'] = changed['trusted_binding']['known_cas_keys'][:-1]
    assert changed['caller_sha'] == payload['caller_sha']
    with pytest.raises(ValueError, match='complete saved domain'): compare(changed, changed)


def test_external_caller_image_rejects_same_bytes_new_anchor_identity(context, monkeypatch):
    original = f.stamp
    monkeypatch.setattr(f, 'stamp', lambda path: (0, 0, 0, 0) if path == f.ANCHOR else original(path))
    with pytest.raises(ValueError, match='external caller image'):
        f.hold(context['source_pins'], cli.canonical(context['caller_core']))


def test_context_cannot_extend_deadline_by_rehashing(context):
    changed = deepcopy(context); changed['deadline'] += 10000
    raw = cli.canonical(changed)
    with pytest.raises(ValueError, match='invocation budget'): cli.check_context(raw, sha256(raw).hexdigest())


@pytest.mark.parametrize('target', ['repo', 'src', 'other_result', 'arbitrary_temp'])
def test_context_output_scope_does_not_expand_with_a_new_sha(context, tmp_path, target):
    changed = deepcopy(context)
    changed['output_root'] = str({'repo': cli.ROOT, 'src': cli.ROOT/'src',
        'other_result': f.P1.parent, 'arbitrary_temp': tmp_path/'other'}[target])
    raw = cli.canonical(changed)
    with pytest.raises(ValueError): cli.check_context(raw, sha256(raw).hexdigest())


def test_argv_requires_the_same_raw_context_and_sha(context):
    raw = cli.canonical(context)
    other = deepcopy(context); other['deadline'] -= 1
    with pytest.raises(ValueError, match='context SHA'):
        cli.argv_for('fresh', raw, sha256(cli.canonical(other)).hexdigest())


def test_bootstrap_environment_matches_the_bound_original_without_importing_it():
    from src.staged_rts24_process_guard_v1 import controlled_environment
    assert cli.environment() == controlled_environment()


def test_actual_entry_and_expanded_arguments_are_bound(context, monkeypatch):
    raw = cli.canonical(context); digest = sha256(raw).hexdigest()
    entry = str(cli.ROOT/cli.NEW_SOURCES[1])
    monkeypatch.setattr(sys.modules['__main__'], '__file__', entry)
    monkeypatch.setattr(sys, 'argv', cli.argv_for('fresh', raw, digest)[3:])
    assert cli.validate_actual_entry('fresh', raw, digest) == context
    monkeypatch.setattr(sys, 'argv', [entry, '--fresh'])
    with pytest.raises(ValueError, match='actual role entry'): cli.validate_actual_entry('fresh', raw, digest)


def test_safety_accounting_rejects_layer_roots_even_when_they_exist(context):
    root = Path(context['output_root']); (root/'worker/fresh').mkdir(parents=True)
    for wrong in (root/'worker', root/'worker/fresh'):
        with pytest.raises(ValueError, match='global F output root'): safety(context, wrong)


def test_actual_test_argv_cannot_enter_F_execution_or_adoption(context, monkeypatch):
    raw = cli.canonical(context); digest = sha256(raw).hexdigest(); entry = str(cli.ROOT/cli.NEW_SOURCES[1])
    monkeypatch.setattr(sys.modules['__main__'], '__file__', entry)
    monkeypatch.setattr(sys, 'argv', cli.argv_for('parent', raw, digest)[3:])
    with pytest.raises(ValueError, match='ordinary test context'):
        cli.execution_context('parent', raw, digest)


def test_safety_context_cannot_be_redirected_by_mutating_its_source_dict(context):
    root = Path(context['output_root']); (root/'worker').mkdir(parents=True)
    raw = cli.canonical(context); held = cli.hold_context(raw, sha256(raw).hexdigest())
    context['output_root'] = str(root/'worker')
    with pytest.raises(ValueError, match='global F output root'): cli.safety_accounting(held, root/'worker')
    with pytest.raises(ValueError, match='held context'): cli.safety_accounting(context, root/'worker')


def test_safety_context_detects_output_root_replacement(context):
    root = Path(context['output_root']); root.mkdir()
    raw = cli.canonical(context); held = cli.hold_context(raw, sha256(raw).hexdigest())
    preserved = root.with_name('preserved_output'); root.rename(preserved); root.mkdir()
    with pytest.raises(ValueError, match='root identity'): cli.safety_accounting(held, root)


def test_entry_import_bootstrap_does_not_load_project_or_scientific_modules():
    import subprocess
    code = ("import sys; from experiments import staged_rts24_saved_fresh_adoption_v1; "
        "assert not any(n == 'src' or n.startswith(('src.','pyomo','highspy')) for n in sys.modules)")
    run = subprocess.run([sys.executable, '-B', '-s', '-c', code], cwd=cli.ROOT, capture_output=True, timeout=10)
    assert run.returncode == 0 and run.stdout == run.stderr == b''


@pytest.mark.parametrize('bookend_fails', [False, True])
def test_scientific_failure_always_checks_final_inputs_and_preserves_both_errors(monkeypatch, bookend_fails):
    from types import SimpleNamespace
    held = SimpleNamespace(fixture=None, expectations={}, outer={}, source={name: {} for name in f.prefix.SOURCES})
    calls = []
    def bookend(value, *, inventory=True):
        calls.append(inventory)
        if inventory and bookend_fails: raise OSError('bookend failure')
    def fail(*args, **kwargs): raise ValueError('primary failure')
    monkeypatch.setattr(f, 'bookend', bookend)
    monkeypatch.setattr(f.prefix, 'replay_prefix', fail)
    if bookend_fails:
        with pytest.raises(f.ReplayUnresolved) as found: f.replay(held, 'a'*64)
        assert found.value.primary_error['message'] == 'primary failure'
        assert found.value.bookend_error['message'] == 'bookend failure'
        assert found.value.infeasibility_inferred is False
    else:
        with pytest.raises(ValueError, match='primary failure'): f.replay(held, 'a'*64)
    assert calls == [False, True]


class _StageUnitOwner:
    """Fault-only owner; records must identify it as injected unit evidence."""
    fault = None

    def __init__(self, *args, **kwargs):
        from types import SimpleNamespace
        self.pid, self.creation_filetime = cli._own_process_identity(cli._stage_api())
        self._job = 1; self._released = False; self.calls = []; self.polls = 0
        self.quiescence_witness = None
        self._k = SimpleNamespace(TerminateJobObject=self.kill)
        if self.fault == 'construct': raise ValueError('construct primary')

    def _live_owner(self): pass

    def kill(self, *args):
        self.calls.append('kill')
        if self.fault == 'layers': raise OSError('kill secondary')
        return True

    def release(self):
        self.calls.append('release'); self._released = True
        if self.fault in ('release', 'layers'): raise ValueError('release primary')

    def poll(self):
        self.polls += 1
        return 0 if self.fault == 'fast' or self.polls > 1 else None

    def sample(self):
        self.calls.append('sample')
        if self.fault == 'sample': raise OSError('sample primary')
        return dict(rss_bytes=300*1024**2 if self.fault == 'rss' else 100,
            peak_job_commit_bytes=600*1024**2 if self.fault == 'commit' else 200,
            pids=[], processes=0)

    def quiesce(self, *, max_seconds):
        self.calls.append('quiesce')
        assert 0 < max_seconds <= 1
        if self.fault in ('quiesce', 'layers'): raise OSError('quiesce secondary')
        self.quiescence_witness = dict(observed_unique_member_handles=1, all_handles_signaled=True,
            member_identities=[dict(pid=self.pid, creation_filetime=self.creation_filetime)], total_processes=1,
            final_pids=[], active_processes=0, complete_inventory=True)
        if self.fault == 'inventory': self.quiescence_witness['total_processes'] = 2

    def close(self):
        self.calls.append('close')
        if self.fault in ('close', 'layers'): raise OSError('close secondary')


def _unit_stage(fault=None):
    class Owner(_StageUnitOwner): pass
    Owner.fault = fault
    channel = cli.StageChannel.create('a'*64, cli.ordinary_stage_descriptor())
    held = cli._create_probe_owner('normal', channel, owner_factory=Owner)
    writer = cli.StageChannel.attach(channel.name, channel.nonce, channel.context_sha, channel.descriptor)
    return held, writer


def _write_unit_frames(writer):
    for phase in writer.spec['phases']+['terminal']: writer.enter(phase)


def _real_stage(probe_id, *, role='fresh', preset='steady'):
    channel = cli.StageChannel.create('a'*64, cli.ordinary_stage_descriptor(role, preset))
    try:
        held = cli.create_probe_owner(probe_id, channel)
        result = cli.watch_probe_stage(held)
        print('STAGE_PROBE '+cli.canonical(result).decode('ascii'))
        return result
    finally:
        channel.close()


def _closed_stage_gates(record):
    assert record['F_launch_admitted'] is record['saved_P1_fresh_process_verified'] is record['saved_P1_parent_adoption_verified'] is False
    assert all(record[name] is False for name in cli.GATES)
    assert record['artifact_contents_read'] is False
    assert record['external_constructor_and_monitor_interrupt_bound_proved'] is record['terminal_publication_bound_proved'] is False
    assert len(cli.canonical(record)) <= 131072
    import struct
    def slot(raw, marker):
        assert len(raw) <= 4052
        return struct.pack('<I', len(raw))+raw+b'\0'*(4052-len(raw))+sha256(raw).digest()+marker
    header_slot = slot(cli.canonical(record['stage_header']), b'GRIDHDR1')
    previous = '0'*64; slots = []
    header = record['stage_header']
    for index, frame in enumerate(record['transcript_frames']):
        raw = cli.canonical(frame)
        assert frame['sequence'] == index and frame['previous_sha'] == previous
        assert frame['binding_sha'] == sha256(header_slot).hexdigest()
        assert (frame['producer_pid'], frame['producer_creation_filetime']) == (header['owner_pid'], header['owner_creation_filetime'])
        slots.append(slot(raw, b'GRIDFRM1')); previous = sha256(raw).hexdigest()
    assert sha256(b''.join(slots)).hexdigest() == record['transcript_sha']


@pytest.mark.parametrize('role,total', [('fresh', 50.), ('parent', 125.), ('controller', 180.)])
def test_stage_fixed_descriptors_do_not_authorize_production(role, total):
    raw = cli.stage_descriptor(role); spec = cli.checked_stage_descriptor(raw)
    assert spec['total_seconds'] == total and len(spec['phases'])+2 <= cli.STAGE_SLOTS
    channel = cli.StageChannel.create('a'*64, raw)
    try:
        with pytest.raises(ValueError, match='production stage launch'):
            cli.create_probe_owner('normal', channel)
    finally: channel.close()
    spec['phase_seconds'][0] += 1
    with pytest.raises(ValueError, match='descriptor differs'): cli.checked_stage_descriptor(cli.canonical(spec))


def test_stage_mapping_is_create_only_and_attach_never_recreates():
    held, writer = _unit_stage()
    channel = held.channel
    try:
        before = cli.C.string_at(channel._view, cli.STAGE_MAP_BYTES)
        with pytest.raises(cli.StageChannelError, match='collision'):
            cli.StageChannel.create(channel.context_sha, channel.descriptor, name=channel.name)
        assert cli.C.string_at(channel._view, cli.STAGE_MAP_BYTES) == before
        _write_unit_frames(writer)
        with pytest.raises(ValueError, match='already contains frames'):
            cli.StageChannel.attach(channel.name, channel.nonce, channel.context_sha, channel.descriptor)
    finally: writer.close(); held.close()
    with pytest.raises(OSError): cli.StageChannel.attach(channel.name, channel.nonce, channel.context_sha, channel.descriptor)


def test_stage_mutex_collision_rejects_and_closes_partial_mapping():
    api = cli._stage_api(); name = cli.STAGE_PREFIX+cli.secrets.token_hex(32)
    mutex = cli._native(api.CreateMutexW(None, False, name+'_mutex'))
    descriptor = cli.ordinary_stage_descriptor()
    try:
        with pytest.raises(cli.StageChannelError, match='collision'):
            cli.StageChannel.create('a'*64, descriptor, name=name)
        with pytest.raises(OSError): cli.StageChannel.attach(name, 'b'*64, 'a'*64, descriptor)
    finally: cli._native(api.CloseHandle(mutex))


@pytest.mark.parametrize('path', ['create', 'attach'])
def test_stage_channel_constructor_cleanup_error_retains_actual_partial_handles(monkeypatch, path):
    import pickle
    held = writer = None
    if path == 'attach': held, writer = _unit_stage(); writer.close()
    original = cli._stage_api()
    class Api:
        def __getattr__(self, name): return getattr(original, name)
        def CreateMutexW(self, *args):
            cli.C.set_last_error(5); return 0
        def UnmapViewOfFile(self, view): return False
        def CloseHandle(self, handle): return False
    monkeypatch.setattr(cli, '_stage_api', lambda: Api())
    partial = None
    try:
        with pytest.raises(cli.StageChannelConstructionUnresolved) as found:
            if path == 'create': cli.StageChannel.create('a'*64, cli.ordinary_stage_descriptor())
            else: cli.StageChannel.attach(held.channel.name, 'b'*64, 'a'*64, held.channel.descriptor)
        partial = found.value.channel
        assert partial._map is not None and found.value.cleanup_error['kind'] == 'close'
        assert found.value.primary['type'] == ('PermissionError' if path == 'create' else 'ValueError')
        if path == 'attach': assert partial._mutex is not None and partial._view is not None
        with pytest.raises(TypeError, match='cannot be serialized'): pickle.dumps(found.value)
    finally:
        if partial is not None: partial._api = original; partial.close()
        if held is not None: held.close()


@pytest.mark.parametrize('domain', ['nonce', 'context', 'owner'])
def test_stage_attach_binds_actual_process_and_held_fields(domain):
    held, writer = _unit_stage(); channel = held.channel
    writer.close()
    try:
        if domain == 'owner':
            value = cli.parse(cli._stage_decode(channel._header, cli.STAGE_HEADER_COMMIT))
            value['owner_pid'] += 1
            changed = cli._stage_slot(cli.canonical(value), cli.STAGE_HEADER_COMMIT)
            cli.C.memmove(channel._view, changed, len(changed))
        with pytest.raises(ValueError, match='binding differs|wrong stage writer'):
            cli.StageChannel.attach(channel.name, 'b'*64 if domain == 'nonce' else channel.nonce,
                'b'*64 if domain == 'context' else channel.context_sha, channel.descriptor)
    finally: held.close()


@pytest.mark.parametrize('fault', ['partial', 'sha', 'gap'])
def test_stage_uncommitted_or_incomplete_slot_is_not_progress(fault):
    held, writer = _unit_stage(); channel = held.channel
    try:
        writer.enter('fresh')
        slot = cli.C.string_at(channel._view+cli.STAGE_SLOT_BYTES, cli.STAGE_SLOT_BYTES)
        if fault == 'partial': slot = slot[:-8]+b'\0'*8
        elif fault == 'sha': slot = slot[:-40]+b'x'*32+slot[-8:]
        else:
            cli.C.memmove(channel._view+2*cli.STAGE_SLOT_BYTES, slot, len(slot)); slot = b'\0'*len(slot)
        cli.C.memmove(channel._view+cli.STAGE_SLOT_BYTES, slot, len(slot))
        assert channel.read_available() == [] and channel.pending_data is True and channel._history == []
        assert channel.read_available() == []
    finally: writer.close(); held.close()


@pytest.mark.parametrize('field', ['sequence', 'binding_sha', 'previous_sha', 'producer_pid', 'stamp'])
def test_stage_valid_checksum_does_not_hide_invalid_binding(field):
    held, writer = _unit_stage(); channel = held.channel
    try:
        writer.enter('fresh')
        value = cli.parse(cli._stage_decode(writer._history[0], cli.STAGE_COMMIT))
        value[field] = 'b'*64 if field.endswith('_sha') else (True if field == 'sequence' else 0)
        slot = cli._stage_slot(cli.canonical(value), cli.STAGE_COMMIT)
        cli.C.memmove(channel._view+cli.STAGE_SLOT_BYTES, slot, len(slot))
        with pytest.raises(ValueError, match='binding differs'): channel.read_available()
        with pytest.raises(cli.StageChannelError, match='unresolved'): channel.read_available()
    finally: writer.close(); held.close()


@pytest.mark.parametrize('domain', ['header', 'history'])
def test_stage_accepted_bytes_are_rechecked_and_failure_is_sticky(domain):
    held, writer = _unit_stage(); channel = held.channel
    try:
        writer.enter('fresh'); assert len(channel.read_available()) == 1
        offset = 0 if domain == 'header' else cli.STAGE_SLOT_BYTES
        cli.C.memmove(channel._view+offset, b'x', 1)
        with pytest.raises(cli.StageChannelError, match=domain): channel.read_available()
        with pytest.raises(cli.StageChannelError, match='unresolved'): channel.read_available()
    finally: writer.close(); held.close()


@pytest.mark.parametrize('phase', ['terminal', 'parent', 'fresh'])
def test_stage_writer_forbids_skip_repeat_and_post_terminal(phase):
    held, writer = _unit_stage()
    try:
        if phase == 'fresh': _write_unit_frames(writer)
        with pytest.raises(ValueError, match='strict next phase|single live stage writer'): writer.enter(phase)
        with pytest.raises(cli.StageChannelError, match='unresolved'): writer.enter('fresh')
    finally: writer.close(); held.close()


def test_stage_busy_mutex_is_no_progress_and_abandonment_is_sticky():
    import threading
    held, writer = _unit_stage(); channel = held.channel
    writer.close()
    ready, release = threading.Event(), threading.Event()
    def own_then_abandon():
        api = cli._stage_api()
        assert api.WaitForSingleObject(channel._mutex, 0) == 0
        ready.set(); assert release.wait(2)
        # Thread exit abandons ownership; the creating observer retains the HANDLE.
    thread = threading.Thread(target=own_then_abandon)
    thread.start()
    native_thread = None
    try:
        assert ready.wait(2)
        api = cli._stage_api()
        api.OpenThread.argtypes = [cli.W.DWORD, cli.W.BOOL, cli.W.DWORD]
        api.OpenThread.restype = cli.W.HANDLE
        native_thread = cli._native(api.OpenThread(0x100000, False, thread.native_id))
        assert channel.read_available() is None and channel._history == []
        release.set(); thread.join(2); assert not thread.is_alive()
        assert api.WaitForSingleObject(native_thread, 1000) == 0
        with pytest.raises(cli.StageChannelError, match='abandoned'): channel.read_available()
        with pytest.raises(cli.StageChannelError, match='unresolved'): channel.read_available()
    finally:
        release.set(); thread.join(2)
        if native_thread is not None: cli._native(api.CloseHandle(native_thread))
        held.close()


def test_stage_handle_failures_preserve_partial_capability_and_primary(monkeypatch):
    held, writer = _unit_stage(); channel = held.channel
    writer.close(); original = channel._api
    class Api:
        def __getattr__(self, name): return getattr(original, name)
        def ReleaseMutex(self, handle): return False
        def UnmapViewOfFile(self, view): return False
        def CloseHandle(self, handle): return False
    channel._api = Api()
    try:
        with pytest.raises(cli.StageChannelError, match='mutex_release') as found:
            with channel._locked(0): raise ValueError('body primary')
        assert found.value.primary['message'] == 'body primary'
        assert cli._stage_error(found.value)['primary']['message'] == 'body primary'
        # Fault injection left the real lock held; release with the original API.
        cli._native(original.ReleaseMutex(channel._mutex))
        with pytest.raises(cli.StageChannelError, match='close'): channel.close()
        assert channel._view is not None and channel._map is not None and channel._mutex is not None
    finally: channel._api = original; held.close()


@pytest.mark.parametrize('fault', [None, 'fast', 'release', 'sample', 'rss', 'commit', 'quiesce', 'inventory', 'close', 'layers'])
def test_stage_fault_layers_do_not_adopt_or_infer_quiet(fault):
    held, writer = _unit_stage(fault)
    _write_unit_frames(writer); writer.close()
    result = cli.watch_probe_stage(held)
    _closed_stage_gates(result)
    assert result['owner_evidence'] == 'injected_unit_owner'
    assert result['stage_process_observed_successfully'] is result['job_quiet_confirmed'] is False
    assert result['logic_path_completed'] is (fault is None)
    assert result['quiet_witness_consistent'] is (fault not in ('sample', 'quiesce', 'inventory', 'close', 'layers'))
    if fault == 'fast':
        assert result['samples'] == 0 and result['sampled_tree_peak_rss_bytes'] is None
        assert result['primary_stop_reason'] == 'rss_observation_unavailable'
    if fault in ('release', 'sample', 'rss', 'commit', 'layers'):
        assert held.owner.calls.index('kill') < held.owner.calls.index('quiesce')
    if fault == 'layers':
        assert result['monitor_error']['message'] == 'release primary'
        assert result['termination_error']['message'] == 'kill secondary'
        assert result['quiesce_error']['message'] == 'quiesce secondary'
        assert result['close_error']['message'] == 'close secondary'


def test_stage_constructor_error_retains_owner_and_cleanup():
    class Owner(_StageUnitOwner): fault = 'construct'
    channel = cli.StageChannel.create('a'*64, cli.ordinary_stage_descriptor())
    try:
        with pytest.raises(cli.StageConstructionUnresolved) as found:
            cli._create_probe_owner('normal', channel, owner_factory=Owner)
        assert found.value.primary_error['message'] == 'construct primary'
        assert found.value.owner.calls == ['kill', 'quiesce', 'close'] and found.value.cleanup_errors == []
    finally: channel.close()


def test_stage_constructor_internal_cleanup_keeps_original_exception_context():
    class Owner(_StageUnitOwner):
        fault = 'layers'
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            try: raise ValueError('constructor original')
            except ValueError: raise OSError('constructor internal close')
    channel = cli.StageChannel.create('a'*64, cli.ordinary_stage_descriptor())
    try:
        with pytest.raises(cli.StageConstructionUnresolved) as found:
            cli._create_probe_owner('normal', channel, owner_factory=Owner)
        assert found.value.primary_error['message'] == 'constructor internal close'
        assert found.value.primary_error['context']['message'] == 'constructor original'
        assert [error['layer'] for error in found.value.cleanup_errors] == ['termination', 'quiesce', 'close']
    finally: channel.close()


@pytest.mark.parametrize('fault', ['argv', 'unknown', 'descriptor', 'bound', 'writer'])
def test_stage_closed_probe_rejects_scope_expansion_before_construct(monkeypatch, fault):
    from src.staged_rts24_process_guard_v1 import OwnedChild
    held = writer = None
    if fault in ('bound', 'writer'):
        held, writer = _unit_stage(); channel = writer if fault == 'writer' else held.channel
    else:
        channel = cli.StageChannel.create('a'*64, cli.ordinary_stage_descriptor(preset='deadline' if fault == 'descriptor' else 'steady'))
    def denied(*args, **kwargs): pytest.fail('invalid scope reached actual process constructor')
    monkeypatch.setattr(OwnedChild, '__init__', denied)
    try:
        argument = [str(cli.EXE), '-B', '-s', '-c', 'pass'] if fault == 'argv' else ('arbitrary' if fault == 'unknown' else 'normal')
        with pytest.raises(ValueError, match='closed ordinary|fixed descriptor|unbound observer'): cli.create_probe_owner(argument, channel)
    finally:
        if writer is not None: writer.close(); held.close()
        else: channel.close()


def test_stage_startup_records_the_same_frozen_environment_passed_to_constructor(monkeypatch):
    calls = []
    def environment():
        calls.append(1); return {'STAGE_UNIT_ENV': str(len(calls))}
    class Owner(_StageUnitOwner):
        def __init__(self, *args, **kwargs):
            self.actual_environment = kwargs['environment']; super().__init__(*args, **kwargs)
    channel = cli.StageChannel.create('a'*64, cli.ordinary_stage_descriptor())
    monkeypatch.setattr(cli, 'environment', environment)
    held = cli._create_probe_owner('normal', channel, owner_factory=Owner)
    try:
        assert calls == [1]
        assert cli.parse(held.startup)['environment_sha'] == cli.digest(held.owner.actual_environment)
    finally: held.close()


def test_stage_root_exit_uses_both_final_samples_for_descendant_detection():
    held, writer = _unit_stage('fast'); _write_unit_frames(writer); writer.close()
    calls = []
    def sample():
        calls.append(1)
        return dict(rss_bytes=0, peak_job_commit_bytes=200, pids=[99] if len(calls) == 1 else [], processes=1 if len(calls) == 1 else 0)
    held.owner.sample = sample
    result = cli.watch_probe_stage(held)
    assert result['primary_stop_reason'] == 'root_exited_with_descendants' and result['termination_requested'] is True
    assert result['job_quiet_confirmed'] is result['stage_process_observed_successfully'] is False


def test_stage_monitor_and_final_bookend_errors_keep_both_layers():
    held, writer = _unit_stage(); _write_unit_frames(writer); writer.close()
    cli.C.memmove(held.channel._view, b'x', 1)
    result = cli.watch_probe_stage(held)
    assert result['channel_error']['kind'] == result['monitor_error']['kind'] == 'header'
    assert result['final_bookend_error']['kind'] == 'header'
    assert result['primary_stop_reason'] == 'monitor_or_channel_error'


def test_stage_invalid_observation_argument_does_not_consume_suspended_owner():
    held, writer = _unit_stage()
    try:
        with pytest.raises(ValueError, match='earlier stage deadline'): cli.watch_probe_stage(held, absolute_deadline=float('nan'))
        assert held._attempted is held.owner._released is False
    finally: writer.close(); held.close()


@pytest.mark.parametrize('field', ['real_owner', 'owner', 'channel', 'startup', 'created_at'])
def test_stage_retained_binding_rejects_one_sided_mutation_before_release(field):
    from dataclasses import FrozenInstanceError
    held, writer = _unit_stage()
    original = getattr(held, field)
    changed = dict(real_owner=True, owner=object(), channel=object(), startup=b'{}', created_at=held.created_at+100)[field]
    try:
        with pytest.raises(FrozenInstanceError): setattr(held, field, changed)
        object.__setattr__(held, field, changed)
        with pytest.raises(ValueError, match='binding changed'): cli.watch_probe_stage(held)
        assert held._attempted is False and (held.owner if field != 'owner' else original)._released is False
    finally:
        object.__setattr__(held, field, original)
        writer.close(); held.close()


def test_stage_live_capabilities_are_not_serializable():
    import pickle
    held, writer = _unit_stage()
    try:
        for value in (held, held.channel, writer):
            with pytest.raises(TypeError, match='cannot be serialized'): pickle.dumps(value)
    finally: writer.close(); held.close()


def test_stage_saved_record_reconstructs_transcript_after_mapping_close():
    held, writer = _unit_stage(); _write_unit_frames(writer); writer.close()
    result = cli.watch_probe_stage(held)
    assert held.channel._view is held.channel._map is held.channel._mutex is None
    _closed_stage_gates(result)
    assert [frame['phase'] for frame in result['transcript_frames']] == ['fresh', 'terminal']


def test_stage_committed_wrong_phase_triggers_kill_without_clock_extension():
    held, writer = _unit_stage()
    writer.enter('fresh'); writer.close()
    value = cli.parse(cli._stage_decode(
        cli.C.string_at(held.channel._view+cli.STAGE_SLOT_BYTES, cli.STAGE_SLOT_BYTES), cli.STAGE_COMMIT))
    value['phase'] = 'parent'
    slot = cli._stage_slot(cli.canonical(value), cli.STAGE_COMMIT)
    cli.C.memmove(held.channel._view+cli.STAGE_SLOT_BYTES, slot, len(slot))
    result = cli.watch_probe_stage(held)
    print('STAGE_UNIT '+cli.canonical(result).decode('ascii'))
    assert result['primary_stop_reason'] == 'phase_protocol' and result['frames_observed'] == 0
    assert len(result['phases_observed']) == 1
    assert held.owner.calls.index('kill') < held.owner.calls.index('quiesce')


def test_stage_channel_close_failure_is_distinct_and_retains_handles():
    held, writer = _unit_stage(); _write_unit_frames(writer); writer.close()
    channel = held.channel; original = channel._api
    class Api:
        def __getattr__(self, name): return getattr(original, name)
        def UnmapViewOfFile(self, view): return False
        def CloseHandle(self, handle): return False
    channel._api = Api()
    try:
        result = cli.watch_probe_stage(held)
        assert result['primary_stop_reason'] == 'channel_close_unknown'
        assert result['channel_close_error'] is not None and result['close_error'] is None
        assert result['quiet_witness_consistent'] is True and result['job_quiet_confirmed'] is result['stage_process_observed_successfully'] is False
        assert channel._map is not None and channel._mutex is not None and channel._view is not None
    finally: channel._api = original; held.close()


def test_stage_maximum_complete_witness_fits_without_dropping_members():
    held, writer = _unit_stage(); _write_unit_frames(writer); writer.close()
    original = held.owner.quiesce
    def quiesce(*, max_seconds):
        original(max_seconds=max_seconds)
        witness = held.owner.quiescence_witness
        witness['member_identities'] += [dict(pid=2**32-1-index, creation_filetime=2**64-1-index) for index in range(1023)]
        witness['observed_unique_member_handles'] = witness['total_processes'] = 1024
    held.owner.quiesce = quiesce
    result = cli.watch_probe_stage(held)
    assert result['logic_path_completed'] is True and result['stage_process_observed_successfully'] is False
    assert len(result['quiescence_witness']['member_identities']) == 1024
    assert len(cli.canonical(result)) <= 131072
    _closed_stage_gates(result)


def test_stage_oversized_original_observation_is_retained_instead_of_truncated():
    held, writer = _unit_stage(); _write_unit_frames(writer); writer.close()
    def quiesce(*, max_seconds): held.owner.quiescence_witness = {'unresolved': 'x'*131073}
    held.owner.quiesce = quiesce
    with pytest.raises(cli.StageChannelError, match='record_byte_cap'): cli.watch_probe_stage(held)
    assert held.last_observation['stage_process_observed_successfully'] is False
    assert len(held.last_observation['quiescence_witness']['unresolved']) == 131073
    assert held.channel._map is held.channel._mutex is held.channel._view is None


def test_stage_real_exit_uses_observer_clock_without_artifact_reads(monkeypatch):
    channel = cli.StageChannel.create('a'*64, cli.ordinary_stage_descriptor())
    held = cli.create_probe_owner('normal', channel)
    def denied(*args, **kwargs): pytest.fail('active stage observer requested filesystem contents')
    monkeypatch.setattr(cli, 'read', denied); monkeypatch.setattr(cli.os, 'scandir', denied)
    result = cli.watch_probe_stage(held)
    print('STAGE_PROBE '+cli.canonical(result).decode('ascii'))
    _closed_stage_gates(result)
    assert result['stage_process_observed_successfully'] is True and result['owner_evidence'] == 'direct_owned_child'
    assert result['quiescence_witness']['total_processes'] == result['quiescence_witness']['observed_unique_member_handles'] >= 1
    assert result['samples'] > 0 and result['frames_observed'] == 2
    assert result['startup']['actual_os_commandline_independently_verified'] is False
    assert result['startup']['owner_pid'] == held.owner.pid
    assert result['root_exit_observed_at'] <= result['quiesce_started_at'] <= result['quiesce_completed_at'] <= result['close_attempts_finished_at']
    with pytest.raises(ValueError, match='already attempted'): cli.watch_probe_stage(held)


@pytest.mark.parametrize('probe_id', ['no_first_frame', 'hang', 'terminal_hang', 'terminal_exit_hang', 'late_terminal_hang'])
def test_stage_real_deadline_requests_kill_before_quiesce(probe_id):
    result = _real_stage(probe_id, preset='steady' if probe_id in ('terminal_exit_hang', 'late_terminal_hang') else 'deadline')
    _closed_stage_gates(result)
    assert result['primary_stop_reason'] in ('phase_limit', 'total_active_limit', 'terminal_exit_limit')
    if probe_id in ('terminal_exit_hang', 'late_terminal_hang'): assert result['primary_stop_reason'] == 'terminal_exit_limit'
    if probe_id == 'late_terminal_hang': assert result['terminal_exit_limiting_deadline'] == 'active'
    assert result['termination_requested'] is result['termination_call_succeeded'] is result['job_quiet_confirmed'] is True
    assert result['stage_process_observed_successfully'] is False
    assert result['termination_requested_at'] <= result['quiesce_started_at'] <= result['quiesce_completed_at'] <= result['close_attempts_finished_at']
    assert result['observation_seconds'] < result['descriptor']['total_seconds']


@pytest.mark.parametrize('probe_id,reason', [('missing_terminal', 'incomplete_terminal'),
    ('exit_nonzero', 'child_exit_nonzero'), ('reported_error', 'child_reported_error')])
def test_stage_real_terminal_is_independent_of_exit_and_quiet(probe_id, reason):
    result = _real_stage(probe_id)
    _closed_stage_gates(result)
    assert result['primary_stop_reason'] == reason and result['job_quiet_confirmed'] is True
    assert result['stage_process_observed_successfully'] is False


@pytest.mark.parametrize('leave_alive', [False, True])
def test_stage_real_nested_jobs_require_complete_retained_member_inventory(leave_alive):
    result = _real_stage('root_exited_with_descendants' if leave_alive else 'nested_quiet', role='parent', preset='nested')
    _closed_stage_gates(result)
    assert result['quiescence_witness']['total_processes'] == result['quiescence_witness']['observed_unique_member_handles'] >= 2
    assert result['job_quiet_confirmed'] is True
    assert result['stage_process_observed_successfully'] is (not leave_alive)
    assert result['primary_stop_reason'] == ('root_exited_with_descendants' if leave_alive else None)
