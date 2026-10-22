"""Finite named runtime observations for the detached historical successor.

DRAFT_NONAUTHORITATIVE. These endpoint checks cover the enumerated slots and
concrete Path descriptors. They do not prove arbitrary dynamic input closure,
intermediate ABA freedom, or the behavior of native callable implementations.
"""
import builtins
import dis
import sys
from pathlib import Path
from types import CellType, CodeType, FunctionType, ModuleType

SCHEMA = 'h1_constructor_runtime_guard_development_v1'
MAX_FUNCTIONS = 2048
MAX_SLOTS = 16384
MAX_CLASSES = 512
_MISSING = object()
_MODULES = ('experiments.', 'src.', 'pathlib', 'ntpath', 'posixpath',
            'genericpath', 'json', 'dataclasses')


def function_state(function):
    return (function.__code__, function.__globals__, function.__defaults__,
            repr(function.__defaults__), function.__kwdefaults__,
            repr(function.__kwdefaults__), function.__closure__,
            tuple(cell.cell_contents for cell in function.__closure__ or ()))


def same_function(function, before):
    after = function_state(function)
    return (all(after[i] is before[i] for i in (0, 1, 2, 4, 6))
            and all(after[i] == before[i] for i in (3, 5))
            and len(after[7]) == len(before[7])
            and all(a is b for a, b in zip(after[7], before[7])))


def _codes(code):
    yield code
    for value in code.co_consts:
        if type(value) is CodeType:
            yield from _codes(value)


class NamedRuntimeSnapshot:
    """Identity observations, with hard collection bounds and no replay cache."""
    __slots__ = ('functions', 'slots', 'classes', 'objects', 'summary')

    def __init__(self, roots):
        functions, slots, classes, objects = [], [], [], []
        seen_functions, seen_slots, seen_classes, seen_objects = set(), set(), set(), set()

        def slot(namespace, name, label):
            key = (id(namespace), name)
            if key not in seen_slots:
                if len(slots) >= MAX_SLOTS:
                    raise ValueError('named runtime slot cap exceeded')
                seen_slots.add(key)
                slots.append((namespace, name, namespace.get(name, _MISSING), label))

        def visit(value, label, forced=False):
            module = getattr(value, '__module__', '') or ''
            allowed = forced or module.startswith(_MODULES)
            if type(value) is FunctionType and allowed:
                if id(value) in seen_functions:
                    return
                if len(functions) >= MAX_FUNCTIONS:
                    raise ValueError('named runtime function cap exceeded')
                seen_functions.add(id(value))
                functions.append((value, function_state(value), label))
                codes = tuple(_codes(value.__code__))
                names = set(name for code in codes for name in code.co_names)
                global_names = set(op.argval for code in codes for op in dis.get_instructions(code)
                                   if op.opname in ('LOAD_GLOBAL', 'LOAD_NAME'))
                for name in sorted(global_names):
                    slot(value.__globals__, name, label + ':global:' + name)
                    item = value.__globals__.get(name, _MISSING)
                    if item is _MISSING:
                        slot(value.__builtins__, name, label + ':builtin:' + name)
                        item = value.__builtins__.get(name, _MISSING)
                    if type(item) is ModuleType:
                        for attribute in sorted(names & vars(item).keys()):
                            slot(vars(item), attribute, label + ':module:' + item.__name__ + '.' + attribute)
                            visit(vars(item)[attribute], label + '.' + attribute)
                    else:
                        visit(item, label + '.' + name)
                # Observe literal module attribute chains such as
                # candidate.history._inventory and model_api.stage_order.
                for code in codes:
                    instructions=tuple(dis.get_instructions(code))
                    for index,op in enumerate(instructions):
                        if op.opname not in ('LOAD_GLOBAL','LOAD_NAME'):
                            continue
                        item=value.__globals__.get(op.argval,_MISSING)
                        for following in instructions[index+1:]:
                            if following.opname not in ('LOAD_ATTR','LOAD_METHOD') or type(item) is not ModuleType:
                                break
                            slot(vars(item),following.argval,label+':attribute_chain:'+following.argval)
                            item=vars(item).get(following.argval,_MISSING)
                            visit(item,label+':attribute_chain:'+following.argval)
                for i, cell in enumerate(value.__closure__ or ()):
                    visit(cell.cell_contents, label + ':cell:' + str(i),
                          forced=type(cell.cell_contents) is FunctionType)
            elif isinstance(value, type) and allowed:
                if value in seen_classes:
                    return
                if len(classes) >= MAX_CLASSES:
                    raise ValueError('named runtime class cap exceeded')
                seen_classes.add(value)
                classes.append((value, tuple(vars(value)), value.__bases__, value.__mro__, label))
                for name, item in vars(value).items():
                    slot(vars(value), name, label + ':descriptor:' + name)
                    if isinstance(item, (staticmethod, classmethod)):
                        visit(item.__func__, label + '.' + name)
                    elif isinstance(item, property):
                        for role in ('fget', 'fset', 'fdel'):
                            visit(getattr(item, role), label + '.' + name + '.' + role)
                    else:
                        visit(item, label + '.' + name)
                for parent in value.__bases__:
                    visit(parent, label + ':base')
            elif type(value).__module__.startswith(('json.', 'pathlib')) and hasattr(value, '__dict__'):
                if id(value) in seen_objects:
                    return
                seen_objects.add(id(value))
                # Shallow configuration only; mutable internals are not a closure proof.
                objects.append((value, tuple(vars(value)), label))
                for name, item in vars(value).items():
                    slot(vars(value), name, label + ':configuration:' + name)
                visit(type(value), label + ':type')

        for label, namespace, name in roots:
            slot(namespace, name, label)
            visit(namespace.get(name, _MISSING), label, forced=True)
        self.functions, self.slots = tuple(functions), tuple(slots)
        self.classes, self.objects = tuple(classes), tuple(objects)
        self.summary = dict(schema=SCHEMA, functions=len(functions), slots=len(slots),
                            classes=len(classes), shallow_objects=len(objects),
                            complete_dynamic_input_closure_proved=False,
                            unobserved_between_bookends_ABA_covered=False)

    def check(self):
        for namespace, name, expected, label in self.slots:
            if namespace.get(name, _MISSING) is not expected:
                raise ValueError('named runtime slot changed: ' + label)
        for function, before, label in self.functions:
            if not same_function(function, before):
                raise ValueError('named runtime callable changed: ' + label)
        for kind, names, bases, mro, label in self.classes:
            if tuple(vars(kind)) != names or kind.__bases__ is not bases or kind.__mro__ is not mro:
                raise ValueError('named runtime class changed: ' + label)
        for value, names, label in self.objects:
            if tuple(vars(value)) != names:
                raise ValueError('named runtime configuration changed: ' + label)


