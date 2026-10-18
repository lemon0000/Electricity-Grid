from datetime import datetime
import json

import pytest
from pyomo.environ import ConcreteModel, Var, Constraint, Objective, Block, Binary, Param, maximize

from src.rq2_joint_deliverability_boundary_v1 import grid_structure_fast as api


def model():
    m = ConcreteModel()
    m.p = Param(initialize=2., mutable=True)
    m.x = Var([0, 1], bounds=(-3., 8.))
    m.c = Constraint(expr=m.p*m.x[0]+m.x[1] <= 7.)
    m.b = Block()
    m.b.z = Var(domain=Binary)
    m.b.c = Constraint(expr=m.x[0]-m.b.z >= -2.)
    m.o = Objective(expr=m.x[0]+3.*m.x[1]+m.b.z)
    return m


@pytest.mark.parametrize('mutation', [
    lambda m: None, lambda m: m.x[0].setlb(-4.), lambda m: m.x[1].setub(9.),
    lambda m: m.x[0].fix(1.), lambda m: m.x[1].set_value(3.),
    lambda m: m.b.deactivate(), lambda m: m.c.deactivate(), lambda m: m.o.deactivate(),
    lambda m: m.deactivate(), lambda m: m.o.set_value(m.x[0]+4.*m.x[1]),
    lambda m: m.o.__setattr__('sense', maximize), lambda m: m.p.set_value(3.),
    lambda m: m.x[0].__setattr__('domain', Binary),
    lambda m: m.add_component('quoted " unicode \u7535', Constraint(expr=m.x[0] <= 4.)),
])
def test_full_structure_matches_legacy_before_and_after_mutation(mutation):
    m = model()
    assert api.structure(m) == api.legacy._structure(m)
    mutation(m)
    assert api.structure(m) == api.legacy._structure(m)


def test_payload_bytes_match_legacy_encoder(monkeypatch):
    observed = []
    original = api.legacy._digest
    def capture(*items):
        observed.append(items)
        return original(*items)
    monkeypatch.setattr(api.legacy, '_digest', capture)
    m = model()
    assert api.structure(m) == api.legacy._structure(m)
    assert len(observed) == 1
    assert api._bytes(observed[0]) == json.dumps(api.encoding._encode(observed[0]),
        ensure_ascii=True, allow_nan=False).encode()


def test_no_name_cache_survives_an_invocation():
    m = model()
    first = api.structure(m)
    variable = m.x
    m.del_component('x')
    m.add_component('renamed', variable)
    assert api.structure(m) == api.legacy._structure(m) != first


def test_external_variable_reference_is_included():
    m = model(); external = ConcreteModel(); external.z = Var()
    m.o.set_value(m.x[0]+external.z)
    assert api.structure(m) == api.legacy._structure(m)


def test_nonlinear_rejection_matches():
    m = model(); m.o.set_value(m.x[0]**2)
    for compute in (api.structure, api.legacy._structure):
        with pytest.raises(ValueError, match='linear canonical model'): compute(m)


@pytest.mark.parametrize('value', [(.0, -.0, '"\\\u7535', True, None),
    {'z': 2., 'a': 1.}, datetime(2020, 1, 1), {1, 3}, [1, (2, 3)]])
def test_nonprimitive_fallback_preserves_wire_bytes(value):
    assert api._bytes(value) == json.dumps(api.encoding._encode(value),
        ensure_ascii=True, allow_nan=False).encode()
