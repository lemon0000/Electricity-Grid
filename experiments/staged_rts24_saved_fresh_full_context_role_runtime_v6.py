"""Draft full-context role/session engine; the external authority root is closed.

The mechanical engine connects the original hold/replay/bookend operations,
mutually exclusive effect windows and retained Parent quiet coordination.
Its private bindings must be made by a separately approved source successor.
This version cannot issue a genuine grant or construct a production session.
"""
import ast
import builtins
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import time
from threading import Lock, get_ident
from types import CodeType, FunctionType


ROOT = Path(__file__).absolute().parents[1]
OUTER_BINDING = None
SCOPE = 'saved_P1_actual_21_and_journal_5h'
CONTEXT_SCHEMA = 'staged_rts24_saved_P1_fresh_context_development_v1'
SOURCE_EPOCH = 'acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875'
PAYLOAD_CAP = 131072
GATES = ('native_authorized', 'resource_admission', 'formal_result', 'scientific_evidence_adopted', 'public_P2_execution_enabled')
FALSE_FIELDS = GATES + ('run_authority', 'actual_F', 'production_seal', 'parent_independent_P1_verified',
                       'saved_P1_fresh_process_verified', 'saved_P1_parent_adoption_verified')
PARENT_OBLIGATIONS = ('LC.parent.G3', 'Parent.independent_inventory', 'F.G1')
FRESH_OBLIGATIONS = ('LC.fresh.G3',)
CALL_NAMES = ('owner_entry', 'owner_sources', 'owner_close', 'context_check', 'role_entry',
              'hold', 'replay', 'bookend', 'caller_image', 'program_check')
_REGISTRY = {}
_TERMINALS = {}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('ascii')


def pin(raw):
    require(type(raw) is bytes, 'raw bytes required')
    return len(raw), sha256(raw).hexdigest()


def parse(raw, cap=2097152):
    require(type(raw) is bytes and len(raw) <= cap, 'bounded canonical raw required')
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate JSON key')
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
    require(canonical(value) == raw, 'canonical original bytes required')
    return value


def creator():
    return os.getpid(), get_ident()


class FullRoleUnavailable(PermissionError):
    pass


class FullRoleFailure(RuntimeError):
    __slots__ = ('primary', 'secondary', 'session', 'stage', 'committed', 'close_started', 'physical', 'runtime_carrier', 'evidence')
    def __init__(self, session, primary, secondary, stage):
        for name, value in dict(primary=primary, secondary=tuple(secondary), session=session, stage=stage,
                                committed=session._committed, close_started=session._close_started,
                                physical=(session._hold_returned, session._replay_returned, session._g3_returned),
                                runtime_carrier=session._runtime_carrier, evidence=_physical_image(session)).items():
            object.__setattr__(self, name, value)
        super().__init__('full-context scientific role failed or cleanup unresolved')
    def __setattr__(self, name, value):
        if name in ('__traceback__', '__cause__', '__context__', '__suppress_context__'):
            object.__setattr__(self, name, value)
        else:
            raise AttributeError('retained failure is immutable')


class FullRoleEmergency(RuntimeError):
    __slots__ = ('primary', 'secondary', 'session', 'stage', 'committed', 'close_started', 'physical', 'runtime_carrier', 'evidence')
    def __setattr__(self, name, value):
        if name in ('__traceback__', '__cause__', '__context__', '__suppress_context__'):
            object.__setattr__(self, name, value)
        else:
            raise AttributeError('emergency failure is immutable')


_FAILURE_TYPES = (FullRoleFailure, FullRoleEmergency)


class BoundCall:
    """A source-authenticated function row held by the creating bootstrap.

    No public operation accepts a replacement row or arbitrary callback.
    Production row construction is deliberately unavailable in this version.
    """
    __slots__ = ('namespace', 'name', 'function', 'code', 'defaults', 'kwdefaults', 'kwraw', 'prefix')
    def __new__(cls, *args, **kwargs):
        raise TypeError('bootstrap-private source row required')
    def __setattr__(self, name, value):
        raise AttributeError('source row is immutable')
    def __reduce__(self):
        raise TypeError('source row is process-local')


def _row(namespace, name, prefix=()):
    function = namespace[name]
    require(type(function) is FunctionType and function.__globals__ is namespace and function.__closure__ is None,
            'one closed source function required')
    row = object.__new__(BoundCall)
    for key, value in dict(namespace=namespace, name=name, function=function, code=function.__code__,
                           defaults=function.__defaults__, kwdefaults=function.__kwdefaults__,
                           kwraw=canonical(function.__kwdefaults__), prefix=prefix).items():
        object.__setattr__(row, key, value)
    return row


def _check_row(row):
    require(type(row) is BoundCall and type(row.prefix) is tuple and row.namespace.get(row.name) is row.function
            and row.function.__globals__ is row.namespace and row.function.__code__ is row.code
            and row.function.__defaults__ is row.defaults and row.function.__kwdefaults__ is row.kwdefaults
            and (b'null' if row.kwdefaults is None else canonical(row.function.__kwdefaults__)) == row.kwraw
            and row.function.__closure__ is None,
            'held source function changed')


def _invoke(row, *args):
    raise FullRoleUnavailable('v1 bound effects require a separately approved source successor')
    _check_row(row)
    function = FunctionType(row.code, row.namespace, row.name, row.defaults)
    function.__kwdefaults__ = row.kwdefaults
    return function(*row.prefix, *args)


def _source_row(namespace, name, raw, filename, prefix=()):
    """Compile-only verification; never executes the bound target source."""
    unit = compile(raw, filename, 'exec', dont_inherit=True, optimize=0)
    codes = [item for item in unit.co_consts if type(item) is CodeType and item.co_name == item.co_qualname == name]
    row = _row(namespace, name, prefix)
    require(len(codes) == 1 and row.code == codes[0], 'exact source CodeType required')
    return row


class RoleEntryBinding:
    __slots__ = ('creator', 'owner', 'role', 'context_pin', 'entry_row', 'receipt', 'child_template_raw', 'seal')
    def __new__(cls, *args, **kwargs):
        raise TypeError('bootstrap-private actual-entry binding required')
    def __setattr__(self, name, value):
        raise AttributeError('entry binding is immutable')
    def __reduce__(self):
        raise TypeError('entry binding is process-local')


def _entry_binding_image(binding):
    return (binding.creator, id(binding.owner), binding.role, binding.context_pin, id(binding.entry_row),
            pin(binding.receipt), None if binding.child_template_raw is None else pin(binding.child_template_raw))


def _mechanical_entry_binding(owner, role, context_raw, entry_row, receipt, child_template_raw=None):
    """Private fixture/kernel binding; this does not authenticate an entry."""
    _check_row(entry_row)
    require(role in ('parent', 'fresh') and type(receipt) is bytes, 'bounded held entry data required')
    data = parse(receipt, PAYLOAD_CAP)
    require(type(data) is dict and set(data) == {'schema', 'role', 'context_sha', 'owner_identity'}
            and data['schema'] == 'staged_saved_F_role_entry_receipt_v1'
            and type(data['owner_identity']) is str and 0 < len(data['owner_identity']) <= 512
            and data.get('role') == role and data.get('context_sha') == sha256(context_raw).hexdigest(),
            'entry role/context data differs')
    require((role == 'parent') == (type(child_template_raw) is bytes), 'parent needs fixed child template')
    if child_template_raw is not None:
        parse(child_template_raw, PAYLOAD_CAP)
    result = object.__new__(RoleEntryBinding)
    for name, value in dict(creator=creator(), owner=owner, role=role, context_pin=pin(context_raw),
                            entry_row=entry_row, receipt=receipt, child_template_raw=child_template_raw).items():
        object.__setattr__(result, name, value)
    object.__setattr__(result, 'seal', _entry_binding_image(result))
    return result


