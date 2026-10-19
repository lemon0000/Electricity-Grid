"""Bounded ordinary fault/oracle checks; heavy project imports stay in cases."""
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
import sys
import tempfile
from time import perf_counter
from types import ModuleType
import unittest
from unittest.mock import patch

from performance import static_input_capability_v1 as transport


REPO = Path('D:/CUHKSZ/Research Project/electricity-grid')
UNIT_EVIDENCE = {}
SOURCE_NAMES = ('experiments/h1_origin_grid_step_development_v1.py',
    'experiments/h1_outage_registry_development_v1.py',
    'experiments/h1_outage_source_development_v1.py',
    'src/rq2_joint_deliverability_boundary_v1/source_window.py',
    'src/rq2_joint_deliverability_boundary_v1/continuous_grid_normal.py',
    'experiments/h1_repair_cap_normalization_operation_development_v2.py')


def modules():
    from experiments import h1_origin_grid_step_development_v1 as physical
    from experiments import h1_repair_cap_normalization_operation_development_v2 as normalizer
    return physical, normalizer


def lease():
    expected = {REPO/name: sha256((REPO/name).read_bytes()).hexdigest() for name in SOURCE_NAMES}
    return transport.CapabilityByteLease(expected, transport.core.scientific_inputs(REPO),
                                        root=REPO, code_root=Path('D:/'))


class CapabilityTests(unittest.TestCase):
    def setUp(self):
        self.original_read = Path.read_bytes

    def tearDown(self):
        self.assertIs(Path.read_bytes, self.original_read)

    def test_one_borrow_release_and_frozen_detached_closed_receipt(self):
        owner = lease()
        with owner:
            cap = owner.borrow_static_inputs()
            payload = cap.view()
            self.assertEqual(len(payload[2]), 2)
            self.assertEqual(json.loads(payload[3])['session'], owner._session)
            cap.release()
        closed = owner.closed_receipt()
        self.assertTrue(closed['all_handles_closed'])
        self.assertEqual(closed['borrow_releases'], 1)
        self.assertEqual(closed['borrow_forced_revokes'], 0)
        owner._bound_borrow[:] = [True, None, None, False, 999, 7, RuntimeError('late'), 9]
        owner._borrow_entry_identity = ('late',)
        owner._creator = (0, 0)
        self.assertEqual(owner.closed_receipt(), closed)
        closed['borrow_binding']['session'] = 'caller mutation'
        self.assertNotEqual(owner.closed_receipt()['borrow_binding']['session'], 'caller mutation')

    def test_transient_view_failure_poison_survives_restore_and_forces_revoke(self):
        owner = lease()
        with self.assertRaisesRegex(ValueError, 'borrow identity changed'):
            with owner:
                cap = owner.borrow_static_inputs()
                raw = cap._payload
                cap._payload = object()
                with self.assertRaises(ValueError): cap.view()
                cap._payload = raw
                with self.assertRaisesRegex(ValueError, 'poisoned'): cap.release()
        closed = owner.closed_receipt()
        self.assertIn('borrow identity changed', closed['borrow_first_failure'])
        self.assertEqual(closed['borrow_releases'], 0)
        self.assertEqual(closed['borrow_forced_revokes'], 1)
        self.assertFalse(closed['borrow_active'])
        self.assertTrue(closed['all_handles_closed'])

    def test_working_ledger_control_and_session_failures_are_sticky(self):
        for name in ('_borrow', '_control', '_session', '_borrow_binding'):
            with self.subTest(name=name):
                owner = lease()
                with self.assertRaises(ValueError):
                    with owner:
                        cap = owner.borrow_static_inputs()
                        before = getattr(owner, name)
                        setattr(owner, name, object())
                        try:
                            with self.assertRaises(ValueError): cap.view()
                        finally: setattr(owner, name, before)
                        with self.assertRaises(ValueError): cap.release()
                closed = owner.closed_receipt()
                self.assertIsNotNone(closed['borrow_first_failure'])
                self.assertTrue(closed['all_handles_closed'])

    def test_duplicate_issue_is_sticky_and_not_a_second_release(self):
        owner = lease()
        with self.assertRaisesRegex(ValueError, 'one borrow'):
            with owner:
                cap = owner.borrow_static_inputs()
                with self.assertRaisesRegex(ValueError, 'one borrow'): owner.borrow_static_inputs()
                with self.assertRaises(ValueError): cap.release()
        self.assertEqual(owner.closed_receipt()['borrow_forced_revokes'], 1)

    def test_foreign_thread_is_refused_without_poisoning_creator(self):
        owner = lease()
        with owner:
            cap = owner.borrow_static_inputs()
            with ThreadPoolExecutor(max_workers=1) as pool:
                with self.assertRaisesRegex(ValueError, 'creating process/thread'):
                    pool.submit(cap.view).result()
            cap.view()
            cap.release()
        self.assertIsNone(owner.closed_receipt()['borrow_first_failure'])

    def test_body_exception_remains_primary_and_cleanup_is_real(self):
        owner = lease()
        primary = RuntimeError('body is primary')
        with self.assertRaises(RuntimeError) as caught:
            with owner:
                owner.borrow_static_inputs()
                raise primary
        self.assertIs(caught.exception, primary)
        closed = owner.closed_receipt()
        self.assertTrue(closed['all_handles_closed'])
        self.assertEqual(closed['borrow_forced_revokes'], 1)
        self.assertIsNotNone(closed['borrow_first_failure'])

    def test_inactive_or_closed_owner_cannot_issue(self):
        owner = lease()
        with self.assertRaises(ValueError): owner.borrow_static_inputs()
        owner = lease()
        with owner: pass
        before = owner.closed_receipt()
        with self.assertRaises(ValueError): owner.borrow_static_inputs()
        self.assertEqual(before, owner.closed_receipt())

    def test_core_scientific_declaration_callable_and_constant_are_fixed(self):
        for name, replacement in (('scientific_inputs', lambda _: {}), ('SCIENTIFIC_INPUTS', ())):
            owner = lease()
            with self.assertRaises(ValueError):
                with owner:
                    cap = owner.borrow_static_inputs()
                    with patch.object(transport.core, name, replacement):
                        with self.assertRaises(ValueError): cap.view()
                    with self.assertRaises(ValueError): cap.release()
            self.assertTrue(owner.closed_receipt()['all_handles_closed'])


