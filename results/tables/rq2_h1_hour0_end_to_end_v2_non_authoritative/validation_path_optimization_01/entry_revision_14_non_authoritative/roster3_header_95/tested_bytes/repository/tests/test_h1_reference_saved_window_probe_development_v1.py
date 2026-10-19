"""Opt-in bounded replay of completed synthetic Rref files; no producer calls.

The input and numerical replay are genuine saved-chain bytes. Parent/lock
anchors are explicit probe objects, so this does not establish Parent4 or
whole-workflow acceptance.
"""
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
from threading import Lock, get_ident
from time import perf_counter
from types import SimpleNamespace as NS

import pytest


def test_completed_reference_bookend_replay_matches_independent_original(tmp_path):
    named = os.environ.get('H1_REFERENCE_SAVED_PROBE_PLAN')
    if named is None:
        pytest.skip('requires the separately bounded saved-input probe plan')
    plan_path = Path(named)
    plan_raw = plan_path.read_bytes()
    assert sha256(plan_raw).hexdigest() == os.environ['H1_REFERENCE_SAVED_PROBE_PLAN_SHA256']
    plan = json.loads(plan_raw)
    assert plan['status'] == 'DRAFT_NONAUTHORITATIVE' and plan['attempts'] == 1
    for name, pin in {**plan['sources_sha256'], **plan['saved_sha256']}.items():
        assert sha256(Path(name).read_bytes()).hexdigest() == pin, name

    fixture_path = Path(plan['fixture_module'])
    spec = importlib.util.spec_from_file_location('reference_saved_probe_fixture', fixture_path)
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    patch = fixture.complete_fixture(fixture.saved.synthetic_source)(Path(plan['fixture_base']))
    output = tmp_path / 'saved_reference_window_result.json'
    result = dict(status='DRAFT_NONAUTHORITATIVE', formal_result=False, resource_admission=False,
                  native_execution_authorized=False, whole_workflow_accepted=False,
                  live_Parent_credential_issued=False, explicit_synthetic_parent_anchors=True)
    started = perf_counter()
    engine = None
    locks = (Lock(), Lock())

    def save():
        with output.open('x', encoding='utf-8') as stream:
            json.dump(result, stream, indent=2)

    def trace(stage):
        print(json.dumps(dict(stage=stage, elapsed_seconds=perf_counter()-started)), flush=True)

    try:
        from experiments import h1_selector_input_snapshot_development_v2 as snapshot
        from experiments import h1_reference_sequence_window_development_v1 as window
        trace('reconstruct_saved_reference_context')
        declaration = json.loads(Path(plan['snapshot']).read_bytes())['declaration']
        (frame, disclosure, before, arguments, configuration, cap), _ = snapshot._build(declaration)
        sequence = snapshot.sequence
        root = Path(plan['reference_root'])
        terminal = sha256((root/'terminal.json').read_bytes()).hexdigest()
        request = json.loads((root/'terminal.json').read_bytes())['request_sha256']
        keywords = dict(expected_terminal_sha256=terminal, max_archive_bytes=cap,
                        run_configuration=configuration, **arguments)
        args = root, frame, disclosure, before
        trace('independent_original_inspect')
        original = sequence.inspect(*args, **keywords)
        signature = window._payload_signature((original['records'], original['replay']))
        result['context_and_independent_original_seconds'] = perf_counter()-started
        trace('original_complete')
        completion = NS(scientific_root=str(root), scientific_terminal_sha256=terminal,
                        scientific_request_sha256=request, max_archive_bytes=cap)
        owner = NS(_raw=json.dumps(dict(declaration=dict(reference=dict(root=str(root),
            terminal_sha256=terminal, request_sha256=request, max_archive_bytes=cap)))).encode())
        reference = NS(_issued=completion)
        row = dict(kind='validate', owner=owner, creator=(os.getpid(),get_ident()),
                   parents=((owner,), (reference,None,None,None,None,completion)),
                   failure=None, frames=[dict(owner=owner)])
        for lock in locks:
            assert lock.acquire(blocking=False)

        def check_owner(observed, borrowed_owner=None, *, borrowed=False):
            assert observed is row and all(lock.locked() for lock in locks)
            assert row['creator'] == (os.getpid(),get_ident())
            assert borrowed_owner is (owner if borrowed else None)

        build_globals = {'__builtins__': __builtins__, 'args': args, 'keywords': keywords}
        exec('def build():\n return inspect(*args,**keywords)\n', build_globals)
        build = build_globals['build']
        rebuild_globals = {'__builtins__': __builtins__, 'build': build}
        exec('def rebuild():\n return build()\n', rebuild_globals)
        rebuild = rebuild_globals['rebuild']
        scope_globals = {'__builtins__': __builtins__}
        exec('def scope():\n return finish()\n', scope_globals)
        scope = scope_globals['scope']
        trace('bind_canonical_reference_window')
        bind_start = perf_counter()
        engine = window._bind(row, NS(), check_owner, sequence,
            caller_code=build.__code__, caller_globals=build_globals,
            rebuild_code=rebuild.__code__, rebuild_globals=rebuild_globals,
            scope_code=scope.__code__, scope_globals=scope_globals)
        build_globals['inspect'] = engine['inspect']
        scope_globals['finish'] = engine['finish']
        # These probe callers are fixed before binding; the runtime engine also
        # requires the exact supplied code/globals at every dispatch.
        values = []
        for index in range(16):
            value = rebuild()
            assert set(value) == {'request_sha256','replay'}
            assert value['request_sha256'] == request
            assert type(value['replay']) is type(original['replay'])
            assert window._payload_signature((original['records'],value['replay'])) == signature
            assert all(value is not previous for previous in values)
            values.append(value)
            if index == 0: trace('first_reference_result')
        receipt = scope()
        assert receipt['canonical_reference_sequence'] is True
        assert receipt['logical_reference_inspects'] == 16
        assert receipt['original_reference_inspects'] == 2
        assert receipt['borrowed_reference_results'] == 15
        assert receipt['scientific_payload_compatible'] and not receipt['per_call_fresh_at_return']
        trace('window_complete')
        engine['close']()
        assert engine['generator'].gi_frame is None
        result['window_seconds_including_bind_and_close'] = perf_counter()-bind_start
        receipt['cache_cleared'] = True
        result.update(receipt=receipt, independent_payload_signature=signature[0],
                      saved_files_unchanged=len(plan['saved_sha256']),
                      Jobs=0, new_producer_calls=0, real_native_calls=0)
        for name, pin in {**plan['sources_sha256'], **plan['saved_sha256']}.items():
            assert sha256(Path(name).read_bytes()).hexdigest() == pin, name
        result['completed'] = True
    except BaseException as error:
        result.update(completed=False, error=repr(error))
        raise
    finally:
        if engine is not None:
            engine['close']()
            result['cache_cleared'] = engine['generator'].gi_frame is None
        for lock in reversed(locks):
            if lock.locked(): lock.release()
        result['explicit_probe_locks_released'] = not any(lock.locked() for lock in locks)
        patch.undo()
        result['elapsed_seconds'] = perf_counter()-started
        save()