class RoleBinding:
    __slots__ = ('creator', 'owner', 'role', 'context_raw', 'context_sha', 'context', 'caller_raw',
                 'calls', 'role_proof', 'deadline', 'launch_request', 'launch_program', 'quiet_program', 'clock', 'cleanup', 'core_cleanup', 'seal')
    def __new__(cls, *args, **kwargs):
        raise TypeError('actual-entry role binding must come from approved bootstrap')
    def __setattr__(self, name, value):
        raise AttributeError('role binding is immutable')
    def __reduce__(self):
        raise TypeError('role binding is process-local')


def _binding_image(binding):
    return (binding.creator, id(binding.owner), binding.role, pin(binding.context_raw), binding.context_sha,
            pin(canonical(binding.context)), pin(binding.caller_raw), tuple((name, id(row)) for name, row in binding.calls),
            _entry_binding_image(binding.role_proof), binding.deadline, pin(canonical(binding.launch_request)),
            id(binding.launch_program), id(binding.quiet_program), id(binding.clock), id(binding.cleanup), id(binding.core_cleanup))


def _mechanical_binding(owner, role, context_raw, calls, role_proof, *, outer_deadline,
                        launch_request=None, launch_program=None, quiet_program=None, _clock=time.monotonic, core_cleanup=None):
    """Private phase-kernel constructor, not an authority issuer.

    Only a future source-authenticated bootstrap may use this for live objects.
    Ordinary tests use a private synthetic source binding. Public preparation
    remains closed before this function or any target call can be reached.
    """
    raise FullRoleUnavailable('v1 role binding is closed, including private constructors')
    require(role in ('parent', 'fresh') and role_proof is not None, 'held actual-entry role proof required')
    require(type(role_proof) is RoleEntryBinding and role_proof.creator == creator()
            and role_proof.owner is owner and role_proof.role == role and role_proof.context_pin == pin(context_raw)
            and role_proof.seal == _entry_binding_image(role_proof),
            'same creating owner/role/context entry binding required')
    context = parse(context_raw)
    require(context.get('schema') == CONTEXT_SCHEMA and context.get('scope') == SCOPE
            and context.get('output_mode') == 'saved_P1_F_validation'
            and context.get('authority') == 'DRAFT_NONAUTHORITATIVE'
            and all(context.get(key) is False for key in GATES), 'full F context required')
    require(not ({'caller_expectation_core', 'caller_expectation_sha', 'expectation_sha'} & set(context)), 'expectation-only context cannot enter full F')
    start, deadline = context['invocation_started'], context['deadline']
    require(type(start) is type(deadline) is type(outer_deadline) is float and all(math.isfinite(x) for x in (start, deadline, outer_deadline))
            and start > 0 and deadline == start+180.0 and outer_deadline >= deadline, 'original finite invocation clock required')
    caller_raw = canonical(context['caller_core'])
    require(sha256(caller_raw).hexdigest() == context['caller_sha'] and context['caller_core']['source'] == context['source_pins']
            and context['caller_core']['files'] == context['input_files'], 'external caller/source/input join differs')
    require(type(calls) is tuple and tuple(name for name, _ in calls) == CALL_NAMES, 'closed source call set required')
    for _, row in calls:
        _check_row(row)
    require(role_proof.entry_row is dict(calls)['role_entry'], 'original held actual-entry row required')
    bookend = dict(calls)['bookend']
    require(bookend.kwdefaults == {'inventory': True}, 'physical full inventory default required')
    require((launch_request is not None and type(launch_program) is LaunchBinding and type(quiet_program) is QuietBinding)
            if role == 'parent' else (launch_request is None and launch_program is None and quiet_program is None),
            'parent requires launch/quiet bindings and fresh cannot hold them')
    if role == 'parent':
        _check_program(launch_program, LAUNCH_CALLS)
        _check_program(quiet_program, QUIET_CALLS)
        require(canonical(launch_request) == role_proof.child_template_raw, 'original exact child launch template required')
        _launch_request_data(launch_request, context, role_proof)
    if core_cleanup is not None:
        _check_core_cleanup(core_cleanup)
        require(core_cleanup.owner is owner, 'same owner source cleanup required')
    binding = object.__new__(RoleBinding)
    for name, value in dict(creator=creator(), owner=owner, role=role, context_raw=context_raw,
                            context_sha=sha256(context_raw).hexdigest(), context=context, caller_raw=caller_raw,
                            calls=calls, role_proof=role_proof, deadline=min(deadline, outer_deadline),
                            launch_request=launch_request, launch_program=launch_program,
                            quiet_program=quiet_program, clock=_clock, core_cleanup=core_cleanup,
                            cleanup=(_capture_cleanup(dict(calls), launch_program, quiet_program) if core_cleanup is None else
                                     _capture_cleanup(dict(calls), launch_program, quiet_program, core_cleanup))).items():
        object.__setattr__(binding, name, value)
    object.__setattr__(binding, 'seal', _binding_image(binding))
    return binding


def bind_full_role(*args, **kwargs):
    # A context, public role string, callback, nonce or same PID cannot open this.
    raise FullRoleUnavailable('approved actual-entry/outer binding is not implemented in this source')


