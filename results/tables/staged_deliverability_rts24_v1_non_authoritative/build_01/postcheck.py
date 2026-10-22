"""Read back the fixed build_01 artifacts; no model construction or solving."""
from collections import Counter
from fractions import Fraction as Q
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
import experiments.staged_rts24_build_diagnostic_v1 as d
import src.staged_rts24_development_v1 as c
from src.staged_rts24_audit_v1 import audit_point, audit_economic_base
from src.grid.rts24 import Rts24Data, Bus, Generator, Branch

SUPPLEMENTAL = ("launcher.json", "postcheck.py", "verification.json", "preseal_findings.json", "validation_report.md")


def witness(value):
    if value is None: return None
    raw = dict(value)
    for name in ("generation_mw", "angles_rad", "flows_mw"):
        raw[name] = tuple(tuple(row) for row in raw[name])
    return c.PointWitness(**raw)


def economic(value):
    if value is None: return None
    return c.EconomicEvidence(**{name: tuple(tuple(row) for row in item) if name.endswith("duals") else item
                                for name, item in value.items()})


def bound(value):
    if value is None: return None
    raw = dict(value["request"])
    data = dict(raw["data"])
    for name, cls in (("buses", Bus), ("generators", Generator), ("branches", Branch)):
        data[name] = tuple(cls(**row) for row in data[name])
    raw["data"] = Rts24Data(**data)
    for name in ("meter_min", "meter_max", "curtailment_max", "connection_capacity", "redispatch_fraction", "economic_regularization_quadratic"):
        raw[name] = Q(raw[name])
    raw["rights"] = tuple(Q(v) for v in raw["rights"])
    raw["outages"] = c.Outage(raw["outages"]["name"], tuple(raw["outages"]["branches"]), tuple(raw["outages"]["generators"]))
    result = c.BoundQuery(c.PointRequest(**raw), bound(value["base_query"]), witness(value["base_point"]), economic(value["base_economic"]))
    d.require(c.plain(result) == value, "saved bound-query roundtrip differs")
    return result


