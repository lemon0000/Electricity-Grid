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
    for role in ('parent', 'fresh'):
        argv = _saved_argv(role, raw, sha256(raw).hexdigest())
        assert argv[:4] == [str(cli.EXE), '-B', '-s', str(cli.ROOT/cli.NEW_SOURCES[1])]
        assert '--'+role in argv
        assert '--input-root' not in argv and '--output-root' not in argv
    with pytest.raises(ValueError, match='separate trusted invocation'):
        _saved_argv('supervise', raw, sha256(raw).hexdigest())


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
        _saved_argv('fresh', raw, sha256(cli.canonical(other)).hexdigest())


def test_bootstrap_environment_matches_the_bound_original_without_importing_it():
    from src.staged_rts24_process_guard_v1 import controlled_environment
    assert cli.environment() == controlled_environment()


def test_actual_entry_and_expanded_arguments_are_bound(context, monkeypatch):
    raw = cli.canonical(context); digest = sha256(raw).hexdigest()
    entry = str(cli.ROOT/cli.NEW_SOURCES[1])
    monkeypatch.setattr(sys.modules['__main__'], '__file__', entry)
    monkeypatch.setattr(sys, 'argv', _saved_argv('fresh', raw, digest)[3:])
    with pytest.raises(ValueError, match='creating saved file bootstrap'):
        cli.validate_actual_entry('fresh', raw, digest)
    monkeypatch.setattr(sys, 'argv', [entry, '--fresh'])
    with pytest.raises(ValueError, match='creating saved file bootstrap'): cli.validate_actual_entry('fresh', raw, digest)


def test_safety_accounting_rejects_layer_roots_even_when_they_exist(context):
    root = Path(context['output_root']); (root/'worker/fresh').mkdir(parents=True)
    for wrong in (root/'worker', root/'worker/fresh'):
        with pytest.raises(ValueError, match='global F output root'): safety(context, wrong)


def test_actual_test_argv_cannot_enter_F_execution_or_adoption(context, monkeypatch):
    raw = cli.canonical(context); digest = sha256(raw).hexdigest(); entry = str(cli.ROOT/cli.NEW_SOURCES[1])
    monkeypatch.setattr(sys.modules['__main__'], '__file__', entry)
    monkeypatch.setattr(sys, 'argv', _saved_argv('parent', raw, digest)[3:])
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


@pytest.fixture
def role_store(tmp_path):
    raw = cli.make_role_probe_context(tmp_path/'output')
    return cli.prepare_role_probe_output(raw, sha256(raw).hexdigest())


def _role_store_as(store, role):
    return cli.RoleStore(store.raw, store.sha, cli.digest(store.tree), role)


def _capture_role_graph(scenario, result):
    root = Path(result['output_root']); files = {}
    for name in cli.TARGETS:
        path = root/name
        if path.exists():
            raw = path.read_bytes()
            files[name] = dict(pin=cli.pin(raw), hex=raw.hex()) if name != 'context.json' else dict(pin=cli.pin(raw))
    context = json.loads((root/'context.json').read_bytes())
    environment = context.pop('environment')
    context['environment_sha'] = cli.digest(environment)
    print('ROLE_GRAPH '+cli.canonical(dict(scenario=scenario, result=result, files=files,
        context_projection=context, context_projection_omits=['environment'],
        projection_scope='ordinary fixture and hashes; original context remains in pytest output')).decode('ascii'))


def test_role_target_reservations_cover_all_writers_and_failure(role_store):
    caps = cli.role_target_caps(); owners = [name for role in ('external', 'controller', 'parent', 'fresh') for name in cli.role_targets(role)]
    assert len(owners) == len(set(owners)) == 17 and set(owners) == set(cli.TARGETS)
    assert sum(caps.values()) == 5537792 < cli.CAPS['output_bytes']
    assert sum(caps[name] for name in cli.RECORDS) == 524288
    result = role_store.accounting()
    assert result['bytes']+result['all_targets_reserved_bytes'] == 5537792
    assert result['files']+result['all_targets_reserved_files'] == 17
    assert caps['diagnostics/failure.json'] == 131072


@pytest.mark.parametrize('fault', ['target', 'pending', 'wrong_writer', 'extra', 'oversized', 'hardlink'])
def test_role_publication_rejects_conflict_scope_and_alias(role_store, fault):
    import os
    target = role_store.root/'worker/parent_startup.json'
    if fault == 'target': target.write_bytes(b'{}')
    elif fault == 'pending': target.with_name(target.name+'.pending').write_bytes(b'{}')
    elif fault == 'extra': (role_store.root/'unexpected').write_bytes(b'')
    elif fault == 'hardlink':
        target.write_bytes(b'{}'); os.link(target, role_store.root/'worker/launcher.json')
    data = {'padding': 'x'*16384} if fault == 'oversized' else {}
    with pytest.raises((ValueError, cli.RolePublicationUnresolved)):
        role_store.publish('fresh' if fault == 'wrong_writer' else 'controller', 'worker/parent_startup.json', data)


@pytest.mark.parametrize('phase', ['before_open', 'after_write', 'after_fsync', 'after_pending_readback',
    'before_rename', 'after_rename', 'after_final_readback'])
def test_role_publication_window_retains_expected_bytes_and_disallows_retry(role_store, phase):
    raw = cli.canonical({'value': 7})
    def fault(stage, target):
        if stage == phase: raise OSError('fixed publication window')
    with pytest.raises(cli.RolePublicationUnresolved) as found:
        cli._publish_role_target(role_store, 'controller', 'worker/parent_startup.json', raw, hook=fault)
    error = found.value
    assert error.expected_sha == sha256(raw).hexdigest() and error.phase == phase
    assert error.may_have_published is (phase in ('after_rename', 'after_final_readback'))
    image = cli._stage_error(error)
    assert image['phase'] == phase and image['expected_sha'] == error.expected_sha and image['primary']['message'] == 'fixed publication window'
    if phase != 'before_open':
        target = role_store.root/'worker/parent_startup.json'
        existing = target if error.may_have_published else target.with_name(target.name+'.pending')
        assert existing.read_bytes() == raw
    with pytest.raises(ValueError, match='single role target attempt'):
        role_store.publish('controller', 'worker/parent_startup.json', {'value': 7})


def test_role_store_rejects_context_same_bytes_replacement_and_frozen_state(role_store):
    from dataclasses import FrozenInstanceError
    target = role_store.root/'context.json'; saved = target.with_name('original_context')
    target.rename(saved); target.write_bytes(role_store.raw)
    with pytest.raises(ValueError, match='bookend differs'): role_store.check()
    with pytest.raises(FrozenInstanceError): role_store.writer = 'fresh'


def test_role_source_context_cannot_adopt_F_or_expand_fixture(role_store):
    value = cli.parse(role_store.raw)
    for key, changed in (('F_launch_admitted', True), ('fixture', {'left': 2, 'right': 3, 'expected': 6}), ('case', 'arbitrary')):
        current = dict(value); current[key] = changed; raw = cli.canonical(current)
        with pytest.raises(ValueError): cli.check_role_probe_context(raw, sha256(raw).hexdigest())
    with pytest.raises(ValueError): cli.check_context(role_store.raw, role_store.sha)


def test_role_child_reservation_is_consumed_once_including_constructor_failure(role_store, monkeypatch):
    calls = []
    def fail(*args, **kwargs): calls.append(kwargs.get('started')); raise ValueError('fixed pre-constructor failure')
    monkeypatch.setattr(cli, '_construct_stage_owner', fail)
    with pytest.raises(ValueError, match='pre-constructor'): cli._create_role_owner('parent', role_store)
    assert role_store.child_consumed is True and calls == [role_store.child_reservation[1]]
    with pytest.raises(ValueError, match='single nested role reservation'): cli._create_role_owner('parent', role_store)
    assert len(calls) == 1


def _role_relay_endpoints():
    channel = cli.StageChannel.create('a'*64, cli.ordinary_stage_descriptor('parent', 'nested'))
    owner = _StageUnitOwner(); channel.bind_owner(owner)
    writer = cli.StageChannel.attach(channel.name, channel.nonce, channel.context_sha, channel.descriptor)
    writer.enter('parent'); writer.enter('fresh')
    return channel, writer


@pytest.mark.parametrize('fault', [None, 'quiesce', 'close', 'relay'])
def test_role_relay_tracks_actual_cleanup_and_preserves_failure_layers(fault, monkeypatch):
    held, child_writer = _unit_stage(None if fault == 'relay' else fault)
    _write_unit_frames(child_writer); child_writer.close()
    channel, relay = _role_relay_endpoints()
    if fault == 'relay':
        original = relay.enter
        def fail(phase):
            if phase == 'inner_quiesce': raise OSError('fixed relay failure')
            return original(phase)
        monkeypatch.setattr(relay, 'enter', fail)
    try:
        result = cli._watch_stage(held, relay=relay)
        phases = [frame['phase'] for frame in channel.read_available()]
        assert phases == (['parent', 'fresh', 'inner_quiesce', 'inner_terminal'] if fault is None else
            ['parent', 'fresh'] if fault == 'relay' else ['parent', 'fresh', 'inner_quiesce'])
        assert result['stage_process_observed_successfully'] is result['job_quiet_confirmed'] is False
        if fault == 'relay':
            assert result['relay_error']['message'] == 'fixed relay failure'
            assert held.owner.calls.index('kill') < held.owner.calls.index('quiesce')
    finally: relay.close(); channel.close()


def test_role_json_or_fake_owner_cannot_grant_worker_read(role_store, monkeypatch):
    parent = _role_store_as(role_store, 'parent')
    target = role_store.root/'worker/fresh/metrics.json'; target.write_bytes(b'{}')
    original = cli.read
    def guard(path, **kwargs):
        if Path(path) == target: pytest.fail('forbidden worker content read')
        return original(path, **kwargs)
    monkeypatch.setattr(cli, 'read', guard)
    with pytest.raises(ValueError, match='direct retained owner'): parent.read_after_quiet('worker/fresh/metrics.json', {'job_quiet_confirmed': True})
    held, writer = _unit_stage(); _write_unit_frames(writer); writer.close(); cli.watch_probe_stage(held)
    with pytest.raises(ValueError): parent.read_after_quiet('worker/fresh/metrics.json', held)


def test_role_actual_witness_and_full_record_are_checked_before_content(role_store, monkeypatch):
    parent = _role_store_as(role_store, 'parent'); held = cli._create_role_owner('fresh', parent)
    parent.publish('parent', 'worker/fresh/startup.json', cli.parse(held.startup))
    result = cli.watch_probe_stage(held); assert result['stage_process_observed_successfully'] is True
    target = parent.root/'worker/fresh/metrics.json'; original_read = cli.read
    def guard(path, **kwargs):
        if Path(path) == target: pytest.fail('worker content read before complete permission')
        return original_read(path, **kwargs)
    monkeypatch.setattr(cli, 'read', guard)
    witness = held.owner.quiescence_witness
    try:
        held.owner.quiescence_witness = deepcopy(witness); held.owner.quiescence_witness['complete_inventory'] = False
        with pytest.raises(ValueError, match='closed retained owner quiet'): parent.read_after_quiet('worker/fresh/metrics.json', held)
        held.owner.quiescence_witness = witness
        current, raw = held.last_observation, held.last_image
        changed = deepcopy(current); changed['clock']['resolution'] = 1.
        object.__setattr__(held, 'last_observation', changed); object.__setattr__(held, 'last_image', cli.canonical(changed))
        with pytest.raises(ValueError, match='terminal observation changed'): parent.read_after_quiet('worker/fresh/metrics.json', held)
        object.__setattr__(held, 'observation_commit', (len(held.last_image), sha256(held.last_image).hexdigest()))
        with pytest.raises(ValueError, match='monitor contract differs'): parent.read_after_quiet('worker/fresh/metrics.json', held)
    finally:
        held.owner.quiescence_witness = witness
        object.__setattr__(held, 'last_observation', current); object.__setattr__(held, 'last_image', raw)
        object.__setattr__(held, 'observation_commit', (len(raw), sha256(raw).hexdigest()))
        held.close()


@pytest.mark.parametrize('case', cli.ROLE_PROBE_CASES)
def test_role_real_parent_fresh_graph_and_all_bookend_failures(tmp_path, case):
    result = cli.run_ordinary_role_graph(tmp_path/'output', case)
    _capture_role_graph(case, result)
    assert result['ordinary_graph_completed'] is (case == 'normal')
    assert result['saved_P1_fresh_process_verified'] is result['saved_P1_parent_adoption_verified'] is result['F_launch_admitted'] is False
    assert all(result[name] is False for name in cli.GATES)
    root = Path(result['output_root'])
    if case == 'normal':
        assert set(result['output_inventory']) == set(cli.TARGETS)-{'diagnostics/failure.json'}
        assert [item['stage'] for item in result['input_bookends']] == ['G0', 'G2', 'G3']
        candidate = json.loads((root/'worker/comparison_candidate.json').read_bytes())
        assert candidate['G1']['stage'] == 'G1'
        outer = json.loads((root/'worker/launcher.json').read_bytes()); inner = json.loads((root/'worker/fresh/launcher.json').read_bytes())
        assert outer['quiescence_witness']['total_processes'] >= 4 and inner['quiescence_witness']['total_processes'] >= 2
        phases = outer['transcript_frames']
        assert [f['phase'] for f in phases] == ['parent', 'fresh', 'inner_quiesce', 'inner_terminal', 'parent_compare', 'terminal']
        assert phases[2]['stamp'] <= inner['quiesce_started_at'] and inner['close_attempts_finished_at'] <= phases[3]['stamp']
        observation = json.loads((root/'parent/parent_observation.json').read_bytes())
        assert [m['stage'] for m in observation['input_bookends_before_publication']] == ['G0', 'G2']
        assert 'G3' not in observation and observation['saved_P1_parent_adoption_verified'] is False
    else:
        assert (root/'diagnostics/failure.json').exists()
        assert (root/'parent/parent_observation.json').exists() is (case == 'g3_error')
        if case.startswith('entry_'):
            inner = json.loads((root/'worker/fresh/launcher.json').read_bytes())
            assert inner['frames_observed'] == 0 and inner['exit_code'] != 0
            assert inner['job_quiet_confirmed'] is True and inner['stage_process_observed_successfully'] is False
            assert inner['startup']['argv'][:4] == [str(cli.EXE), '-B', '-s', str(cli.ROOT/cli.NEW_SOURCES[1])]
            assert not (root/'worker/fresh/events.jsonl').exists() and not (root/'worker/fresh/metrics.json').exists()


def test_role_outer_launcher_corruption_is_rejected_against_live_image(tmp_path, monkeypatch):
    import os
    original = cli._publish_role_target
    def corrupt(store, role, name, raw, **kwargs):
        result = original(store, role, name, raw, **kwargs)
        if name == 'worker/launcher.json':
            path = store.root/name; before = path.stat(); value = cli.parse(raw); value['exit_code'] = 9
            changed = cli.canonical(value); assert len(changed) == len(raw)
            path.write_bytes(changed); os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
        return result
    monkeypatch.setattr(cli, '_publish_role_target', corrupt)
    result = cli.run_ordinary_role_graph(tmp_path/'output')
    assert result['ordinary_graph_completed'] is False and result['error']['message'] == 'saved outer process differs from live owner'
    _capture_role_graph('outer_launcher_corruption', result)


def test_role_late_payload_drift_preserves_published_observation_but_refuses_return(tmp_path, monkeypatch):
    original = cli._role_input_bookend
    def drift(store, stage, held=None):
        result = original(store, stage, held)
        if stage == 'G3':
            target = store.root/'worker/fresh/metrics.json'; value = cli.parse(target.read_bytes()); value['result'] = 999
            target.write_bytes(cli.canonical(value))
        return result
    monkeypatch.setattr(cli, '_role_input_bookend', drift)
    result = cli.run_ordinary_role_graph(tmp_path/'output')
    assert result['ordinary_graph_completed'] is False and result['observation_pin'] is not None
    assert result['error']['message'] == 'validated role core changed after final publication'
    _capture_role_graph('late_payload_drift', result)


def test_role_constructor_and_publication_cleanup_layers_remain_available(role_store, monkeypatch):
    import pickle
    owner = _StageUnitOwner()
    primary = cli.StageConstructionUnresolved(owner, ValueError('constructor original'),
        [dict(layer='quiesce', type='OSError', message='quiesce secondary')])
    def fail(*args, **kwargs): raise primary
    monkeypatch.setattr(cli, '_construct_stage_owner', fail)
    with pytest.raises(cli.RoleExecutionUnresolved) as found: cli._run_role_controller(role_store)
    assert found.value.primary is primary and found.value.primary.owner is owner
    image = json.loads((role_store.root/'diagnostics/failure.json').read_bytes())['error']
    assert image['construction_primary']['message'] == 'constructor original'
    assert image['cleanup_errors'][0]['message'] == 'quiesce secondary'
    assert role_store.child_consumed is True
    with pytest.raises(TypeError, match='cannot be serialized'): pickle.dumps(found.value)


def _role_fake_open_stage():
    from types import SimpleNamespace
    value = dict(stage_process_observed_successfully=False, job_quiet_confirmed=False)
    stage = SimpleNamespace(owner=SimpleNamespace(_job=None, _process=None, _thread=None,
        _members={(7, 9): 123}, _info=SimpleNamespace(process=None, thread=None)),
        channel=SimpleNamespace(_map=None, _mutex=None, _view=None), startup=b'{"unit":true}',
        last_observation=value, last_image=cli.canonical(value))
    return stage


