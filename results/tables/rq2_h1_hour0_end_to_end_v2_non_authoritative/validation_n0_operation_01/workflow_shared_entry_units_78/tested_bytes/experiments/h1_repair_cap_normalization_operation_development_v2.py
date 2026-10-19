"""Draft static repair-identity reuse under an explicit immutable-input borrow.

This deliberately changes observation timing: original pin/SHA/JSON/Fraction/
digest work runs in entry/exit oracles, while routed calls check live ownership,
fixed dependencies and held-byte identities. Use only in a dedicated process;
save joint closed evidence and exit after restoring the physical alias.
"""
from contextlib import contextmanager
import builtins
from dis import get_instructions
from fractions import Fraction
from hashlib import sha256
import json
import marshal
import os
from pathlib import Path
import sys
from threading import get_ident
from types import CodeType, FunctionType, ModuleType

from experiments import h1_origin_grid_step_development_v1 as _physical


SCHEMA = 'h1_repair_cap_normalization_operation_development_v2'


def _encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')


def _state(value):
    if isinstance(value, property):
        return tuple(_state(fn) for fn in (value.fget, value.fset, value.fdel))
    if type(value) is not FunctionType:
        return None
    return (value.__code__, id(value.__defaults__), repr(value.__defaults__),
            id(value.__kwdefaults__), repr(value.__kwdefaults__),
            tuple(id(c.cell_contents) for c in value.__closure__ or ()))


def _source_authored(fn, module, qualname):
    if type(fn) is not FunctionType:
        raise TypeError('original source-authored Python body required')
    path = Path(getattr(module, '__file__', ''))
    if (fn.__module__ != module.__name__ or fn.__qualname__ != qualname or
            fn.__globals__ is not vars(module) or fn.__code__.co_filename != str(path)):
        raise ValueError('original scientific function provenance required')
    def walk(code):
        if code.co_qualname == fn.__qualname__:
            return code
        for value in code.co_consts:
            if type(value) is CodeType:
                found = walk(value)
                if found is not None: return found
        return None
    expected = walk(compile(path.read_bytes(), str(path), 'exec'))
    if expected is None or fn.__code__ != expected:
        raise ValueError('original scientific source code required')
    return sha256(marshal.dumps(expected)).hexdigest()


