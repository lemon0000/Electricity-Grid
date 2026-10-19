"""One-shot callable seals for non-authoritative synchronous validation APIs."""
import dis
import sys
from threading import RLock, get_ident
from types import CodeType, FunctionType


def _cell(function, name):
    return dict(zip(function.__code__.co_freevars, function.__closure__ or ()))[name]


def _state(function, dynamic):
    return (function.__code__, function.__globals__, function.__defaults__, repr(function.__defaults__),
        function.__kwdefaults__, repr(function.__kwdefaults__), function.__closure__,
        tuple((cell, None if id(cell) in dynamic else cell.cell_contents)
            for cell in function.__closure__ or ()))


def _inventory(functions, namespace, dynamic):
    rows, globals_rows, seen, keys = [], [], set(), set()
    def names(code):
        result = {item.argval for item in dis.get_instructions(code) if item.opname == 'LOAD_GLOBAL'}
        for value in code.co_consts:
            if type(value) is CodeType:
                result.update(names(value))
        return result
    def visit(function):
        if isinstance(function, (staticmethod, classmethod)):
            visit(function.__func__)
            return
        if isinstance(function, property):
            for accessor in (function.fget, function.fset, function.fdel):
                visit(accessor)
            return
        if type(function) is not FunctionType or id(function) in seen:
            return
        seen.add(id(function))
        rows.append((function, _state(function, dynamic)))
        for cell in function.__closure__ or ():
            if id(cell) not in dynamic:
                visit(cell.cell_contents)
        visit(getattr(function, '__wrapped__', None))
        for name in names(function.__code__) | {'__builtins__'}:
            spaces = (function.__globals__,) if name in function.__globals__ else (
                function.__globals__, function.__builtins__)
            for space in spaces:
                key = id(space), name
                if key in keys:
                    continue
                keys.add(key)
                value = space.get(name)
                globals_rows.append((space, name, name in space, value))
                if type(value) is FunctionType and (value.__globals__ is namespace or value.__module__ == __name__):
                    visit(value)
    for function in functions:
        visit(function)
    return tuple(rows), tuple(globals_rows)


def _verify(inventory, dynamic):
    rows, globals_rows = inventory
    for function, before in rows:
        after = _state(function, dynamic)
        if (after[0] is not before[0] or after[1] is not before[1]
                or after[2] is not before[2] or after[3] != before[3]
                or after[4] is not before[4] or after[5] != before[5]
                or after[6] is not before[6]
                or any(cell is not old_cell or value is not old_value
                    for (cell, value), (old_cell, old_value) in zip(after[7], before[7]))):
            raise ValueError('callable code/default/global/closure changed')
    if any((name in space) != present or space.get(name) is not value
            for space, name, present, value in globals_rows):
        raise ValueError('callable used global or builtin shadow changed')