def test_role_controller_retains_descendant_only_handle_capability(role_store, monkeypatch):
    stage = _role_fake_open_stage()
    monkeypatch.setattr(cli, '_create_role_owner', lambda *args, **kwargs: stage)
    monkeypatch.setattr(cli, '_watch_stage', lambda *args, **kwargs: stage.last_observation)
    with pytest.raises(cli.RoleExecutionUnresolved) as found: cli._run_role_controller(role_store)
    assert found.value.stage is stage and found.value.stage.owner._members == {(7, 9): 123}
    assert found.value.primary.args == ('parent role unsuccessful or unknown',)
    stage.owner._members.clear(); assert cli._role_stage_still_open(stage) is False
    stage.owner._info.thread = 345; assert cli._role_stage_still_open(stage) is True
    stage.owner._info.thread = None


@pytest.mark.parametrize('role', ['controller', 'parent'])
def test_role_wrapper_keeps_watch_primary_and_stage_close_secondary(role_store, monkeypatch, role):
    stage = _role_fake_open_stage()
    def close(): raise OSError('stage close secondary')
    stage.close = close
    def watch(*args, **kwargs): raise ValueError('watch primary')
    monkeypatch.setattr(cli, '_create_role_owner', lambda *args, **kwargs: stage)
    monkeypatch.setattr(cli, '_watch_stage', watch)
    if role == 'parent':
        from types import SimpleNamespace
        parent = _role_store_as(role_store, 'parent')
        monkeypatch.setattr(cli, '_role_reconstruct', lambda *args: (b'{"unit":true}', None))
        run = lambda: cli._run_parent_role(parent, SimpleNamespace(enter=lambda phase: None))
    else: run = lambda: cli._run_role_controller(role_store)
    with pytest.raises(cli.RoleExecutionUnresolved) as found: run()
    current = found.value.primary if isinstance(found.value.primary, cli.RoleExecutionUnresolved) else found.value
    assert current.primary.args == ('watch primary',) and current.stage is stage
    assert current.cleanup_errors[0][1].args == ('stage close secondary',)
    normalized = cli._stage_error(current)
    assert normalized['role_primary']['message'] == 'watch primary'
    assert normalized['cleanup_errors'][0]['message'] == 'stage close secondary'
    stage.owner._members.clear()


@pytest.fixture
def invocation_mailbox():
    import time
    request = cli.canonical({'unit_protocol_only': True})
    mailbox = cli.InvocationMailbox.create(sha256(request).hexdigest())
    channel = cli.StageChannel.create(mailbox.request_sha, cli.ordinary_stage_descriptor('controller', 'invocation'))
    owner = _StageUnitOwner(); channel.bind_owner(owner)
    # Same-process endpoints exercise only the wire protocol, never process proof.
    stage = cli.OwnedStage(owner, channel, b'{}', time.monotonic(), True)
    mailbox.bind(stage, request)
    broker = cli.InvocationMailbox.attach(mailbox.name, mailbox.request_sha, 'broker')
    try: yield mailbox, broker
    finally: broker.close(); mailbox.close(); channel.close()


@pytest.mark.parametrize('fault', ['nonce', 'producer', 'sequence', 'previous', 'accepted_bytes', 'partial', 'sha', 'length'])
def test_invocation_mailbox_rejects_replay_producer_and_accepted_drift(invocation_mailbox, fault):
    mailbox, broker = invocation_mailbox
    broker.write_packet('ready', {'ready': True})
    offset, size = mailbox._layout['ready']; slot = cli.C.string_at(mailbox._view+offset, size)
    if fault == 'accepted_bytes': assert mailbox.read_packet('ready') == {'ready': True}
    value = cli.parse(cli._invocation_decode(slot))
    if fault == 'nonce': value['direction_nonce'] = 'f'*64
    elif fault == 'producer': value['producer_identity'][0] += 1
    elif fault == 'sequence': value['sequence'] += 1
    elif fault == 'previous': value['previous_sha'] = 'f'*64
    elif fault == 'accepted_bytes': value['payload']['ready'] = False
    changed = cli._invocation_slot(cli.canonical(value), size)
    if fault == 'partial': changed = changed[:-8]+b'\0'*8
    elif fault == 'sha': changed = changed[:-40]+b'x'*32+changed[-8:]
    elif fault == 'length': changed = b'\xff'*4+changed[4:]
    cli.C.memmove(mailbox._view+offset, changed, size)
    with pytest.raises(ValueError): mailbox.read_packet('ready', bookend=True)
    cli.C.memmove(mailbox._view+offset, slot, size)
    with pytest.raises(cli.StageChannelError, match='remains unresolved'): mailbox.read_packet('ready')


def test_invocation_mailbox_is_create_only_single_writer_and_single_use(invocation_mailbox):
    mailbox, broker = invocation_mailbox
    with pytest.raises(ValueError, match='collision'): cli.InvocationMailbox.create(mailbox.request_sha, name=mailbox.name)
    broker.write_packet('ready', {'ready': True})
    with pytest.raises(ValueError, match='already consumed'): broker.write_packet('ready', {'ready': True})
    with pytest.raises(ValueError, match='wrong invocation transfer writer'): mailbox.write_packet('context', {})
    with pytest.raises(ValueError): cli.InvocationMailbox.attach(mailbox.name, mailbox.request_sha, 'controller')


@pytest.mark.parametrize('fault', ['fixture', 'source', 'environment', 'deadline', 'gate', 'receipt', 'root', 'broker'])
def test_invocation_context_offer_is_compared_to_independent_host_inputs(tmp_path, monkeypatch, fault):
    import time
    request = cli.parse(cli._invocation_request(tmp_path/'output', 'normal')); started = time.monotonic()
    raw = cli.make_role_probe_context(tmp_path/'output', started=started); root = tmp_path/'output'; root.mkdir()
    receipt = cli._publish_role_file(root/'context.json', raw); broker = cli._own_process_identity(cli._stage_api())
    offer = cli.parse(cli.canonical(dict(context=cli.parse(raw), context_sha=sha256(raw).hexdigest(),
        context_receipt=receipt, root_directories=cli.directories(root), broker_identity=broker)))
    if fault == 'fixture': offer['context']['fixture']['expected'] = 6
    elif fault == 'source': offer['context']['source_pins'][cli.NEW_SOURCES[1]]['sha256'] = 'f'*64
    elif fault == 'environment': offer['context']['environment']['PYTHONHASHSEED'] = '1'
    elif fault == 'deadline': offer['context']['deadline'] += 1.
    elif fault == 'gate': offer['context']['F_launch_admitted'] = True
    elif fault == 'receipt': offer['context_receipt']['identity'][2] += 1
    elif fault == 'root': offer['root_directories'][-1][0] += '_other'
    elif fault == 'broker': offer['broker_identity'][0] += 1
    if fault in ('fixture', 'source', 'environment', 'deadline', 'gate'):
        changed = cli.canonical(offer['context']); offer['context_sha'] = sha256(changed).hexdigest()
        offer['context_receipt'].update(cli.pin(changed)); offer['context_receipt']['identity'][2] = len(changed)
    def forbidden(*args, **kwargs): pytest.fail('host offer validation performed filesystem I/O')
    monkeypatch.setattr(cli, 'read', forbidden); monkeypatch.setattr(cli, 'directories', forbidden)
    with pytest.raises(ValueError): cli._held_context_offer(request, started, offer, broker)


def _capture_invocation(case, result, root):
    files = {}
    for name in cli.TARGETS:
        for suffix in ('', '.pending'):
            path = root/(name+suffix)
            if path.exists():
                raw = path.read_bytes()
                files[name+suffix] = dict(pin=cli.pin(raw), hex=raw.hex()) if name != 'context.json' else dict(pin=cli.pin(raw))
    projection = None
    if (root/'context.json').exists():
        projection = cli.parse((root/'context.json').read_bytes()); env = projection.pop('environment')
        projection['environment_sha'] = cli.digest(env)
    print('INVOCATION_GRAPH '+cli.canonical(dict(case=case, result=result, files=files, context_projection=projection,
        context_projection_omits=['environment'], projection_is_original_context=False)).decode())


def test_invocation_real_external_host_holds_context_and_observes_complete_graph(tmp_path, monkeypatch):
    armed = cli.arm_ordinary_invocation(tmp_path/'output')
    assert armed.held_context is None and armed.stage.owner._released and not (tmp_path/'output').exists()
    original_read, original_write = armed.mailbox.read_packet, armed.mailbox.write_packet
    ack_observation = dict(busy_seen=False, absence_confirmed=False, ack_written=False)
    def read_packet(kind, **kwargs):
        if kind == 'binding' and armed.ack_raw is None and not ack_observation['busy_seen']:
            armed.mailbox._read_busy = True; ack_observation['busy_seen'] = True; return None
        value = original_read(kind, **kwargs)
        if kind == 'binding' and armed.ack_raw is None and not armed.mailbox._read_busy:
            ack_observation['absence_confirmed'] = True
        return value
    def write_packet(kind, payload):
        if kind == 'ack':
            assert ack_observation['busy_seen'] and ack_observation['absence_confirmed']
            ack_observation['ack_written'] = True
        return original_write(kind, payload)
    monkeypatch.setattr(armed.mailbox, 'read_packet', read_packet); monkeypatch.setattr(armed.mailbox, 'write_packet', write_packet)
    def forbidden(*args, **kwargs): pytest.fail('external host active path performed artifact/source I/O or constructed actor')
    with monkeypatch.context() as patch:
        for name in ('read', 'directories', 'source_pins', '_construct_stage_owner'): patch.setattr(cli, name, forbidden)
        patch.setattr(cli.os.path, 'lexists', forbidden)
        try: result = cli.invoke_ordinary(armed)
        except cli.InvocationUnresolved as error:
            print('INVOCATION_NORMAL_UNRESOLVED '+cli.canonical(dict(primary=cli._stage_error(error.primary),
                process=armed.stage.last_observation)).decode())
            raise
    _capture_invocation('normal', result, tmp_path/'output')
    assert all(ack_observation.values())
    assert result['ordinary_external_invocation_completed'] is True
    _closed_stage_gates(result['broker_process'])
    controller = result['broker_return']['controller_process']; _closed_stage_gates(controller)
    parent = cli.parse((tmp_path/'output/worker/launcher.json').read_bytes())
    fresh = cli.parse((tmp_path/'output/worker/fresh/launcher.json').read_bytes())
    witnesses = [result['broker_process'], controller, parent, fresh]
    member_sets = [{(m['pid'], m['creation_filetime']) for m in r['quiescence_witness']['member_identities']} for r in witnesses]
    assert member_sets[3] < member_sets[2] < member_sets[1] < member_sets[0]
    assert len(member_sets[0]) >= 8
    context_value = cli.parse(bytes.fromhex(armed.held_context))
    controller_proof = result['broker_return']['controller_return']['entry_bootstrap']
    proofs = [controller_proof]
    for name in ('worker/events.jsonl', 'worker/fresh/events.jsonl'):
        event = cli.parse((tmp_path/'output'/name).read_bytes().splitlines()[0]); proofs.append(event['entry_bootstrap'])
    for role, process, proof in zip(('supervise', 'parent', 'fresh'), witnesses[1:], proofs):
        assert process['startup']['argv'][:4] == [str(cli.EXE), '-B', '-s', str(cli.ROOT/cli.NEW_SOURCES[1])]
        assert process['startup']['argv'][4:6] == ['--ordinary-entry', '--'+role]
        assert proof['entry_pin'] == context_value['source_pins'][cli.NEW_SOURCES[1]]
        assert proof['argv_sha'] == proof['orig_argv_sha'] == cli.digest(process['startup']['argv'])
        assert proof['sys_path'][0] == str(cli.ROOT) and proof['sys_path'].count(str(cli.ROOT)) == 1
        assert proof['main_is_canonical_module'] is proof['main_spec_is_none'] is True
        assert proof['project_imports_before_bootstrap'] == [] and proof['independent_OS_commandline_verified'] is False
        assert proof['full_runtime_closure_verified'] is False and all(proof[k] is False for k in cli.GATES)
    assert result['broker_job_counted_once'] is True and result['resource_samples'] > 1
    assert result['final_host_observation']['after_payload_encoding'] is result['final_host_observation']['after_mailbox_close'] is True
    assert result['final_host_observation']['protocol_progress_permitted'] is False
    assert result['sampled_combined_peak_rss_bytes'] >= result['broker_process']['sampled_tree_peak_rss_bytes']
    assert result['conservative_combined_peak_commit_bytes'] >= result['host_lifetime_peak_pagefile_bytes']+result['broker_process']['peak_job_commit_bytes']
    ack = cli.parse(bytes.fromhex(armed.ack_raw)); binding = cli.parse(bytes.fromhex(armed.controller_binding))
    assert ack['context_sha'] == result['held_context_pin']['sha256'] == binding['context_sha']
    assert controller['stage_header']['descriptor']['invocation_ack_sha'] == result['ack_sha']
    context = cli.parse(bytes.fromhex(armed.held_context))
    assert context['started'] == result['invocation_started'] and context['deadline'] == context['started']+8.
    assert [f['phase'] for f in controller['transcript_frames']] == [*cli.STAGE_PHASES['controller'], 'terminal']
    assert set(result['broker_return']['controller_return']['result']['output_inventory']) == set(cli.TARGETS)-{'diagnostics/failure.json'}
    assert all(result[name] is False for name in (*cli.GATES, 'F_launch_admitted', 'saved_P1_fresh_process_verified', 'saved_P1_parent_adoption_verified',
        'host_hard_resource_enforcement_proved', 'arming_interrupt_bound_proved', 'whole_F_180_seconds_proved'))
    with pytest.raises(ValueError, match='already consumed'): cli.invoke_ordinary(armed)


@pytest.mark.parametrize('case', ['prepare_wait', 'constructor_wait', 'publication_wait'])
def test_invocation_native_wait_in_constructor_or_publication_is_stopped_by_external_job(tmp_path, monkeypatch, case):
    import time
    started = time.monotonic(); armed = cli.arm_ordinary_invocation(tmp_path/'output', case)
    if case == 'constructor_wait':
        original = armed.mailbox.read_packet
        def delayed_marker(kind, **kwargs):
            if kind == 'constructor_probe' and kwargs.get('_wait', 0) == 0 and not kwargs.get('bookend', False):
                armed.mailbox._read_busy = True; return None
            return original(kind, **kwargs)
        monkeypatch.setattr(armed.mailbox, 'read_packet', delayed_marker)
    try: result = cli.invoke_ordinary(armed)
    except cli.InvocationUnresolved as error:
        # Killing an actor while it holds the mailbox mutex preserves an
        # unresolved protocol capability; physical all-Job quiet is separate.
        assert case == 'publication_wait' and error.capability is armed
        assert isinstance(error.primary, cli.StageChannelError) and error.primary.kind == 'abandoned'
        result = dict(result_kind='retained_unresolved_capability', primary=cli._stage_error(error.primary),
            ordinary_external_invocation_completed=False, broker_return=None, broker_process=armed.stage.last_observation,
            held_context_pin=cli.pin(bytes.fromhex(armed.held_context)), ack_sha=sha256(bytes.fromhex(armed.ack_raw)).hexdigest(),
            controller_binding_pin=cli.pin(bytes.fromhex(armed.controller_binding)), constructor_probe=None,
            F_launch_admitted=False, saved_P1_fresh_process_verified=False, saved_P1_parent_adoption_verified=False, **cli.GATES)
    _capture_invocation(case, result, tmp_path/'output')
    assert time.monotonic()-started < 12.
    record = result['broker_process']
    assert result['ordinary_external_invocation_completed'] is False and result['broker_return'] is None
    assert record['termination_requested'] is record['termination_call_succeeded'] is record['job_quiet_confirmed'] is True
    assert record['stage_process_observed_successfully'] is False and record['quiescence_witness']['complete_inventory'] is True
    assert record['primary_stop_reason'] == 'phase_limit'
    if case == 'prepare_wait': assert not (tmp_path/'output').exists()
    elif case == 'constructor_wait':
        assert result['held_context_pin'] is not None and result['ack_sha'] is not None
        assert result['constructor_probe']['phase'] == 'controller_constructor_native_wait' and result['controller_binding_pin'] is None
        assert 2.9 <= record['observation_seconds'] <= 4.5 and record['frames_observed'] == 1
        assert set((tmp_path/'output').iterdir()) == {tmp_path/'output/context.json'}
    else:
        assert (tmp_path/'output/parent/parent_observation.json.pending').exists()
        assert not (tmp_path/'output/parent/parent_observation.json').exists()


def test_invocation_ready_expires_and_cannot_be_reused_or_serialized(tmp_path):
    import pickle,time
    armed = cli.arm_ordinary_invocation(tmp_path/'output')
    with pytest.raises(TypeError): pickle.dumps(armed)
    time.sleep(max(0., armed.standby_deadline-time.monotonic())+.05)
    with pytest.raises(cli.InvocationUnresolved) as found: cli.invoke_ordinary(armed)
    assert found.value.capability is armed and found.value.primary.args == ('armed broker standby expired',)
    assert armed.consumed and not (tmp_path/'output').exists()
    assert cli._stage_complete_witness(armed.stage.owner.quiescence_witness, armed.stage.owner.pid, armed.stage.owner.creation_filetime)
    with pytest.raises(ValueError, match='already consumed'): cli.invoke_ordinary(armed)


@pytest.mark.parametrize('case', ['normal', 'constructor_wait'])
def test_invocation_host_resource_failure_never_reads_return(tmp_path, monkeypatch, case):
    armed = cli.arm_ordinary_invocation(tmp_path/'output', case); reads = []
    original = armed.mailbox.read_packet
    def read_packet(kind, **kwargs): reads.append(kind); return original(kind, **kwargs)
    monkeypatch.setattr(armed.mailbox, 'read_packet', read_packet)
    monkeypatch.setattr(cli, '_host_memory', lambda api: dict(rss_bytes=1024**3+1, peak_pagefile_bytes=0))
    with pytest.raises(cli.InvocationUnresolved) as found: cli.invoke_ordinary(armed)
    print('INVOCATION_RESOURCE_FAILURE '+cli.canonical(dict(primary=cli._stage_error(found.value.primary),
        process=armed.stage.last_observation)).decode())
    assert found.value.capability is armed and 'broker_return' not in reads
    assert armed.sampled_combined_peak_rss_bytes > 1024**3
    assert armed.stage.last_observation['stage_process_observed_successfully'] is False
    assert armed.stage.last_observation['job_quiet_confirmed'] is True
    assert armed.stage.last_observation['monitor_error']['message'] == 'combined host and owned Job resource limit'
    assert cli._stage_error(found.value.primary)['message'] == 'combined host and owned Job resource limit'


