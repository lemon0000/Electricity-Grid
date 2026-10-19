"""Draft single-borrow lifetime for two held immutable scientific inputs."""
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
from threading import get_ident
from types import FunctionType
from uuid import uuid4

from performance import static_scientific_input_read_lease_v2 as core

SCHEMA = 'h1_static_input_single_borrow_capability_draft_v1'
_ISSUER = object()


def _encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')


class StaticInputBorrow:
    __slots__ = ('_owner', '_bound_owner', '_payload', '_bound_payload')

    def __init__(self, issuer, owner, payload):
        if issuer is not _ISSUER or type(owner) is not CapabilityByteLease:
            raise TypeError('live byte lease issuer required')
        self._owner = self._bound_owner = owner
        self._payload = self._bound_payload = payload

    def view(self):
        owner = self._bound_owner
        owner._creating_thread()  # Foreign callers do not poison the creator.
        try:
            _RUNTIME()
            if self._owner is not owner or self._payload is not self._bound_payload:
                raise ValueError('borrow identity changed')
            return owner._borrow_view(self)
        except BaseException as error:
            owner._fail_borrow(error)
            raise

    def release(self):
        owner = self._bound_owner
        owner._creating_thread()
        try:
            _RUNTIME()
            if self._owner is not owner:
                raise ValueError('borrow owner changed')
            owner._release_borrow(self)
        except BaseException as error:
            owner._fail_borrow(error)
            raise


class CapabilityByteLease(core.StaticScientificInputReadLease):
    def __init__(self, *args, **kwargs):
        _RUNTIME()
        super().__init__(*args, **kwargs)
        # active, cap, payload, issued, views, releases, first error, forced revokes
        self._borrow = self._bound_borrow = [False, None, None, False, 0, 0, None, 0]
        self._creator = self._bound_creator = (os.getpid(), get_ident())
        self._session = self._bound_session = uuid4().hex
        self._borrow_entry_identity = None
        self._closed_borrow = None
        self._borrow_binding = self._bound_borrow_binding = _encode(dict(
            session=self._bound_session,
            capability_helper_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
            byte_lease_helper_sha256=sha256(Path(core.__file__).read_bytes()).hexdigest(),
            code_lease_helper_sha256=sha256(Path(core.base.__file__).read_bytes()).hexdigest(),
            held_code_allowlist_sha256=sha256(_encode({str(p): pin for p, pin in self._expected.items()})).hexdigest(),
            scientific_inputs={str(p): dict(sha256=pin, size_bytes=size)
                               for p, (pin, size) in self._bound_science.items()}))

    def _creating_thread(self):
        if self._bound_creator != (os.getpid(), get_ident()):
            raise ValueError('scientific input creating process/thread required')

    def _fail_borrow(self, error):
        if self._bound_borrow[6] is None:
            self._bound_borrow[6] = error

    def _borrow_check(self):
        _RUNTIME()
        if (type(self) is not CapabilityByteLease or self._borrow is not self._bound_borrow or
                self._creator is not self._bound_creator or self._session is not self._bound_session or
                self._borrow_binding is not self._bound_borrow_binding or self._state != 'active'):
            raise ValueError('active creator-owned byte lease required')
        if self._bound_borrow[6] is not None:
            raise ValueError('scientific input borrow poisoned')
        core.base.CodeReadLease._check_hooks(self)
        self._check_control()
        if self._data is not self._bound_data:
            raise ValueError('held scientific bytes changed')

    def borrow_static_inputs(self):
        self._creating_thread()
        try:
            self._check_hooks()
            self._borrow_check()
            state = self._bound_borrow
            if state[3]:
                raise ValueError('scientific input lease permits one borrow only')
            pairs = tuple((str(path), pin, size, self._data[core.base._key(path)])
                          for path, (pin, size) in self._bound_science.items())
            if len(pairs) != 2:
                raise ValueError('exact two scientific inputs required')
            payload = (SCHEMA, self._bound_creator, pairs, self._bound_borrow_binding)
            capability = StaticInputBorrow(_ISSUER, self, payload)
            state[:6] = [True, capability, payload, True, 0, 0]
            self._borrow_entry_identity = tuple((row[0], row[1], row[2]) for row in pairs)
            return capability
        except BaseException as error:
            self._fail_borrow(error)
            raise

    def _borrow_view(self, capability):
        self._borrow_check()
        active, issued, payload = self._bound_borrow[:3]
        if (not active or capability is not issued or type(capability) is not StaticInputBorrow or
                capability._payload is not payload or capability._bound_payload is not payload):
            raise ValueError('live exact borrowed input capability required')
        pairs = payload[2]
        if (payload[3] is not self._bound_borrow_binding or
                tuple((p, pin, size) for p, pin, size, _ in pairs) != self._borrow_entry_identity or
                any(self._data[core.base._key(path)] is not raw for path, _, _, raw in pairs)):
            raise ValueError('borrowed held-byte object identity changed')
        self._bound_borrow[4] += 1
        return payload

    def _release_borrow(self, capability):
        self._borrow_view(capability)
        state = self._bound_borrow
        state[0] = False
        state[1] = state[2] = None
        state[5] += 1
        capability._payload = capability._bound_payload = None

    def _borrow_facts(self):
        state = self._bound_borrow
        return dict(capability_schema=SCHEMA, borrow_issued=state[3], borrow_active=state[0],
                    borrow_view_checks=state[4], borrow_releases=state[5], borrow_forced_revokes=state[7],
                    borrow_first_failure=repr(state[6]) if state[6] is not None else None,
                    borrow_binding=json.loads(self._bound_borrow_binding), creator=list(self._bound_creator),
                    scientific_input_declaration=self._borrow_entry_identity,
                    borrowed_identity_checks='v1 dispatch, bound control, creator, active state and exact held-byte objects; full closure at lifecycle gates')

    def receipt(self):
        self._creating_thread()
        try:
            _RUNTIME()
            value = super().receipt()
            value.update(self._borrow_facts())
            if self._bound_borrow[6] is not None:
                raise ValueError('scientific input borrow poisoned')
            return value
        except BaseException as error:
            self._fail_borrow(error)
            raise

    def closed_receipt(self):
        if self._closed_borrow is None:
            raise ValueError('terminal capability byte lease required')
        value = super().closed_receipt()
        value.update(json.loads(self._closed_borrow))
        return value

    def __exit__(self, kind, value, tb):
        failure = value
        state = self._bound_borrow
        try:
            self._creating_thread()
            _RUNTIME()
            if self._borrow is not state:
                raise ValueError('borrow ledger binding changed')
            if state[6] is not None:
                raise state[6]
            if state[0] or (state[3] and state[5] != 1):
                raise ValueError('issued borrow requires exactly one normal release before exit')
        except BaseException as error:
            if state[6] is None: state[6] = error
            if failure is None: failure = error
            elif failure is not error: failure.add_note('byte lease borrow cleanup: '+repr(error))
        finally:
            # Revocation uses only bound state; ordinary poisoned view is bypassed.
            if state[1] is not None:
                state[1]._payload = state[1]._bound_payload = None
                state[7] += 1
            state[0] = False
            state[1] = state[2] = None
        try:
            super().__exit__(type(failure) if failure is not None else kind,
                             failure, failure.__traceback__ if failure is not None else tb)
        except BaseException as error:
            if state[6] is None: state[6] = error
            raise
        finally:
            self._closed_borrow = _encode(self._borrow_facts())
        if value is None and failure is not None:
            raise failure
        return False