def make_runtime(namespace, label, *, alias='_RUNTIME'):
    """Return a captured checker and a private arm that accepts exactly once.

    Sealed tuples live in generator locals, outside writable closure containers.
    Named state cells change only between an original caller's begin/commit.
    An observed change without that handshake permanently invalidates the seal.
    """
    lock = RLock()
    verify = _verify
    getframe, thread = sys._getframe, get_ident
    def machine():
        sealed = None
        observed = ()
        pending = None
        response = ('ok', None)
        while True:
            command, payload = yield response
            response = ('ok', None)
            sender = getframe(1)
            sender_function = arm if command == 'arm' else check
            if sender.f_code is not sender_function.__code__ or sender.f_globals is not sender_function.__globals__:
                raise ValueError('original runtime transport caller required')
            if command == 'arm':
                if sealed is not None:
                    raise ValueError('runtime already armed')
                sealed = payload
                observed = tuple(cell.cell_contents for cell, _, _ in sealed[3])
                if any(value is not None for value in observed):
                    raise ValueError('state cells must be empty when armed')
                continue
            if sealed is None:
                raise ValueError('runtime is not armed')
            caller_code, caller_globals, creator, action, token = payload
            if pending is not None and creator != pending[6]:
                # An ordinary competing caller cannot poison the owner's tiny
                # begin/commit interval. It receives no token or state update.
                response = ('error', ValueError('nonreentrant validation transition active'))
                continue
            bindings, inventory, dynamic, transitions, constants, attributes, checks = sealed
            if namespace.get(alias) is not check:
                raise ValueError('runtime alias changed')
            if any(namespace.get(name) is not value for name, value in bindings):
                raise ValueError('module definition changed')
            verify(inventory, dynamic)
            for obj, name, value, raw in attributes:
                found = vars(obj).get(name) if raw else getattr(obj, name)
                if found is not value:
                    raise ValueError('validation dependency changed: ' +
                        getattr(obj, '__name__', type(obj).__name__) + '.' + name)
            if any(tuple(sorted(value.items())) != expected for value, expected in constants):
                raise ValueError('validation constants changed')
            current = tuple(cell.cell_contents for cell, _, _ in transitions)
            if action == 'commit':
                if pending is None or token is not pending[7]:
                    raise ValueError('original pending transition token required')
                index, old, target, original, code, space, owner, nonce = pending
                if caller_code is not code or caller_globals is not space or creator != owner:
                    raise ValueError('original transition completion caller required')
                if any(value is not before for n, (value, before) in enumerate(zip(current, observed)) if n != index):
                    raise ValueError('unrelated state cell changed during transition')
                changed = current[index]
                if ((target == 'empty' and changed is not None)
                        or (target == 'binding' and type(changed) is not tuple)
                        or (target == 'active' and type(changed) is not dict)
                        or changed is old):
                    raise ValueError('exact transition state change required')
                observed = current
                pending = None
            else:
                if any(value is not before for value, before in zip(current, observed)):
                    raise ValueError('state cell changed outside original transition')
                if action == 'cancel':
                    if (pending is None or token is not pending[7]
                            or caller_code is not pending[4] or caller_globals is not pending[5]):
                        raise ValueError('original transition cancellation required')
                    pending = None
                elif action is None:
                    if pending is not None:
                        raise ValueError('original transition completion missing')
                else:
                    if pending is not None:
                        raise ValueError('validation transition is nonreentrant')
                    selected = None
                    for index, (_, role, functions) in enumerate(transitions):
                        choices = ((functions, 'begin_binding', 'binding'),) if role == 'binding' else (
                            (functions[0], 'begin_active_claim', 'active'),
                            (functions[1], 'begin_active_clear', 'empty'))
                        for function, operation, target in choices:
                            if (action == operation and caller_code is function.__code__
                                    and caller_globals is function.__globals__):
                                selected = index, function, target
                    if selected is None:
                        raise ValueError('original transition begin caller required')
                    index, function, target = selected
                    old = current[index]
                    if (target == 'empty' and type(old) is not dict) or (target != 'empty' and old is not None):
                        raise ValueError('original transition predecessor required')
                    nonce = object()
                    pending = (index, old, target, function, caller_code, caller_globals, creator, nonce)
                    response = ('ok', nonce)
            for dependency_check in checks:
                dependency_check()
    generator = machine()
    next(generator)
    def check(*, transition=None, token=None):
        try:
            if generator.gi_code is not machine.__code__ or generator.gi_frame is None:
                raise ValueError('runtime seal is closed')
            caller = getframe(1)
            with lock:
                response = generator.send(('check', (caller.f_code, caller.f_globals, thread(), transition, token)))
            if response[0] == 'error':
                raise response[1]
            return response[1]
        except BaseException as error:
            if isinstance(error, (KeyboardInterrupt, SystemExit)):
                raise
            raise ValueError('definition-time ' + label + ' changed: ' + str(error)) from error
    def arm(*, transitions=(), attributes=(), checks=(), ignored=()):
        with lock:
            dynamic = frozenset(id(cell) for cell, _, _ in transitions)
            bindings = tuple((name, value) for name, value in namespace.items()
                if not name.startswith('__') and name not in ignored)
            functions = [value for _, value in bindings]
            functions.extend(value for _, _, value in attributes)
            functions.extend(checks)
            functions.extend((check, arm, machine))
            inventory = _inventory(functions, namespace, dynamic)
            constants = tuple((value, tuple(sorted(value.items()))) for name, value in bindings
                if name.isupper() and type(value) is dict)
            fixed_attributes = tuple((obj, name, value, vars(obj).get(name) is value)
                for obj, name, value in (*tuple(attributes), (sys, '_getframe', getframe)))
            generator.send(('arm', (bindings, inventory, dynamic, tuple(transitions), constants,
                fixed_attributes, tuple(checks))))
    return check, arm