def test_invocation_unknown_actual_quiet_blocks_return_consumption(tmp_path, monkeypatch):
    armed = cli.arm_ordinary_invocation(tmp_path/'output'); reads = []
    original = armed.mailbox.read_packet
    def read_packet(kind, **kwargs): reads.append(kind); return original(kind, **kwargs)
    monkeypatch.setattr(armed.mailbox, 'read_packet', read_packet)
    original_quiesce = armed.stage.owner.quiesce
    def unknown(*, max_seconds):
        original_quiesce(max_seconds=max_seconds); raise OSError('injected final quiet unknown')
    monkeypatch.setattr(armed.stage.owner, 'quiesce', unknown)
    with pytest.raises(cli.InvocationUnresolved) as found: cli.invoke_ordinary(armed)
    print('INVOCATION_QUIET_UNKNOWN '+cli.canonical(dict(primary=cli._stage_error(found.value.primary),
        process=armed.stage.last_observation)).decode())
    assert found.value.capability is armed and 'broker_return' not in reads
    assert armed.stage.last_observation['job_quiet_confirmed'] is False
    assert armed.stage.last_observation['quiesce_error']['message'] == 'injected final quiet unknown'


def test_invocation_public_entry_rejects_unarmed_or_arbitrary_requests(tmp_path):
    with pytest.raises(ValueError): cli.invoke_ordinary({'ready': True})
    with pytest.raises(ValueError): cli.arm_ordinary_invocation(tmp_path/'output', 'arbitrary')
    with pytest.raises(ValueError): cli.arm_ordinary_invocation(cli.OUTPUT)
    with pytest.raises(ValueError): cli.checked_stage_descriptor(cli.canonical(dict(cli.parse(cli.stage_descriptor('controller')), invocation_ack_sha='a'*64)))


@pytest.mark.parametrize('prefix', [1, 2, 3, 'hole'])
def test_invocation_terminal_failure_binds_only_contiguous_progress(invocation_mailbox, prefix):
    mailbox, broker = invocation_mailbox
    broker.write_packet('ready', {'unit': 'ready'})
    if prefix in (2, 3): broker.write_packet('context', {'unit': 'context'})
    if prefix == 3: broker.write_packet('binding', {'unit': 'binding'})
    if prefix == 'hole':
        offset, size = mailbox._layout['binding']; slot = cli._invocation_slot(b'{"unit":"hole"}', size)
        cli.C.memmove(mailbox._view+offset, slot, size)
        with pytest.raises(ValueError, match='noncontiguous'): broker.write_packet('broker_return', {'kind': 'failure'})
    else:
        broker.write_packet('broker_return', {'kind': 'failure', 'unit': True})
        assert mailbox.read_packet('broker_return', bookend=True) == {'kind': 'failure', 'unit': True}
        packet = cli.parse(cli._invocation_decode(mailbox._accepted['broker_return']))
        assert packet['sequence'] == 0 and packet['previous_sha'] == '0'*64
        assert len(packet['payload']['progress']['prefix']) == prefix and packet['payload']['status'] == 'failure'


def test_invocation_busy_poll_is_not_missing_prior_or_protocol_corruption(invocation_mailbox):
    import threading,time
    mailbox, broker = invocation_mailbox; broker.write_packet('ready', {'unit': True})
    acquired = threading.Event()
    def hold_mutex():
        assert mailbox._api.WaitForSingleObject(mailbox._mutex, 100) == 0
        acquired.set(); time.sleep(.04); cli._native(mailbox._api.ReleaseMutex(mailbox._mutex))
    thread = threading.Thread(target=hold_mutex); thread.start(); assert acquired.wait(1.)
    try:
        assert mailbox.read_packet('ready') is None and mailbox._read_busy and mailbox._poison is None
        mailbox.write_packet('start', {'unit': 'one START'})
    finally: thread.join(1.)
    assert not thread.is_alive() and broker.read_packet('start', bookend=True) == {'unit': 'one START'}
    assert mailbox._poison is None


def test_invocation_partial_mapping_cleanup_retains_actual_handle(monkeypatch):
    import pickle
    original = cli._stage_api(); partial = None
    class Api:
        def __getattr__(self, name): return getattr(original, name)
        def CreateMutexW(self, *args): cli.C.set_last_error(5); return 0
        def CloseHandle(self, handle): return False
    monkeypatch.setattr(cli, '_stage_api', lambda: Api())
    try:
        with pytest.raises(cli.StageChannelConstructionUnresolved) as found: cli.InvocationMailbox.create('a'*64)
        partial = found.value.channel
        assert type(partial) is cli.InvocationMailbox and partial._map is not None and partial._mutex is partial._view is None
        assert found.value.primary['type'] == 'PermissionError' and found.value.cleanup_error['kind'] == 'close'
        with pytest.raises(TypeError): pickle.dumps(found.value)
    finally:
        if partial is not None: partial._api = original; partial.close()


@pytest.mark.parametrize('field', ['nonce', 'receipt_sha'])
def test_invocation_wrong_host_ack_is_diagnosed_before_controller_construct(tmp_path, monkeypatch, field):
    original = cli._invocation_ack
    def bad(*args):
        value = original(*args); value[field] = 'f'*64; return value
    monkeypatch.setattr(cli, '_invocation_ack', bad)
    result = cli.run_ordinary_invocation(tmp_path/'output')
    _capture_invocation('wrong_ack_'+field, result, tmp_path/'output')
    assert result['ordinary_external_invocation_completed'] is False and result['broker_return'] is None
    assert result['held_context_pin'] is not None and result['controller_binding_pin'] is None
    diagnostic = result['broker_diagnostic']
    assert diagnostic['phase'] == 'ack' and diagnostic['primary']['message'] == 'host exact context ACK missing or differs'
    assert result['broker_process']['job_quiet_confirmed'] is True
    assert set((tmp_path/'output').iterdir()) == {tmp_path/'output/context.json'}


def test_invocation_busy_prestart_cannot_write_start(tmp_path, monkeypatch):
    armed = cli.arm_ordinary_invocation(tmp_path/'output'); original = armed.mailbox.read_packet; writes = []
    helper_pids = {row[0] for row in armed.ready_members}-{armed.stage.owner.pid}
    if helper_pids:
        helpers = cli._terminal_console_helpers(armed.stage.owner, helper_pids)
        assert len(helpers) == 1 and helpers[0]['image_path'].lower() == cli._system_console_path()
        with monkeypatch.context() as patch:
            patch.setattr(cli, '_system_console_path', lambda *args: 'C:\\wrong\\conhost.exe')
            assert cli._terminal_console_helpers(armed.stage.owner, helper_pids) is None
    assert cli._terminal_console_helpers(armed.stage.owner, {armed.stage.owner.pid}) is None
    assert cli._terminal_console_helpers(armed.stage.owner, {1, 2}) is None
    def busy(kind, **kwargs):
        if kind == 'context': armed.mailbox._read_busy = True; return None
        return original(kind, **kwargs)
    monkeypatch.setattr(armed.mailbox, 'read_packet', busy)
    monkeypatch.setattr(armed.mailbox, 'write_packet', lambda kind, payload: writes.append(kind))
    with pytest.raises(cli.InvocationUnresolved) as found: cli.invoke_ordinary(armed)
    assert found.value.primary.args == ('pre-START context absence unknown',) and writes == []
    assert found.value.capability is armed and armed.stage.last_observation is None


def test_invocation_expiry_during_preflight_prevents_start(tmp_path, monkeypatch):
    armed = cli.arm_ordinary_invocation(tmp_path/'output'); original_members = cli._invocation_ready_members
    original_clock = cli.time.monotonic; crossed = [False]; writes = []
    def members(*args):
        value = original_members(*args); crossed[0] = True; return value
    monkeypatch.setattr(cli, '_invocation_ready_members', members)
    monkeypatch.setattr(cli.time, 'monotonic', lambda: original_clock()+(2. if crossed[0] else 0.))
    monkeypatch.setattr(armed.mailbox, 'write_packet', lambda kind, payload: writes.append(kind))
    with pytest.raises(cli.InvocationUnresolved) as found: cli.invoke_ordinary(armed)
    assert found.value.primary.args == ('armed broker standby expired during preflight',) and writes == []
    assert found.value.capability is armed


@pytest.mark.parametrize('case', ['normal', 'prepare_wait', 'publication_wait'])
def test_invocation_constructor_probe_rejects_wrong_case(case):
    import time
    started = time.monotonic(); probe = dict(request_sha='a'*64, context_sha='b'*64, ack_sha='c'*64,
        phase='controller_constructor_native_wait', stamp=time.monotonic())
    with pytest.raises(ValueError, match='native wait marker differs'):
        cli._constructor_probe_value({'case': case}, 'a'*64, 'b'*64, 'c'*64, started, probe)


def _file_entry_args(tmp_path, role='parent'):
    return cli.ordinary_file_argv(role, str(tmp_path/'output/context.json'), 'a'*64,
        cli.STAGE_PREFIX+'b'*64, 'c'*64, **(dict(tree_sha='d'*64) if role != 'supervise' else
            dict(mailbox_name=cli.INVOCATION_PREFIX+'e'*64, request_sha='f'*64, ack_sha='1'*64)))


@pytest.mark.parametrize('role', ['parent', 'fresh', 'supervise'])
def test_file_entry_builder_binds_script_and_closed_transport(tmp_path, role):
    argv = _file_entry_args(tmp_path, role); values = cli.ordinary_file_arguments(argv[4:])
    assert argv[:4] == [str(cli.EXE), '-B', '-s', str(cli.ROOT/cli.NEW_SOURCES[1])]
    assert values['role'] == role and values['context_path'] == str(tmp_path/'output/context.json')
    assert values['context_sha'] == 'a'*64 and values['channel_name'] == cli.STAGE_PREFIX+'b'*64
    assert values['channel_nonce'] == 'c'*64
    if role == 'supervise': assert values['mailbox_name'] == cli.INVOCATION_PREFIX+'e'*64 and values['tree_sha'] is None
    else: assert values['tree_sha'] == 'd'*64 and values['mailbox_name'] is None


@pytest.mark.parametrize('fault', ['empty', 'mode', 'role', 'unknown', 'duplicate', 'order', 'missing', 'relative',
    'dotdot', 'basename', 'sha', 'nonce', 'channel', 'factory', 'nul', 'upper_sha'])
def test_file_entry_malformed_arguments_fail_before_io_or_transport(tmp_path, monkeypatch, fault):
    argv = _file_entry_args(tmp_path)[4:]
    if fault == 'empty': argv = []
    elif fault == 'mode': argv[0] = '--ordinary'
    elif fault == 'role': argv[1] = '--controller'
    elif fault == 'unknown': argv += ['--unknown', 'x']
    elif fault == 'duplicate': argv += ['--context-sha', 'a'*64]
    elif fault == 'order': argv[2], argv[4] = argv[4], argv[2]
    elif fault == 'missing': argv.pop()
    elif fault == 'relative': argv[3] = 'output/context.json'
    elif fault == 'dotdot': argv[3] = str(tmp_path/'other/../output/context.json')
    elif fault == 'basename': argv[3] = str(tmp_path/'output/other.json')
    elif fault == 'sha': argv[5] = 'a'*63
    elif fault == 'upper_sha': argv[5] = 'A'*64
    elif fault == 'nonce': argv[-1] = 'c'*65
    elif fault == 'channel': argv[-3] = 'Global\\arbitrary'
    elif fault == 'factory': argv += ['--factory', 'os.system']
    elif fault == 'nul': argv[3] += '\0'
    def forbidden(*args, **kwargs): pytest.fail('malformed file entry reached I/O or transport')
    monkeypatch.setattr(cli, 'read', forbidden); monkeypatch.setattr(cli.StageChannel, 'attach', forbidden)
    monkeypatch.setattr(cli.InvocationMailbox, 'attach', forbidden)
    with pytest.raises(ValueError): cli._ordinary_file_dispatch(argv)


def test_file_entry_imported_module_cannot_claim_direct_main(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs): pytest.fail('imported dispatcher reached context/transport')
    monkeypatch.setattr(cli, 'read', forbidden); monkeypatch.setattr(cli.StageChannel, 'attach', forbidden)
    with pytest.raises(ValueError, match='direct ordinary main'): cli._ordinary_file_dispatch(_file_entry_args(tmp_path)[4:])


@pytest.mark.parametrize('args', [[], ['--help'], ['--supervise'], ['--parent'], ['--fresh'],
    ['--ordinary-entry', '--factory', 'os.system']])
def test_file_entry_default_and_saved_cli_remain_disabled(args):
    import subprocess
    run = subprocess.run([str(cli.EXE), '-B', '-s', str(cli.ROOT/cli.NEW_SOURCES[1]), *args],
        cwd=cli.ROOT, env=cli.environment(), capture_output=True, timeout=4)
    assert run.returncode != 0 and run.stdout == b''
    if args[:1] != ['--ordinary-entry']: assert b'F launch remains disabled' in run.stderr


@pytest.mark.parametrize('fault', ['context', 'argv', 'source', 'alias', 'flags_scalar', 'path_relative', 'path_duplicate',
    'path_other_root', 'OS_claim', 'runtime_claim', 'gate', 'extra'])
def test_file_entry_bootstrap_diagnostic_rejects_forged_fields(tmp_path, fault):
    context = cli.parse(cli.make_role_probe_context(tmp_path/'output')); argv = _file_entry_args(tmp_path)
    paths = [str(cli.ROOT), str(cli.EXE.parent/'Lib')]
    proof = dict(schema=cli.ORDINARY_ENTRY_SCHEMA, authority='DRAFT_NONAUTHORITATIVE', scope='ordinary_file_entry_self_check_only',
        role='parent', context_sha='a'*64, entry_path=str(cli.ROOT/cli.NEW_SOURCES[1]), entry_pin=context['source_pins'][cli.NEW_SOURCES[1]],
        executable=context['executable'], cwd=str(cli.ROOT), argv_sha=cli.digest(argv), orig_argv_sha=cli.digest(argv),
        sys_path=paths, sys_path_sha=cli.digest(paths), main_is_canonical_module=True, main_spec_is_none=True,
        project_imports_before_bootstrap=[], project_import_scan='module_file_paths_and_project_namespaces',
        flags=dict(dont_write_bytecode=True, no_user_site=True, hash_randomization=False),
        independent_OS_commandline_verified=False, full_runtime_closure_verified=False, F_launch_admitted=False,
        saved_P1_fresh_process_verified=False, saved_P1_parent_adoption_verified=False, **cli.GATES)
    assert cli.checked_ordinary_bootstrap(proof, 'parent', 'a'*64, argv, context) == proof
    proof = deepcopy(proof)
    if fault == 'context': proof['context_sha'] = '0'*64
    elif fault == 'argv': proof['argv_sha'] = '0'*64
    elif fault == 'source': proof['entry_pin']['sha256'] = '0'*64
    elif fault == 'alias': proof['main_is_canonical_module'] = False
    elif fault == 'flags_scalar': proof['flags']['dont_write_bytecode'] = 1
    elif fault == 'path_relative': proof['sys_path'] = ['.', str(cli.EXE.parent/'Lib')]
    elif fault == 'path_duplicate': proof['sys_path'].append(str(cli.ROOT))
    elif fault == 'path_other_root': proof['sys_path'].append(str(tmp_path))
    elif fault == 'OS_claim': proof['independent_OS_commandline_verified'] = True
    elif fault == 'runtime_claim': proof['full_runtime_closure_verified'] = True
    elif fault == 'gate': proof['F_launch_admitted'] = True
    elif fault == 'extra': proof['extra'] = None
    with pytest.raises(ValueError): cli.checked_ordinary_bootstrap(proof, 'parent', 'a'*64, argv, context)


@pytest.mark.parametrize('role', ['parent', 'fresh', 'supervise'])
@pytest.mark.parametrize('fault', ['schema', 'authority', 'F_launch_admitted', 'saved_P1_fresh_process_verified', 'saved_P1_parent_adoption_verified'])
def test_file_entry_context_domain_rejects_local_authority_before_main_or_io(tmp_path, monkeypatch, role, fault):
    context = cli.parse(cli._invocation_request(tmp_path/'output', 'normal') if role == 'supervise'
        else cli.make_role_probe_context(tmp_path/'output'))
    assert cli._ordinary_bootstrap_context(role, context) == context
    if fault == 'schema': context['schema'] = cli.ROLE_PROBE_SCHEMA if role == 'supervise' else cli.INVOCATION_SCHEMA
    elif fault == 'authority': context['authority'] = 'FORMAL'
    else: context[fault] = True
    def forbidden(*args): pytest.fail('invalid context reached main/source/transport')
    monkeypatch.setattr(cli, '_direct_main_shape', forbidden)
    with pytest.raises(ValueError, match='bootstrap context'): cli._bind_ordinary_main(role, 'a'*64, [], context)


