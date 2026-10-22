"""Explicit analytic three-bus evidence for ordinary tests, never RTS24 results."""
from dataclasses import replace
from fractions import Fraction as Q
import json

from src.grid.rts24 import Bus, Generator, Branch, Rts24Data
from src import staged_rts24_development_v1 as c
from src.staged_deliverability_development_v1 import Parameters
from src.staged_rts24_child_optimality_v1 import ChildLpEvidence, reduction
from src.staged_rts24_causal_v1 import PointEvidence, HourEvidence


def analytic_fixture(late=False):
    parameters = Parameters(Q(60), Q(4, 5), Q(1), Q(1), Q(1), Q(0), Q(60), Q(60), Q(200), Q(200), Q(60), 5, 3, 0)
    data = Rts24Data(100., tuple(Bus(i, 0.) for i in (1, 2, 3)),
        (Generator(0, 1, 40., 300., 0., 1.-2e-8*100., 0., None, None, True),),
        tuple(Branch(i, a, b, .1, rate, rate, rate, 1., 0., True)
              for i, a, b, rate in ((0, 1, 2, 200.), (1, 2, 3, 60.), (2, 1, 3, 200.))),
        1, "explicit_analytic_causal_three_bus", "v1")
    early = ["200"]*5
    late_values = ["200", "200", "80", "80", "200"]
    business = dict(deadline_lag=2, flexible_fraction="1", prehistory_clean="200",
        equipment=[dict(id="analytic_module", start=0, lead=0, delay=0, capacity="200", idle_mw="0")],
        workload=dict(before="100", after="100", change_hour=3), clean_paths=dict(early=early, late=late_values if late else early))
    x = dict(max_call_mw="130", max_ramp_mw_per_hour="130", max_energy_mwh="260", max_duration_hours=3, max_events=5, minimum_rest_hours=0)
    identity = c.digest(dict(data=data, parameters=parameters, business=business, x=x, source="analytic_only_not_public_case"))
    return c.Fixture(data, data, 3, parameters, Q(1), json.dumps(business, sort_keys=True), (Q(20), Q(130)),
        (Q(20), Q(130)), json.dumps(x, sort_keys=True), (c.Outage("branch_2", (2,)),), 0, 2,
        (("delayed", 2), ("on_time", 0)), 1, 1, 0, 3, 5, Q(1, 2), identity)


def analytic_point(query, meter, curtail=0):
    net = float(meter)-float(curtail)
    if query.request.outages.branches:
        theta, flow = (0., -net/1000., -net/500.), (net, net, 0.)
    else:
        theta, flow = (0., -net/3000., -net/1500.), (net/3., net/3., 2.*net/3.)
    return c.PointWitness(query.identity, float(meter), float(curtail), ((0, net),),
                          tuple(zip((1, 2, 3), theta)), tuple(zip((0, 1, 2), flow)))


def analytic_economic(query, point):
    g = query.request.data.generators[0]
    gradient = 2*(g.cost_quadratic+1e-8)*point.generation_mw[0][1]+g.cost_linear
    return c.EconomicEvidence(query.identity, c.digest(point), tuple((i, -gradient) for i in (1, 2, 3)),
        ((0, 0.), (1, 0.), (2, 0.)), ((0, 0.),), ((0, 0.),), ((0, 0.), (1, 0.), (2, 0.)), ((0, 0.), (1, 0.), (2, 0.)))


def analytic_child(query):
    q = query.request
    fault = bool(q.outages.branches)
    if q.objective == "min_curtailment": meter, curtail = q.meter_max, q.meter_max-60
    elif q.objective == "min_meter": meter, curtail = Q(40), Q(0)
    else: meter, curtail = Q(60 if fault else 150), Q(0)
    point = analytic_point(query, meter, curtail)
    lam = (1., 1., 1.) if q.objective == "min_meter" else (0., 0., -1.) if fault else (0., 0., 0.)
    gl = ((0, 1. if q.objective == "min_meter" else 0.),)
    fu = tuple((i, 1. if fault and q.objective != "min_meter" and i == 1 else 0.) for i in (0, 1, 2))
    evidence = ChildLpEvidence(query.identity, c.digest(point), c.digest(reduction(query)), tuple(zip((1, 2, 3), lam)),
        ((0, 0.), (1, 0.), (2, 0.)), gl, ((0, 0.),), ((0, 0.), (1, 0.), (2, 0.)), fu,
        connection_dual=1. if q.objective == "max_meter" and not fault else 0.)
    return PointEvidence(query, point, child_lp=evidence)


def analytic_hour(fixture, state):
    h = c.hour_requests(fixture, state.plan, state.clean_path, state.method, state.next_hour)
    requests = {r.role: r for r in h["requests"] if not r.role.startswith("fault_")}
    base = c.bind(requests["reference_base_P0"])
    point = analytic_point(base, requests["reference_base_P0"].meter_min)
    root = PointEvidence(base, point, economic=analytic_economic(base, point))

    def child(role):
        if role not in requests: return None
        return analytic_child(c.bind(requests[role], base, point, root.economic))

    return HourEvidence(root, child("reference_raw_need"), child("recovery_min_meter"), child("recovery_max_meter"))


def analytic_actual(prepared, proposal):
    root = prepared.evidence.reference
    request = replace(root.query.request, role="actual_P", meter_min=proposal.power_mw, meter_max=proposal.power_mw,
        outages=prepared.actual_outage, anchor_id=root.query.request.identity)
    query = c.bind(request, root.query, root.point, root.economic)
    return PointEvidence(query, analytic_point(query, proposal.power_mw))