def check():
    begin = time.perf_counter()
    output = Path(__file__).resolve().parent
    d.require(output == d.OUTPUT, "wrong saved diagnostic root")
    counts = Counter(solver_factory_requests=0)
    original = []

    def denied(*args, **kwargs):
        counts["solver_factory_requests"] += 1
        raise ValueError("solver request forbidden in saved readback")

    try:
        import pyomo.environ as pyo
        import src.grid.dc_opf as dc
        import src.grid.network_grid_need as need
        import src.grid.scopf as security
        for module in (pyo, dc, need, security):
            original.append((module, module.SolverFactory)); module.SolverFactory = denied
        completion = d.verify_completion(output, SUPPLEMENTAL)
        before = d.fingerprints()
        report = json.loads((output/"report.json").read_text(encoding="utf-8"))
        start = json.loads((output/"start.json").read_text(encoding="utf-8"))
        d.require(before == report["fingerprints"] == start["fingerprints"], "bound sources/environment changed")
        old = d.preserved()
        fixture = c.load_fixture()
        frames = json.loads((output/"network_frames.json").read_text(encoding="utf-8"))
        d.require(frames == c.plain(dict(before=fixture.before, after=fixture.after, source_identity=fixture.source_identity,
            selected=fixture.selected, effective_x_envelope=json.loads(fixture.x_envelope_json))), "saved network frames differ")
        templates = json.loads((output/"query_dag.json").read_text(encoding="utf-8"))
        roles = Counter()
        root_nodes = 0
        all_request_ids = []
        for item in templates:
            fresh = c.hour_requests(fixture, item["plan"], item["clean"], item["method"], item["hour"])
            requests = fresh.pop("requests")
            metadata = {k: v for k, v in item.items() if k not in ("plan", "clean", "method", "hour", "nodes")}
            d.require(metadata == c.plain(fresh), "saved hour inputs differ")
            d.require(len(requests) == len(item["nodes"]), "saved request count differs")
            local_ids = {r.identity for r in requests}
            for request, node in zip(requests, item["nodes"]):
                expected = dict(request_identity=request.identity, role=request.role, outage=request.outages.name,
                    parent_request_identity=request.anchor_id,
                    binding_status="request_descriptor_only" if request.anchor_id is None else "unbound_missing_public_economic_parent",
                    bound_query_identity=None, meter_min=request.meter_min, meter_max=request.meter_max,
                    curtailment_max=request.curtailment_max, rights=request.rights)
                d.require(node == c.plain(expected), "saved request descriptor differs")
                d.require(request.anchor_id is None or request.anchor_id in local_ids, "missing local parent request")
                root_nodes += request.anchor_id is None
                roles[request.role] += 1
                all_request_ids.append(request.identity)
        d.require(len(templates) == 12 and len(all_request_ids) == len(set(all_request_ids)) == 1699 and root_nodes == 24,
                  "DAG counts/identity uniqueness differ")
        points = json.loads((output/"analytic_points.json").read_text(encoding="utf-8"))
        for item in points:
            query, point = bound(item["query"]), witness(item["point"])
            audited = audit_point(query, point)
            d.require(audited == item["audit"] and audited["point_constraints_satisfied"] and not audited["minimum_established"],
                      "saved analytic point audit differs")
            counts["saved_points_reaudited"] += 1
            if item["role"] == "base":
                # Unanchored base evidence is saved in its child, while item.economic is the original audit result.
                child = next(p for p in points if p["role"] == "raw" and p["transformer"] == item["transformer"])
                evidence = economic(child["query"]["base_economic"])
                audited_economic = audit_economic_base(query, point, evidence)
                d.require(audited_economic == item["economic"] and audited_economic["economic_kkt_satisfied"], "saved KKT audit differs")
                counts["saved_kkt_reaudited"] += 1
        d.require(counts["saved_points_reaudited"] == 6 and counts["saved_kkt_reaudited"] == 2, "saved analytic counts differ")
        shapes = json.loads((output/"model_shapes.json").read_text(encoding="utf-8"))
        d.require(len(shapes) == 8 and all((s["variables"], s["constraints"]) == ((97, 64) if s["source"] == "public_case" else (11, 8))
                  for s in shapes), "saved model shapes differ")
        launcher = json.loads((output/"launcher.json").read_text(encoding="utf-8"))
        terminal = json.loads(launcher["stdout"])
        d.require(launcher["exit_code"] == 0 and terminal["counts"] == report["counts"] and terminal["counts"]["solver_factory_requests"] == 0,
                  "saved terminal differs")
        core = {**completion["inventory"], "completion.json": d.stamp(output/"completion.json")}
        d.require(launcher["core_machine_files"] == len(core) == 8 and launcher["core_machine_bytes"] == sum(v["bytes"] for v in core.values()),
                  "saved core byte accounting differs")
        d.require(terminal["elapsed_seconds"] <= launcher["interpreter_start_to_exit_seconds"] <= d.LIMITS["wall_seconds"]
                  and terminal["sampled_peak_rss_bytes"] <= d.LIMITS["rss_bytes"], "saved resource limit differs")
        d.require(d.preserved() == old and d.fingerprints() == before and counts["solver_factory_requests"] == 0, "readback bookend differs")
        d.verify_completion(output, SUPPLEMENTAL)
        return dict(status="saved_build_readback_completed", authority="DRAFT_NONAUTHORITATIVE", elapsed_seconds=time.perf_counter()-begin,
            counts=dict(counts), dag=dict(templates=12, request_descriptors=1699, root_requests=24, child_requests=1675,
                future_actual_slots=12, logical_upper_bound=1711, roles=dict(roles), completed_public_network_solves=0),
            core_inventory=core, postcheck_source=d.stamp(Path(__file__)),
            preserved={k: v for k, v in old.items() if k != "expected"}, fingerprints=before,
            public_network_results=False, main_experiment_performance_review_complete=False)
    finally:
        for module, function in original: module.SolverFactory = function


if __name__ == "__main__": print(json.dumps(check(), sort_keys=True, indent=2))