def test_file_entry_preimport_scan_includes_noncanonical_repository_modules():
    from types import ModuleType
    main = ModuleType('__main__'); main.__file__ = str(cli.ROOT/cli.NEW_SOURCES[1])
    other = ModuleType('innocent'); other.__file__ = str(cli.ROOT/'experiments/unrelated.py')
    relative = ModuleType('relative'); relative.__file__ = 'tests/unrelated.py'
    standard = ModuleType('standard'); standard.__file__ = str(cli.EXE.parent/'Lib/json/__init__.py')
    found = cli._ordinary_preimports(main, modules={'__main__': main, cli.ENTRY_MODULE_NAME: main,
        'innocent': other, 'relative': relative, 'standard': standard, 'experiments': ModuleType('experiments')})
    assert found == ['experiments', 'innocent', 'relative']


def _console_unit(monkeypatch, *, image='c:\\windows\\system32\\conhost.exe', signaled=False, query_error=False, system_error=False):
    from types import SimpleNamespace
    state = {'wait': 0 if signaled else 258, 'queries': 0, 'image': image, 'query_error': query_error, 'system_error': system_error}
    owner = SimpleNamespace(pid=1, _members={(1, 11): 101, (2, 22): 202},
        _k=SimpleNamespace(WaitForSingleObject=lambda *args: state['wait']))
    def query(*args):
        state['queries'] += 1
        if state['query_error']: raise OSError('fixed image query failure')
        return state['image']
    def system(*args):
        if state['system_error']: raise OSError('fixed system directory failure')
        return 'c:\\windows\\system32\\conhost.exe'
    monkeypatch.setattr(cli, '_console_image', query); monkeypatch.setattr(cli, '_system_console_path', system)
    cache = cli.ConsoleImageCache(owner)
    data = dict(pids=[1, 2], rss_bytes=17, peak_job_commit_bytes=23, processes=2)
    return owner, cache, state, data


@pytest.mark.parametrize('fault', ['creation', 'duplicate_creation', 'handle', 'missing', 'multiple', 'invalid_handle', 'corrupt'])
def test_file_entry_console_cache_rejects_identity_handle_and_state_drift(monkeypatch, fault):
    owner, cache, state, data = _console_unit(monkeypatch); cache.observe(owner, data)
    assert cache.classify(owner, {2}) is not None
    if fault == 'creation': owner._members = {(1, 11): 101, (2, 33): 202}
    elif fault == 'duplicate_creation': owner._members[(2, 33)] = 303
    elif fault == 'handle': owner._members[(2, 22)] = 303
    elif fault == 'missing': del owner._members[(2, 22)]
    elif fault == 'invalid_handle': state['wait'] = 0xffffffff
    elif fault == 'corrupt': cache._entries[(2, 22)] = (202, 'positive', -1.)
    assert cache.classify(owner, {2, 3} if fault == 'multiple' else {2}) is None


@pytest.mark.parametrize('fault', ['negative', 'signaled', 'query', 'system'])
def test_file_entry_console_cache_unknown_and_negative_are_sticky(monkeypatch, fault):
    owner, cache, state, data = _console_unit(monkeypatch, image='c:\\other.exe' if fault == 'negative' else 'c:\\windows\\system32\\conhost.exe',
        signaled=fault == 'signaled', query_error=fault == 'query', system_error=fault == 'system')
    cache.observe(owner, data); first_queries = state['queries']
    state.update(wait=258, image='c:\\windows\\system32\\conhost.exe', query_error=False, system_error=False)
    for _ in range(3): cache.observe(owner, data)
    assert state['queries'] == first_queries <= 1 and cache.classify(owner, {2}) is None


def test_file_entry_console_cache_binds_live_query_when_terminal_query_fails(monkeypatch):
    import time
    owner, cache, state, data = _console_unit(monkeypatch); before = deepcopy(data)
    assert cache.classify(owner, {2}) is None
    cache.observe(owner, data); observed = cache._entries[(2, 22)][2]
    assert observed is not None and data == before
    state.update(wait=0, query_error=True)
    helpers = cache.classify(owner, {2})
    assert helpers[0]['pid'] == 2 and helpers[0]['creation_filetime'] == 22
    assert observed <= helpers[0]['observed_at'] <= time.monotonic()
    assert state['queries'] == 2 and cache.classify(owner, {2, 3}) is None


def test_file_entry_console_factory_preserves_base_sample_and_injected_owner_scope(monkeypatch):
    from types import SimpleNamespace
    data = dict(pids=[1, 2], rss_bytes=17, peak_job_commit_bytes=23, processes=2)
    def query(*args): return 'c:\\windows\\system32\\conhost.exe'
    monkeypatch.setattr(cli, '_console_image', query); monkeypatch.setattr(cli, '_system_console_path', query)
    class Base:
        fail = False
        def __init__(self):
            self.pid = 1; self._members = {(1, 11): 101, (2, 22): 202}
            self._k = SimpleNamespace(WaitForSingleObject=lambda *args: 258)
        def sample(self):
            if self.fail: raise ValueError('base sample original')
            return data
    assert cli._stage_owner_factory(Base, None, 'normal') is Base
    assert cli._stage_owner_factory(Base, None, 'unknown') is Base
    assert cli._stage_owner_factory(Base, Base, 'role_graph_fresh') is Base
    factory = cli._stage_owner_factory(Base, None, 'role_graph_fresh'); owner = factory()
    assert owner.sample() is data and owner._ordinary_console_cache.classify(owner, {2}) is not None
    owner.fail = True
    with pytest.raises(ValueError, match='base sample original'): owner.sample()
    channel = cli.StageChannel.create('a'*64, cli.ordinary_stage_descriptor('fresh', 'role_graph'))
    held = cli._construct_stage_owner([str(cli.EXE), '-B', '-s', '-c', 'pass'], channel, 'role_graph_fresh', owner_factory=_StageUnitOwner)
    try: assert held.real_owner is False and not hasattr(held.owner, '_ordinary_console_cache')
    finally: held.close()


def test_file_entry_native_console_cache_classification_and_actual_quiet(tmp_path, monkeypatch):
    armed = cli.arm_ordinary_invocation(tmp_path/'output'); owner = armed.stage.owner
    cache = owner._ordinary_console_cache; cache.check(owner)
    positives = [key for key, value in cache._entries.items() if value[1] == 'positive']
    assert len(positives) == 1 and positives[0][0] != owner.pid
    def fail(*args): raise OSError('fixed terminal image query failure')
    monkeypatch.setattr(cli, '_console_image', fail)
    helpers = cli._terminal_console_helpers(owner, {positives[0][0]})
    assert len(helpers) == 1 and (helpers[0]['pid'], helpers[0]['creation_filetime']) == positives[0]
    armed.close()
    witness = owner.quiescence_witness
    assert cli._stage_complete_witness(witness, owner.pid, owner.creation_filetime)
    print('CONSOLE_CACHE_NATIVE '+cli.canonical(dict(scope='live metadata classification then actual close only',
        helpers=helpers, witness=witness, stage_success_claimed=False, F_launch_admitted=False, **cli.GATES)).decode())


def test_file_entry_cached_owner_still_rejects_actual_live_python_descendant():
    channel = cli.StageChannel.create('a'*64, cli.ordinary_stage_descriptor('parent', 'role_graph'))
    code = ('import os,time,subprocess; from experiments import staged_rts24_saved_fresh_adoption_v1 as e; '
        f'w=e.StageChannel.attach({channel.name!r},{channel.nonce!r},{channel.context_sha!r},{channel.descriptor!r}); '
        "w.enter('parent'); child=subprocess.Popen([str(e.EXE),'-B','-s','-c','import time; time.sleep(20)']); "
        "w.enter('fresh'); time.sleep(.3); w.enter('inner_quiesce'); w.enter('inner_terminal'); "
        "w.enter('parent_compare'); w.enter('terminal'); os._exit(0)")
    held = cli._construct_stage_owner([str(cli.EXE), '-B', '-s', '-c', code], channel, 'role_graph_parent')
    result = cli.watch_probe_stage(held)
    assert held.real_owner and hasattr(held.owner, '_ordinary_console_cache')
    assert result['primary_stop_reason'] == 'root_exited_with_descendants'
    assert result['job_quiet_confirmed'] is True and result['stage_process_observed_successfully'] is False
    assert any(value[1] == 'negative' for value in held.owner._ordinary_console_cache._entries.values())
    print('CONSOLE_CACHE_DESCENDANT '+cli.canonical(result).decode())


def _saved_argv(role, raw, sha, **changes):
    values = dict(tree_sha='c'*64, channel_name=cli.STAGE_PREFIX+'a'*64, channel_nonce='b'*64)
    values.update(changes)
    return cli.argv_for(role, raw, sha, **values)


@pytest.fixture(scope='module')
def saved_binding_context():
    # Capture bytes only. No output tree, scientific replay, owner or child.
    assert not cli.OUTPUT.exists()
    directories = cli.directories
    parent = cli.OUTPUT.parent
    # Actual output parent does not exist. Its identity is a logical unit
    # boundary, never a physical-input or readiness observation.
    logical = (*directories(parent.parent), (str(parent), 0, 0))
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(cli, 'directories', lambda path: logical if Path(path) == parent else directories(path))
        raw = cli.make_context(cli.OUTPUT, started=time.monotonic())
        print('SAVED_BINDING_FIXTURE '+cli.canonical(dict(scope='unit interface only',
            logical_output_parent_identity=True, actual_saved_F_execution=False, F_launch_admitted=False,
            context_pin=cli.pin(raw))).decode())
        yield raw, sha256(raw).hexdigest()
    assert not cli.OUTPUT.exists()


def _saved_unit_endpoint(role, sha, *, reader=False):
    import os
    from threading import get_ident
    endpoint = object.__new__(cli.StageChannel)
    endpoint.name = cli.STAGE_PREFIX+'a'*64; endpoint.nonce = 'b'*64
    endpoint.context_sha = sha; endpoint.descriptor = cli.stage_descriptor(role)
    endpoint._creator = os.getpid(), get_ident()
    endpoint._view = endpoint._map = endpoint._mutex = 1  # Logical unit values, never native HANDLEs.
    endpoint._binding_inputs = endpoint.name, endpoint.nonce, sha, endpoint.descriptor
    endpoint._poison = None; endpoint._reader = reader; endpoint._header = None if reader else b'unit-header'
    def close(): endpoint._view = endpoint._map = endpoint._mutex = None
    endpoint.close = close
    return endpoint


def _saved_unit_main(monkeypatch, captured, *, role='fresh', tree_sha='c'*64):
    from types import ModuleType
    raw, sha = captured; args = _saved_argv(role, raw, sha, tree_sha=tree_sha)
    main = ModuleType('__main__'); main.__file__ = str(cli.ROOT/cli.NEW_SOURCES[1]); main.__spec__ = None
    flags = sys.flags
    class UnitFlags:
        dont_write_bytecode = no_user_site = 1
        hash_randomization = 0
        def __getattr__(self, name): return getattr(flags, name)
    monkeypatch.setattr(sys, 'flags', UnitFlags())
    monkeypatch.setattr(cli, '__name__', '__main__')
    monkeypatch.setitem(sys.modules, '__main__', main)
    monkeypatch.delitem(sys.modules, cli.ENTRY_MODULE_NAME, raising=False)
    monkeypatch.setattr(sys, 'argv', args[3:]); monkeypatch.setattr(sys, 'orig_argv', list(args))
    monkeypatch.setattr(sys, 'path', [str(cli.ROOT/'experiments'), str(cli.EXE.parent), str(cli.EXE.parent/'Lib')])
    monkeypatch.setattr(cli, '_DIRECT_BOOTSTRAP', None); monkeypatch.setattr(cli, '_SAVED_BOOTSTRAP', None)
    # Pytest has imported science already. Only this preimport boundary is
    # injected; this fixture does not prove an actual saved process bootstrap.
    monkeypatch.setattr(cli, '_ordinary_preimports', lambda main: [])
    for name, value in [('PYTHONDONTWRITEBYTECODE', '1'), ('PYTHONNOUSERSITE', '1'), ('PYTHONHASHSEED', '0')]:
        monkeypatch.setenv(name, value)
    for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'): monkeypatch.setenv(name, '1')
    for name in ('PYTHONPATH', 'PYTHONHOME', 'PYTHONSTARTUP'): monkeypatch.delenv(name, raising=False)
    return raw, sha, args, main


def _saved_unit_bound(monkeypatch, captured, *, role='fresh', tree_sha='c'*64):
    raw, sha, args, main = _saved_unit_main(monkeypatch, captured, role=role, tree_sha=tree_sha)
    held = cli._bind_saved_main(role, raw, sha, tree_sha, cli.STAGE_PREFIX+'a'*64, 'b'*64)
    channel = _saved_unit_endpoint(role, sha); held.bind_channel(channel)
    return raw, sha, args, main, held, channel


def _saved_unit_store(monkeypatch, captured):
    tree = (('unit_output_tree', ()),); tree_sha = cli.digest(tree)
    raw, sha, args, main, held, channel = _saved_unit_bound(monkeypatch, captured, role='parent', tree_sha=tree_sha)
    original = cli.read
    monkeypatch.setattr(cli, '_role_tree', lambda root: tree)
    monkeypatch.setattr(cli, 'read', lambda path, **kw: raw if Path(path) == cli.OUTPUT/'context.json' else original(path, **kw))
    return cli.RoleStore(raw, sha, tree_sha, 'parent')


@pytest.mark.parametrize('role', ['parent', 'fresh'])
def test_saved_binding_canonical_grammar_and_separate_supervise(saved_binding_context, role):
    raw, sha = saved_binding_context; args = _saved_argv(role, raw, sha)
    assert args[4:6] == ['--saved-entry', '--'+role]
    parsed = cli.saved_file_arguments(args[4:])
    assert parsed['role'] == role and parsed['context_path'] == str(cli.OUTPUT/'context.json')
    assert '--input-root' not in args and '--output-root' not in args
    with pytest.raises(ValueError): cli.ordinary_file_arguments(args[4:])
    with pytest.raises(ValueError, match='separate trusted invocation'): _saved_argv('supervise', raw, sha)


@pytest.mark.parametrize('fault', ['ordinary', 'supervise', 'duplicate', 'missing', 'order', 'unknown',
    'input_root', 'output_root', 'relative', 'parent_path', 'nul', 'uppercase', 'short_sha', 'bad_channel', 'abbrev'])
def test_saved_binding_parser_rejects_before_io(saved_binding_context, monkeypatch, fault):
    raw, sha = saved_binding_context; args = _saved_argv('fresh', raw, sha)[4:]
    if fault == 'ordinary': args[0] = '--ordinary-entry'
    elif fault == 'supervise': args[1] = '--supervise'
    elif fault == 'duplicate': args += args[-2:]
    elif fault == 'missing': args = args[:-2]
    elif fault == 'order': args[2:6] = args[4:6]+args[2:4]
    elif fault == 'unknown': args[2] = '--other'
    elif fault in ('input_root', 'output_root'): args += ['--'+fault.replace('_', '-'), str(cli.P1)]
    elif fault == 'relative': args[3] = 'context.json'
    elif fault == 'parent_path': args[3] = str(cli.OUTPUT/'..'/'context.json')
    elif fault == 'nul': args[3] += '\0'
    elif fault == 'uppercase': args[7] = 'A'*64
    elif fault == 'short_sha': args[5] = 'a'*63
    elif fault == 'bad_channel': args[9] = 'Local\\wrong'
    else: args[6] = '--tree'
    monkeypatch.setattr(cli, 'read', lambda *a, **k: pytest.fail('malformed argv read content'))
    monkeypatch.setattr(cli.StageChannel, 'attach', lambda *a: pytest.fail('malformed argv attached'))
    with pytest.raises(ValueError): cli._open_saved_role_inputs(args)


@pytest.mark.parametrize('role', ['parent', 'fresh'])
def test_saved_binding_unit_holds_exact_context_tree_and_open_writer(saved_binding_context, monkeypatch, role):
    raw, sha, args, main, held, channel = _saved_unit_bound(monkeypatch, saved_binding_context, role=role)
    assert cli.execution_context(role, raw, sha) == cli.parse(raw)
    proof = held.proof()
    assert proof['context_sha'] == sha and proof['transport_sha'] == cli.digest(cli.parse(held.transport))
    assert proof['executable']['identity'] == cli.parse(raw)['executable']['identity']
    assert len(cli.canonical(proof)) <= 16384 and 'caller_core' not in proof and 'input_files' not in proof
    assert proof['F_launch_admitted'] is proof['full_runtime_closure_verified'] is False
    assert all(proof[k] is False for k in cli.GATES)
    with pytest.raises(ValueError): held.bind_channel(channel)
    import pickle
    with pytest.raises(TypeError): pickle.dumps(held)


@pytest.mark.parametrize('fault', ['role', 'raw', 'sha', 'tree', 'channel', 'nonce', 'descriptor', 'closed',
    'header', 'alias', 'argv', 'orig_argv', 'path', 'creator', 'transport', 'global'])
def test_saved_binding_rejects_late_cross_binding(saved_binding_context, monkeypatch, fault):
    raw, sha, args, main, held, channel = _saved_unit_bound(monkeypatch, saved_binding_context)
    role, tree = 'fresh', 'c'*64
    if fault == 'role': role = 'parent'
    elif fault == 'raw': raw += b' '
    elif fault == 'sha': sha = '0'*64
    elif fault == 'tree': tree = '0'*64
    elif fault == 'channel': channel.name = cli.STAGE_PREFIX+'d'*64
    elif fault == 'nonce': channel.nonce = 'd'*64
    elif fault == 'descriptor': channel.descriptor = cli.stage_descriptor('parent')
    elif fault == 'closed': channel.close()
    elif fault == 'header': channel._header = b'changed'
    elif fault == 'alias': sys.modules[cli.ENTRY_MODULE_NAME] = object()
    elif fault == 'argv': sys.argv.append('--drift')
    elif fault == 'orig_argv': sys.orig_argv.append('--drift')
    elif fault == 'path': sys.path.append(str(cli.EXE.parent/'other'))
    elif fault == 'creator': object.__setattr__(held, 'creator', (0, 0))
    elif fault == 'transport': object.__setattr__(held, 'transport', b'{}')
    else: monkeypatch.setattr(cli, '_SAVED_BOOTSTRAP', object())
    with pytest.raises(ValueError): cli._held_saved_bootstrap(role, raw, sha, tree_sha=tree)