def _launch_request_data(request, context, entry):
    fields = ('schema scope context_sha source_epoch role argv cwd environment channel_name channel_nonce '
              'global_deadline parent_identity manifest_pin transport_pin').split()
    require(type(request) is dict and set(request) == set(fields), 'closed child launch request required')
    require(request['schema'] == 'staged_saved_F_full_role_launch_request_v1' and request['scope'] == SCOPE
            and request['role'] == 'fresh' and request['context_sha'] == sha256(canonical(context)).hexdigest()
            and request['source_epoch'] == SOURCE_EPOCH and request['cwd'] == context['repo_root']
            and request['environment'] == context['environment'] and request['global_deadline'] == context['deadline'],
            'same context/source/cwd/environment/deadline launch required')
    require(type(request['argv']) is list and 1 <= len(request['argv']) <= 32
            and all(type(value) is str and value for value in request['argv'])
            and sum(len(value.encode('utf-16-le'))//2 for value in request['argv']) <= 30000,
            'bounded exact argv required')
    require(all(type(request[key]) is str and 0 < len(request[key]) <= 512 for key in ('channel_name', 'channel_nonce')),
            'bounded exact channel binding required')
    require(request['parent_identity'] == parse(entry.receipt, PAYLOAD_CAP)['owner_identity'], 'same parent owner identity required')
    for key in ('manifest_pin', 'transport_pin'):
        value = request[key]
        require(type(value) is dict and set(value) == {'bytes', 'sha256'} and type(value['bytes']) is int
                and 0 <= value['bytes'] <= 2097152 and type(value['sha256']) is str and len(value['sha256']) == 64
                and all(ch in '0123456789abcdef' for ch in value['sha256']), 'bounded exact launch pin required')


class EffectWindow:
    __slots__ = ('phase', 'role', 'launch_request', 'launch_consumed', 'reads', 'launches', 'output_reads', 'faults')
    def __init__(self, role, launch_request):
        self.phase = 'DENY'
        self.role = role
        self.launch_request = canonical(launch_request)
        self.launch_consumed = False
        self.reads = self.launches = self.output_reads = 0
        self.faults = []

    def deny(self, error):
        self.phase = 'DENY'
        if len(self.faults) < 4:
            self.faults.append(error)
        raise error

    def switch(self, expected, phase):
        require(self.phase == expected and not self.faults, 'exclusive effect window transition required')
        self.phase = phase

    def read(self):
        if self.phase != 'P1_READ_WINDOW' or self.faults:
            self.deny(PermissionError('P1 read outside read window'))
        self.reads += 1

    def launch(self, request):
        if self.role != 'parent' or self.phase != 'LAUNCH_WINDOW' or self.launch_consumed or self.faults:
            self.deny(PermissionError('single parent launch window required'))
        # Consume before request validation or invocation; failed attempts cost.
        self.launch_consumed = True
        self.launches += 1
        if canonical(request) != self.launch_request:
            self.deny(PermissionError('exact held launch request required'))
        self.phase = 'CHILD_ACTIVE'

    def output(self):
        if self.phase != 'CHILD_OUTPUT_READ_WINDOW' or self.faults:
            self.deny(PermissionError('quiet-bound child output read required'))
        self.output_reads += 1

    def retire(self):
        self.phase = 'RETIRED'


def _window_primitive(window, operation, value):
    """Fixed code and isolated globals; never dispatch through window methods."""
    put = object.__setattr__
    get = object.__getattribute__
    error = None
    if operation == 'switch':
        expected, phase = value
        if get(window, 'phase') != expected or get(window, 'faults'):
            error = ValueError('exclusive effect window transition required')
        else:
            put(window, 'phase', phase)
    elif operation == 'read':
        if get(window, 'phase') != 'P1_READ_WINDOW' or get(window, 'faults'):
            error = PermissionError('P1 read outside read window')
        else:
            put(window, 'reads', get(window, 'reads')+1)
    elif operation == 'launch':
        if get(window, 'role') != 'parent' or get(window, 'phase') != 'LAUNCH_WINDOW' or get(window, 'launch_consumed') or get(window, 'faults'):
            error = PermissionError('single parent launch window required')
        else:
            put(window, 'launch_consumed', True)
            put(window, 'launches', get(window, 'launches')+1)
            if value != get(window, 'launch_request'):
                error = PermissionError('exact held launch request required')
            else:
                put(window, 'phase', 'CHILD_ACTIVE')
    elif operation == 'output':
        if get(window, 'phase') != 'CHILD_OUTPUT_READ_WINDOW' or get(window, 'faults'):
            error = PermissionError('quiet-bound child output read required')
        else:
            put(window, 'output_reads', get(window, 'output_reads')+1)
    elif operation == 'retire':
        put(window, 'phase', 'RETIRED')
    else:
        error = ValueError('unknown fixed window operation')
    if error is not None:
        put(window, 'phase', 'DENY')
        if len(get(window, 'faults')) < 4:
            list.append(get(window, 'faults'), error)
        raise error


def _make_window_runner(code, context, factory):
    def run(window, operation, value=None):
        return factory(code, context)(window, operation, value)
    return run


_window_apply = _make_window_runner(_window_primitive.__code__,
    dict(__builtins__=dict(vars(builtins))), FunctionType)


def _window_do(session, operation, value=None, _runner=_window_apply,
               _code=_window_apply.__code__, _roots=tuple(cell.cell_contents for cell in _window_apply.__closure__),
               _builtins=tuple(vars(builtins).items())):
    # Check the held runner before any transition. Class methods are never used.
    require(_window_apply is _runner and _runner.__code__ is _code
            and all(cell.cell_contents is root for cell, root in zip(_runner.__closure__, _roots)),
            'fixed window runner changed')
    context = next(root for root in _roots if type(root) is dict)
    require(set(context) == {'__builtins__'} and tuple(context['__builtins__'].items()) == _builtins,
            'fixed window globals changed')
    return _runner(session._window, operation, value)


LAUNCH_CALLS = ('create_owned', 'capture_owned', 'capture_failed')
QUIET_CALLS = ('finish_owned', 'retained_result', 'child_is_terminal', 'consume_original_output',
               'abort_owned', 'child_identity', 'observation_raw')


class LaunchBinding:
    __slots__ = ('creator', 'calls')
    def __new__(cls, *args, **kwargs):
        raise TypeError('approved source-held launcher required')
    def __setattr__(self, name, value):
        raise AttributeError('launcher binding is immutable')


class QuietBinding:
    __slots__ = ('creator', 'calls')
    def __new__(cls, *args, **kwargs):
        raise TypeError('retained exact-child quiet program required')
    def __setattr__(self, name, value):
        raise AttributeError('quiet binding is immutable')


def _program_binding(cls, rows):
    names = LAUNCH_CALLS if cls is LaunchBinding else QUIET_CALLS if cls is QuietBinding else None
    require(names is not None and type(rows) is tuple and tuple(name for name, _ in rows) == names,
            'closed launch/quiet program required')
    for _, row in rows:
        _check_row(row)
    program = object.__new__(cls)
    object.__setattr__(program, 'creator', creator())
    object.__setattr__(program, 'calls', rows)
    return program


def _check_program(program, names):
    require(type(program) is (LaunchBinding if names == LAUNCH_CALLS else QuietBinding)
            and program.creator == creator() and type(program.calls) is tuple
            and tuple(name for name, _ in program.calls) == names, 'creating exact source program required')
    for _, row in program.calls:
        _check_row(row)


def _program_call(program, name, *args):
    names = LAUNCH_CALLS if type(program) is LaunchBinding else QUIET_CALLS
    _check_program(program, names)
    return _invoke(dict(program.calls)[name], *args)


def _cleanup_packet(row):
    _check_row(row)
    # Clone same-namespace helper functions as well as the top function. This
    # isolates function metadata drift; mutable objects/classes remain outside
    # any genuine Native cleanup-equivalence claim in this closed draft.
    context = dict(row.namespace)
    context['__builtins__'] = dict(row.namespace['__builtins__'])
    for name, value in tuple(context.items()):
        if type(value) is FunctionType and value.__globals__ is row.namespace:
            require(value.__closure__ is None, 'closed cleanup helper required')
            clone = FunctionType(value.__code__, context, name, value.__defaults__)
            clone.__kwdefaults__ = None if value.__kwdefaults__ is None else dict(value.__kwdefaults__)
            context[name] = clone
    kwdefaults = None if row.kwdefaults is None else dict(row.kwdefaults)
    packet = (row.code, context, row.defaults, kwdefaults, row.prefix)
    return packet + (_cleanup_image(packet),)


def _cleanup_image(packet):
    code, context, defaults, kwdefaults, prefix = packet[:5]
    roots = tuple((name, id(value), value.__code__, id(value.__defaults__), canonical(value.__kwdefaults__))
                  if type(value) is FunctionType else (name, id(value)) for name, value in context.items())
    return (code, id(context), id(defaults), canonical(kwdefaults), prefix, roots,
            tuple(context['__builtins__'].items()))


CORE_CLEANUP_PIN = (98453, 'ea92529f8bf2792367bc961d3464309dd2892afc53ba0ada1f9833c41f49ca20')


class CoreOwnerCleanup:
    __slots__ = ('owner', 'creator', 'raw', 'namespace', 'anchor', 'packet', 'wrapper', 'functions', 'seal')
    def __new__(cls, *args, **kwargs):
        raise TypeError('source capture owns Core cleanup capsule')
    def __setattr__(self, name, value):
        raise AttributeError('Core cleanup capsule is immutable')
    def __delattr__(self, name):
        raise AttributeError('Core cleanup capsule is immutable')
    def __reduce__(self):
        raise TypeError('Core cleanup capsule is process local')


def _core_cleanup_image(cap):
    return (id(cap.owner), cap.creator, pin(cap.raw), id(cap.namespace), id(cap.anchor), id(cap.packet),
            _cleanup_image(cap.packet), id(cap.wrapper),
            tuple((name, id(fn), code, id(defaults)) for name, fn, code, defaults in cap.functions))


def _check_core_cleanup(cap):
    require(type(cap) is CoreOwnerCleanup and cap.creator == creator()
            and pin(cap.raw) == CORE_CLEANUP_PIN and cap.seal == _core_cleanup_image(cap),
            'source-held Core cleanup capsule required')
    owner=cap.owner; namespace=cap.namespace; cls=namespace['LocalRuntimeInputs']
    require(type(owner) is cls and owner._runtime_cleanup_anchor is cap.anchor
            and owner._seal[0] == id(cap.anchor), 'original Core owner/anchor required')
    for name, fn, code, defaults in cap.functions:
        actual=vars(cls)['close'] if name=='close' else namespace[name]
        require(actual is fn and fn.__globals__ is namespace and fn.__code__ is code
                and fn.__defaults__ is defaults and fn.__kwdefaults__ is None and fn.__closure__ is None,
                'captured Core function changed')
    held=dict(cap.anchor)
    require(held['owner'] is owner and held['packet'] is owner._runtime_cleanup
            and held['resource'] is owner._resource and owner._resource.owner is owner
            and held['ownership'] is owner._ownership and owner._resource.phase == 'LIVE',
            'same live Core cleanup owner required')
    _,_,code,defaults=cap.functions[2]
    FunctionType(code, {'__builtins__': {}, 'dict': dict, 'type': type}, 'held_core_join_roots', defaults)(owner._bindings)
    require(owner._phase == 'LIVE' and owner._consume_state == 'RUNNING'
            and owner._cleanup_started is False and owner._failure is None, 'LIVE role cleanup readiness required')
    packet=held['packet'];ledger=held['ledger']
    _,_,code,defaults=cap.functions[3]
    image=FunctionType(code, {'__builtins__': {}}, 'held_core_cleanup_image', defaults)(packet)
    _,_,code,defaults=cap.functions[4]
    latest,error=FunctionType(code, {'__builtins__': {}}, 'held_core_cleanup_journal', defaults)(held['binding_journal'],held['initial_binding'])
    require(error is None and latest[2] == 'BOUNDARY_OBJECT', 'complete original cleanup binding required')
    names=('boundary','boundary_spec','boundary_proof','boundary_state','boundary_type','boundary_slot')
    require(owner._runtime_cleanup_seal is held['root_image'] and image == held['root_image']
            and packet.binding_stage == latest[2]
            and all(object.__getattribute__(packet,name) is value for name,value in zip(names,latest[3])),
            'original cleanup binding mirrors required')
    require(type(ledger) is list and len(ledger)==6 and ledger[0]=='IDLE' and ledger[1] is ledger[2] is None
            and ledger[3] is ledger[4] is False and ledger[5]==(), 'unused original cleanup ledger required')
    names=('execution_state','failure','reentry','native_started','native_terminal','domain_errors')
    require(all(object.__getattribute__(packet,name) is ledger[index] for index,name in enumerate(names)),
            'original cleanup execution mirrors required')
    require(cap.packet[4] == (owner,) and cap.packet[5] == _cleanup_image(cap.packet)
            and cap.wrapper is cap.functions[1][3][1][11], 'original Core cleanup packet/carrier required')


def _capture_core_owner_cleanup(owner, raw, namespace):
    """Bind only cleanup of an already-held Core47 owner, never role authority.

    The future actual-entry factory must authenticate the bootstrap namespace.
    This mechanical join verifies exact Core cleanup code and retains its
    original defaults and owner; it cannot create a session or invoke effects.
    """
    require(type(raw) is bytes and pin(raw) == CORE_CLEANUP_PIN, 'exact Core47 cleanup source required')
    normalized = raw.replace(b'\r\n', b'\n')
    require(normalized.count(b'\nimport builtins\n') == 1, 'unique Core payload boundary required')
    payload = b'import builtins\n' + normalized.split(b'\nimport builtins\n', 1)[1]
    unit = compile(payload, '<pre_entry_payload>', 'exec', dont_inherit=True, optimize=0)
    codes = {item.co_name: item for item in unit.co_consts if type(item) is CodeType}
    class_code = codes['LocalRuntimeInputs']
    close_code = next(item for item in class_code.co_consts if type(item) is CodeType and item.co_name == 'close')
    cls = namespace['LocalRuntimeInputs']
    close = vars(cls)['close']; runner = namespace['run_runtime_cleanup']; check = namespace['check_bindings']
    require(type(owner) is cls and type(close) is type(runner) is type(check) is FunctionType
            and close.__globals__ is runner.__globals__ is check.__globals__ is namespace
            and close.__code__ == close_code and runner.__code__ == codes['run_runtime_cleanup']
            and check.__code__ == codes['check_bindings'] and close.__closure__ is runner.__closure__ is check.__closure__ is None,
            'original Core cleanup functions required')
    require(close.__defaults__ == (None, runner.__code__, runner.__defaults__, FunctionType, object.__getattribute__)
            and check.__defaults__ == (getattr, type, ValueError, vars, tuple), 'held Core cleanup defaults required')
    FunctionType(check.__code__, {'__builtins__': {}, 'dict': dict, 'type': type}, 'held_core_capture_roots', check.__defaults__)(owner._bindings)
    anchor = owner._runtime_cleanup_anchor; held = dict(anchor)
    require(owner._seal[0] == id(anchor) and held['owner'] is owner and held['packet'] is owner._runtime_cleanup
            and held['resource'] is owner._resource and owner._resource.owner is owner
            and held['ownership'] is owner._ownership and owner._resource.phase == 'LIVE'
            and owner._creator[:2] == creator(), 'same creating Core native owner required')
    for name in ('cleanup_root_image','cleanup_binding_snapshot'):
        fn=namespace[name]
        require(type(fn) is FunctionType and fn.__globals__ is namespace and fn.__code__==codes[name]
                and fn.__closure__ is fn.__kwdefaults__ is None, 'original cleanup readiness code required')
    require(namespace['cleanup_root_image'].__defaults__==(object.__getattribute__,id,tuple)
            and namespace['cleanup_binding_snapshot'].__defaults__==((type,list,tuple,len,ValueError,range,BaseException,int,str,bool),),
            'original cleanup readiness defaults required')
    context = {'__builtins__': {}}
    packet = (close_code, context, close.__defaults__, None, (owner,))
    packet += (_cleanup_image(packet),)
    cap=object.__new__(CoreOwnerCleanup)
    fields=dict(owner=owner, creator=creator(), raw=raw, namespace=namespace, anchor=anchor, packet=packet,
                wrapper=runner.__defaults__[1][11],
                functions=tuple((name, fn, fn.__code__, fn.__defaults__) for name,fn in
                                (('close',close),('run_runtime_cleanup',runner),('check_bindings',check),
                                 ('cleanup_root_image',namespace['cleanup_root_image']),
                                 ('cleanup_binding_snapshot',namespace['cleanup_binding_snapshot']))))
    for name,value in fields.items():object.__setattr__(cap,name,value)
    object.__setattr__(cap,'seal',_core_cleanup_image(cap))
    _check_core_cleanup(cap)
    return cap


def _capture_cleanup(calls, launcher, quiet, core_cleanup=None):
    result = {'owner_close': _cleanup_packet(calls['owner_close']) if core_cleanup is None else core_cleanup.packet,
              'wrapper_class': calls['owner_close'].namespace.get('LocalRuntimeUnresolved') if core_cleanup is None else core_cleanup.wrapper}
    if quiet is not None:
        rows = dict(quiet.calls)
        result['child_abort'] = _cleanup_packet(rows['abort_owned'])
        result['child_terminal'] = _cleanup_packet(rows['child_is_terminal'])
    if launcher is not None:
        result['capture_failed'] = _cleanup_packet(dict(launcher.calls)['capture_failed'])
    return tuple(result.items())


def _cleanup_call(packet, *args):
    raise FullRoleUnavailable('v1 cannot invoke live cleanup targets')
    require(type(packet) is tuple and len(packet) == 6 and _cleanup_image(packet) == packet[5],
            'held cleanup packet changed')
    code, context, defaults, kwdefaults, prefix = packet[:5]
    function = FunctionType(code, context, 'held_full_role_cleanup', defaults)
    function.__kwdefaults__ = kwdefaults
    return function(*prefix, *args)


def _window_image(window):
    get = object.__getattribute__
    return tuple(get(window, name) for name in ('phase', 'role', 'launch_request', 'launch_consumed',
                                               'reads', 'launches', 'output_reads')) + (tuple(id(error) for error in get(window, 'faults')),)


class FullRoleSession:
    __slots__ = ('_creator', '_binding', '_owner', '_window', '_phase', '_held', '_payload_raw', '_payload_pin',
                 '_quiet', '_child', '_committed', '_failure', '_close_started', '_closed', '_lock', '_seal',
                 '_replay_started', '_late_started', '_child_cleanup_started', '_pending_reentry',
                 '_hold_returned', '_replay_returned', '_g3_returned', '_terminal_raw', '_terminal_payload',
                 '_pre_errors', '_launch_result', '_runtime_carrier', '_replay_result', '_g3_result',
                 '_output_raw', '_quiet_raw', '_child_identity', '_launch_error', '_replay_raw',
                 '_replay_return_pin', '_output_result', '_output_return_pin', '_quiet_return_pin',
                 '_registries', '_active_row', '_runtime_closed', '_child_terminal',
                 '_identity_result', '_observation_result', '_failure_record', '_registry_unpublished', '_foreign_terminal')
    def __new__(cls, *args, **kwargs):
        raise TypeError('creating source-held full role session required')
    def __setattr__(self, name, value):
        raise AttributeError('role session is immutable')
    def __reduce__(self):
        raise TypeError('role session is process-local')


def _session_image(session):
    return (session._creator, id(session._binding), id(session._owner), session._phase, id(session._held),
            None if session._payload_raw is None else pin(session._payload_raw), session._payload_pin,
            id(session._quiet), id(session._child), tuple(pin(raw) for raw in session._committed), id(session._failure),
            session._close_started, session._closed, id(session._lock), session._replay_started,
            session._late_started, session._child_cleanup_started, _window_image(session._window),
            id(session._pending_reentry), session._hold_returned, session._replay_returned, session._g3_returned,
            None if session._terminal_raw is None else pin(session._terminal_raw),
            None if session._terminal_payload is None else pin(session._terminal_payload),
            tuple((name, id(error)) for name, error in session._pre_errors), id(session._launch_result),
            _physical_image(session), None if session._replay_raw is None else pin(session._replay_raw),
            tuple(id(value) for value in session._registries), id(session._active_row),
            session._runtime_closed, session._child_terminal, id(session._failure_record),
            session._registry_unpublished, id(session._foreign_terminal))


def _physical_image(session):
    return (session._hold_returned, session._replay_returned, session._g3_returned,
            id(session._replay_result), id(session._g3_result), id(session._runtime_carrier), id(session._launch_error),
            None if session._output_raw is None else pin(session._output_raw),
            None if session._quiet_raw is None else pin(session._quiet_raw),
            session._child_identity, session._replay_return_pin, session._output_return_pin,
            session._quiet_return_pin, id(session._output_result), id(session._identity_result), id(session._observation_result))


def _put(session, **changes):
    for key, value in changes.items():
        object.__setattr__(session, key, value)
    object.__setattr__(session, '_seal', _session_image(session))


def _new_session(binding):
    raise FullRoleUnavailable('v1 cannot construct a live role session')
    require(type(binding) is RoleBinding and binding.creator == creator() and binding.seal == _binding_image(binding), 'creating role binding required')
    session = object.__new__(FullRoleSession)
    for name, value in dict(_creator=creator(), _binding=binding, _owner=binding.owner,
                            _window=_new_window(binding.role, binding.launch_request), _phase='PREPARED', _held=None,
                            _payload_raw=None, _payload_pin=None, _quiet=None, _child=None, _committed=(), _failure=None,
                            _close_started=False, _closed=False, _lock=Lock(), _replay_started=False,
                            _late_started=False, _child_cleanup_started=False, _pending_reentry=None,
                            _hold_returned=False, _replay_returned=False, _g3_returned=False,
                            _terminal_raw=None, _terminal_payload=None, _pre_errors=(), _launch_result=None,
                            _runtime_carrier=None, _replay_result=None, _g3_result=None, _output_raw=None,
                            _quiet_raw=None, _child_identity=None, _launch_error=None, _replay_raw=None,
                            _replay_return_pin=None, _output_result=None, _output_return_pin=None,
                            _quiet_return_pin=None, _registries=(_REGISTRY, _TERMINALS), _active_row=None,
                            _runtime_closed=False, _child_terminal=True, _identity_result=None, _observation_result=None,
                            _failure_record=None, _registry_unpublished=False, _foreign_terminal=None).items():
        object.__setattr__(session, name, value)
    row = (session, binding, session._lock)
    object.__setattr__(session, '_active_row', row)
    object.__setattr__(session, '_seal', _session_image(session))
    _REGISTRY[id(session)] = row
    return session


def _time(binding):
    raise FullRoleUnavailable('v1 does not invoke caller-supplied or live clocks')
    now = binding.clock()
    require(type(now) is float and math.isfinite(now) and binding.context['invocation_started'] <= now <= binding.deadline,
            'original absolute deadline exceeded')
    return now


def _new_window(role, request):
    window = object.__new__(EffectWindow)
    for name, value in dict(phase='DENY', role=role, launch_request=canonical(request), launch_consumed=False,
                            reads=0, launches=0, output_reads=0, faults=[]).items():
        object.__setattr__(window, name, value)
    return window


def _entry(session):
    raise FullRoleUnavailable('v1 cannot enter a live role or perform target effects')
    require(type(session) is FullRoleSession and session._creator == creator(), 'creating exact role session required')
    _sticky_gate(session)
    if session._pending_reentry is not None:
        raise session._pending_reentry
    require(session._registries[0].get(id(session)) is session._active_row
            and session._seal == _session_image(session), 'retained session registry/image changed')
    binding = session._binding
    require(binding.seal == _binding_image(binding) and binding.creator == creator(), 'held role binding changed')
    if binding.core_cleanup is not None:
        _check_core_cleanup(binding.core_cleanup)
        require(binding.core_cleanup.owner is session._owner, 'same session Core cleanup owner required')
    _time(binding)
    for name, packet in binding.cleanup:
        if name != 'wrapper_class':
            require(_cleanup_image(packet) == packet[5], 'held cleanup capability changed before effects')
    for _, row in binding.calls:
        _check_row(row)
    _invoke(dict(binding.calls)['program_check'])
    require(_invoke(dict(binding.calls)['owner_entry']) is session._owner, 'same LIVE runtime owner required')
    require(session._owner._phase == 'LIVE' and session._owner._consume_state == 'RUNNING', 'LIVE/RUNNING owner required')
    require(_invoke(dict(binding.calls)['owner_sources']) == binding.context['source_pins'], 'runtime source bookend differs')
    require(binding.seal == _binding_image(binding) and session._seal == _session_image(session)
            and session._registries[0].get(id(session)) is session._active_row, 'post-entry binding/session changed')
    return binding


def _identity(session):
    binding = session._binding
    held = session._held
    require(held is not None and held.image == binding.caller_raw
            and _invoke(dict(binding.calls)['caller_image'], held) == binding.caller_raw
            and held.files == binding.context['input_files'], 'same full HeldInput/caller map required')
    return held


def _candidate(session, phase, obligations, *, payload_pin=None):
    require(type(obligations) is tuple and all(type(name) is str for name in obligations), 'fixed obligation tuple required')
    row = dict(phase=phase, obligations=list(obligations), context_sha=session._binding.context_sha,
               role=session._binding.role, observed_at=_time(session._binding), payload_pin=payload_pin)
    raw = canonical(row)
    require(len(raw) <= 4096, 'bounded phase candidate required')
    return session._committed + (raw,)


def _commit(session, phase, candidate, **changes):
    # Encoding/candidate formation precedes phase changes. A commit error after
    # the physical operation is sticky and cannot make that operation retryable.
    require(type(candidate) is tuple and candidate[:-1] == session._committed, 'one append-only phase candidate required')
    _put(session, _phase=phase, _committed=candidate, **changes)


def _reconstruct(session, _window=_window_do):
    binding = _entry(session)
    require(session._phase == 'PREPARED' and not session._replay_started, 'single full reconstruction required')
    _put(session, _replay_started=True, _phase='RECONSTRUCTING')
    _window(session, 'switch', ('DENY', 'P1_READ_WINDOW'))
    _put(session)
    calls = dict(binding.calls)
    context = _invoke(calls['context_check'], binding.context_raw, binding.context_sha)
    require(canonical(context) == binding.context_raw, 'same full context raw required')
    actual = _invoke(calls['role_entry'], binding.role, binding.context_raw, binding.context_sha)
    require(canonical(actual) == binding.context_raw, 'same actual-entry role/context result required')
    _window(session, 'read')
    _put(session)
    held = _invoke(calls['hold'], context['source_pins'], binding.caller_raw)
    _put(session, _held=held, _hold_returned=True)
    _identity(session)
    # The original replay validates all 21 points, five hours, full metrics,
    # caller binding and its final physical inventory before normal return.
    _window(session, 'read')
    _put(session)
    payload = _invoke(calls['replay'], held, binding.context_sha)
    _put(session, _replay_returned=True, _replay_result=payload)
    raw = canonical(payload)
    _put(session, _replay_return_pin=pin(raw), _replay_raw=raw if len(raw) <= PAYLOAD_CAP else None)
    require(len(raw) <= PAYLOAD_CAP and type(payload) is dict and payload.get('context_sha') == binding.context_sha
            and payload.get('caller_sha') == sha256(binding.caller_raw).hexdigest(), 'bounded complete replay payload binding required')
    _identity(session)
    _entry(session)
    candidate = _candidate(session, 'G2', ('LC.'+binding.role+'.G2', 'E.'+binding.role+'.final_inventory'), payload_pin=pin(raw))
    _commit(session, 'G2', candidate, _payload_raw=raw, _payload_pin=pin(raw))
    return raw


def _suspend(session, _window=_window_do):
    binding = _entry(session)
    require(binding.role == 'parent' and session._phase == 'G2', 'parent G2 before launch required')
    _window(session, 'switch', ('P1_READ_WINDOW', 'LAUNCH_WINDOW'))
    _put(session)
    candidate = _candidate(session, 'LAUNCH_READY', (), payload_pin=session._payload_pin)
    _commit(session, 'LAUNCH_READY', candidate)


def _launch_child(session, _window=_window_do):
    binding = _entry(session)
    require(binding.role == 'parent' and session._phase == 'LAUNCH_READY' and session._child is None,
            'one retained direct-child owner required')
    _window(session, 'launch', canonical(binding.launch_request))
    _put(session)
    try:
        result = _program_call(binding.launch_program, 'create_owned', binding.launch_request)
    except BaseException as primary:
        _put(session, _launch_error=primary)
        try:
            partial = _cleanup_call(dict(binding.cleanup)['capture_failed'], primary, None)
        except BaseException as secondary:
            _put(session, _child_terminal=False, _pre_errors=session._pre_errors+(('launch_capture', secondary),))
            raise primary from secondary
        if partial is not None:
            _put(session, _child=partial, _child_terminal=False)
        raise
    _put(session, _launch_result=result)
    try:
        child = _program_call(binding.launch_program, 'capture_owned', result)
        require(child is not None, 'exact captured child capability required')
    except BaseException as primary:
        _put(session, _launch_error=primary)
        try:
            partial = _cleanup_call(dict(binding.cleanup)['capture_failed'], primary, result)
        except BaseException as secondary:
            _put(session, _child_terminal=False, _pre_errors=session._pre_errors+(('launch_capture', secondary),))
            raise primary from secondary
        if partial is not None:
            _put(session, _child=partial, _child_terminal=False)
        else:
            _put(session, _child_terminal=False, _pre_errors=session._pre_errors+(('created_child_unresolved', primary),))
        raise
    _put(session, _child=child, _child_terminal=False)
    candidate = _candidate(session, 'CHILD_ACTIVE', (), payload_pin=session._payload_pin)
    _commit(session, 'CHILD_ACTIVE', candidate)


def _quiet_child(session, _window=_window_do):
    binding = _entry(session)
    require(binding.role == 'parent' and session._phase == 'CHILD_ACTIVE', 'exact active child required')
    program = binding.quiet_program
    # A source-held quiet program owns release/drain/close/finish and validates
    # the exact registry/creator/direct child. No caller bool or JSON is read.
    quiet = _program_call(program, 'finish_owned', session._child, binding.context_sha, binding.deadline)
    _put(session, _quiet=quiet)
    require(quiet is _program_call(program, 'retained_result', session._child), 'original retained quiet result required')
    require(_program_call(program, 'child_is_terminal', session._child) is True, 'complete child owner must be quiet')
    _put(session, _child_terminal=True)
    identity_raw = _program_call(program, 'child_identity', session._child)
    _put(session, _identity_result=identity_raw)
    require(type(identity_raw) is bytes and len(identity_raw) <= 8192, 'bounded held child identity required')
    parse(identity_raw, 8192)
    _put(session, _child_identity=identity_raw)
    quiet_raw = _program_call(program, 'observation_raw', session._child, quiet)
    _put(session, _observation_result=quiet_raw)
    if type(quiet_raw) is bytes:
        _put(session, _quiet_return_pin=pin(quiet_raw), _quiet_raw=quiet_raw if len(quiet_raw) <= PAYLOAD_CAP else None)
    require(type(quiet_raw) is bytes and len(quiet_raw) <= PAYLOAD_CAP, 'bounded original quiet observation required')
    _put(session, _quiet_raw=quiet_raw)
    parse(quiet_raw, PAYLOAD_CAP)
    _window(session, 'switch', ('CHILD_ACTIVE', 'CHILD_OUTPUT_READ_WINDOW'))
    _put(session, _quiet=quiet)
    candidate = _candidate(session, 'CHILD_QUIET', (), payload_pin=session._payload_pin)
    _commit(session, 'CHILD_QUIET', candidate, _quiet=quiet)


def _consume_child(session, _window=_window_do):
    binding = _entry(session)
    require(binding.role == 'parent' and session._phase == 'CHILD_QUIET', 'quiet precedes child output consumption')
    _window(session, 'output')
    _put(session)
    program = binding.quiet_program
    raw = _program_call(program, 'consume_original_output', session._child, session._quiet, binding.context_raw)
    _put(session, _output_result=raw)
    if type(raw) is bytes:
        _put(session, _output_return_pin=pin(raw))
    if type(raw) is bytes and len(raw) <= PAYLOAD_CAP:
        _put(session, _output_raw=raw)
    require(type(raw) is bytes and len(raw) <= PAYLOAD_CAP and raw == session._payload_raw,
            'complete independent parent/fresh payload equality required')
    candidate = _candidate(session, 'CHILD_COMPARED', (), payload_pin=pin(raw))
    _commit(session, 'CHILD_COMPARED', candidate)


def _late_bookend(session, _window=_window_do):
    binding = _entry(session)
    require(not session._late_started, 'terminal inventory attempt cannot be retried')
    if binding.role == 'parent':
        require(session._phase == 'CHILD_COMPARED' and session._quiet is not None
                and _program_call(binding.quiet_program, 'child_is_terminal', session._child) is True, 'quiet/compared parent window required')
        _window(session, 'switch', ('CHILD_OUTPUT_READ_WINDOW', 'P1_READ_WINDOW'))
        _put(session)
        obligations = PARENT_OBLIGATIONS
    else:
        require(session._phase == 'G2' and session._child is None, 'fresh terminal window required')
        obligations = FRESH_OBLIGATIONS
    _put(session, _late_started=True)
    held = _identity(session)
    _window(session, 'read')
    _put(session)
    result = _invoke(dict(binding.calls)['bookend'], held)
    _put(session, _g3_returned=True, _g3_result=result)
    require(result is None and _identity(session) is held, 'same successful physical terminal inventory required')
    _entry(session)
    candidate = _candidate(session, 'G3', obligations, payload_pin=session._payload_pin)
    _commit(session, 'G3', candidate)


def _close_once(session, primary):
    if session._close_started:
        return ()
    object.__setattr__(session, '_close_started', True)
    # Cleanup must still run when a callback changed the window runner.
    object.__setattr__(session._window, 'phase', 'RETIRED')
    secondary = []
    cleanup = dict(session._binding.cleanup)
    if session._child is not None and not session._child_cleanup_started:
        object.__setattr__(session, '_child_cleanup_started', True)
        terminal = False
        try:
            terminal = _cleanup_call(cleanup['child_terminal'], session._child) is True
        except BaseException as error:
            secondary.append(('child_terminal_probe', error))
        if not terminal:
            try:
                _cleanup_call(cleanup['child_abort'], session._child, primary, session._binding.deadline)
            except BaseException as error:
                secondary.append(('child_abort', error))
            try:
                terminal = _cleanup_call(cleanup['child_terminal'], session._child) is True
                require(terminal, 'child cleanup remains unresolved')
            except BaseException as error:
                secondary.append(('child_terminal_after_abort', error))
        object.__setattr__(session, '_child_terminal', terminal)
    try:
        _cleanup_call(cleanup['owner_close'], primary)
    except BaseException as error:
        expected = cleanup['wrapper_class']
        if expected is not None and type(error) is expected and error.owner is session._owner and error.primary is primary and error.secondary == ():
            object.__setattr__(session, '_runtime_carrier', error)
        else:
            secondary.append(('runtime_close', error))
    owner = session._owner
    try:
        require(owner._resource.phase == 'CLOSED' and not any(owner._resource.pending)
                and owner._resource.close_calls == [1, 1] and owner._phase in ('CLOSED', 'UNRESOLVED'), 'physical native owner remains unresolved')
        if primary is None:
            require(owner._phase == 'CLOSED', 'successful native close required')
        object.__setattr__(session, '_runtime_closed', True)
    except BaseException as error:
        secondary.append(('runtime_terminal', error))
    object.__setattr__(session, '_closed', session._runtime_closed and session._child_terminal)
    object.__setattr__(session._window, 'phase', 'CLOSED' if session._closed and not secondary else 'UNRESOLVED')
    object.__setattr__(session, '_seal', _session_image(session))
    return tuple(secondary)


def _failure_fingerprint(failure):
    require(type(failure) in _FAILURE_TYPES, 'exact retained failure type required')
    return (id(failure.primary), tuple((name, id(error)) for name, error in failure.secondary),
            id(failure.session), failure.stage, failure.committed, failure.close_started,
            failure.physical, id(failure.runtime_carrier), failure.evidence)


def _sticky_gate(session, _fingerprint=_failure_fingerprint):
    record = session._registries[1].get(id(session))
    if session._failure is not None:
        expected = session._failure_record
        require(type(expected) is tuple and len(expected) == 3 and expected[0] is session
                and expected[1] is session._failure and expected[2] == _fingerprint(session._failure),
                'retained failure fingerprint changed')
        if session._registry_unpublished:
            require(type(session._failure) is FullRoleEmergency and record is session._foreign_terminal,
                    'unpublished emergency foreign row changed')
        else:
            require(record is expected, 'sticky failure registry changed')
        raise session._failure
    require(record is None, 'foreign terminal registry row preserved')


def _publish_failure(session, failure, phase):
    _put(session, _failure=failure, _phase=phase)
    active, terminal = session._registries
    row = active.get(id(session))
    if row is session._active_row:
        del active[id(session)]
    else:
        require(row is None, 'foreign active registry row preserved')
    require(terminal.get(id(session)) is None, 'foreign terminal registry row preserved')
    record = (session, failure, _failure_fingerprint(failure))
    terminal[id(session)] = record
    object.__setattr__(session, '_failure_record', record)


def _emergency_failure(session, primary, secondary, stage):
    failure = RuntimeError.__new__(FullRoleEmergency, 'full-role failure preservation emergency')
    values = dict(primary=primary, secondary=tuple(secondary), session=session, stage=stage,
                  committed=session._committed, close_started=session._close_started,
                  physical=(session._hold_returned, session._replay_returned, session._g3_returned),
                  runtime_carrier=session._runtime_carrier,
                  evidence=('emergency_retained_references', id(session._replay_result), id(session._g3_result),
                            id(session._quiet), id(session._output_result), id(session._identity_result),
                            id(session._observation_result), session._replay_return_pin,
                            session._quiet_return_pin, session._output_return_pin))
    for name, value in values.items():
        object.__setattr__(failure, name, value)
    object.__setattr__(session, '_failure', failure)
    object.__setattr__(session, '_phase', 'UNRESOLVED')
    active, terminal = session._registries
    if dict.get(active, id(session)) is session._active_row:
        dict.__delitem__(active, id(session))
    fingerprint = (id(primary), tuple((name, id(error)) for name, error in failure.secondary), id(session),
                   stage, failure.committed, failure.close_started, failure.physical,
                   id(failure.runtime_carrier), failure.evidence)
    record = (session, failure, fingerprint)
    foreign = dict.get(terminal, id(session))
    object.__setattr__(session, '_failure_record', record)
    object.__setattr__(session, '_registry_unpublished', foreign is not None)
    object.__setattr__(session, '_foreign_terminal', foreign)
    if foreign is None:
        dict.__setitem__(terminal, id(session), record)
    return failure


def _fail(session, primary, stage, secondary=()):
    # A foreign terminal row must not suppress cleanup of our held owner.
    if session._failure is not None:
        _sticky_gate(session)
    errors = session._pre_errors + tuple(secondary)
    try:
        errors += _close_once(session, primary)
    except BaseException as error:
        errors += (('emergency_cleanup', error),)
    try:
        failure = FullRoleFailure(session, primary, errors, stage)
        _publish_failure(session, failure, 'FAILED' if session._closed and not errors else 'UNRESOLVED')
    except BaseException as error:
        failure = _emergency_failure(session, primary, errors+(('failure_publication', error),), stage)
    raise failure from primary


def _finish(session):
    binding = _entry(session)
    require(session._phase == 'G3', 'G3 precedes runtime close')
    # Construct/encode the data candidate before native cleanup. This is not a
    # final adoption/publication record and all authority fields stay false.
    value = dict(schema='staged_saved_F_full_context_role_candidate_v1', authority='DRAFT_NONAUTHORITATIVE',
                 scope=SCOPE, role=binding.role, context_sha=binding.context_sha,
                 context_pin=pin(binding.context_raw), payload_pin=session._payload_pin,
                 launch_request_pin=None if binding.launch_request is None else pin(canonical(binding.launch_request)),
                 child_identity=None if session._child_identity is None else parse(session._child_identity, 8192),
                 quiet_observation_pin=session._quiet_return_pin, child_output_pin=session._output_return_pin,
                 physical_returns=dict(hold=session._hold_returned, replay=session._replay_returned, G3=session._g3_returned),
                 window_entries=dict(P1_operations=object.__getattribute__(session._window, 'reads'),
                                     launch_attempts=object.__getattribute__(session._window, 'launches'),
                                     child_output_consumptions=object.__getattribute__(session._window, 'output_reads')),
                 phases=[parse(raw, 4096) for raw in session._committed], **{name: False for name in FALSE_FIELDS})
    raw = canonical(value)
    require(len(raw) <= PAYLOAD_CAP and pin(session._payload_raw) == session._payload_pin, 'bounded retained data candidate required')
    errors = _close_once(session, None)
    if session._pending_reentry is not None:
        _fail(session, session._pending_reentry, 'close_reentry', errors)
    if errors:
        _fail(session, None, 'close', errors)
    payload_raw = session._payload_raw
    _put(session, _phase='CLOSED', _terminal_raw=raw, _terminal_payload=payload_raw)
    expected = session._registries[0].get(id(session))
    require(expected is session._active_row, 'exact registry row required for retirement')
    del session._registries[0][id(session)]
    _put(session, _owner=None, _binding=None, _held=None, _child=None, _quiet=None, _launch_result=None,
         _replay_result=None, _g3_result=None, _output_result=None, _identity_result=None, _observation_result=None, _active_row=None)
    return raw, payload_raw


def dispatch(session, operation):
    require(type(session) is FullRoleSession and session._creator == creator(), 'foreign session rejected without cleanup')
    if session._failure is not None:
        _sticky_gate(session)
    if session._phase == 'CLOSED':
        require(operation == 'close' and session._seal == _session_image(session), 'terminal session permits data close only')
        return session._terminal_raw, session._terminal_payload
    if not session._lock.acquire(False):
        error = session._pending_reentry
        if error is None:
            error = ValueError('same-thread full-role operation reentered')
            _put(session, _pending_reentry=error)
        raise error
    try:
        _sticky_gate(session)
        require(session._registries[0].get(id(session)) is session._active_row, 'exact creating session registry required')
        if operation == 'reconstruct':
            result = _reconstruct(session)
        elif operation == 'suspend_for_launch':
            result = _suspend(session)
        elif operation == 'launch_child':
            result = _launch_child(session)
        elif operation == 'quiet_child':
            result = _quiet_child(session)
        elif operation == 'consume_child':
            result = _consume_child(session)
        elif operation == 'late_bookend':
            result = _late_bookend(session)
        elif operation == 'close':
            result = _finish(session)
        else:
            raise ValueError('unknown fixed full-role operation')
        if session._pending_reentry is not None:
            raise session._pending_reentry
        if session._phase != 'CLOSED':
            require(session._registries[0].get(id(session)) is session._active_row
                    and session._seal == _session_image(session), 'post-operation registry/image changed')
        return result
    except BaseException as primary:
        _fail(session, primary, operation)
    finally:
        session._lock.release()


def current():
    raw = Path(__file__).read_bytes()
    tree = ast.parse(raw)
    return None, dict(schema='staged_saved_F_full_context_role_contract_v1', authority='DRAFT_NONAUTHORITATIVE',
                      scope=SCOPE, source_pin=pin(raw), external_root_available=False,
                      live_effect_invocation_available=False, actual_entry_factory_implemented=False,
                      actual_audit_hook_integrated=False, source_specific_launcher_and_quiet_binding_available=False,
                      activation_requires_source_successor=True,
                      stages=['PREPARED', 'RECONSTRUCTING', 'G2', 'LAUNCH_READY', 'CHILD_ACTIVE', 'CHILD_QUIET', 'CHILD_COMPARED', 'G3', 'CLOSED'],
                      parent_obligations=list(PARENT_OBLIGATIONS), fresh_obligations=list(FRESH_OBLIGATIONS),
                      functions=[node.name for node in tree.body if type(node) is ast.FunctionDef],
                      P1_reads=0, native_owner_calls=0, source49_target_modules_executed=0,
                      **{name: False for name in FALSE_FIELDS})