def _canonical_closure(physical, transport, byte_lease, root):
    """Capture the used project bodies and their direct/transitive bindings.

    Project code is checked against the held canonical files. JSON/Fraction
    and the encoding helpers have their used globals/descriptors fixed too.
    This is a named Python binding fault model, not arbitrary-memory security.
    """
    definitions = (
        ('experiments.h1_origin_grid_step_development_v1', 'experiments/h1_origin_grid_step_development_v1.py'),
        ('experiments.h1_outage_registry_development_v1', 'experiments/h1_outage_registry_development_v1.py'),
        ('experiments.h1_outage_source_development_v1', 'experiments/h1_outage_source_development_v1.py'),
        ('src.rq2_joint_deliverability_boundary_v1.source_window', 'src/rq2_joint_deliverability_boundary_v1/source_window.py'),
        ('src.rq2_joint_deliverability_boundary_v1.continuous_grid_normal', 'src/rq2_joint_deliverability_boundary_v1/continuous_grid_normal.py'))
    modules, pins, rows, attributes = [], {}, [], []
    def bind(obj, *names):
        for name in names:
            value = getattr(obj, name)
            attributes.append((obj, name, value, _state(value)))
    for name, relative in definitions:
        module, path = sys.modules.get(name), root/relative
        if (type(module) is not ModuleType or module.__name__ != name or module.__file__ != str(path) or
                module.__spec__ is None or module.__spec__.name != name or
                module.__spec__.origin != str(path) or module.__spec__.loader is not module.__loader__ or
                getattr(module.__loader__, 'path', None) != str(path)):
            raise ValueError('canonical scientific defining module required: '+name)
        pin = sha256(path.read_bytes()).hexdigest()
        if byte_lease._bound_expected.get(path) != pin:
            raise ValueError('canonical scientific source must be in held code allowlist: '+relative)
        pins[name] = dict(path=str(path), sha256=pin)
        bind(module, '__name__', '__file__', '__spec__', '__loader__')
        bind(module.__spec__, 'name', 'origin', 'loader')
        bind(module.__loader__, 'path')
        modules.append(module)
    canonical, registry, old, source, digest = modules
    if (physical is not canonical or physical.registry is not registry or registry.old is not old or
            old.source is not source or physical._digest is not digest._digest or
            physical.json is not json or registry.sha256 is not sha256 or registry.Path is not Path or
            digest.sha256 is not sha256 or digest.json is not json or physical.Q is not Fraction or
            registry.ROOT != root or registry.AUTHORITY != root/transport.core.SCIENTIFIC_INPUTS[0][0] or
            registry.AUTHORITY_SHA != transport.core.SCIENTIFIC_INPUTS[0][1]):
        raise ValueError('canonical original scientific dependency graph required')
    project_functions = ((physical, 'repair_mechanism_identity'), (registry, '_pin'),
        (source, '_sha'), (digest, '_digest'), (digest, '_encode'), (digest, '_number'))
    functions = [getattr(module, name) for module, name in project_functions]
    code_pins = {module.__name__+'.'+name: _source_authored(getattr(module, name), module, name)
                 for module, name in project_functions}
    for obj, names in ((physical, ('registry', 'json', 'Q', '_digest')),
        (registry, ('_pin', 'AUTHORITY', 'AUTHORITY_SHA', 'ROOT', 'Path', 'sha256', 'old')),
        (old, ('source',)), (source, ('_sha',)),
        (digest, ('_digest', '_encode', '_number', 'sha256', 'json', 'is_dataclass', 'fields', 'datetime', 'isfinite')),
        (json, ('loads', 'dumps', '_default_decoder', '_default_encoder', 'JSONDecoder', 'JSONEncoder', 'encoder', 'decoder')),
        (Fraction, ('__new__', '__init__', 'numerator', 'denominator')),
        (transport, ('CapabilityByteLease', 'StaticInputBorrow', '_RUNTIME', 'core', 'SCHEMA', 'register_normalization_receipt')),
        (transport.core, ('scientific_inputs', 'SCIENTIFIC_INPUTS'))):
        bind(obj, *names)
    # JSON's C scanner and decoder configuration are instance attributes.
    decoder = json._default_decoder
    if type(decoder) is not json.JSONDecoder:
        raise ValueError('canonical JSON decoder required')
    bind(decoder, *vars(decoder))
    bind(type(decoder), 'decode', 'raw_decode')
    bind(json._default_encoder, *vars(json._default_encoder))
    bind(json.JSONEncoder, '__init__', 'encode', 'iterencode')
    bind(json.encoder, '_make_iterencode', 'c_make_encoder', 'encode_basestring', 'encode_basestring_ascii', 'INFINITY')
    functions += [json.loads, json.dumps, type(decoder).decode, type(decoder).raw_decode,
                  json.JSONEncoder.__init__, json.JSONEncoder.encode, json.JSONEncoder.iterencode,
                  json.encoder._make_iterencode,
                  Fraction.__new__, Fraction.numerator.fget, Fraction.denominator.fget,
                  digest.is_dataclass, digest.fields, transport.core.scientific_inputs]
    for fn in (json.loads, json.dumps, type(decoder).decode, type(decoder).raw_decode,
               json.JSONEncoder.__init__, json.JSONEncoder.encode, json.JSONEncoder.iterencode,
               json.encoder._make_iterencode, Fraction.__new__, Fraction.numerator.fget, Fraction.denominator.fget,
               digest.is_dataclass, digest.fields):
        module = sys.modules.get(fn.__module__)
        code_pins[fn.__module__+'.'+fn.__qualname__] = _source_authored(fn, module, fn.__qualname__)
    # Recursive comprehensions have their own bytecode/global lookups.
    def names(code):
        result = {i.argval for i in get_instructions(code) if i.opname in ('LOAD_GLOBAL', 'LOAD_NAME')}
        for value in code.co_consts:
            if type(value) is CodeType: result.update(names(value))
        return result
    function_states = []
    for fn in functions:
        if type(fn) is not FunctionType: continue
        function_states.append((fn, _state(fn)))
        namespace = fn.__globals__
        for name in names(fn.__code__):
            mapping = namespace if name in namespace else fn.__builtins__
            value = mapping[name]
            # A builtin shadow in a project function is not source-canonical.
            if fn in functions[:6] and hasattr(builtins, name) and value is not getattr(builtins, name):
                raise ValueError('canonical project builtin required: '+name)
            rows.append((mapping, name, value, _state(value)))
    # Attributes reached through standard-library modules in Fraction/JSON.
    import math
    import numbers
    bind(math, 'gcd', 'isfinite')
    bind(numbers, 'Rational', 'Integral')
    rows = list({(id(mapping), name): (mapping, name, value, state)
                 for mapping, name, value, state in rows}.values())
    attributes = list({(id(obj), name): (obj, name, value, state)
                       for obj, name, value, state in attributes}.values())
    declaration = transport.core.scientific_inputs(root)
    evidence = dict(modules=pins, function_code_sha256=code_pins,
                    helper_implementation=implementation_identity(),
                    scientific_inputs=declaration,
                    scope='canonical project bodies, recursive global loads and used JSON/Fraction descriptors; named binding fault model')
    def check():
        if any(sys.modules.get(name) is not module for (name, _), module in zip(definitions, modules)):
            raise ValueError('canonical defining module replaced')
        changed = [name for mapping, name, value, state in rows
                   if mapping.get(name) is not value or _state(value) != state]
        changed += [name for obj, name, value, state in attributes
                    if getattr(obj, name, None) is not value or _state(value) != state]
        if changed:
            raise ValueError('static repair transitive binding changed: '+','.join(dict.fromkeys(changed)))
        if any(_state(fn) != state for fn, state in function_states):
            raise ValueError('static repair transitive function changed')
    return check, evidence


