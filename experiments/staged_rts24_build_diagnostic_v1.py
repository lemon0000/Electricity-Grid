"""Registered, bounded public-network build-only diagnostic; no solver calls."""
import time
IMPORT_START = time.perf_counter()
from datetime import datetime, timezone
IMPORT_START_UTC = datetime.now(timezone.utc).isoformat()

import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import psutil
import src.staged_rts24_development_v1 as c
from src.staged_rts24_audit_v1 import audit_point, audit_economic_base
from experiments.staged_rts24_analytic_examples_v1 import example

OUTPUT = ROOT/"results/tables/staged_deliverability_rts24_v1_non_authoritative/build_01"
PRIOR = ROOT/"results/tables/staged_deliverability_c_v1_non_authoritative/saved_audit_01/audit.json"
PRIOR_SHA256 = "9a04b13e1778614ecefac1890c0f68ab30d81dd5990b7be2cf6c745763ff6e90"
SOURCES = ("configs/staged_deliverability_rts24_v1.DRAFT.yaml", "src/staged_rts24_development_v1.py",
    "src/staged_rts24_audit_v1.py", "experiments/staged_rts24_analytic_examples_v1.py",
    "experiments/staged_rts24_build_diagnostic_v1.py", "tests/test_staged_rts24_development_v1.py",
    "docs/model_spec/staged_deliverability_rts24_development_v1.md",
    "docs/plan/staged_deliverability_c_rts24_build_contract_v1.md")
ROLES = {"start.json", "network_frames.json", "query_dag.json", "analytic_points.json",
         "model_shapes.json", "report.json", "events.jsonl"}
LIMITS = dict(wall_seconds=60, no_progress_seconds=20, rss_bytes=512*1024**2,
              output_bytes=16*1024**2, single_bytes=4*1024**2, files=16)


def require(value, message):
    if not value: raise ValueError(message)


def stamp(path):
    require(path.is_file() and not path.is_symlink(), "nonregular evidence file")
    raw = path.read_bytes()
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def write(path, value):
    raw = (json.dumps(c.plain(value), sort_keys=True, indent=2, allow_nan=False)+"\n").encode("utf-8")
    require(len(raw) <= LIMITS["single_bytes"], "diagnostic file size limit")
    with path.open("xb") as stream:
        stream.write(raw); stream.flush()


def fingerprints():
    from pypower import case24_ieee_rts
    return dict(repository={n: stamp(ROOT/n) for n in SOURCES}, prior_audit=stamp(PRIOR),
                public_case=stamp(Path(case24_ieee_rts.__file__)),
                versions={n: version(n) for n in ("PYPOWER", "Pyomo", "PyYAML", "numpy", "scipy", "psutil")},
                python=sys.version, executable=sys.executable)


def preserved():
    require(stamp(PRIOR)["sha256"] == PRIOR_SHA256, "published prior audit SHA changed")
    prior = json.loads(PRIOR.read_text(encoding="utf-8"))
    overlap = set(prior["saved_files"]) & set(prior["repository_pins"])
    require(all(prior["saved_files"][n] == prior["repository_pins"][n] for n in overlap), "conflicting old evidence pins")
    files = {**prior["saved_files"], **prior["repository_pins"]}
    require(all(stamp(ROOT/n) == expected for n, expected in files.items()), "B1-B3 saved or source bytes changed")
    b3 = json.loads((ROOT/"results/tables/staged_deliverability_b3_v1_non_authoritative/attempt_01/report.json").read_text(encoding="utf-8"))["fingerprints"]
    external = {n: stamp(Path(item["path"])) for n, item in b3["external_selected"].items()}
    require(external == prior["selected_external"], "B1-B3 selected external bytes changed")
    require(all(version(n) == expected for n, expected in b3["versions"].items()), "B1-B3 selected dependency version changed")
    return dict(files=len(prior["saved_files"]), repository_pins=len(prior["repository_pins"]), unique_files=len(files),
                selected_external=external, expected=files)


def inventory(output):
    paths = list(output.iterdir())
    require(all(p.is_file() and not p.is_symlink() for p in paths), "unexpected nonregular diagnostic artifact")
    return {p.name: stamp(p) for p in sorted(paths) if p.name != "completion.json"}


def verify_completion(output, supplemental=()):
    require(stamp(output/"completion.json")["bytes"] <= LIMITS["single_bytes"], "completion size limit")
    completion = json.loads((output/"completion.json").read_text(encoding="utf-8"))
    require(completion["status"] == "build_only_diagnostic_completed" and completion["authority"] == "DRAFT_NONAUTHORITATIVE", "wrong completion scope")
    actual = inventory(output)
    actual = {n: item for n, item in actual.items() if n not in supplemental}
    require(set(actual) == ROLES and actual == completion["inventory"] and not (output/"failure.json").exists(), "completion inventory differs")
    return completion