@pytest.mark.parametrize('fault', ['environment', 'main_file', 'flags', 'preimports', 'alias', 'path', 'argv', 'orig_argv', 'exe_identity'])
def test_saved_binding_rejects_bootstrap_drift(saved_binding_context, monkeypatch, fault):
    raw, sha, args, main = _saved_unit_main(monkeypatch, saved_binding_context)
    if fault == 'environment': monkeypatch.setenv('PYTHONHASHSEED', '1')
    elif fault == 'main_file': main.__file__ = str(cli.ROOT/'other.py')
    elif fault == 'flags': sys.flags.no_user_site = 0
    elif fault == 'preimports': monkeypatch.setattr(cli, '_ordinary_preimports', lambda *a: ['src.unexpected'])
    elif fault == 'alias': sys.modules[cli.ENTRY_MODULE_NAME] = object()
    elif fault == 'path': sys.path.append('relative')
    elif fault == 'argv': sys.argv.append('--drift')
    elif fault == 'orig_argv': sys.orig_argv.append('--drift')
    else:
        original = cli.identity
        def identity(info):
            value = original(info)
            return (value[0], value[1]+1, *value[2:]) if info.st_size == cli.EXE.stat().st_size else value
        monkeypatch.setattr(cli, 'identity', identity)
    with pytest.raises(ValueError): cli._bind_saved_main('fresh', raw, sha, 'c'*64, cli.STAGE_PREFIX+'a'*64, 'b'*64)
    assert cli._SAVED_BOOTSTRAP is None


def test_saved_binding_ordinary_schema_cannot_cross_domains(saved_binding_context, tmp_path):
    raw, sha = saved_binding_context
    with pytest.raises(ValueError): cli._ordinary_bootstrap_context('fresh', cli.parse(raw))
    ordinary = cli.make_role_probe_context(tmp_path/'output')
    with pytest.raises(ValueError):
        cli._bind_saved_main('fresh', ordinary, sha256(ordinary).hexdigest(), 'c'*64, cli.STAGE_PREFIX+'a'*64, 'b'*64)


def test_saved_binding_owner_inputs_are_data_and_production_constructor_stays_closed(saved_binding_context, monkeypatch):
    store = _saved_unit_store(monkeypatch, saved_binding_context)
    role, raw, sha = 'fresh', store.raw, store.sha
    reservation = store.reserve_child(role); channel = _saved_unit_endpoint(role, sha, reader=True)
    inputs = cli.saved_owner_inputs(role, store, reservation, channel=channel)
    value = inputs.check()
    assert value['argv'] == _saved_argv(role, raw, sha, tree_sha=cli.digest(store.tree))
    assert value['reservation'] == cli.parse(cli.canonical(list(reservation))) and store.child_consumed
    assert value['native_owner_constructed'] is value['run_authority'] is value['F_launch_admitted'] is False
    assert value['descriptor_sha'] == sha256(cli.stage_descriptor(role)).hexdigest()
    with pytest.raises(ValueError, match='production stage launch remains disabled'):
        cli._construct_stage_owner(value['argv'], channel, 'saved_'+role)
    with pytest.raises(TypeError): cli.saved_owner_inputs(role, store, reservation, channel=channel, owner_factory=object)
    with pytest.raises(TypeError): cli.saved_owner_inputs(role, store, reservation, channel=channel, tree_sha='0'*64)
    with pytest.raises(ValueError): cli.saved_owner_inputs(role, store, reservation, channel=channel)
    import pickle
    with pytest.raises(TypeError): pickle.dumps(inputs)
    channel.close()
    with pytest.raises(ValueError): inputs.check()


def test_saved_binding_store_checks_same_role_tree_and_context_before_science(saved_binding_context, monkeypatch):
    tree = (('unit_output_tree', ()),); tree_sha = cli.digest(tree)
    raw, sha, args, main, held, channel = _saved_unit_bound(monkeypatch, saved_binding_context, tree_sha=tree_sha)
    read = cli.read
    monkeypatch.setattr(cli, '_role_tree', lambda root: tree)
    monkeypatch.setattr(cli, 'read', lambda path, **kw: raw if Path(path) == cli.OUTPUT/'context.json' else read(path, **kw))
    store = cli.RoleStore(raw, sha, tree_sha, 'fresh'); store.check()
    with pytest.raises(ValueError): cli.RoleStore(raw, sha, tree_sha, 'parent')
    with pytest.raises(ValueError): cli.RoleStore(raw, sha, '0'*64, 'fresh')
    monkeypatch.setattr(f, 'replay', lambda *a, **k: pytest.fail('missing binding entered scientific replay'))
    monkeypatch.setattr(cli, '_SAVED_BOOTSTRAP', None)
    with pytest.raises(ValueError): cli._role_reconstruct(store, 'fresh')


def test_saved_binding_open_seam_is_open_only_and_never_executes_science(saved_binding_context, monkeypatch):
    raw, sha, args, main = _saved_unit_main(monkeypatch, saved_binding_context)
    original = cli.read; calls = []
    monkeypatch.setattr(cli, 'read', lambda path, **kw: raw if Path(path) == cli.OUTPUT/'context.json' else original(path, **kw))
    class UnitStore:
        def __init__(self, image, digest, tree, role):
            assert (image, digest, tree, role) == (raw, sha, 'c'*64, 'fresh'); calls.append('store')
            cli._held_saved_bootstrap(role, image, digest, tree_sha=tree, require_channel=False)
        def check(self): calls.append('protected'); cli._held_saved_bootstrap('fresh', raw, sha, tree_sha='c'*64)
    monkeypatch.setattr(cli, 'RoleStore', UnitStore)
    channel = _saved_unit_endpoint('fresh', sha)
    def attach(name, nonce, digest, descriptor):
        assert (name, nonce, digest, descriptor) == (channel.name, channel.nonce, sha, cli.stage_descriptor('fresh'))
        calls.append('open_only'); return channel
    monkeypatch.setattr(cli.StageChannel, 'attach', attach)
    monkeypatch.setattr(cli.StageChannel, 'create', lambda *a, **k: pytest.fail('saved binding created transport'))
    monkeypatch.setattr(f, 'replay', lambda *a, **k: pytest.fail('binding ran science'))
    store, held, writer = cli._open_saved_role_inputs(args[4:])
    assert writer is channel and held is cli._SAVED_BOOTSTRAP and calls == ['store', 'open_only', 'protected']


def test_saved_binding_terminal_image_conflict_stays_unresolved(monkeypatch):
    owner, cache, state, sample = _console_unit(monkeypatch); cache.observe(owner, sample)
    state['image'] = 'c:\\other.exe'
    assert cache.classify(owner, {2}) is None and cache._entries[(2, 22)][1] == 'unresolved'
    state.update(image='c:\\windows\\system32\\conhost.exe', query_error=True)
    assert cache.classify(owner, {2}) is None


@pytest.mark.parametrize('role', ['parent', 'fresh', 'supervise'])
def test_saved_binding_public_cli_stays_disabled(role):
    import subprocess
    result = subprocess.run([str(cli.EXE), '-B', '-s', str(cli.ROOT/cli.NEW_SOURCES[1]),
        '--saved-entry', '--'+role], cwd=cli.ROOT, capture_output=True, timeout=5)
    assert result.returncode != 0 and b'F launch remains disabled' in result.stderr
    assert not cli.OUTPUT.exists()


@pytest.mark.parametrize('fault', ['role', 'descriptor', 'context', 'reader', 'header', 'creator', 'data'])
def test_saved_binding_owner_input_drift_never_constructs_native_owner(saved_binding_context, monkeypatch, fault):
    store = _saved_unit_store(monkeypatch, saved_binding_context); channel = _saved_unit_endpoint('fresh', store.sha, reader=True)
    inputs = cli.saved_owner_inputs('fresh', store, store.reserve_child('fresh'), channel=channel)
    if fault == 'role': object.__setattr__(inputs, 'raw', inputs.raw.replace(b'"role":"fresh"', b'"role":"parent"'))
    elif fault == 'descriptor': channel.descriptor = cli.stage_descriptor('parent')
    elif fault == 'context': channel.context_sha = '0'*64
    elif fault == 'reader': channel._reader = False
    elif fault == 'header': channel._header = b'bound'
    elif fault == 'creator': object.__setattr__(inputs, 'creator', (0, 0))
    else: object.__setattr__(store, 'raw', store.raw+b' ')
    with pytest.raises(ValueError): inputs.check()


@pytest.mark.parametrize('fault', ['writer_pair', 'foreign_reservation', 'equal_copy', 'wrong_channel', 'tree'])
def test_saved_binding_constructor_inputs_require_store_reservation(saved_binding_context, monkeypatch, fault):
    store = _saved_unit_store(monkeypatch, saved_binding_context)
    reservation = store.reserve_child('fresh'); channel = _saved_unit_endpoint('fresh', store.sha, reader=True)
    role = 'fresh'
    if fault == 'writer_pair': role = 'parent'
    elif fault == 'foreign_reservation': reservation = ('fresh', time.monotonic(), '0'*64, store.creator)
    elif fault == 'equal_copy': reservation = tuple(list(reservation))
    elif fault == 'wrong_channel': channel = _saved_unit_endpoint('parent', store.sha, reader=True)
    else: object.__setattr__(store, 'tree', (('different', ()),))
    with pytest.raises(ValueError): cli.saved_owner_inputs(role, store, reservation, channel=channel)
    assert not store.child_consumed


def test_saved_binding_existing_saved_capability_rejects_ordinary_store(saved_binding_context, tmp_path, monkeypatch):
    _saved_unit_bound(monkeypatch, saved_binding_context)
    ordinary = cli.make_role_probe_context(tmp_path/'output'); sha = sha256(ordinary).hexdigest()
    with pytest.raises(ValueError, match='saved bootstrap cannot enter an ordinary store'):
        cli.RoleStore(ordinary, sha, 'c'*64, 'fresh')
    store = object.__new__(cli.RoleStore); object.__setattr__(store, 'raw', ordinary)
    object.__setattr__(store, 'schema', cli.ROLE_PROBE_SCHEMA)
    with pytest.raises(ValueError, match='saved bootstrap cannot enter an ordinary store'): store.check()


@pytest.mark.parametrize('fault', ['entry_identity', 'entry_parent'])
def test_saved_binding_same_bytes_new_entry_identity_is_rejected(saved_binding_context, monkeypatch, fault):
    raw, sha, args, main, held, channel = _saved_unit_bound(monkeypatch, saved_binding_context)
    proof = held.proof()
    if fault == 'entry_identity':
        original = cli.identity; expected = tuple(proof['entry_identity'])
        monkeypatch.setattr(cli, 'identity', lambda info: (expected[0], expected[1]+1, *expected[2:])
            if original(info) == expected else original(info))
    else:
        original = cli.directories
        def directories(path):
            values = original(path)
            return (*values[:-1], (values[-1][0], values[-1][1], values[-1][2]+1)) if Path(path) == cli.ROOT/'experiments' else values
        monkeypatch.setattr(cli, 'directories', directories)
    with pytest.raises(ValueError, match='file/parent identity drift'): cli.execution_context('fresh', raw, sha)


@pytest.mark.parametrize('fault', ['expired', 'source', 'exe', 'environment'])
def test_saved_binding_current_bookend_rejects_before_reservation_consumption(saved_binding_context, monkeypatch, fault):
    from types import SimpleNamespace
    store = _saved_unit_store(monkeypatch, saved_binding_context)
    reservation = store.reserve_child('fresh'); channel = _saved_unit_endpoint('fresh', store.sha, reader=True)
    context = cli.parse(store.raw)
    if fault == 'expired': monkeypatch.setattr(cli, 'time', SimpleNamespace(monotonic=lambda: context['deadline']+1.))
    elif fault == 'source':
        changed = deepcopy(context['source_pins']); changed[cli.NEW_SOURCES[0]]['sha256'] = '0'*64
        monkeypatch.setattr(cli, 'source_pins', lambda: changed)
    elif fault == 'exe':
        original = cli.identity; expected = tuple(context['executable']['identity'])
        monkeypatch.setattr(cli, 'identity', lambda info: (expected[0], expected[1]+1, *expected[2:])
            if original(info) == expected else original(info))
    else: monkeypatch.setenv('OMP_NUM_THREADS', '2')
    with pytest.raises(ValueError): cli.saved_owner_inputs('fresh', store, reservation, channel=channel)
    assert store.child_consumed is False


def test_saved_binding_owner_inputs_expire_after_creation_without_resetting_start(saved_binding_context, monkeypatch):
    from types import SimpleNamespace
    store = _saved_unit_store(monkeypatch, saved_binding_context)
    reservation = store.reserve_child('fresh'); channel = _saved_unit_endpoint('fresh', store.sha, reader=True)
    inputs = cli.saved_owner_inputs('fresh', store, reservation, channel=channel)
    assert inputs.check()['reservation'][1] == reservation[1]
    monkeypatch.setattr(cli, 'time', SimpleNamespace(monotonic=lambda: cli.parse(store.raw)['deadline']+1.))
    with pytest.raises(ValueError): inputs.check()
    assert store.child_consumed is True


def test_saved_binding_new_allowed_environment_key_is_rejected(saved_binding_context, monkeypatch):
    raw, sha = saved_binding_context; value = cli.parse(raw)
    # Use an allowed key absent at binding time, including on conda-launched hosts.
    key = 'CONDA_DEFAULT_ENV'; monkeypatch.delenv(key, raising=False)
    value['environment'].pop(key, None)
    raw = cli.canonical(value); sha = sha256(raw).hexdigest()
    _saved_unit_bound(monkeypatch, (raw, sha))
    monkeypatch.setenv(key, 'late_environment_key')
    with pytest.raises(ValueError, match='actual environment drift'):
        cli._held_saved_bootstrap('fresh', raw, sha)


@pytest.mark.parametrize('fault', ['expired', 'source', 'exe', 'environment'])
def test_saved_binding_commit_bookend_rejects_drift_after_first_check(saved_binding_context, monkeypatch, fault):
    from types import SimpleNamespace
    store = _saved_unit_store(monkeypatch, saved_binding_context)
    reservation = store.reserve_child('fresh'); channel = _saved_unit_endpoint('fresh', store.sha, reader=True)
    original = cli._saved_owner_endpoint; context = cli.parse(store.raw)
    def endpoint(*args):
        original(*args)
        if fault == 'expired': monkeypatch.setattr(cli, 'time', SimpleNamespace(monotonic=lambda: context['deadline']+1.))
        elif fault == 'source':
            changed = deepcopy(context['source_pins']); changed[cli.NEW_SOURCES[0]]['sha256'] = '0'*64
            monkeypatch.setattr(cli, 'source_pins', lambda: changed)
        elif fault == 'exe':
            identity = cli.identity; expected = tuple(context['executable']['identity'])
            monkeypatch.setattr(cli, 'identity', lambda info: (expected[0], expected[1]+1, *expected[2:])
                if identity(info) == expected else identity(info))
        else: monkeypatch.setenv('OMP_NUM_THREADS', '2')
    monkeypatch.setattr(cli, '_saved_owner_endpoint', endpoint)
    with pytest.raises(ValueError): cli.saved_owner_inputs('fresh', store, reservation, channel=channel)
    assert store.child_consumed is False


@pytest.fixture
def saved_owner_case(saved_binding_context, monkeypatch):
    from types import SimpleNamespace
    raw, sha = saved_binding_context; cleanup = []
    parent = cli.StageChannel.create(sha, cli.stage_descriptor('parent'), name=cli.STAGE_PREFIX+'a'*64, nonce='b'*64)
    cleanup.append(parent.close)
    pid, creation = cli._own_process_identity(cli._stage_api())
    parent.bind_owner(SimpleNamespace(pid=pid, creation_filetime=creation, _live_owner=lambda: None, _released=False))
    upstream = cli.StageChannel.attach(parent.name, parent.nonce, sha, parent.descriptor); cleanup.append(upstream.close)
    child = cli.StageChannel.create(sha, cli.stage_descriptor('fresh')); cleanup.append(child.close)
    tree = (('unit_output_tree', ()),); tree_sha = cli.digest(tree)
    _saved_unit_main(monkeypatch, (raw, sha), role='parent', tree_sha=tree_sha)
    bootstrap = cli._bind_saved_main('parent', raw, sha, tree_sha, upstream.name, upstream.nonce)
    bootstrap.bind_channel(upstream)
    original = cli.read
    monkeypatch.setattr(cli, '_role_tree', lambda root: tree)
    monkeypatch.setattr(cli, 'read', lambda path, **kw: raw if Path(path) == cli.OUTPUT/'context.json' else original(path, **kw))
    store = cli.RoleStore(raw, sha, tree_sha, 'parent')
    upstream.enter('parent'); upstream.enter('fresh')
    inputs = cli.saved_owner_inputs('fresh', store, store.reserve_child('fresh'), channel=child)
    case = SimpleNamespace(inputs=inputs, store=store, child=child, upstream=upstream, parent=parent,
        calls=[], cleanup=cleanup, primary=ValueError('saved unit primary'),
        secondary={n:OSError(n+' secondary') for n in ('termination', 'quiesce', 'owner_close', 'channel_close')})
    try: yield case
    finally:
        for close in reversed(cleanup):
            try: close()
            except Exception: pass


