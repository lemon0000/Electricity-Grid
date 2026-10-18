"""Read-only common-validation scope over an original registered Handoff.

This diagnostic borrows original guards, never consumes a handoff or creates
a journal. Only its own entry can issue a lease or acquire the operation token.
"""
import os
import sys
from threading import get_ident
import types

from experiments import h1_selector_phase_handoff_development_v2 as handoff

SCHEMA = 'h1_common_validation_operation_development_v1'


class _Lease:
    def __new__(cls, *args, **kwargs):
        raise TypeError('original common validation entry must issue the lease')

    def _no_copy(self, *args):
        raise TypeError('live common validation lease cannot be copied')
    __copy__ = __deepcopy__ = __reduce_ex__ = _no_copy


def _build():
    # The token and lease registry are closure state. Neither caller tokens nor
    # caller-supplied validation callbacks are accepted by any issuing entry.
    records = {}
    lease_type = _Lease
    api = handoff
    owner_type = api.Handoff
    begin, end = api._BEGIN, api._END
    owner_check, original_check = api._VERIFY_OWNER, api._CHECK
    record_bundle, record_predecessor = api._RECORD_BUNDLE, api._RECORD_PREDECESSOR
    resources, bundle_enter = api._common_resources, api._Bundle.enter
    common_enter = api.common.CommonOwnerGenesis._enter
    fixed = ((api, '_BEGIN', begin), (api, '_END', end),
        (api, '_VERIFY_OWNER', owner_check), (api, '_CHECK', original_check),
        (api, '_RECORD_BUNDLE', record_bundle), (api, '_RECORD_PREDECESSOR', record_predecessor),
        (api, '_common_resources', resources), (api._Bundle, 'enter', bundle_enter),
        (api.common.CommonOwnerGenesis, '_enter', common_enter))
    codes = tuple((fn, fn.__code__, repr(fn.__defaults__), repr(fn.__kwdefaults__))
        for _, _, fn in fixed)

    def bindings():
        _RUNTIME()
        if (any(getattr(obj, name) is not fn for obj, name, fn in fixed)
                or any(fn.__code__ is not code or repr(fn.__defaults__) != defaults
                    or repr(fn.__kwdefaults__) != keywords for fn, code, defaults, keywords in codes)):
            raise ValueError('original common validation entry dispatch changed')
        original_check()

    def verify(lease):
        if type(lease) is not lease_type:
            raise TypeError('original common validation lease required')
        row = records.get(id(lease))
        if row is None or row['lease'] is not lease or row['closed']:
            raise ValueError('common validation lease is absent or closed')
        h = row['handoff']
        if ((os.getpid(), get_ident()) != row['creator'] or h._state != 'running'
                or h._guard is not row['guard'] or not row['guard'].locked()
                or h._genesis is not row['genesis'] or h._bundle is not row['bundle']
                or any(not guard.locked() for guard in row['common_guards'])
                or any(getattr(obj, name) is not value for obj, name, value in row['aliases'])):
            raise ValueError('original common validation operation lifetime changed')
        owner_check(h)
        return row['roster'], row['declarations'], row['max_common_calls']

    def claim(lease, session):
        verify(lease)
        row = records[id(lease)]
        if row['session'] is not None:
            raise ValueError('one historical witness session per live operation required')
        from experiments import h1_operation_historical_witness_development_v2 as witness
        if type(session) is not witness.GroupWitnessSession:
            raise TypeError('exact grouped historical witness session required')
        row['session'] = session
        row['session_close'] = witness.GroupWitnessSession.close

    def bookend(lease):
        bindings()
        verify(lease)

    class GuardedCommonOperation:
        def __init__(self, owner, *, max_common_calls=2):
            bindings()
            if type(owner) is not owner_type or type(max_common_calls) is not int or max_common_calls != 2:
                raise ValueError('original Handoff and explicit two-common diagnostic required')
            owner._check()
            if owner._state != 'new':
                raise ValueError('new single-attempt Handoff required')
            self._owner = owner
            self._original_owner = owner
            self._creator = os.getpid(), get_ident()
            self._limit = max_common_calls
            self._lease = self._session = None
            self._entered = self._closed = False

        def __enter__(self):
            bindings()
            h = self._owner
            if (self._entered or self._closed or self._creator != (os.getpid(), get_ident())
                    or h is not self._original_owner or self._limit != 2):
                raise ValueError('single-use creating-thread common validation entry required')
            guard = h._guard
            if not guard.acquire(False):
                raise ValueError('Handoff operation already active')
            self._entered = True
            cleanup = GuardedCommonOperation._release
            bundle = h._bundle
            token = None
            parent_guards = parent_marks = common_guards = ()
            try:
                h._check()
                if h._state != 'new':
                    raise ValueError('new single-attempt Handoff required')
                token = begin(h)
                h._state = 'running'
                bundle_enter(h._bundle)
                parent_guards, parent_marks = tuple(h._bundle.held), tuple(h._bundle.marked)
                record_bundle(h, token)
                proposed_guards, aliases = resources(h._genesis)
                common_enter(h._genesis)
                common_guards = proposed_guards
                record_predecessor(h, token, common_guards, aliases)
                roster = h._genesis._original_roster
                attached, _, _ = roster._replay()
                if len(roster._direct) != 3 or set(attached) != set(roster._direct):
                    raise ValueError('three independently authenticated N0 siblings required')
                declarations = []
                for arm in sorted(roster._direct):
                    local = attached[arm]['reference']['local_terminal']['body']
                    declarations.append((arm, local['controller_root'],
                        local['controller_binding_sha256'], local['controller_terminal_sha256']))
                lease = object.__new__(lease_type)
                row = dict(lease=lease, handoff=h, creator=self._creator, token=token, guard=guard,
                    genesis=h._genesis, bundle=h._bundle, roster=roster, aliases=aliases,
                    common_guards=common_guards, parent_guards=parent_guards, parent_marks=parent_marks,
                    declarations=tuple(declarations), max_common_calls=self._limit,
                    closed=False, session=None, session_close=None)
                records[id(lease)] = row
                self._lease = lease
                from experiments import h1_operation_historical_witness_development_v2 as witness
                self._session = witness.GroupWitnessSession(lease)
                bookend(lease)
                return self
            except BaseException as error:
                cleanup(self, h, bundle, token, guard, common_guards, parent_guards, parent_marks, error)
                raise

        def prepare_common(self):
            try:
                bookend(self._lease)
                from experiments import h1_group_n0_common_input_binding_development_v3 as common
                return common.prepare(self._session)
            except BaseException as error:
                if self._session is not None:self._session._poison(error)
                raise

        def receipt(self):
            if self._session is None:
                return dict(schema=SCHEMA, closed=self._closed, complete=False)
            return self._session.receipt()

        def _release(self, owner, bundle, token, guard, common_guards, parent_guards, parent_marks, body_error):
            errors = []
            row = records.get(id(self._lease))
            if row is not None:
                if row['session'] is not None:
                    try:
                        row['session_close'](row['session'])
                    except BaseException as error:
                        errors.append(error)
                row['closed'] = True
            for held in reversed(common_guards):
                try:
                    held.release()
                except BaseException as error:
                    errors.append(error)
            for owner in reversed(parent_marks):
                owner._reference_held = False
            for held in reversed(parent_guards):
                try:
                    held.release()
                except BaseException as error:
                    errors.append(error)
            bundle.held = []
            bundle.marked = []
            if token is not None:
                try:
                    end(owner, token)
                except BaseException as error:
                    errors.append(error)
            owner._state = 'failed'  # Diagnostic entry is never a consume credential.
            if guard.locked():
                guard.release()
            self._closed = True
            if self._session is not None and (body_error is not None or errors):
                self._session._poison(body_error or errors[0])
            if errors:
                if body_error is not None:
                    for error in errors:
                        body_error.add_note('common validation cleanup: ' + repr(error))
                else:
                    for error in errors[1:]:
                        errors[0].add_note('additional cleanup failure: ' + repr(error))
                    raise errors[0]

        def __exit__(self, kind, value, traceback):
            row = records.get(id(self._lease))
            if row is None:
                raise ValueError('original common validation cleanup record required')
            self._release(row['handoff'], row['bundle'], row['token'], row['guard'], row['common_guards'],
                row['parent_guards'], row['parent_marks'], value)

        def _no_copy(self, *args):
            raise TypeError('live common validation operation cannot be copied')
        __copy__ = __deepcopy__ = __reduce_ex__ = _no_copy

    return GuardedCommonOperation, verify, claim, bookend


GuardedCommonOperation, _VERIFY_LEASE, _CLAIM_SESSION, _BOOKEND = _build()


def _install_runtime():
    module=sys.modules[__name__];expected=[]
    for owner in (module,GuardedCommonOperation,_Lease):
        for name,value in tuple(vars(owner).items()):
            if isinstance(value,(types.FunctionType,types.ModuleType,type,staticmethod,classmethod,property)):
                state=(value.__code__,repr(value.__defaults__),repr(value.__kwdefaults__)) if type(value) is types.FunctionType else None
                expected.append((owner,name,value,state))
    def check():
        if (module._RUNTIME is not check or any(getattr(owner,name,None) is not value
                or state is not None and (value.__code__,repr(value.__defaults__),repr(value.__kwdefaults__))!=state
                for owner,name,value,state in expected)):
            raise ValueError('definition-time common validation bridge dispatch changed')
    return check


_RUNTIME=_install_runtime()