def implementation_identity():
    return sha256(Path(__file__).read_bytes()).hexdigest()


def operation(physical, byte_lease):
    """Return a one-use context and a creator-only detached closed reader."""
    _RUNTIME()
    from performance import static_input_capability_v1 as transport
    transport._RUNTIME()
    if physical is not _physical or type(byte_lease) is not transport.CapabilityByteLease:
        raise TypeError('canonical physical module and exact capability byte lease required')
    original = physical.repair_mechanism_identity
    if original is not _ORIGINAL:
        raise TypeError('original repair body required; nested or stale consumers refused')
    for module in tuple(sys.modules.values()):
        namespace = vars(module) if isinstance(module, ModuleType) else {}
        for row in namespace.get('_SOURCE_FIXED', ()):
            if type(row) is tuple and len(row) == 3 and row[:2] == (physical, 'repair_mechanism_identity'):
                raise ValueError('repair adapter must precede import-fixed consumers')
    root = Path(__file__).resolve().parents[1]
    closure_check, closure_evidence = _canonical_closure(physical, transport, byte_lease, root)
    creator = (os.getpid(), get_ident())
    data = {}
    status = dict(phase='new', route=None, route_state=None, calls=0, capability_checks=0,
                  first_failure=None, cleanup_errors=[], receipt=None,
                  oracle_attempts=dict(entry=0, exit=0), oracle_successes=dict(entry=0, exit=0))
    own = implementation_identity()
    capability = None
    original_state = _state(original)

    def dependencies():
        _RUNTIME()
        closure_check()
        if _state(original) != original_state:
            raise ValueError('static repair dependency changed')

    def check():
        if creator != (os.getpid(), get_ident()):
            raise ValueError('static repair creating process/thread required')
        dependencies()
        if status['first_failure'] is not None:
            raise ValueError('static repair operation poisoned')
        if (status['phase'] != 'active' or physical.repair_mechanism_identity is not status['route'] or
                _state(status['route']) != status['route_state']):
            raise ValueError('static repair live route required')

    def view():
        payload = capability.view()
        if payload is not data['payload'] or any(
                actual[3] is not expected[3] for actual, expected in zip(payload[2], data['payload'][2])):
            raise ValueError('static repair held-byte objects changed')
        return payload

    def oracle(stage):
        dependencies()
        status['oracle_attempts'][stage] += 1
        value = original()
        dependencies()
        if type(value) is not str or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
            raise ValueError('original repair identity digest required')
        status['oracle_successes'][stage] += 1
        return value

    @contextmanager
    def scope():
        nonlocal capability
        primary = None
        restored = False
        released = False
        digest = None
        declared_inputs = None
        lease_binding = None
        try:
            if creator != (os.getpid(), get_ident()) or status['phase'] != 'new':
                raise ValueError('single-use creating-thread static repair scope required')
            dependencies()
            status['phase'] = 'acquiring'
            capability = byte_lease.borrow_static_inputs()
            if type(capability) is not transport.StaticInputBorrow:
                raise TypeError('exact static input borrow required')
            payload = capability.view()
            declared_inputs = tuple(row[:3] for row in payload[2])
            lease_binding = json.loads(payload[3])
            expected = transport.core.scientific_inputs(root)
            if (payload[0] != transport.SCHEMA or payload[1] != creator or len(payload[2]) != 2 or
                    {path: dict(sha256=pin, size_bytes=size) for path, pin, size, _ in payload[2]} != expected):
                raise ValueError('exact canonical scientific input capability required')
            data['payload'] = payload
            digest = oracle('entry')
            data['digest'] = digest
            if physical.repair_mechanism_identity is not original:
                raise ValueError('foreign repair alias before install')
            def route():
                if creator != (os.getpid(), get_ident()):
                    raise ValueError('static repair creating process/thread required')
                try:
                    check(); view(); status['capability_checks'] += 1
                    value = data['digest']
                    check(); view(); status['capability_checks'] += 1
                    status['calls'] += 1
                    return value
                except BaseException as error:
                    if status['first_failure'] is None: status['first_failure'] = repr(error)
                    raise
            status.update(phase='active', route=route, route_state=_state(route))
            physical.repair_mechanism_identity = route
            check()
            yield
            check(); view()
        except BaseException as error:
            primary = error
            if status['first_failure'] is None: status['first_failure'] = repr(error)
            raise
        finally:
            status['phase'] = 'closing'
            if physical.repair_mechanism_identity is status['route'] or physical.repair_mechanism_identity is original:
                physical.repair_mechanism_identity = original
                restored = True
            else:
                status['cleanup_errors'].append(ValueError('foreign repair alias preserved at exit'))
            if restored and digest is not None:
                try:
                    view()
                    if oracle('exit') != digest:
                        raise ValueError('original exit repair digest differs')
                except BaseException as error: status['cleanup_errors'].append(error)
            if capability is not None:
                try:
                    capability.release(); released = True
                except BaseException as error: status['cleanup_errors'].append(error)
            data.clear()
            capability = None
            status.update(phase='closed', route=None, route_state=None)
            if status['first_failure'] is None and status['cleanup_errors']:
                status['first_failure'] = repr(status['cleanup_errors'][0])
            status['receipt'] = _encode(dict(schema=SCHEMA, implementation=own,
                digest=digest, scientific_inputs=declared_inputs, calls=status['calls'],
                session=lease_binding['session'] if lease_binding else None,
                byte_lease_binding=lease_binding, canonical_source_closure=closure_evidence,
                per_route_capability_checks=status['capability_checks'],
                original_oracle_attempts=status['oracle_attempts'],
                original_oracle_invocations=status['oracle_successes'],
                original_pin_reads_in_successful_oracles=2*sum(status['oracle_successes'].values()),
                routed_pin_sha_json_fraction_digest_calls=0,
                per_call_pin_sha_digest_preserved=False, failure_timing_preserved=False,
                repair_identity_digest_cached=True, static_scientific_input_bytes_cached=True,
                numerical_result_cache=False, solver_result_cache=False, saved_record_cache=False,
                native_result_cache=False, capability_released=released,
                original_alias_restored=restored, all_normalization_cache_entries_cleared=not data,
                dependency_metadata_retained_only=True,
                first_failure=status['first_failure'],
                cleanup_errors=[repr(error) for error in status['cleanup_errors']],
                byte_lease_exit_verification_required=True, joint_clean_success_proven=False,
                process_must_exit_after_receipt=True, post_scope_consumer_reuse_allowed=False,
                formal_result=False, formal_execution_ready=False, resource_admission=False,
                native_execution_authorized=False))
            if lease_binding is not None:
                try:
                    transport.register_normalization_receipt(byte_lease, status['receipt'])
                except BaseException as error:
                    status['cleanup_errors'].append(error)
                    if status['first_failure'] is None: status['first_failure'] = repr(error)
                    failed = json.loads(status['receipt'])
                    failed.update(first_failure=status['first_failure'],
                        cleanup_errors=[repr(e) for e in status['cleanup_errors']])
                    status['receipt'] = _encode(failed)
            if status['cleanup_errors']:
                if primary is not None:
                    for error in status['cleanup_errors']: primary.add_note('static repair cleanup: '+repr(error))
                else: raise status['cleanup_errors'][0]

    def receipt():
        _RUNTIME()
        if creator != (os.getpid(), get_ident()) or status['phase'] != 'closed' or status['receipt'] is None:
            raise ValueError('closed static repair creator receipt required')
        return json.loads(status['receipt'])
    return scope(), receipt


def _install_runtime():
    namespace = globals()
    bindings = tuple((name, value, _state(value)) for name, value in namespace.items()
                     if not name.startswith('__'))
    dependencies = tuple((obj, name, getattr(obj, name), _state(getattr(obj, name)))
        for obj, names in ((_physical.json, ('loads',)), (_physical.Q, ('__new__', '__init__', 'numerator', 'denominator')))
        for name in names)
    def check():
        if namespace.get('_RUNTIME') is not check or any(namespace.get(name) is not value or _state(value) != state
                for name, value, state in bindings) or any(getattr(obj, name) is not value or _state(value) != state
                for obj, name, value, state in dependencies):
            raise ValueError('static repair helper or definition dependency changed')
    return check


_ORIGINAL = _physical.repair_mechanism_identity
_RUNTIME = _install_runtime()