def _construct_saved_unit(case, script='normal'):
    try:
        held = cli._construct_saved_stage_for_test(case.inputs, script=script)
        owner = held.owner
    except cli.SavedStageUnresolved as error:
        owner = error.owner
        if owner is not None:
            case.owner, case.calls = owner, owner.calls
            case.primary, case.secondary = owner._primary, owner._secondary
        raise
    case.owner, case.calls = owner, owner.calls
    case.primary, case.secondary = owner._primary, owner._secondary
    return held


def _unissued_saved_permit(inputs):
    import os
    from threading import get_ident
    permit = object.__new__(cli.SavedChildLaunchPermit)
    permit.inputs = inputs; permit.input_pin = cli.pin(inputs.raw); permit.issuer = None
    permit.creator = os.getpid(), get_ident()
    permit.binding_commit = cli.digest(permit._image())
    return permit


def test_saved_owner_normal_unit_transport_never_grants_physical_or_content_permission(saved_owner_case, monkeypatch):
    c = saved_owner_case; held = _construct_saved_unit(c)
    assert c.inputs.constructor_claimed and held.domain == 'saved' and held.real_owner is False
    assert held.created_at == c.inputs.reservation[1] and held.owner.kwargs['max_process_commit_bytes'] == 1024**3
    record = cli.watch_saved_stage(held)
    assert record['logic_path_completed'] is True
    assert record['stage_process_observed_successfully'] is record['job_quiet_confirmed'] is False
    assert record['owner_evidence'] == 'injected_unit_owner' and record['scope'] == 'saved_retained_child_stage_development_only'
    assert cli.saved_stage_process_record(held) == record
    monkeypatch.setattr(cli, 'read', lambda *a, **k: pytest.fail('unit owner read child content'))
    with pytest.raises(ValueError): cli.read_saved_after_quiet(c.store, 'worker/fresh/metrics.json', held)
    assert [cli.parse(cli._stage_decode(s, cli.STAGE_COMMIT))['phase'] for s in c.upstream._history] == [
        'parent', 'fresh', 'inner_quiesce', 'inner_terminal']
    print('SAVED_OWNER_UNIT '+cli.canonical(dict(record=record, physical_success_claimed=False,
        actual_saved_F_execution=False, F_launch_admitted=False)).decode())


@pytest.mark.parametrize('kind', ['none', 'dict', 'object', 'unissued'])
def test_saved_owner_public_issuer_stays_closed_before_claim_or_allocation(saved_owner_case, kind):
    c = saved_owner_case
    permit = {'none':None,'dict':{},'object':object(),'unissued':_unissued_saved_permit(c.inputs)}[kind]
    with pytest.raises(ValueError, match='issuer remains closed'): cli.construct_saved_stage(c.inputs, permit)
    assert not c.inputs.constructor_claimed and c.calls == [] and c.child._view is not None


def test_saved_owner_core_rejects_native_factory_and_foreign_unit_token(saved_owner_case):
    from src.staged_rts24_process_guard_v1 import OwnedChild
    c = saved_owner_case
    for factory in (OwnedChild, type('Subclass', (OwnedChild,), {})):
        with pytest.raises(TypeError): cli._construct_saved_stage_for_test(c.inputs, owner_factory=factory)
        with pytest.raises(ValueError): cli._construct_saved_stage(c.inputs, None, factory)
    with pytest.raises(ValueError): cli._construct_saved_stage_for_test(c.inputs, script=object())
    assert c.calls == [] and not c.inputs.constructor_claimed


@pytest.mark.parametrize('fault', ['none', 'before_commit', 'keyboard_interrupt', 'system_exit'])
def test_saved_owner_permit_and_input_state_commit_together_without_issuance(saved_owner_case, monkeypatch, fault):
    c = saved_owner_case; permit = _unissued_saved_permit(c.inputs)
    initial = c.inputs._attempt_state
    if fault != 'none':
        primary = {'before_commit': c.primary, 'keyboard_interrupt': KeyboardInterrupt(), 'system_exit': SystemExit()}[fault]
        original = cli.digest
        def digest(value):
            if type(value) is tuple and len(value) == 8 and value[-1] is True: raise primary
            return original(value)
        with monkeypatch.context() as scoped:
            scoped.setattr(cli, 'digest', digest)
            with pytest.raises(type(primary)) as error: cli._commit_saved_attempt(c.inputs, permit)
        assert error.value is primary and c.inputs._attempt_state is initial
        assert permit.used is c.inputs.constructor_claimed is False
        permit._binding_entry(c.inputs, used=False)
    else:
        cli._commit_saved_attempt(c.inputs, permit)
        assert permit.used is c.inputs.constructor_claimed is True
        assert c.inputs._attempt_state is not initial and c.inputs._attempt_state[2] is permit
        permit._binding_entry(c.inputs, used=True)
        with pytest.raises(ValueError): cli._commit_saved_attempt(c.inputs, permit)
    with pytest.raises(ValueError): c.inputs.claim_constructor()
    with pytest.raises(ValueError, match='issuer remains closed'): cli.construct_saved_stage(c.inputs, permit)
    assert c.calls == []


def test_saved_owner_constructor_claim_replay_does_not_close_existing_stage(saved_owner_case):
    c = saved_owner_case; held = _construct_saved_unit(c)
    with pytest.raises(ValueError, match='already claimed'):
        cli._construct_saved_stage_for_test(c.inputs)
    assert c.calls == ['init'] and c.child._view is not None
    held.close()


@pytest.mark.parametrize('fault', ['init_early', 'init_job', 'bind', 'startup', 'source', 'released', 'deadline'])
def test_saved_owner_partial_constructor_retains_original_objects_and_cleans_once(saved_owner_case, monkeypatch, fault):
    from types import SimpleNamespace
    c = saved_owner_case; injected = c.primary
    if fault == 'bind': monkeypatch.setattr(c.child, 'bind_owner', lambda *a: (_ for _ in ()).throw(injected))
    elif fault == 'startup':
        original = cli._saved_startup_image
        monkeypatch.setattr(cli, '_saved_startup_image', lambda *a: dict(original(*a), excess='x'*17000))
    elif fault in ('source', 'deadline'):
        original = cli._saved_constructor_bookend
        changed = deepcopy(cli.parse(c.store.raw)['source_pins']); changed[cli.NEW_SOURCES[0]]['sha256'] = '0'*64
        def bookend(inputs, value, *, owner=None):
            if owner is not None:
                if fault == 'source': monkeypatch.setattr(cli, 'source_pins', lambda: changed)
                else: monkeypatch.setattr(cli, 'time', SimpleNamespace(monotonic=lambda: c.inputs.reservation[1]+40.01))
            return original(inputs, value, owner=owner)
        monkeypatch.setattr(cli, '_saved_constructor_bookend', bookend)
    with pytest.raises(cli.SavedStageUnresolved) as error:
        _construct_saved_unit(c, fault if fault in cli._SAVED_UNIT_SCRIPTS else 'normal')
    e = error.value
    assert e.inputs is c.inputs and e.channel is c.child and c.inputs.constructor_claimed and c.child._view is None
    if fault in ('init_early', 'init_job'): assert e.primary is c.primary
    if fault == 'bind': assert e.primary is injected
    assert c.calls.count('kill') <= 1 and c.calls.count('close') <= 1 and 'release' not in c.calls
    import pickle
    with pytest.raises(TypeError): pickle.dumps(e)


def test_saved_owner_partial_constructor_preserves_all_cleanup_errors(saved_owner_case, monkeypatch):
    c = saved_owner_case; close = c.child.close; injected = c.secondary['channel_close']
    def channel_close(): close(); raise injected
    monkeypatch.setattr(c.child, 'close', channel_close)
    with pytest.raises(cli.SavedStageUnresolved) as error:
        _construct_saved_unit(c, 'layers')
    e = error.value
    expected = dict(c.secondary, channel_close=injected)
    assert e.primary is c.primary and {k:v for k,v in e.cleanup_objects} == expected
    assert c.calls == ['init','kill','quiesce','close'] and c.child._view is None


@pytest.mark.parametrize('fault', ['release', 'poll', 'sample', 'rss', 'commit', 'fast', 'nonzero', 'no_terminal',
    'descendant', 'quiesce', 'inventory', 'close', 'bookend', 'channel_close'])
def test_saved_owner_watch_failures_never_grant_success(saved_owner_case, monkeypatch, fault):
    c = saved_owner_case
    held = _construct_saved_unit(c, fault if fault in cli._SAVED_UNIT_SCRIPTS else 'normal')
    if fault == 'bookend':
        original = c.child.read_available
        def available():
            if 'quiesce' in c.calls: raise c.primary
            return original()
        monkeypatch.setattr(c.child, 'read_available', available)
    elif fault == 'channel_close':
        close = c.child.close
        def channel_close(): close(); raise c.secondary['channel_close']
        monkeypatch.setattr(c.child, 'close', channel_close)
    record = cli.watch_saved_stage(held)
    assert record['logic_path_completed'] is record['stage_process_observed_successfully'] is record['job_quiet_confirmed'] is False
    assert record['primary_stop_reason'] and c.calls.count('kill') <= 1 and c.calls.count('close') == 1
    assert c.child._view is None
    assert all(record[k] is False for k in cli.GATES)


@pytest.mark.parametrize('phase', ['inner_quiesce', 'inner_terminal'])
def test_saved_owner_relay_failure_preserves_cleanup(saved_owner_case, monkeypatch, phase):
    c = saved_owner_case; held = _construct_saved_unit(c)
    original = c.upstream.enter
    def enter(value):
        if value == phase: raise c.primary
        return original(value)
    monkeypatch.setattr(c.upstream, 'enter', enter)
    record = cli.watch_saved_stage(held)
    assert record['relay_error']['message'] == str(c.primary) and record['logic_path_completed'] is False
    assert c.calls.count('close') == 1 and 'quiesce' in c.calls


def test_saved_owner_entry_drift_retains_stage_without_foreign_cleanup(saved_owner_case):
    c = saved_owner_case; held = _construct_saved_unit(c)
    object.__setattr__(held.launch_binding, 'upstream', object())
    with pytest.raises(cli.SavedStageEntryUnresolved) as error: cli.watch_saved_stage(held)
    assert error.value.stage is held and error.value.owner is held.owner and error.value.channel is held.channel
    assert error.value.ownership_validated is False and c.calls == ['init']
    held.owner.close(); held.channel.close()


def test_saved_owner_clock_initialization_error_still_cleans_once(saved_owner_case, monkeypatch):
    c = saved_owner_case; held = _construct_saved_unit(c)
    original = cli.SavedStageBinding.prewatch; clock = cli.time
    class Clock:
        first = True
        def monotonic(self):
            if self.first: self.first = False; raise c.primary
            return clock.monotonic()
        def __getattr__(self, name): return getattr(clock, name)
    def prewatch(self, stage): original(self, stage); monkeypatch.setattr(cli, 'time', Clock())
    monkeypatch.setattr(cli.SavedStageBinding, 'prewatch', prewatch)
    with pytest.raises(cli.SavedStageUnresolved) as error: cli.watch_saved_stage(held)
    assert error.value.primary is c.primary and held._attempted and c.calls.count('kill') == c.calls.count('close') == 1


def test_saved_owner_core_active_path_performs_no_source_or_artifact_reads(saved_owner_case, monkeypatch):
    c = saved_owner_case; held = _construct_saved_unit(c)
    original = cli._watch_owned_stage
    def watch(*args, **kwargs):
        monkeypatch.setattr(cli, 'read', lambda *a, **k: pytest.fail('active saved loop did file I/O'))
        return original(*args, **kwargs)
    monkeypatch.setattr(cli, '_watch_owned_stage', watch)
    record = cli.watch_saved_stage(held)
    assert record['logic_path_completed'] is True and record['artifact_contents_read'] is False


def test_saved_owner_active_error_keeps_object_and_first_image(saved_owner_case, monkeypatch):
    c = saved_owner_case; held = _construct_saved_unit(c, 'sample')
    original = cli._stop_owned_job
    def stop(*args):
        c.primary.args = ('mutated after first image',)
        return original(*args)
    monkeypatch.setattr(cli, '_stop_owned_job', stop)
    record = cli.watch_saved_stage(held)
    monitor = next(row for row in held.launch_binding.errors if row[0] == 'monitor')
    assert monitor[1] is c.primary and cli.parse(monitor[2]) == record['monitor_error']
    assert record['monitor_error']['message'] == 'saved unit primary'
    assert str(c.primary) == 'mutated after first image'


def test_saved_owner_ordinary_saved_wrappers_reject_other_domain(saved_owner_case):
    c = saved_owner_case; held = _construct_saved_unit(c)
    with pytest.raises(ValueError): cli.watch_probe_stage(held)
    with pytest.raises(ValueError): cli._watch_stage(held)
    assert c.calls == ['init']; held.close()


@pytest.mark.parametrize('method', ['__init__', 'release', 'sample'])
def test_saved_owner_fixed_unit_rejects_changed_code_before_claim(saved_owner_case, monkeypatch, method):
    c = saved_owner_case
    def foreign(*args, **kwargs): raise AssertionError('foreign code executed')
    with monkeypatch.context() as scoped:
        scoped.setattr(getattr(cli._SavedUnitOwner, method), '__code__', foreign.__code__)
        with pytest.raises(ValueError, match='fixed unit method changed'):
            cli._construct_saved_stage_for_test(c.inputs)
    assert not c.inputs.constructor_claimed and c.child._view is not None


@pytest.mark.parametrize('method', ['release', 'sample', 'kernel', 'kernel_job_none'])
def test_saved_owner_fixed_unit_post_bind_method_drift_retains_without_calling_foreign(saved_owner_case, monkeypatch, method):
    from types import SimpleNamespace
    c = saved_owner_case; held = _construct_saved_unit(c, 'sample'); called = []
    with monkeypatch.context() as scoped:
        if method == 'kernel': scoped.setattr(held.owner._k, 'TerminateJobObject', lambda *a: called.append(True))
        elif method == 'kernel_job_none':
            scoped.setattr(held.owner, '_job', None)
            scoped.setattr(held.owner, '_k', SimpleNamespace(TerminateJobObject=lambda *a: called.append(True)))
        else: scoped.setattr(held.owner, method, lambda *a: called.append(True))
        with pytest.raises(cli.SavedStageEntryUnresolved) as error: cli.watch_saved_stage(held)
        assert error.value.stage is held and error.value.primary is not None
        assert c.calls == ['init'] and called == [] and c.child._view is not None
    held.close()


@pytest.mark.parametrize('drift', ['domain', 'binding', 'unit', 'late_method', 'late_unit'])
def test_saved_owner_all_entry_drift_paths_retain_without_foreign_cleanup(saved_owner_case, monkeypatch, drift):
    c = saved_owner_case; held = _construct_saved_unit(c)
    domain, binding, unit = held.domain, held.launch_binding, held.owner.unit
    replacement = cli._SavedUnitConstruction(c.inputs, 'sample')
    original = cli.SavedStageBinding.prewatch
    try:
        with monkeypatch.context() as scoped:
            if drift == 'domain': object.__setattr__(held, 'domain', 'ordinary')
            elif drift == 'binding': object.__setattr__(held, 'launch_binding', object())
            elif drift == 'unit': held.owner.unit = replacement
            else:
                def prewatch(self, stage):
                    original(self, stage)
                    if drift == 'late_unit': held.owner.unit = replacement
                    else: scoped.setattr(held.owner, 'close', lambda: pytest.fail('foreign cleanup called'))
                scoped.setattr(cli.SavedStageBinding, 'prewatch', prewatch)
            with pytest.raises(cli.SavedStageEntryUnresolved) as error: cli.watch_saved_stage(held)
            assert error.value.stage is held and error.value.entry_error is not None
            assert c.calls == ['init'] and not held._attempted and c.child._view is not None
    finally:
        object.__setattr__(held, 'domain', domain); object.__setattr__(held, 'launch_binding', binding)
        held.owner.unit = unit
        held.close()


@pytest.mark.parametrize('kind', ['keyboard', 'system'])
def test_saved_owner_interrupt_after_state_commit_leaves_both_ledgers_spent(saved_owner_case, kind):
    import sys
    c = saved_owner_case; permit = _unissued_saved_permit(c.inputs)
    primary = KeyboardInterrupt() if kind == 'keyboard' else SystemExit()
    def trace(frame, event, arg):
        if frame.f_code is cli._commit_saved_attempt.__code__ and event == 'return': raise primary
        return trace
    previous = sys.gettrace()
    try:
        sys.settrace(trace)
        with pytest.raises(type(primary)) as error: cli._commit_saved_attempt(c.inputs, permit)
    finally: sys.settrace(previous)
    assert error.value is primary and permit.used is c.inputs.constructor_claimed is True
    permit._binding_entry(c.inputs, used=True)
    assert c.calls == []


def test_saved_owner_active_deadline_uses_original_reservation_before_release(saved_owner_case, monkeypatch):
    from types import SimpleNamespace
    c = saved_owner_case; held = _construct_saved_unit(c)
    original = cli.SavedStageBinding.prewatch; clock = cli.time
    def prewatch(self, stage):
        original(self, stage)
        monkeypatch.setattr(cli, 'time', SimpleNamespace(monotonic=lambda: c.inputs.reservation[1]+40.001,
            get_clock_info=clock.get_clock_info, sleep=lambda seconds: pytest.fail('expired owner slept')))
    monkeypatch.setattr(cli.SavedStageBinding, 'prewatch', prewatch)
    record = cli.watch_saved_stage(held)
    assert record['primary_stop_reason'] == 'construction_or_total_budget'
    assert record['total_deadline'] == c.inputs.reservation[1]+50
    assert record['release_attempted'] is False and 'release' not in c.calls
    assert c.calls.count('kill') == c.calls.count('close') == 1