class RepairIdentityTests(unittest.TestCase):
    def setUp(self):
        self.physical, self.normalizer = modules()
        self.original = self.physical.repair_mechanism_identity
        self.original_read = Path.read_bytes

    def tearDown(self):
        self.assertIs(self.physical.repair_mechanism_identity, self.original)
        self.assertIs(Path.read_bytes, self.original_read)

    def exercise(self, count=3, profile=False):
        owner = lease()
        counts = {'original': 0, 'pin': 0, 'digest': 0}
        physical, normalizer = self.physical, self.normalizer
        targets = {self.original.__code__: 'original', physical.registry._pin.__code__: 'pin',
                   physical._digest.__code__: 'digest'}
        previous = sys.getprofile()
        self.assertIsNone(previous)
        def observer(frame, event, arg):
            if event == 'call' and frame.f_code in targets:
                counts[targets[frame.f_code]] += 1
        with owner:
            scope, reader = normalizer.operation(physical, owner)
            try:
                if profile: sys.setprofile(observer)
                with scope:
                    values = [physical.repair_mechanism_identity() for _ in range(count)]
            finally: sys.setprofile(previous)
            normalized = reader()
        closed = owner.closed_receipt()
        joint = transport.compose_closed_receipts(normalized, closed, execution_success=True)
        self.assertTrue(joint['clean'])
        self.assertEqual(closed['borrow_view_checks'], 2*count+4)
        return values, normalized, closed, joint, counts

    def test_genuine_digest_registry_and_profile_counts(self):
        physical = self.physical
        registry_before = physical.registry.implementation_identity()
        plain = self.original()
        values, normalized, closed, joint, counts = self.exercise(7, profile=True)
        self.assertEqual(values, [plain]*7)
        self.assertEqual(normalized['digest'], plain)
        self.assertEqual(counts, dict(original=2, pin=4, digest=2))
        self.assertEqual(normalized['original_oracle_invocations'], dict(entry=1, exit=1))
        self.assertEqual(normalized['per_route_capability_checks'], 14)
        self.assertEqual(physical.registry.implementation_identity(), registry_before)
        self.assertEqual(self.original(), plain)
        self.assertFalse(transport.compose_closed_receipts(normalized, closed, execution_success=False)['clean'])
        UNIT_EVIDENCE['genuine_oracle'] = dict(digest=plain, registry_implementation=registry_before,
            profile_counts=counts, joint=joint, formal_result=False)

    def test_foreign_source_authored_original_before_import_is_refused(self):
        name = 'experiments._static_identity_preimport_fault'
        module = ModuleType(name)
        module.__file__ = self.normalizer.__file__
        module.__package__ = 'experiments'
        sys.modules[name] = module
        try:
            with patch.object(self.physical, 'repair_mechanism_identity', self.physical.implementation_identity):
                exec(compile(Path(module.__file__).read_bytes(), module.__file__, 'exec'), vars(module))
                with lease() as owner:
                    with self.assertRaisesRegex(ValueError, 'provenance'):
                        module.operation(self.physical, owner)
        finally: sys.modules.pop(name, None)

    def test_entry_requires_canonical_registry_and_source_bodies(self):
        registry = self.physical.registry
        digest = sys.modules['src.rq2_joint_deliverability_boundary_v1.continuous_grid_normal']
        cases = ((self.physical, 'registry', ModuleType('foreign')),
            (registry, 'Path', lambda p: Path(p)), (registry, '_pin', self.physical.implementation_identity),
            (registry.old.source, '_sha', self.original),
            (digest, '_encode', registry.implementation_identity), (digest, 'sha256', lambda _: None))
        for obj, name, replacement in cases:
            with self.subTest(name=name):
                with lease() as owner:
                    with patch.object(obj, name, replacement):
                        with self.assertRaises((ValueError, TypeError)):
                            self.normalizer.operation(self.physical, owner)

    def test_transitive_runtime_faults_poison_even_after_restore(self):
        registry = self.physical.registry
        digest = sys.modules['src.rq2_joint_deliverability_boundary_v1.continuous_grid_normal']
        cases = ((registry, 'Path', lambda p: Path(p)), (registry.old.source, '_sha', lambda p: None),
                 (digest, '_encode', lambda x: x), (digest, 'json', ModuleType('foreign_json')),
                 (digest, 'sha256', lambda x: None))
        for obj, name, replacement in cases:
            with self.subTest(name=name):
                owner = lease()
                with self.assertRaises(ValueError):
                    with owner:
                        scope, reader = self.normalizer.operation(self.physical, owner)
                        with scope:
                            with patch.object(obj, name, replacement):
                                with self.assertRaises(ValueError): self.physical.repair_mechanism_identity()
                            with self.assertRaisesRegex(ValueError, 'poisoned'):
                                self.physical.repair_mechanism_identity()
                self.assertIsNotNone(reader()['first_failure'])
                self.assertTrue(owner.closed_receipt()['all_handles_closed'])

    def test_transitive_function_code_mutation_is_refused(self):
        source = self.physical.registry.old.source
        original_code = source._sha.__code__
        owner = lease()
        with self.assertRaises(ValueError):
            with owner:
                scope, reader = self.normalizer.operation(self.physical, owner)
                with scope:
                    try:
                        source._sha.__code__ = (lambda x: None).__code__
                        with self.assertRaises(ValueError): self.physical.repair_mechanism_identity()
                    finally: source._sha.__code__ = original_code
        self.assertTrue(owner.closed_receipt()['all_handles_closed'])
        self.assertIsNotNone(reader()['first_failure'])

    def test_canonical_sys_modules_and_spec_origin_are_fixed(self):
        registry = self.physical.registry
        for kind in ('module', 'origin'):
            owner = lease()
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                with owner:
                    scope, reader = self.normalizer.operation(self.physical, owner)
                    with scope:
                        context = (patch.dict(sys.modules, {registry.__name__: ModuleType('foreign')}) if kind == 'module'
                                   else patch.object(registry.__spec__, 'origin', 'foreign.py'))
                        with context:
                            with self.assertRaises(ValueError): self.physical.repair_mechanism_identity()
            self.assertTrue(owner.closed_receipt()['all_handles_closed'])

    def test_joint_receipts_from_sequential_leases_cannot_be_mixed(self):
        _, first, first_bytes, joint1, _ = self.exercise()
        _, second, second_bytes, joint2, _ = self.exercise()
        self.assertNotEqual(joint1['session'], joint2['session'])
        for normal, byte in ((first, second_bytes), (second, first_bytes)):
            with self.assertRaisesRegex(ValueError, 'session/provenance'):
                transport.compose_closed_receipts(normal, byte, execution_success=True)
        bad = json.loads(json.dumps(first_bytes))
        bad['borrow_binding']['capability_helper_sha256'] = '0'*64
        with self.assertRaises(ValueError): transport.compose_closed_receipts(first, bad, execution_success=True)

    def test_zero_route_or_missing_lifecycle_view_cannot_be_joint_clean(self):
        owner = lease()
        with owner:
            scope, reader = self.normalizer.operation(self.physical, owner)
            with scope: pass
        self.assertFalse(transport.compose_closed_receipts(reader(), owner.closed_receipt(), execution_success=True)['clean'])
        _, normal, byte, _, _ = self.exercise()
        byte['borrow_view_checks'] -= 1
        with self.assertRaisesRegex(ValueError, 'closed owner record'):
            transport.compose_closed_receipts(normal, byte, execution_success=True)

    def test_compose_inputs_are_detached_and_nested_hashes_match(self):
        _, normal, byte, joint, _ = self.exercise()
        frozen = json.loads(json.dumps(joint))
        normal['calls'] = 999
        normal['byte_lease_binding']['session'] = 'changed caller session'
        byte['files_sha256'].clear()
        byte['borrow_binding']['session'] = 'changed caller session'
        self.assertEqual(joint, frozen)
        for key in ('normalization', 'byte_lease'):
            raw = json.dumps(joint[key], sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')
            self.assertEqual(sha256(raw).hexdigest(), joint[key+'_receipt_sha256'])

    def test_synchronized_detached_receipt_edits_are_not_issuer_bytes(self):
        _, normal, byte, _, _ = self.exercise()
        for field in ('session', 'owner_identity', 'capability_helper_sha256', 'held_code_allowlist_sha256'):
            n, b = json.loads(json.dumps(normal)), json.loads(json.dumps(byte))
            replacement = (n['byte_lease_binding'][field]+1 if field == 'owner_identity' else '0'*32)
            n['byte_lease_binding'][field] = b['borrow_binding'][field] = replacement
            if field == 'session': n['session'] = replacement
            with self.subTest(field=field), self.assertRaises(ValueError):
                transport.compose_closed_receipts(n, b, execution_success=True)
        n, b = json.loads(json.dumps(normal)), json.loads(json.dumps(byte))
        path = n['scientific_inputs'][0][0]
        n['scientific_inputs'][0][1] = '0'*64
        b['scientific_input_declaration'][0][1] = '0'*64
        for value in (n['byte_lease_binding']['scientific_inputs'], b['borrow_binding']['scientific_inputs'], b['scientific_inputs']):
            value[path]['sha256'] = '0'*64
        b['files_sha256'][path] = '0'*64
        with self.assertRaises(ValueError): transport.compose_closed_receipts(n, b, execution_success=True)
        for target, key in (('normalization', 'schema'), ('byte', 'schema'), ('byte', 'capability_schema')):
            n, b = json.loads(json.dumps(normal)), json.loads(json.dumps(byte))
            (n if target == 'normalization' else b)[key] = 'foreign'
            with self.assertRaises(ValueError): transport.compose_closed_receipts(n, b, execution_success=True)

    def test_public_issuer_registry_is_read_only_and_cannot_admit_forged_bytes(self):
        _, normal, byte, joint, _ = self.exercise()
        key = (joint['session'], joint['binding']['owner_identity'])
        original = transport._CLOSED_RECEIPTS[key]
        self.assertTrue(all(type(raw) is bytes for raw in original))
        normal['calls'] = 999
        byte['borrow_view_checks'] = 2002
        forged = (transport._encode(normal), transport._encode(byte))
        with self.assertRaises(TypeError): transport._CLOSED_RECEIPTS[key] = forged
        with self.assertRaises(AttributeError): transport._CLOSED_RECEIPTS.clear()
        with self.assertRaises(TypeError): transport._CLOSED_RECEIPTS[key] = original
        self.assertEqual(transport._LOOKUP_CLOSED(key), original)
        with self.assertRaises(ValueError): transport.compose_closed_receipts(normal, byte, execution_success=True)
        self.assertEqual(transport._LOOKUP_CLOSED(key), original)

    def test_issuer_writer_cannot_register_before_real_close_or_overwrite(self):
        owner = lease()
        with self.assertRaises(ValueError):
            with owner:
                scope, reader = self.normalizer.operation(self.physical, owner)
                with scope: self.physical.repair_mechanism_identity()
                with self.assertRaises(ValueError):
                    transport._REGISTER_CLOSED(owner, owner._bound_normalization, b'{}')
        normal, byte = reader(), owner.closed_receipt()
        before = transport._LOOKUP_CLOSED((normal['session'], normal['byte_lease_binding']['owner_identity']))
        with self.assertRaises(ValueError): transport._REGISTER_CLOSED(owner, b'{}', b'{}')
        self.assertEqual(before, transport._LOOKUP_CLOSED((normal['session'], normal['byte_lease_binding']['owner_identity'])))
        self.assertTrue(byte['all_handles_closed'])
        self.assertFalse(transport.compose_closed_receipts(normal, byte, execution_success=True)['clean'])

    def test_failed_issuer_receipts_cannot_be_edited_into_clean(self):
        owner = lease()
        with self.assertRaisesRegex(RuntimeError, 'body failure'):
            with owner:
                scope, reader = self.normalizer.operation(self.physical, owner)
                with scope:
                    self.physical.repair_mechanism_identity()
                    raise RuntimeError('body failure')
        normal, byte = reader(), owner.closed_receipt()
        self.assertFalse(transport.compose_closed_receipts(normal, byte, execution_success=True)['clean'])
        normal['first_failure'] = None
        normal['cleanup_errors'] = []
        byte['first_failure'] = byte['borrow_first_failure'] = None
        byte['cleanup_errors'] = []
        with self.assertRaises(ValueError): transport.compose_closed_receipts(normal, byte, execution_success=True)

    def test_duplicate_normalization_registration_poisons_owner(self):
        owner = lease()
        with self.assertRaises(ValueError):
            with owner:
                scope, reader = self.normalizer.operation(self.physical, owner)
                with scope: self.physical.repair_mechanism_identity()
                raw = transport._encode(reader())
                with self.assertRaises(ValueError): transport.register_normalization_receipt(owner, raw)
        self.assertTrue(owner.closed_receipt()['all_handles_closed'])
        self.assertIsNotNone(owner.closed_receipt()['borrow_first_failure'])
        self.assertFalse(transport.compose_closed_receipts(reader(), owner.closed_receipt(), execution_success=True)['clean'])

    def test_owner_registration_failure_keeps_first_error_and_closes_handles(self):
        owner = lease()
        patcher = None
        try:
            with self.assertRaises(ValueError):
                with owner:
                    scope, reader = self.normalizer.operation(self.physical, owner)
                    with scope: self.physical.repair_mechanism_identity()
                    patcher = patch.object(transport, '_CLOSED_RECEIPTS', {})
                    patcher.start()
        finally:
            if patcher is not None: patcher.stop()
        self.assertTrue(owner.closed_receipt()['all_handles_closed'])
        self.assertIsNotNone(owner.closed_receipt()['borrow_first_failure'])
        with self.assertRaises(ValueError):
            transport.compose_closed_receipts(reader(), owner.closed_receipt(), execution_success=True)

    def test_foreign_alias_is_preserved_and_body_exception_is_primary(self):
        owner = lease()
        foreign = lambda: 'foreign'
        primary = RuntimeError('body primary')
        try:
            with self.assertRaises(RuntimeError) as caught:
                with owner:
                    scope, reader = self.normalizer.operation(self.physical, owner)
                    with scope:
                        self.physical.repair_mechanism_identity = foreign
                        raise primary
            self.assertIs(caught.exception, primary)
            self.assertIs(self.physical.repair_mechanism_identity, foreign)
            self.assertFalse(reader()['original_alias_restored'])
            self.assertTrue(owner.closed_receipt()['all_handles_closed'])
        finally: self.physical.repair_mechanism_identity = self.original

    def test_cleanup_only_oracle_failure_sets_first_failure(self):
        owner = lease()
        with self.assertRaises(ValueError):
            with owner:
                scope, reader = self.normalizer.operation(self.physical, owner)
                try:
                    with scope:
                        registry = self.physical.registry
                        original_path = registry.Path
                        registry.Path = lambda p: Path(p)
                finally: registry.Path = original_path
        receipt = reader()
        self.assertIsNotNone(receipt['first_failure'])
        self.assertTrue(receipt['cleanup_errors'])
        self.assertTrue(owner.closed_receipt()['all_handles_closed'])

    def test_release_function_failure_still_releases_real_os_handles(self):
        owner = lease()
        method = transport.StaticInputBorrow.release
        original_code = method.__code__
        def failure(self): raise RuntimeError('injected release function')
        with self.assertRaises((RuntimeError, ValueError)):
            with owner:
                scope, reader = self.normalizer.operation(self.physical, owner)
                try:
                    with scope: method.__code__ = failure.__code__
                finally: method.__code__ = original_code
        self.assertIsNotNone(reader()['first_failure'])
        closed = owner.closed_receipt()
        self.assertTrue(closed['all_handles_closed'])
        self.assertEqual(closed['borrow_releases'], 0)
        self.assertEqual(closed['borrow_forced_revokes'], 1)

    def test_import_fixed_and_wrong_type_are_refused(self):
        with self.assertRaises(TypeError): self.normalizer.operation(self.physical, object())
        module = ModuleType('static_identity_import_fixed_test')
        module._SOURCE_FIXED = ((self.physical, 'repair_mechanism_identity', self.original),)
        with lease() as owner, patch.dict(sys.modules, {module.__name__: module}):
            with self.assertRaisesRegex(ValueError, 'import-fixed'):
                self.normalizer.operation(self.physical, owner)

    def test_routes_and_capability_do_not_outlive_scope(self):
        owner = lease()
        with owner:
            scope, reader = self.normalizer.operation(self.physical, owner)
            with scope:
                route = self.physical.repair_mechanism_identity
                route()
            before = reader()
            with self.assertRaises(ValueError): route()
            self.assertEqual(reader(), before)

    def test_local_microbenchmark_includes_entry_exit_and_joint_proof(self):
        count = 200
        start = perf_counter()
        plain = [self.original() for _ in range(count)]
        plain_seconds = perf_counter()-start
        start = perf_counter()
        values, normalized, closed, joint, _ = self.exercise(count)
        held_seconds = perf_counter()-start
        self.assertEqual(values, plain)
        UNIT_EVIDENCE['local_microbenchmark'] = dict(calls=count, plain_seconds=plain_seconds,
            held_including_lease_entry_exit_joint_seconds=held_seconds,
            scope='local digest only; not whole-workflow runtime acceptance',
            declaration=normalized['canonical_source_closure'], formal_result=False)