def run(output=OUTPUT):
    require(output == OUTPUT, "unregistered diagnostic output")
    output.mkdir(parents=True, exist_ok=False)
    begin = IMPORT_START if __name__ == "__main__" else time.perf_counter()
    started_at_utc = IMPORT_START_UTC if __name__ == "__main__" else datetime.now(timezone.utc).isoformat()
    last = begin
    peak = 0
    stages = {}
    counts = dict(hour_templates=0, query_descriptors=0, logical_node_upper_bound_including_actual=0,
                  models_built=0, analytic_points_audited=0, economic_kkt_audited=0,
                  corrupt_point_rejected=0, missing_public_anchor_rejected=0, solver_factory_requests=0)
    original = []

    def guard(stage):
        nonlocal last, peak
        now = time.perf_counter()
        rss = psutil.Process().memory_info().rss
        peak = max(peak, rss)
        paths = list(output.iterdir())
        require(now-begin <= LIMITS["wall_seconds"] and now-last <= LIMITS["no_progress_seconds"]
                and rss <= LIMITS["rss_bytes"], "diagnostic time or RSS limit")
        require(all(p.is_file() and not p.is_symlink() and p.stat().st_size <= LIMITS["single_bytes"] for p in paths)
                and len(paths) <= LIMITS["files"] and sum(p.stat().st_size for p in paths) <= LIMITS["output_bytes"], "diagnostic output limit")
        with (output/"events.jsonl").open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(dict(stage=stage, elapsed=now-begin, rss=rss))+"\n")
        last = now

    def timed(name, call):
        start = time.perf_counter()
        value = call()
        stages[name] = stages.get(name, 0.)+time.perf_counter()-start
        guard(name)
        return value

    def denied(*args, **kwargs):
        counts["solver_factory_requests"] += 1
        raise ValueError("solver request forbidden in build-only diagnostic")

    def shape(bound):
        model = c.build_point_model(bound)
        counts["models_built"] += 1
        return model

    try:
        import pyomo.environ as pyo
        import src.grid.dc_opf as dc
        import src.grid.network_grid_need as need
        import src.grid.scopf as security
        for module in (pyo, dc, need, security):
            original.append((module, module.SolverFactory)); module.SolverFactory = denied
        before = fingerprints()
        old = timed("preserved_before", preserved)
        write(output/"start.json", dict(authority="DRAFT_NONAUTHORITATIVE", scope=c.SCOPE,
            limits=LIMITS, started_at_utc=started_at_utc, fingerprints=before,
            preserved_files=old["files"], preserved_repository_pins=old["repository_pins"], preserved_unique_files=old["unique_files"],
            preserved_selected_external=old["selected_external"]))
        fixture = timed("load_fixture", c.load_fixture)
        write(output/"network_frames.json", dict(before=fixture.before, after=fixture.after,
            source_identity=fixture.source_identity, selected=fixture.selected, effective_x_envelope=json.loads(fixture.x_envelope_json)))
        templates = []
        for plan, clean, hour in (("on_time", "early", 0), ("on_time", "early", 1), ("on_time", "early", 2), ("delayed", "late", 3)):
            for method in c.METHODS:
                def compile_one():
                    h = c.hour_requests(fixture, plan, clean, method, hour)
                    requests = h.pop("requests")
                    nodes = [dict(request_identity=r.identity, role=r.role, outage=r.outages.name, parent_request_identity=r.anchor_id,
                        binding_status="request_descriptor_only" if r.anchor_id is None else "unbound_missing_public_economic_parent",
                        bound_query_identity=None,
                        meter_min=r.meter_min, meter_max=r.meter_max, curtailment_max=r.curtailment_max, rights=r.rights) for r in requests]
                    return dict(plan=plan, clean=clean, method=method, hour=hour, **h, nodes=nodes)
                item = timed("compile_queries", compile_one)
                counts["hour_templates"] += 1; counts["query_descriptors"] += len(item["nodes"])
                counts["logical_node_upper_bound_including_actual"] += item["solver_node_upper_bound_including_actual"]
                templates.append(item)
        write(output/"query_dag.json", templates)
        shapes, points = [], []
        for hour in (0, 2):
            request = c.hour_requests(fixture, "on_time", "early", "full_temporal", hour)["requests"][0]
            bound = c.bind(request)
            model = timed("public_model_build", lambda: shape(bound))
            shapes.append(dict(source="public_case", hour=hour, request_identity=request.identity, bound_query_identity=bound.identity,
                variables=len(list(model.component_data_objects(pyo.Var))), constraints=len(list(model.component_data_objects(pyo.Constraint)))))
        raw = next(r for r in c.hour_requests(fixture, "on_time", "early", "full_temporal", 1)["requests"] if r.role == "fault_raw_need")
        try: c.bind(raw)
        except ValueError: counts["missing_public_anchor_rejected"] += 1
        else: raise ValueError("public corrective accepted without a base")
        from dataclasses import replace
        for transformer in (False, True):
            e = timed("analytic_fixture_and_binding", lambda: example(transformer))
            economic = timed("economic_kkt_audit", lambda: audit_economic_base(e["base_query"], e["base_point"], e["base_economic"]))
            require(economic["economic_kkt_satisfied"], "analytic economic KKT failed")
            counts["economic_kkt_audited"] += 1
            for role in ("base", "raw", "actual"):
                bound, point = e[role+"_query"], e[role+"_point"]
                audit = timed("analytic_point_audit", lambda: audit_point(bound, point))
                require(audit["point_constraints_satisfied"], "analytic point audit failed")
                counts["analytic_points_audited"] += 1
                model = timed("analytic_model_build", lambda: shape(bound))
                model.meter.value, model.curtailment.value = point.meter_load_mw, point.curtailment_mw
                for name, pairs in (("generation", point.generation_mw), ("angle", point.angles_rad), ("flow", point.flows_mw)):
                    for i, value in pairs: getattr(model, name)[i].value = value
                require(c.point_from_model(bound, model) == point, "analytic extraction differs")
                shapes.append(dict(source="analytic_triangle", transformer=transformer, role=role,
                    variables=len(list(model.component_data_objects(pyo.Var))), constraints=len(list(model.component_data_objects(pyo.Constraint)))))
                points.append(dict(transformer=transformer, role=role, query=bound, point=point, audit=audit,
                                   economic=economic if role == "base" else None))
        corrupt = replace(e["raw_point"], flows_mw=((0, 30.), (1, 60.), (2, 1.)))
        require(not audit_point(e["raw_query"], corrupt)["point_constraints_satisfied"], "corrupt point accepted")
        counts["corrupt_point_rejected"] += 1
        write(output/"analytic_points.json", points); write(output/"model_shapes.json", shapes)
        require(counts == dict(hour_templates=12, query_descriptors=1699, logical_node_upper_bound_including_actual=1711,
            models_built=8, analytic_points_audited=6, economic_kkt_audited=2, corrupt_point_rejected=1,
            missing_public_anchor_rejected=1, solver_factory_requests=0), "registered diagnostic counts differ")
        require(timed("preserved_after", preserved) == old and fingerprints() == before, "source/evidence bookend drift")
        guard("final_report")
        write(output/"report.json", dict(authority="DRAFT_NONAUTHORITATIVE", scope=c.SCOPE, counts=counts,
            fingerprints=before, stage_seconds=stages, elapsed_before_report_seconds=time.perf_counter()-begin,
            observed_at_utc_before_report=datetime.now(timezone.utc).isoformat(),
            sampled_peak_rss_before_report_bytes=peak, public_network_solver_results=False,
            main_experiment_performance_review_complete=False, old_bytes_unchanged=True))
        guard("before_completion")
        write(output/"completion.json", dict(status="build_only_diagnostic_completed", authority="DRAFT_NONAUTHORITATIVE",
            observed_at_utc_before_completion=datetime.now(timezone.utc).isoformat(),
            sampled_peak_rss_before_completion_bytes=peak, inventory=inventory(output)))
        verify_completion(output)
        # Check limits without appending to the already inventoried event file.
        final_rss = psutil.Process().memory_info().rss
        require(time.perf_counter()-begin <= LIMITS["wall_seconds"] and final_rss <= LIMITS["rss_bytes"]
                and sum(p.stat().st_size for p in output.iterdir()) <= LIMITS["output_bytes"], "final resource limit")
        print(json.dumps(dict(status="build_only_diagnostic_completed", elapsed_seconds=time.perf_counter()-begin,
                             finished_at_utc=datetime.now(timezone.utc).isoformat(),
                             sampled_peak_rss_bytes=max(peak, final_rss), counts=counts)))
    except BaseException as error:
        try: write(output/"failure.json", dict(status="build_only_diagnostic_failed", error=repr(error), counts=counts, elapsed=time.perf_counter()-begin))
        except BaseException: pass
        raise
    finally:
        for module, function in original: module.SolverFactory = function


if __name__ == "__main__": run()
