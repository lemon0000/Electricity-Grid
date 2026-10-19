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


def test_shared_completed_reference_replay_matches_independent_original(tmp_path):
    named = os.environ.get('H1_SHARED_REFERENCE_SAVED_PROBE_PLAN')
    if named is None:
        pytest.skip('requires the separately bounded saved-input probe plan')
    plan_path = Path(named)
    plan_raw = plan_path.read_bytes()
    assert sha256(plan_raw).hexdigest() == os.environ['H1_SHARED_REFERENCE_SAVED_PROBE_PLAN_SHA256']
    plan = json.loads(plan_raw)
    assert plan['status'] == 'DRAFT_NONAUTHORITATIVE' and plan['attempts'] == 1
    for name, pin in {**plan['sources_sha256'], **plan['saved_sha256']}.items():
        assert sha256(Path(name).read_bytes()).hexdigest() == pin, name

    fixture_path = Path(plan['fixture_module'])
    spec = importlib.util.spec_from_file_location('reference_saved_probe_fixture', fixture_path)
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    patch = fixture.complete_fixture(fixture.saved.synthetic_source)(Path(plan['fixture_base']))
    output = tmp_path / 'shared_saved_reference_window_result.json'
    result = dict(status='DRAFT_NONAUTHORITATIVE', formal_result=False, resource_admission=False,
                  native_execution_authorized=False, whole_workflow_accepted=False,
                  live_Parent_credential_issued=False, explicit_synthetic_parent_anchors=True)
    started = perf_counter()
    engine = None
    locks = tuple(Lock() for _ in range(4))

    def save():
        with output.open('x', encoding='utf-8') as stream:
            json.dump(result, stream, indent=2)

    def trace(stage):
        print(json.dumps(dict(stage=stage, elapsed_seconds=perf_counter()-started)), flush=True)

    try:
        from experiments import h1_selector_input_snapshot_development_v2 as snapshot
        from experiments import h1_reference_validation_window_development_v1 as window
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
        class ProbeParent:pass
        class ProbeCompletion:pass
        def completion_bytes(value):return json.dumps(vars(value),sort_keys=True).encode()
        parent=NS(SCHEMA='h1_selector_parent_controller_development_v4',Parent=ProbeParent,
                  ParentCompletion=ProbeCompletion,_CHECK=lambda:None,_completion_bytes=completion_bytes)
        owners=[]
        for index,lock in enumerate(locks):
            obj=ProbeParent();obj.root=tmp_path/('probe_parent_'+str(index));obj.worker_root=obj.root/'worker'
            obj._own='explicit_synthetic_probe_anchor';obj._pid,obj._thread=os.getpid(),get_ident()
            obj._state='complete';obj._guard=lock;obj._reference_held=bool(index)
            completion=ProbeCompletion()
            completion.root=str(obj.root);completion.scientific_root=str(root)
            completion.scientific_terminal_sha256=terminal;completion.scientific_request_sha256=request
            completion.max_archive_bytes=cap
            obj._issued=completion;obj._issued_bytes=completion_bytes(completion)
            obj._reference_owner=owners[0] if index else None
            obj._reference_completion=owners[0]._issued if index else None
            obj._raw=json.dumps(dict(declaration=dict(role='actual' if index else 'reference',
                source_binding=declaration['source_binding'],reference=None if not index else dict(root=str(root),
                terminal_sha256=terminal,request_sha256=request,max_archive_bytes=cap)))).encode()
            assert lock.acquire(blocking=False)
            owners.append(obj)
        row=dict(window=dict(kind='bundle'),creator=(os.getpid(),get_ident()),failure=None,frames=[],
            parents=tuple((obj,obj._issued,obj._raw,obj._issued_bytes,obj._guard) for obj in owners))
        def check_owner(observed,borrowed_owner=None,*,borrowed=False):
            assert observed is row and all(lock.locked() for lock in locks)
            assert row['creator']==(os.getpid(),get_ident())
            if borrowed:assert any(borrowed_owner is obj for obj in owners[1:])
            else:assert borrowed_owner is None

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
        engine = window._bind_parent_validation_window(row, parent, check_owner, sequence,
            caller_code=build.__code__, caller_globals=build_globals,
            rebuild_code=rebuild.__code__, rebuild_globals=rebuild_globals,
            scope_code=scope.__code__, scope_globals=scope_globals)
        build_globals['inspect'] = engine['inspect']
        scope_globals['finish'] = engine['finish']
        # These probe callers are fixed before binding; the runtime engine also
        # requires the exact supplied code/globals at every dispatch.
        values = []
        for owner in owners[1:]:
            row['frames'].append(dict(owner=owner))
            try:
                for index in range(16):
                    value=rebuild()
                    assert set(value)=={'request_sha256','replay'} and value['request_sha256']==request
                    assert type(value['replay']) is type(original['replay'])
                    assert window._payload_signature((original['records'],value['replay']))==signature
                    assert all(value is not previous for previous in values)
                    values.append(value)
            finally:row['frames'].pop()
        trace('three_Actual_reference_sites_complete')
        receipt = scope()
        assert receipt['canonical_reference_sequence'] is True
        assert receipt['logical_reference_inspects'] == 48
        assert receipt['original_reference_inspects'] == 2
        assert receipt['borrowed_reference_results'] == 47
        assert [site['logical_reference_inspects'] for site in receipt['parent_sites']]==[16]*3
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
