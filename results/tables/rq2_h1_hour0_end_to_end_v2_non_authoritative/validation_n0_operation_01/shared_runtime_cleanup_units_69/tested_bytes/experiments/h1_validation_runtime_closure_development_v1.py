"""One-shot callable seals for non-authoritative synchronous validation APIs."""
import dis
import sys
from threading import RLock
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
    Only two named state cells may change: one exact bind and an active registry.
    Each None -> value transition must occur inside its original transition code.
    """
    lock = RLock()
    verify = _verify
    def machine():
        sealed = None
        observed = ()
        while True:
            command, payload = yield
            if command == 'arm':
                if sealed is not None:
                    raise ValueError('runtime already armed')
                sealed = payload
                observed = tuple(None for _ in sealed[3])
                continue
            if sealed is None:
                raise ValueError('runtime is not armed')
            bindings, inventory, dynamic, transitions, constants, attributes, checks = sealed
            if namespace.get(alias) is not check:
                raise ValueError('runtime alias changed')
            if any(namespace.get(name) is not value for name, value in bindings):
                raise ValueError('module definition changed')
            verify(inventory, dynamic)
            if any(getattr(obj, name) is not value for obj, name, value in attributes):
                raise ValueError('validation dependency changed')
            if any(tuple(sorted(value.items())) != expected for value, expected in constants):
                raise ValueError('validation constants changed')
            updated = []
            caller_code, caller_globals = payload
            for (cell, role, transition), old in zip(transitions, observed):
                current = cell.cell_contents
                if current is not old:
                    if current is None and role == 'active':
                        pass
                    elif (old is None and caller_code is transition.__code__
                            and caller_globals is transition.__globals__
                            and ((role == 'binding' and type(current) is tuple)
                                or (role == 'active' and type(current) is dict))):
                        pass
                    else:
                        raise ValueError('validation state cell transition changed')
                updated.append(current)
            observed = tuple(updated)
            for dependency_check in checks:
                dependency_check()
    generator = machine()
    next(generator)
    def check():
        try:
            if generator.gi_code is not machine.__code__ or generator.gi_frame is None:
                raise ValueError('runtime seal is closed')
            caller = sys._getframe(1)
            with lock:
                generator.send(('check', (caller.f_code, caller.f_globals)))
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
            generator.send(('arm', (bindings, inventory, dynamic, tuple(transitions), constants,
                tuple(attributes), tuple(checks))))
    return check, arm