def runtime_roots(model, packet_source, support):
    roots = []
    # All module-defined numerical and packet functions; recursively observed
    # imported project helpers, plus explicitly forced borrowed aliases.
    for module in (model, packet_source, support, sys.modules[__name__]):
        for name, value in vars(module).items():
            if type(value) is FunctionType:
                roots.append((module.__name__ + '.' + name, vars(module), name))
    roots.append(('runtime_snapshot_definition', globals(), 'NamedRuntimeSnapshot'))
    for kind in type(Path()).__mro__:
        roots.append(('concrete_Path_MRO:' + kind.__name__, {'kind': kind}, 'kind'))
    flavour = getattr(type(Path()), '_flavour', None)
    if flavour is not None:
        roots.append(('concrete_Path_flavour', {'kind': type(flavour)}, 'kind'))
    return tuple(roots)


def frozen_teardown(original):
    """Clone only the known three-function cleanup graph and its closure cells.

    The returned route shares no mutable function/globals/cell with the exported
    helper. It deliberately preserves its exact Reader MRO and creator rules.
    """
    copied = {}
    safe_builtins = {name: getattr(builtins, name) for name in (
        'type', 'ValueError', 'BaseException', 'getattr', 'setattr',
        'reversed', 'list', '__build_class__')}

    def clone(function):
        if type(function) is not FunctionType or function.__defaults__ is not None or function.__kwdefaults__ is not None:
            raise ValueError('exact no-default teardown functions required')
        if id(function) in copied:
            return copied[id(function)]
        cells = tuple(CellType(clone(cell.cell_contents) if type(cell.cell_contents) is FunctionType
                               else cell.cell_contents) for cell in function.__closure__ or ())
        names = {op.argval for code in _codes(function.__code__) for op in dis.get_instructions(code)
                 if op.opname == 'LOAD_GLOBAL'}
        if names - safe_builtins.keys():
            raise ValueError('unregistered frozen teardown global')
        namespace = {'__builtins__': dict(safe_builtins), '__name__': __name__}
        value = FunctionType(function.__code__, namespace, function.__name__, None, cells or None)
        copied[id(function)] = value
        return value

    result = clone(original)
    if len(copied) != 3:
        raise ValueError('exact three-function teardown graph required')
    return result
