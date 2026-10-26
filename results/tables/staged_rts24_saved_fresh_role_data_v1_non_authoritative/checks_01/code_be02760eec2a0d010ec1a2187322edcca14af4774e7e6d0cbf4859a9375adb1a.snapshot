"""Construct the actual-path subset; retain the full contract compiler unchanged."""
from fractions import Fraction as Q

from src import staged_rts24_development_v1 as c


def reference_requests(fixture, plan, clean, method, hour):
    c.require(method in c.METHODS, "unknown evaluation method")
    observation = c.observe(fixture, plan, clean, hour)
    data = fixture.after if observation.commissioned else fixture.before
    firm, conditional = fixture.rights_after if observation.commissioned else fixture.rights_before
    capacity = firm+conditional
    reference = fixture.parameters.facility_factor*(observation.idle_mw+fixture.parameters.beta*observation.workload)+fixture.parameters.auxiliary_mw
    actual = fixture.selected[0] if fixture.actual_hour <= hour < fixture.actual_hour+fixture.actual_duration else c.Outage("normal")

    def request(role, meter, outage=c.Outage("normal"), objective="economic", anchor=None, curtail=Q(0), lower=None):
        return c.PointRequest(data, fixture.source_identity, plan, clean, hour, method, role, fixture.poi_bus,
            meter if lower is None else lower, meter, curtail, capacity, (firm, conditional), outage, objective, anchor, fixture.redispatch_fraction)

    base = request("reference_base_P0", reference)
    # The old full compiler validated all selected N-1 indices, even when unused
    # by the actual path. Preserve that rejection boundary without constructing 2S queries.
    branch_ids = {b.index for b in data.branches}
    generator_ids = {g.index for g in data.generators}
    for outage in fixture.selected:
        c.require(len(outage.branches)+len(outage.generators) == 1
                  and all(type(i) is int for i in (*outage.branches, *outage.generators))
                  and set(outage.branches) <= branch_ids and set(outage.generators) <= generator_ids,
                  "invalid selected N-1 query")
    requests = [base]
    if actual.branches or actual.generators:
        requests.append(request("reference_raw_need", reference, actual, "min_curtailment", base.identity, reference))
    if method != "instantaneous":
        for objective in ("min_meter", "max_meter"):
            requests.append(request("recovery_"+objective, capacity, actual, objective, base.identity, lower=Q(0)))
    return dict(observation=observation, reference_mw=reference, firm=firm, conditional=conditional,
        reference_connection_shortfall_mw=max(reference-capacity, Q(0)), actual_outage=actual, requests=tuple(requests),
        reference_node_upper_bound_including_actual=len(requests)+1, full_contract_requests_materialized=False)
