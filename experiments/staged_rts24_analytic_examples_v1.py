"""Hand-specified three-bus points for independent DC arithmetic checks."""
from dataclasses import replace
from fractions import Fraction as Q

from src.grid.rts24 import Bus, Generator, Branch, Rts24Data
from src.staged_rts24_development_v1 import Outage, PointRequest, PointWitness, EconomicEvidence, bind, digest


def economic_evidence(query, point):
    d = query.request.data
    return EconomicEvidence(query.identity, digest(point), tuple((b.index, -1.) for b in d.buses),
        tuple((b.index, 0.) for b in d.branches), tuple((g.index, 0.) for g in d.generators),
        tuple((g.index, 0.) for g in d.generators), tuple((b.index, 0.) for b in d.branches), tuple((b.index, 0.) for b in d.branches))


def example(transformer=False, firm=50):
    # These are feasible-point fixtures, not solutions or minimum-curtailment claims.
    theta = (0., -.07, -.13) if transformer else (0., -.03, -.09)
    total, first_generation = (190, 160) if transformer else (150, 120)
    data = Rts24Data(100., tuple(Bus(i, 0.) for i in (1, 2, 3)),
        (Generator(0, 1, 0., 400., 0., 1.-2e-8*first_generation, 0., None, None, True),
         Generator(1, 2, 0., 100., 0., 1.-2e-8*30., 0., None, None, True),
         Generator(2, 3, 0., 100., 0., 1., 0., None, None, True)),
        (Branch(0, 1, 2, .1, 200., 200., 200., 2. if transformer else 1., .01 if transformer else 0., True),
         Branch(1, 2, 3, .1, 200., 200., 200., 1., 0., True),
         Branch(2, 1, 3, .1, 200., 200., 200., 1., 0., True)),
        1, "explicit_analytic_three_bus", "v1")
    base = PointRequest(data, "analytic_three_bus", "fixed", "analytic", 0, "full_temporal", "normal_contract_C", 3,
        Q(total), Q(total), Q(0), Q(total), (Q(firm), Q(total-firm)), Outage("normal"), "economic", None, Q(1, 2))
    base_bound = bind(base)
    base_point = PointWitness(base_bound.identity, float(total), 0., ((0, float(first_generation)), (1, 30.), (2, 0.)),
        tuple(zip((1, 2, 3), theta)), ((0, 30.), (1, 60.), (2, float(total-60))))
    base_economic = economic_evidence(base_bound, base_point)
    raw = replace(base, role="fault_raw_need", outages=Outage("branch_2", (2,)), objective="min_curtailment",
                  anchor_id=base.identity, curtailment_max=Q(total))
    raw_bound = bind(raw, base_bound, base_point, base_economic)
    fault_point = PointWitness(raw_bound.identity, float(total), float(total-60),
        ((0, 30.), (1, 30.), (2, 0.)), tuple(zip((1, 2, 3), theta)), ((0, 30.), (1, 60.), (2, 0.)))
    reference = replace(base, role="reference_base_P0")
    reference_bound = bind(reference)
    reference_point = replace(base_point, query_sha=reference_bound.identity)
    reference_economic = economic_evidence(reference_bound, reference_point)
    actual = replace(reference, role="actual_P", meter_min=Q(60), meter_max=Q(60),
                     outages=raw.outages, anchor_id=reference.identity)
    actual_bound = bind(actual, reference_bound, reference_point, reference_economic)
    actual_point = replace(fault_point, query_sha=actual_bound.identity, meter_load_mw=60., curtailment_mw=0.)
    return dict(base_query=base_bound, base_point=base_point, base_economic=base_economic, raw_query=raw_bound, raw_point=fault_point,
                actual_query=actual_bound, actual_point=actual_point)