def compose_closed_receipts(normalization, byte_lease, *, execution_success):
    """Bind detached receipts from the same single borrow, after both exits."""
    _RUNTIME()
    if type(execution_success) is not bool:
        raise TypeError('explicit execution success required')
    binding = normalization['byte_lease_binding']
    if (not binding or binding != byte_lease['borrow_binding'] or
            normalization['scientific_inputs'] != byte_lease['scientific_input_declaration'] or
            normalization['session'] != binding['session']):
        raise ValueError('normalization and byte lease session/provenance differ')
    clean = (execution_success and byte_lease['all_handles_closed'] and
        byte_lease['original_alias_restored'] and byte_lease['exit_files_and_ancestors_verified'] and
        byte_lease['first_failure'] is None and not byte_lease['cleanup_errors'] and
        byte_lease['borrow_issued'] and not byte_lease['borrow_active'] and
        byte_lease['borrow_releases'] == 1 and byte_lease['borrow_forced_revokes'] == 0 and
        byte_lease['borrow_first_failure'] is None and normalization['capability_released'] and
        normalization['original_alias_restored'] and normalization['all_normalization_cache_entries_cleared'] and
        normalization['first_failure'] is None and not normalization['cleanup_errors'] and
        normalization['per_route_capability_checks'] == 2*normalization['calls'] and
        normalization['original_oracle_invocations'] == dict(entry=1, exit=1))
    return dict(schema='h1_static_repair_joint_closed_evidence_draft_v1', clean=bool(clean),
                session=binding['session'], binding=binding,
                normalization_receipt_sha256=sha256(_encode(normalization)).hexdigest(),
                byte_lease_receipt_sha256=sha256(_encode(byte_lease)).hexdigest(),
                normalization_implementation=normalization['implementation'],
                normalization=normalization, byte_lease=byte_lease,
                repair_identity_digest_cached=True, per_call_pin_sha_digest_preserved=False,
                formal_result=False, resource_admission=False, native_execution_authorized=False)


def _install_runtime():
    namespace = globals()
    module = sys.modules[__name__]
    bindings = tuple((name, value) for name, value in namespace.items() if not name.startswith('__'))
    classes = (StaticInputBorrow, CapabilityByteLease)
    methods = tuple((cls, name, value) for cls in classes for name, value in vars(cls).items()
                    if type(value) is FunctionType)
    functions = tuple(value for _, _, value in methods) + (
        _encode, compose_closed_receipts, json.loads, json.dumps,
        core.base.CodeReadLease._check_hooks, core.StaticScientificInputReadLease._check_control,
        core.base._key, core._RUNTIME, core.scientific_inputs)
    before = core._function_signatures(functions)
    core_fixed = tuple((obj, name, getattr(obj, name)) for obj, name in (
        (core, 'StaticScientificInputReadLease'), (core, '_RUNTIME'), (core.base, '_key'),
        (core, 'scientific_inputs'), (core, 'SCIENTIFIC_INPUTS'),
        (json, 'loads'), (json, 'dumps'), (os, 'getpid'),
        (core.base.CodeReadLease, '_check_hooks'), (core.StaticScientificInputReadLease, '_check_control')))
    def check():
        if (namespace.get('_RUNTIME') is not check or sys.modules.get(module.__name__) is not module or
                any(namespace.get(name) is not value for name, value in bindings) or
                any(vars(cls).get(name) is not value for cls, name, value in methods) or
                any(getattr(obj, name) is not value for obj, name, value in core_fixed)):
            raise ValueError('static input capability runtime changed')
        core._verify_functions(before)
    return check


_RUNTIME = _install_runtime()