def test_saved_owner_oversized_terminal_encoding_retains_original_after_cleanup(saved_owner_case, monkeypatch):
    c = saved_owner_case; held = _construct_saved_unit(c); original = cli.canonical
    def canonical(value):
        raw = original(value)
        if type(value) is dict and value.get('schema') == 'staged_saved_F_saved_child_process_development_v1':
            return raw+b' '*(131073-len(raw))
        return raw
    monkeypatch.setattr(cli, 'canonical', canonical)
    with pytest.raises(cli.SavedStageUnresolved) as error: cli.watch_saved_stage(held)
    assert error.value.stage is held and error.value.owner is c.owner
    assert isinstance(error.value.primary, cli.StageChannelError)
    assert held.last_observation['record_encoding_error'] and held.last_image is None
    assert c.calls.count('close') == 1 and c.child._view is None
    with pytest.raises(ValueError): cli.saved_stage_process_record(held)


@pytest.fixture(scope='module')
def saved_expectation_base():
    from types import SimpleNamespace
    import highspy
    import pyomo.environ as pyo
    with pytest.MonkeyPatch.context() as patch:
        def denied(*args, **kwargs): pytest.fail('expectation preparation entered scientific/native/write execution')
        for module, name in ((pyo,'SolverFactory'), (highspy,'Highs'),
                (f.prefix.point.backend,'make_model'), (f.prefix.point.backend,'call_highs'),
                (f.prefix.point.backend,'snapshot_from_raw'), (f.prefix.point.numeric,'compile_problem'),
                (f.prefix.point.numeric,'import_snapshot'), (f.prefix,'replay_prefix'), (f,'replay'),
                (f.journal,'reopen'), (f.codec.EvidenceStore,'put'), (f.codec,'publish'), (f.journal,'publish')):
            patch.setattr(module,name,denied)
        for name in ('create_session','begin_step','commit_step','finish'): patch.setattr(f.journal,name,denied)
        source = cli.source_pins(); original_open = Path.open; reads = []
        def tracking(path, *args, **kwargs):
            if Path(path).is_relative_to(cli.P1): reads.append(Path(path).relative_to(cli.P1).as_posix())
            return original_open(path,*args,**kwargs)
        with pytest.MonkeyPatch.context() as counter:
            counter.setattr(Path,'open',tracking); gold = f.capture(source)
        assert len(reads) == 683; reads.clear()
        with pytest.MonkeyPatch.context() as counter:
            counter.setattr(Path,'open',tracking); expectation = cli.capture_saved_expectation(source)
        assert len(reads) == 53 and set(reads) == set(cli.EXPECTATION_FILES)
        assert expectation.image == gold.image
        print('EXPECTATION_READ_PROOF '+cli.canonical(dict(full_content_reads=683,selected_content_reads=53,
            metadata_passes=2,expectation_image_sha=sha256(expectation.image).hexdigest(),
            full_P1_content_verified=False,actual_saved_F_execution=False,F_launch_admitted=False)).decode())
        yield SimpleNamespace(source=source,gold=gold,expectation=expectation)


def _expectation_context(base, tmp_path):
    raw = cli.context_from_saved_expectation(base.expectation,tmp_path/'output',started=time.monotonic())
    return raw,sha256(raw).hexdigest()


def _corrupt_read(monkeypatch, name):
    original = Path.open; target = cli.P1/name
    class ChangedRead:
        def __init__(self,stream): self.stream=stream
        def __enter__(self): return self
        def __exit__(self,*args): return self.stream.__exit__(*args)
        def fileno(self): return self.stream.fileno()
        def read(self,*args):
            raw=self.stream.read(*args)
            return bytes([raw[0]^1])+raw[1:] if raw else raw
    def opened(path,*args,**kwargs):
        stream=original(path,*args,**kwargs)
        return ChangedRead(stream) if Path(path)==target else stream
    monkeypatch.setattr(Path,'open',opened)


def test_saved_expectation_projection_has_equal_image_and_distinct_semantics(saved_expectation_base):
    b=saved_expectation_base; value=cli.parse(b.expectation.raw)
    assert len(cli.EXPECTATION_FILES)==len(set(cli.EXPECTATION_FILES))==53
    assert b.expectation.image==b.gold.image and type(b.expectation) is not f.HeldInput
    assert value['full_P1_content_verified'] is value['F_launch_admitted'] is False
    assert not any(hasattr(b.expectation,n) for n in ('files','fixture','outer','inventory','replay','spawn','consume'))
    import pickle
    with pytest.raises(TypeError): pickle.dumps(b.expectation)


def test_saved_expectation_successor_context_is_rejected_by_all_legacy_entry_points(saved_expectation_base,tmp_path):
    raw,sha=_expectation_context(saved_expectation_base,tmp_path); value=cli.check_expectation_context(raw,sha)
    assert value['schema']==cli.EXPECTATION_CONTEXT_SCHEMA and value['full_P1_content_verified'] is False
    assert 'caller_core' not in value and 'caller_sha' not in value
    assert value['caller_expectation_sha']==sha256(saved_expectation_base.expectation.image).hexdigest()
    for call in (lambda:cli.validate_context(value),lambda:cli.check_context(raw,sha),
            lambda:cli.RoleStore(raw,sha,'0'*64),lambda:cli.execution_context('parent',raw,sha),
            lambda:cli.argv_for('parent',raw,sha,tree_sha='0'*64,channel_name=cli.STAGE_PREFIX+'a'*64,channel_nonce='b'*64)):
        with pytest.raises(ValueError): call()
    assert not (tmp_path/'output').exists() and not cli.OUTPUT.parent.exists()


@pytest.mark.parametrize('field',['raw','image','creator'])
def test_saved_expectation_immutable_projection_rejects_drift(saved_expectation_base,field):
    original=saved_expectation_base.expectation; changed=object.__new__(cli.SavedCallerExpectation)
    for name in ('raw','image','creator','commit'): object.__setattr__(changed,name,getattr(original,name))
    object.__setattr__(changed,field,(0,0) if field=='creator' else getattr(changed,field)+b' ')
    with pytest.raises(ValueError): changed.entry()


@pytest.mark.parametrize('field',['schema','full_P1_content_verified','caller_core','caller_expectation_sha','expectation_sha','deadline','executable_extra'])
def test_saved_expectation_context_closed_schema_rejects_drift(saved_expectation_base,tmp_path,field):
    raw,_=_expectation_context(saved_expectation_base,tmp_path); value=cli.parse(raw)
    if field=='caller_core': value[field]=value['caller_expectation_core']
    elif field=='full_P1_content_verified': value[field]=True
    elif field=='schema': value[field]=cli.SCHEMA
    elif field=='deadline': value[field]+=1.
    elif field=='executable_extra': value['executable']['extra']='unexpected'
    else: value[field]='not-a-sha'
    raw=cli.canonical(value)
    with pytest.raises(ValueError): cli.check_expectation_context(raw,sha256(raw).hexdigest())


def test_saved_expectation_selected_content_mismatch_is_rejected(saved_expectation_base,monkeypatch):
    _corrupt_read(monkeypatch,'points/point_0001/request.json')
    with pytest.raises(ValueError,match='pin changed'): cli.capture_saved_expectation(saved_expectation_base.source)


def test_saved_expectation_double_error_preserves_original_objects(saved_expectation_base,monkeypatch):
    _corrupt_read(monkeypatch,'points/point_0001/request.json')
    original=cli._expectation_metadata; secondary=OSError('metadata secondary'); calls=[]
    def metadata(*args):
        calls.append(1)
        if len(calls)==2: raise secondary
        return original(*args)
    monkeypatch.setattr(cli,'_expectation_metadata',metadata)
    with pytest.raises(cli.SavedExpectationUnresolved) as error: cli.capture_saved_expectation(saved_expectation_base.source)
    assert isinstance(error.value.primary,ValueError) and error.value.bookend_errors==( ('metadata',secondary), )


@pytest.mark.parametrize('stage',['G0','H3'])
def test_saved_expectation_unread_same_metadata_content_requires_full_verification(saved_expectation_base,tmp_path,monkeypatch,stage):
    b=saved_expectation_base; name=next(n for n in sorted(b.gold.files) if n not in cli.EXPECTATION_FILES)
    _corrupt_read(monkeypatch,name)
    expectation=cli.capture_saved_expectation(b.source)
    assert expectation.image==b.expectation.image and cli.parse(expectation.raw)['full_P1_content_verified'] is False
    raw=cli.context_from_saved_expectation(expectation,tmp_path/'output',started=time.monotonic())
    constructed=[]; monkeypatch.setattr(cli,'construct_saved_stage',lambda *a:constructed.append(True))
    with pytest.raises(ValueError): cli._probe_saved_expectation_input(expectation,raw,sha256(raw).hexdigest(),stage=stage)
    assert constructed==[] and not (tmp_path/'output').exists()


def test_saved_expectation_G0_G2_G3_and_H3_use_full_exact_local_inputs(saved_expectation_base,tmp_path,monkeypatch):
    b=saved_expectation_base; raw,sha=_expectation_context(b,tmp_path)
    original=Path.open; reads=[]
    def tracking(path,*args,**kwargs):
        if Path(path).is_relative_to(cli.P1): reads.append(Path(path))
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,'open',tracking)
    cap=cli._probe_saved_expectation_input(b.expectation,raw,sha,stage='G0'); held=cap._held
    assert len(reads)==683 and type(held) is f.HeldInput and held is not b.gold
    assert cap.entry() is cap and cap.real_verified is False and not hasattr(cap,'held')
    assert not hasattr(cli,'verify_saved_expectation_input') and not hasattr(cli,'bookend_verified_saved_input')
    for stage in ('G2','G3'):
        reads.clear(); observed=cli._probe_bookend_saved_input(cap,stage)
        assert len(reads)==683 and cap._held is held and observed['local_full_input_bookend'] is True
        assert observed['actual_saved_F_execution'] is observed['F_launch_admitted'] is False
    reads.clear(); final=cli._probe_saved_expectation_input(b.expectation,raw,sha,stage='H3')
    assert len(reads)==683 and final._held is not held and final._held.image==held.image
    with pytest.raises(ValueError): cli._probe_bookend_saved_input(final,'G2')
    assert cli.parse(raw)['full_P1_content_verified'] is False
    import pickle
    with pytest.raises(TypeError): pickle.dumps(cap)


@pytest.mark.parametrize('misuse',['expectation','held','dict','bad_stage'])
def test_saved_expectation_verified_gateway_rejects_untyped_or_wrong_phase(saved_expectation_base,misuse):
    b=saved_expectation_base
    argument={'expectation':b.expectation,'held':b.gold,'dict':{},'bad_stage':b.expectation}[misuse]
    with pytest.raises(ValueError): cli._probe_bookend_saved_input(argument,'G2')
    with pytest.raises(ValueError): cli._probe_saved_expectation_input(argument,b'{}','0'*64,stage='parent')
    with pytest.raises(ValueError): cli._construct_saved_stage_for_test(argument)


@pytest.mark.parametrize('drift',['held_identity','raw_snapshot','creator'])
def test_saved_expectation_verified_input_rejects_mutable_or_identity_drift(saved_expectation_base,tmp_path,drift):
    b=saved_expectation_base; raw,sha=_expectation_context(b,tmp_path)
    cap=cli._probe_saved_expectation_input(b.expectation,raw,sha,stage='G0')
    if drift=='held_identity': object.__setattr__(cap,'_held',b.gold)
    elif drift=='creator': object.__setattr__(cap,'creator',(0,0))
    else:
        name=next(iter(cap._held.inventory['raw'])); cap._held.inventory['raw'][name]=b'changed'
    with pytest.raises(ValueError): cli._probe_bookend_saved_input(cap,'G2')


def test_saved_expectation_verified_bookend_failure_is_sticky(saved_expectation_base,tmp_path,monkeypatch):
    b=saved_expectation_base; raw,sha=_expectation_context(b,tmp_path)
    cap=cli._probe_saved_expectation_input(b.expectation,raw,sha,stage='G0')
    name=next(n for n in sorted(b.gold.files) if n not in cli.EXPECTATION_FILES)
    with monkeypatch.context() as changed:
        _corrupt_read(changed,name)
        with pytest.raises(ValueError) as error: cli._probe_bookend_saved_input(cap,'G2')
    assert cap._state[2] is error.value
    with pytest.raises(ValueError,match='unresolved'): cli._probe_bookend_saved_input(cap,'G2')


@pytest.mark.parametrize('drift',['hold_function','hold_code','bookend_default'])
def test_saved_expectation_fixed_dependency_rejects_callable_drift(saved_expectation_base,monkeypatch,drift):
    calls=[]
    def foreign(*args,**kwargs): calls.append(True)
    if drift=='hold_function': monkeypatch.setattr(f,'hold',foreign)
    elif drift=='hold_code':
        def foreign_code(*args,**kwargs): raise AssertionError('foreign hold code executed')
        monkeypatch.setattr(f.hold,'__code__',foreign_code.__code__)
    else: monkeypatch.setitem(f.bookend.__kwdefaults__,'inventory',False)
    with pytest.raises(ValueError): cli.capture_saved_expectation(saved_expectation_base.source)
    assert calls==[]


def test_saved_expectation_metadata_rejects_extra_and_hardlinked_files(tmp_path):
    first=tmp_path/'a.json';first.write_bytes(b'{}'); expected={'a.json':cli.pin(b'{}')}
    before=cli._expectation_metadata(tmp_path,expected)
    assert before['files']['a.json']==cli.identity(first.stat())
    extra=tmp_path/'extra.json';extra.write_bytes(b'{}')
    with pytest.raises(ValueError,match='unexpected'): cli._expectation_metadata(tmp_path,expected)
    import os
    linked=tmp_path/'linked';linked.mkdir();os.link(first,linked/'a.json')
    with pytest.raises(ValueError,match='nonordinary'): cli._expectation_metadata(linked,expected)


@pytest.mark.parametrize('drift',['source','anchor','metadata_after'])
def test_saved_expectation_rejects_dependency_and_final_metadata_drift(saved_expectation_base,monkeypatch,drift):
    b=saved_expectation_base; expected=deepcopy(b.source)
    if drift=='source': expected[cli.NEW_SOURCES[0]]['sha256']='0'*64
    elif drift=='anchor':
        original=cli.read; anchor=cli.P1.parent/'p1_execution_review_01/postcheck_03.stdout.json'
        monkeypatch.setattr(cli,'read',lambda path,**kw:b'changed anchor' if Path(path)==anchor else original(path,**kw))
    else:
        original=cli._expectation_metadata; calls=[]
        def metadata(*args):
            value=original(*args);calls.append(1)
            if len(calls)==2:
                value=deepcopy(value);name=next(iter(value['files']));row=list(value['files'][name]);row[1]+=1;value['files'][name]=tuple(row)
            return value
        monkeypatch.setattr(cli,'_expectation_metadata',metadata)
    with pytest.raises(ValueError): cli.capture_saved_expectation(expected)


def test_saved_expectation_probe_bookend_keeps_primary_and_final_context_error(saved_expectation_base,tmp_path,monkeypatch):
    b=saved_expectation_base;raw,sha=_expectation_context(b,tmp_path)
    cap=cli._probe_saved_expectation_input(b.expectation,raw,sha,stage='G0')
    original=cli.check_expectation_context;calls=[];secondary=OSError('final context secondary')
    def context(*args):
        calls.append(1)
        if len(calls)==2: raise secondary
        return original(*args)
    monkeypatch.setattr(cli,'check_expectation_context',context)
    name=next(n for n in sorted(b.gold.files) if n not in cli.EXPECTATION_FILES)
    _corrupt_read(monkeypatch,name)
    with pytest.raises(cli.SavedExpectationUnresolved) as error: cli._probe_bookend_saved_input(cap,'G2')
    assert isinstance(error.value.primary,ValueError) and error.value.bookend_errors==( ('context_final',secondary), )
    assert cap._state[2] is error.value


@pytest.mark.parametrize('hold_fails',[True,False])
def test_saved_expectation_probe_hold_always_checks_final_context_before_capability(saved_expectation_base,tmp_path,monkeypatch,hold_fails):
    from types import SimpleNamespace
    b=saved_expectation_base;raw,sha=_expectation_context(b,tmp_path)
    original=cli.check_expectation_context;calls=[];secondary=OSError('hold final context secondary');constructed=[]
    def context(*args):
        calls.append(1)
        if len(calls)==2: raise secondary
        return original(*args)
    monkeypatch.setattr(cli,'check_expectation_context',context)
    def no_construction(*args): constructed.append(True); pytest.fail('capability allocated after final error')
    monkeypatch.setattr(cli,'object',SimpleNamespace(__new__=no_construction),raising=False)
    if hold_fails:
        name=next(n for n in sorted(b.gold.files) if n not in cli.EXPECTATION_FILES)
        _corrupt_read(monkeypatch,name)
    with pytest.raises(cli.SavedExpectationUnresolved) as error:
        cli._probe_saved_expectation_input(b.expectation,raw,sha,stage='G0')
    assert (isinstance(error.value.primary,ValueError) if hold_fails else error.value.primary is None)
    assert error.value.bookend_errors==( ('context_final',secondary), ) and constructed==[] and len(calls)==2


def test_saved_source_bytes_are_read_once_for_compile_and_freshly_per_call(saved_expectation_base,monkeypatch):
    import sys
    from collections import Counter
    b=saved_expectation_base; original=Path.open; reads=[]
    selected={cli.ROOT/name:name for name in b.source}
    def opened(path,*args,**kwargs):
        if Path(path) in selected: reads.append(selected[Path(path)])
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,'open',opened)
    loaded={name for name in b.source if name.startswith('src/') and name.endswith('.py')
        and sys.modules.get(name[:-3].replace('/','.').removesuffix('.__init__')) is not None}
    expected=Counter({name:2+int(name in loaded) for name in b.source})
    first=cli._expectation_adapter(b.source)
    assert Counter(reads)==expected and first[0] is f and len(first[1])==10
    reads.clear(); second=cli._expectation_adapter(b.source)
    assert Counter(reads)==expected and second is not first
    assert 'source_bytes' not in vars(cli)
    for row in (*first[1],*second[1]):
        assert len(row)==6 and callable(row[2]) and row[3] is row[2].__code__ and type(row[5]) is bytes
    print('SOURCE_RAW_REUSE '+cli.canonical(dict(selected_sources=49,loaded_sources=len(loaded),
        each_call_selected_source_reads=sum(expected.values()),duplicate_code_reads=0,
        source_raw_bytes=sum(p['bytes'] for p in b.source.values()),raw_cap_bytes=cli.EXPECTATION_SOURCE_RAW_CAP,
        independent_calls=2,actual_saved_F_execution=False)).decode())


