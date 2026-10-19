"""Byte-equivalent linear structure identity with invocation-local names."""
from hashlib import sha256
import json
from pathlib import Path

from . import continuous_grid_candidate as legacy
from . import continuous_grid_normal as encoding


def implementation_identity():
    return sha256(repr(tuple((m.__name__, sha256(Path(m.__file__).read_bytes()).hexdigest())
        for m in (legacy, encoding)) + (sha256(Path(__file__).read_bytes()).hexdigest(),)).encode()).hexdigest()


def _encode(value):
    kind = type(value)
    if value is None or kind in (str, int, bool):
        return value
    if kind in (tuple, list):
        return [kind.__name__, [_encode(item) for item in value]]
    return encoding._encode(value)


def _bytes(items):
    return json.dumps(_encode(items), ensure_ascii=True, allow_nan=False).encode()


def structure(model):
    names = {}
    def name(variable):
        key = id(variable)
        if key not in names:
            names[key] = variable.name
        return names[key]
    def active(component):
        while component is not None:
            if not component.active:
                return False
            component = component.parent_block()
        return True
    def number(x):
        return None if x is None else legacy._number(legacy.value(x)).hex()
    def linear(expr):
        repn = legacy.generate_standard_repn(expr, compute_values=True)
        if not repn.is_linear():
            raise ValueError('linear canonical model required')
        return (number(repn.constant), tuple(sorted((name(v), number(c))
            for v, c in zip(repn.linear_vars, repn.linear_coefs, strict=True))))
    items = (model.active,
        tuple(sorted((name(v), str(v.domain), number(v.lb), number(v.ub),
            v.fixed, number(v.value) if v.fixed else None)
            for v in model.component_data_objects(legacy.Var))),
        tuple(sorted((c.name, active(c), number(c.lower), number(c.upper), linear(c.body))
            for c in model.component_data_objects(legacy.Constraint, active=None))),
        tuple(sorted((o.name, active(o), int(o.sense), linear(o.expr))
            for o in model.component_data_objects(legacy.Objective, active=None))))
    return sha256(_bytes(items)).hexdigest()
