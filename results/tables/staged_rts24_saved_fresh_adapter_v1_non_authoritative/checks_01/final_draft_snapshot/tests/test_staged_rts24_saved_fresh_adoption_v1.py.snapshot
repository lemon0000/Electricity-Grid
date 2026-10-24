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