def test_saved_source_bytes_wrong_pin_stops_before_compile(saved_expectation_base,monkeypatch):
    expected=deepcopy(saved_expectation_base.source); expected[cli.NEW_SOURCES[1]]['sha256']='0'*64
    compiled=[]
    def compile_forbidden(*args,**kwargs): compiled.append(True); pytest.fail('unbound source was compiled')
    monkeypatch.setattr(cli,'compile',compile_forbidden,raising=False)
    with pytest.raises(cli.SavedExpectationUnresolved) as error: cli._expectation_adapter(expected)
    assert isinstance(error.value.primary,ValueError) and 'initial source' in str(error.value.primary)
    assert error.value.bookend_errors[0][0]=='source_final' and compiled==[]


def test_saved_source_bytes_late_same_metadata_content_needs_full_final_guard(saved_expectation_base,monkeypatch):
    target=cli.ROOT/next(n for n in sorted(saved_expectation_base.source) if n.startswith('configs/'))
    original=Path.open; calls=[]; before=cli.identity(target.stat())
    class ChangedRead:
        def __init__(self,stream): self.stream=stream
        def __enter__(self): return self
        def __exit__(self,*args): return self.stream.__exit__(*args)
        def fileno(self): return self.stream.fileno()
        def read(self,*args):
            raw=self.stream.read(*args)
            return bytes([raw[0]^1])+raw[1:]
    def opened(path,*args,**kwargs):
        stream=original(path,*args,**kwargs)
        if Path(path)==target:
            calls.append(1)
            if len(calls)==2: return ChangedRead(stream)
        return stream
    monkeypatch.setattr(Path,'open',opened)
    with pytest.raises(cli.SavedExpectationUnresolved) as error: cli._expectation_adapter(saved_expectation_base.source)
    assert error.value.primary is None and len(error.value.bookend_errors)==1
    assert error.value.bookend_errors[0][0]=='source_final'
    assert 'saved fresh source changed' in str(error.value.bookend_errors[0][1])
    assert calls==[1,1] and cli.identity(target.stat())==before


@pytest.mark.parametrize('final_fails',[False,True])
def test_saved_source_bytes_initial_read_keeps_primary_and_independent_final(saved_expectation_base,monkeypatch,final_fails):
    target=cli.ROOT/sorted(saved_expectation_base.source)[0]
    original=cli.read; primary=OSError('initial source read'); secondary=OSError('independent source final'); calls=[]
    def read(path,**kwargs):
        if Path(path)==target:
            calls.append(1)
            if len(calls)==1: raise primary
            if final_fails: raise secondary
        return original(path,**kwargs)
    monkeypatch.setattr(cli,'read',read)
    with pytest.raises(cli.SavedExpectationUnresolved if final_fails else OSError) as error:
        cli._expectation_adapter(saved_expectation_base.source)
    if final_fails:
        assert error.value.primary is primary and error.value.bookend_errors==( ('source_final',secondary), )
        import pickle
        with pytest.raises(TypeError): pickle.dumps(error.value)
    else: assert error.value is primary
    assert calls==[1,1]


@pytest.mark.parametrize('final_fails',[False,True])
def test_saved_source_bytes_compile_keeps_primary_and_original_final_guard(saved_expectation_base,monkeypatch,final_fails):
    original=Path.open; target=cli.ROOT/cli.NEW_SOURCES[0]; calls=[]
    primary=OSError('code comparison compile'); secondary=OSError('resolved source final')
    def opened(path,*args,**kwargs):
        if Path(path)==target:
            calls.append(1)
            if len(calls)==2 and final_fails: raise secondary
        return original(path,*args,**kwargs)
    def compiler(*args,**kwargs): raise primary
    monkeypatch.setattr(Path,'open',opened); monkeypatch.setattr(cli,'compile',compiler,raising=False)
    with pytest.raises(cli.SavedExpectationUnresolved if final_fails else OSError) as error:
        cli._expectation_adapter(saved_expectation_base.source)
    if final_fails:
        assert error.value.primary is primary and error.value.bookend_errors==( ('source_final',secondary), )
    else: assert error.value is primary
    assert calls==([1,1] if final_fails else [1,1,1])


@pytest.mark.parametrize('invalid',['aggregate','boolean','negative'])
def test_saved_source_bytes_raw_budget_rejects_before_retaining_files(saved_expectation_base,monkeypatch,invalid):
    expected=deepcopy(saved_expectation_base.source); name=cli.NEW_SOURCES[1]
    expected[name]['bytes']={'aggregate':cli.EXPECTATION_SOURCE_RAW_CAP+1,'boolean':True,'negative':-1}[invalid]
    original=cli.read; reads=[]; finals=[]
    def read(path,**kwargs):
        if Path(path).relative_to(cli.ROOT).as_posix() in expected: reads.append(Path(path))
        return original(path,**kwargs)
    def final_source(): finals.append(True); return expected
    monkeypatch.setattr(cli,'read',read); monkeypatch.setattr(cli,'source_pins',final_source)
    with pytest.raises(ValueError,match='raw byte cap' if invalid=='aggregate' else 'source size'):
        cli._expectation_adapter(expected)
    assert reads==[] and finals==[True]


@pytest.fixture(scope='module')
def saved_successor_case():
    import importlib.util
    path=cli.ROOT/'results/tables/staged_rts24_saved_fresh_successor_data_v1_non_authoritative/checks_01/fixture_builder.py'
    spec=importlib.util.spec_from_file_location('independent_successor_fixture',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.build()


def _successor_json(value):
    return json.dumps(value,ensure_ascii=True,sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii')


def _successor_call(case):
    args=dict(case);context=args.pop('context_raw');request=args.pop('request_raw')
    return cli.validate_saved_successor_data(context,request,**args)


def test_saved_successor_positive_is_immutable_data_with_declared_time(saved_successor_case):
    c=saved_successor_case;result=_successor_call(c)
    assert type(result) is cli.SavedSuccessorDataCheck and result.entry() is result
    assert result.raw==c['context_raw'] and result.request_raw==c['request_raw'] and result.expectation_raw==c['expectation_raw']
    for name,raw in [('context_sha',c['context_raw']),('request_sha',c['request_raw']),('expectation_sha',c['expectation_raw'])]:
        assert getattr(result,name)==sha256(raw).hexdigest()
    status=json.loads(result.status_raw)
    assert status['data_only'] is status['declared_time_consistent'] is True
    assert all(value is False for name,value in status.items() if name not in ('schema','data_only','declared_time_consistent'))
    assert not hasattr(result,'context') and not any(type(v) in (dict,list) for v in vars(result).values())
    assert result.spec_pin==(18167,'b151876e286f24dca3571134e4506e55978f0fe1dee949b76005f3e3c24b2f90')
    import pickle
    with pytest.raises(TypeError):pickle.dumps(result)
    with pytest.raises(TypeError):cli.SavedSuccessorDataCheck()


_SUCCESSOR_FIELDS=json.loads((cli.ROOT/'results/tables/staged_rts24_saved_fresh_runtime_binding_v1_non_authoritative/checks_01/successor_context_spec_v3.json').read_bytes())['fields']
_SUCCESSOR_REQUEST_FIELDS=json.loads((cli.ROOT/'results/tables/staged_rts24_saved_fresh_runtime_binding_v1_non_authoritative/checks_01/request_contract_v2.json').read_bytes())['fields']


@pytest.mark.parametrize('field',_SUCCESSOR_FIELDS)
def test_saved_successor_requires_each_context_field(saved_successor_case,field):
    c=dict(saved_successor_case);value=json.loads(c['context_raw']);del value[field];c['context_raw']=_successor_json(value)
    with pytest.raises(ValueError):_successor_call(c)


@pytest.mark.parametrize('field',_SUCCESSOR_REQUEST_FIELDS)
def test_saved_successor_requires_each_request_field(saved_successor_case,field):
    c=dict(saved_successor_case);request=json.loads(c['request_raw']);del request[field];c['request_raw']=_successor_json(request)
    context=json.loads(c['context_raw']);context['request_sha']=sha256(c['request_raw']).hexdigest();c['context_raw']=_successor_json(context)
    with pytest.raises(ValueError):_successor_call(c)


@pytest.mark.parametrize('edge',['source','environment','input','executable','core','caller_sha','expectation_sha',
    'request_sha','runtime_profile','deadline_profile','start_deadline','broker_kernel'])
def test_saved_successor_independent_cross_field_constraints(saved_successor_case,edge):
    c=dict(saved_successor_case);context=json.loads(c['context_raw']);request=json.loads(c['request_raw'])
    if edge=='source':
        context['source_pins'][cli.NEW_SOURCES[1]]['sha256']='0'*64;request['source_sha']=sha256(_successor_json(context['source_pins'])).hexdigest()
    elif edge=='environment':
        context['environment']['PATH']='different';request['environment_sha']=sha256(_successor_json(context['environment'])).hexdigest()
    elif edge=='input':
        context['input_files'][next(iter(context['input_files']))]['sha256']='0'*64;request['input_pins_sha']=sha256(_successor_json(context['input_files'])).hexdigest()
    elif edge=='executable':
        context['executable']['pin']['sha256']='0'*64;request['executable_pin']=context['executable']['pin']
    elif edge=='core':
        context['caller_expectation_core']['historical_metrics']['summary']['remaining_debt']='different'
        context['caller_expectation_sha']=sha256(_successor_json(context['caller_expectation_core'])).hexdigest();request['caller_expectation_sha']=context['caller_expectation_sha']
    elif edge in ('caller_sha','expectation_sha'):
        name='caller_expectation_sha' if edge=='caller_sha' else edge;context[name]=request[name]='0'*64
    elif edge=='request_sha':context['request_sha']='0'*64
    elif edge in ('runtime_profile','deadline_profile'):
        name='runtime_binding_contract_sha' if edge=='runtime_profile' else 'deadline_profile_sha';context[name]=request[name]='0'*64
    elif edge=='start_deadline':context['invocation_started']+=1.;context['deadline']+=1.
    else:context['broker_identity']['pid']+=1
    c['request_raw']=_successor_json(request)
    if edge!='request_sha':context['request_sha']=sha256(c['request_raw']).hexdigest()
    c['context_raw']=_successor_json(context)
    with pytest.raises(ValueError):_successor_call(c)


@pytest.mark.parametrize('fault',['ctx_extra','req_extra','basis_extra','schema','mode','full_true','gate_true','limit_bool',
    'stage_change','source_bool','source_total','broker_bool','host_zero','exe_extra','exe_python','env_alias','env_value',
    'parent_identity','input_alias','inherited','nonce','expectation_extra','expectation_passes'])
def test_saved_successor_closed_types_and_domains(saved_successor_case,fault):
    c=dict(saved_successor_case);v=json.loads(c['context_raw']);r=json.loads(c['request_raw']);b=json.loads(c['host_basis_raw']);e=json.loads(c['expectation_raw'])
    if fault=='ctx_extra':v['ack_sha']='0'*64
    elif fault=='req_extra':r['context_sha']='0'*64
    elif fault=='basis_extra':b['authority']=True
    elif fault=='schema':v['schema']=cli.EXPECTATION_CONTEXT_SCHEMA
    elif fault=='mode':v['output_mode']='saved_P1_F_validation'
    elif fault=='full_true':v['full_P1_content_verified']=True
    elif fault=='gate_true':v['formal_result']=True
    elif fault=='limit_bool':v['limits']['files']=True
    elif fault=='stage_change':v['stage_seconds']['fresh']=41
    elif fault=='source_bool':b['source_pins'][cli.NEW_SOURCES[1]]['bytes']=True
    elif fault=='source_total':b['source_pins'][cli.NEW_SOURCES[1]]['bytes']=2097153
    elif fault=='broker_bool':b['broker_identity']['pid']=True
    elif fault=='host_zero':b['host_identity']['creation_filetime']=0
    elif fault=='exe_extra':b['executable']['extra']=True
    elif fault=='exe_python':b['executable']['python']='other runtime'
    elif fault=='env_alias':b['environment']['Path']='aliased'
    elif fault=='env_value':b['environment']['PYTHONHASHSEED']='random'
    elif fault=='parent_identity':b['output_parent_directories'][-1][2]=False
    elif fault=='input_alias':v['input_files']['../elsewhere']=v['input_files'].pop(next(iter(v['input_files'])))
    elif fault=='inherited':v['inherited_sources_pin']['bytes']+=1
    elif fault=='nonce':r['nonce']='not hex'
    elif fault=='expectation_extra':e['caller_core']=e['caller_expectation_core']
    else:e['metadata_passes']=True
    c.update(host_basis_raw=_successor_json(b),expectation_raw=_successor_json(e),request_raw=_successor_json(r))
    v['request_sha']=sha256(c['request_raw']).hexdigest();c['context_raw']=_successor_json(v)
    with pytest.raises(ValueError):_successor_call(c)


@pytest.mark.parametrize('now',[1000,True,999.0,1180.01,float('nan'),float('inf')])
def test_saved_successor_only_checks_declared_time_domain(saved_successor_case,now):
    c=dict(saved_successor_case,now=now)
    with pytest.raises(ValueError):_successor_call(c)


@pytest.mark.parametrize('field,cap',[('context_raw',2097152),('request_raw',32768),('expectation_raw',2097152),
    ('host_basis_raw',2097152),('anchor_raw',8388608),('runtime_contract_raw',65536),('deadline_contract_raw',65536),('request_contract_raw',65536)])
def test_saved_successor_caps_raw_before_decoding(saved_successor_case,field,cap):
    c=dict(saved_successor_case);c[field]=b' '*(cap+1)
    with pytest.raises(ValueError):_successor_call(c)


@pytest.mark.parametrize('kind',['duplicate','whitespace','depth','nonfinite','not_bytes','anchor','runtime_contract','deadline_contract','request_contract'])
def test_saved_successor_canonical_and_fixed_provenance(saved_successor_case,kind):
    c=dict(saved_successor_case)
    if kind=='duplicate':c['context_raw']=b'{"schema":"x",'+c['context_raw'][1:]
    elif kind=='whitespace':c['context_raw']+=b'\n'
    elif kind=='depth':c['context_raw']=b'['*257+b'0'+b']'*257
    elif kind=='nonfinite':c['context_raw']=b'{"x":NaN}'
    elif kind=='not_bytes':c['context_raw']=bytearray(c['context_raw'])
    else:
        field='anchor_raw' if kind=='anchor' else kind+'_raw';c[field]=c[field]+b' '
    with pytest.raises(ValueError):_successor_call(c)


@pytest.mark.parametrize('field',['_raw','_request_raw','_expectation_raw','basis_sha','anchor_sha','spec_pin','contract_shas','declared_now','commit'])
def test_saved_successor_result_all_accessors_recheck_commit(saved_successor_case,field):
    result=_successor_call(saved_successor_case)
    value=getattr(result,field)
    changed=value+b' ' if type(value) is bytes else ('changed' if type(value) is str else value+1 if type(value) is float else ())
    object.__setattr__(result,field,changed)
    for name in ('raw','request_raw','expectation_raw','context_sha','request_sha','expectation_sha','status_raw'):
        with pytest.raises(ValueError):getattr(result,name)


def test_saved_successor_version_is_frozen_and_io_is_not_observed(saved_successor_case,monkeypatch):
    from types import SimpleNamespace
    def denied(*args,**kwargs):raise AssertionError('static successor validator accessed live state')
    with monkeypatch.context() as scoped:
        scoped.setattr(cli,'sys',SimpleNamespace(version='changed live runtime'))
        scoped.setattr(cli,'time',SimpleNamespace(monotonic=denied))
        scoped.setattr(cli,'os',SimpleNamespace(stat=denied,lstat=denied,scandir=denied,open=denied))
        for name in ('read','directories','source_names','source_pins','_expectation_adapter'):scoped.setattr(cli,name,denied)
        for name in ('open','stat','lstat','resolve','exists','is_file','is_dir','read_bytes','read_text'):scoped.setattr(Path,name,denied)
        result=_successor_call(saved_successor_case)
    assert json.loads(result.status_raw)['actual_clock_verified'] is False
    c=dict(saved_successor_case);v=json.loads(c['context_raw']);b=json.loads(c['host_basis_raw'])
    v['executable']['python']=b['executable']['python']='changed live runtime'
    c.update(context_raw=_successor_json(v),host_basis_raw=_successor_json(b))
    with pytest.raises(ValueError):_successor_call(c)


def test_saved_successor_static_result_has_no_legacy_role_or_launch_domain(saved_successor_case):
    result=_successor_call(saved_successor_case);raw=result.raw;sha=sha256(raw).hexdigest();v=json.loads(raw)
    for operation in (lambda:cli.validate_context(v),lambda:cli.validate_expectation_context(v),
        lambda:cli.RoleStore(raw,sha,'0'*64),lambda:cli.argv_for('parent',raw,sha,tree_sha='0'*64,
            channel_name=cli.STAGE_PREFIX+'a'*64,channel_nonce='b'*64),
        lambda:cli.construct_saved_stage(result,None),lambda:cli._construct_saved_stage_for_test(result)):
        with pytest.raises((ValueError,TypeError)):operation()
    assert not cli.OUTPUT.parent.exists()
