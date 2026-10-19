"""Find the first concrete project-view drift without starting bootstrap or a Job."""
from dataclasses import fields
import json
import threading
from time import perf_counter

from tests import test_h1_registry_validation_fresh_n0_development_v1 as cold
from tests.test_h1_registry_validation_fresh_n0_development_v1 import (
    example, setup, numerical, environment, synthetic_reports, supplied, no_solver,
    saved, retained, prepared)

pytestmark = cold.source_fixture.pytestmark


def test_definition_dispatch_checkpoints_without_job(prepared, tmp_path, monkeypatch):
    s, prior, _, final = prepared
    assert not final
    monkeypatch.setattr(cold.source_fixture.m.symbolic, 'inspect', cold.ORIGINAL_SYMBOLIC_INSPECT)
    resolver = [None]

    def open_manifest():
        if resolver[0] is None:
            raise ValueError('successor symbolic resolver not prepared')
        return resolver[0]

    monkeypatch.setattr(cold.source_fixture.m.owned.binding, 'open_manifest', open_manifest)
    start = perf_counter()
    from experiments import h1_bootstrap_integration_development_v4 as m
    verifier = m.historical_verifier
    captured = dict(zip(verifier._runtime_check.__code__.co_freevars,
        (cell.cell_contents for cell in verifier._runtime_check.__closure__)))
    definition_baseline = captured['baseline']
    definition = captured['definition_view']
    captured.update(zip(definition.__code__.co_freevars,
        (cell.cell_contents for cell in definition.__closure__)))
    with captured['denial']():
        baseline = captured['dispatch'](captured['module'])
    checkpoints = []

    def save(name, value):
        with (tmp_path / name).open('x', encoding='utf-8') as stream:
            json.dump(value, stream, indent=2,
                default=lambda v: {'bytes_hex': v.hex()} if type(v) is bytes else repr(v))

    save('definition_baseline.json', definition_baseline)
    save('runtime_baseline.json', baseline)

    def checkpoint(stage):
        verifier._runtime_check(True)
        with captured['denial']():
            observed = captured['dispatch'](captured['module'])
        diff = {}
        for name, index, key in (('bindings', 0, lambda row: row[0]),
                ('files', 1, lambda row: row[:2])):
            before = {key(row): row for row in baseline[index]}
            after = {key(row): row for row in observed[index]}
            changes = [dict(key=k, before=before.get(k), after=after.get(k))
                for k in sorted(set(before) | set(after)) if before.get(k) != after.get(k)]
            diff[name] = changes
        row = dict(stage=stage, seconds=perf_counter() - start, equal=observed == baseline,
            static_definition_guard_passed=True,
            changed_binding_keys=[v['key'] for v in diff['bindings']],
            changed_file_keys=[v['key'] for v in diff['files']])
        checkpoints.append(row)
        save(stage + '_diff.json', diff)
        print(json.dumps(row), flush=True)

    checkpoint('successor_imported')
    config = m.RunConfiguration(**{f.name: getattr(prior.run_configuration, f.name)
        for f in fields(m.RunConfiguration)})
    registry = m.RegistryBinding(**{f.name: getattr(prior.registry_binding, f.name)
        for f in fields(m.RegistryBinding)})
    values = {f.name: getattr(prior, f.name) for f in fields(m.BootstrapDeclaration)}
    profile = config.declared_profile()
    snapshot = m.symbolic.build(m.symbolic.StaticProfile(**profile))
    path = tmp_path / 'successor_symbolic_profile.json'
    path.write_bytes(snapshot.raw)
    pin = m.sha256(snapshot.raw).hexdigest()
    assert m.symbolic.inspect(path, expected_sha256=pin).data()['declared_static_profile'] == profile
    resolver[0] = m.symbolic.proof._resolver(snapshot._proof_raw)
    values.update(run_configuration=config, registry_binding=registry,
        symbolic_path=str(path), symbolic_sha256=pin)
    declaration = m.BootstrapDeclaration(**values)
    checkpoint('profile_prepared')
    monkeypatch.setattr(m.BootstrapOwner, '_continue_bootstrap', m.BootstrapOwner._continue_registered_development)
    checkpoint('continuation_installed')
    owner = m.BootstrapOwner(declaration, create=True, create_study=True,
        retain_global_head=s.retain, retain_bootstrap_head=s.retain)
    try:
        checkpoint('owner_opened')
        opener = dict(zip(m._run_registry_operation.__code__.co_freevars,
            (cell.cell_contents for cell in m._run_registry_operation.__closure__)))['open_scope']
        owner._operation.acquire()
        owner._operation_nonce = object()
        errors = []

        def foreign():
            try:
                opener(owner)
            except ValueError as error:
                errors.append(str(error))

        try:
            thread = threading.Thread(target=foreign)
            thread.start()
            thread.join(timeout=5)
            assert not thread.is_alive() and errors
        finally:
            owner._operation_nonce = None
            owner._operation.release()
        checkpoint('foreign_opener_rejected')
    finally:
        owner.close()
    checkpoint('owner_closed')
    assert [row['stage'] for row in checkpoints if not row['equal']] == ['owner_opened', 'foreign_opener_rejected']
    assert all(not row['changed_file_keys'] for row in checkpoints)
    assert all(all(tuple(key) == ('src.rq2_joint_deliverability_boundary_v1.episode_store', '_REGISTRY')
        for key in row['changed_binding_keys']) for row in checkpoints)
    save('dispatch_diagnostic.json', dict(checkpoints=checkpoints,
        differences_found=any(not row['equal'] for row in checkpoints),
        differences_are_expected_runtime_membership=True,static_definition_guard_passed_all=True,
        bootstrap_called=False, synthetic_jobs=0, native_calls=0, formal_result=False,
        full_hour0_chain_passed=False))
