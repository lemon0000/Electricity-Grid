"""B2 fixed-balance DC corridor: numerical network checks, never certification.

The supported network is two buses/two parallel lines, one source, no shift.
PYPOWER solves every saved operating point; exact bounds only serve this scope.
"""
from dataclasses import dataclass, replace
from fractions import Fraction as Q
import hashlib
import json
from math import isfinite
from pathlib import Path

import numpy as np
import yaml
from pypower.makeBdc import makeBdc
from pypower.dcpf import dcpf
from pypower.idx_bus import BUS_I
from pypower.idx_brch import F_BUS, T_BUS, BR_X, TAP, SHIFT, BR_STATUS

from src.grid.rts24 import Bus, Generator, Branch, Rts24Data
from src.staged_deliverability_development_v1 import (
    StageState, advance, initialize, load_small_case, plain, power_mapping,
    _exact, _keys, _integer, _unique_pairs,
)

ROOT = Path(__file__).resolve().parents[1]
TOL = 1e-9


def require(condition, message):
    if not condition:
        raise ValueError(message)


def rational(value):
    require(not isinstance(value, bool) and isfinite(float(value)), "invalid network quantity")
    return Q(str(value))


def library_float(value):
    result = float(value)
    require(isfinite(result) and Q(str(result)) == value, "network decimal loses input precision")
    return result


@dataclass(frozen=True)
class NetworkConfig:
    before: Rts24Data
    after: Rts24Data
    poi_bus: int
    angle_limit: Q
    project_start: int
    project_lead: int
    delays: tuple[tuple[str, int], ...]
    actual_outages: tuple[tuple[int, int], ...]
    selected_outages: tuple[int, ...]
    rights_before: tuple[Q, Q]
    rights_after: tuple[Q, Q]
    hourly_ramp: Q
    max_x_call: Q
    max_x_ramp: Q
    max_x_energy: Q
    max_x_duration: int
    max_x_events: int
    x_minimum_rest: int
    business_fixture: str
    business_sha256: str


def load_config(path):
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    _keys(raw, "status source_class business_fixture business_sha256 network rights x_envelope")
    require(raw["status"] == "DRAFT_NONAUTHORITATIVE" and raw["source_class"] == "mechanism_assumption",
            "development mechanism inputs required")
    n, rights, x = raw["network"], raw["rights"], raw["x_envelope"]
    _keys(n, "base_mva source_bus poi_bus background_mw generator_max_mw hourly_generator_ramp_mw reactance_pu angle_limit_rad line_rating_before_mw line_rating_after_mw project_start project_lead delays actual_outages selected_outages")
    _keys(rights, "firm_before_mw conditional_before_mw firm_after_mw conditional_after_mw")
    _keys(x, "response_model max_call_mw max_ramp_mw_per_hour max_energy_mwh max_duration_hours max_events minimum_rest_hours")
    _keys(n["delays"], "on_time delayed")
    require(x["response_model"] == "preventive_hourly_declared_line_outage", "unsupported response model")
    qn = {k: _exact(v, k) for k, v in n.items() if k.endswith(("mw", "mva", "pu", "rad"))}
    qr = {k: _exact(v, k) for k, v in rights.items()}
    qx = {k: _exact(x[k], k) for k in ("max_call_mw", "max_ramp_mw_per_hour", "max_energy_mwh")}
    require(all(v >= 0 for v in (*qn.values(), *qr.values(), *qx.values())), "negative input quantity")
    for k in ("base_mva", "reactance_pu", "angle_limit_rad", "generator_max_mw",
              "line_rating_before_mw", "line_rating_after_mw"):
        require(qn[k] > 0, "positive electrical parameters required")
    for k in ("source_bus", "poi_bus", "project_start", "project_lead"):
        _integer(n[k], k)
    require(n["source_bus"] != n["poi_bus"] and n["project_lead"] >= 0, "invalid network/project")
    for value in n["delays"].values():
        _integer(value, "delay")
        require(value >= 0, "negative delay")
    for k in ("max_duration_hours", "max_events", "minimum_rest_hours"):
        _integer(x[k], k)
        require(x[k] >= 0 and (k != "max_duration_hours" or x[k] > 0), "invalid X envelope")
    selected = tuple(n["selected_outages"])
    require(selected == (0, 1) and all(type(i) is int for i in selected), "declare both individual line outages")
    for hour, branch in n["actual_outages"].items():
        _integer(hour, "outage hour")
        require(type(branch) is int and branch in selected, "invalid actual outage")
    fixture = (ROOT / raw["business_fixture"]).resolve()
    require(fixture.is_relative_to(ROOT), "business fixture outside repository")
    require(hashlib.sha256(fixture.read_bytes()).hexdigest() == raw["business_sha256"], "business SHA mismatch")
    source, poi = n["source_bus"], n["poi_bus"]

    def data(rating):
        return Rts24Data(
            library_float(qn["base_mva"]),
            (Bus(source, 0.), Bus(poi, library_float(qn["background_mw"]))),
            (Generator(0, source, 0., library_float(qn["generator_max_mw"]), 0., 0., 0., None, None, True),),
            tuple(Branch(i, source, poi, library_float(qn["reactance_pu"]),
                         library_float(rating), library_float(rating), library_float(rating), 1., 0., True)
                  for i in (0, 1)), source, "synthetic_two_line_B2", "development_v1")

    return NetworkConfig(data(qn["line_rating_before_mw"]), data(qn["line_rating_after_mw"]), poi,
                         qn["angle_limit_rad"], n["project_start"], n["project_lead"],
                         tuple(sorted(n["delays"].items())), tuple(sorted(n["actual_outages"].items())), selected,
                         (qr["firm_before_mw"], qr["conditional_before_mw"]),
                         (qr["firm_after_mw"], qr["conditional_after_mw"]),
                         qn["hourly_generator_ramp_mw"], qx["max_call_mw"], qx["max_ramp_mw_per_hour"],
                         qx["max_energy_mwh"], x["max_duration_hours"], x["max_events"],
                         x["minimum_rest_hours"], raw["business_fixture"], raw["business_sha256"])


def validate_corridor(data, poi, outages):
    ids = tuple(b.index for b in data.buses)
    require(len(ids) == len(set(ids)) == 2 and all(type(i) is int for i in ids), "two unique buses required")
    require(type(data.reference_bus) is int and type(poi) is int
            and data.reference_bus in ids and poi in ids and poi != data.reference_bus, "invalid source/POI")
    require(len(data.generators) == 1 and len(data.branches) == 2, "single-source two-line scope")
    source = data.generators[0]
    require(source.bus == data.reference_bus and source.in_service and source.p_min_mw == 0,
            "unsupported source dispatch")
    require(rational(source.p_max_mw) > 0 and rational(data.base_mva) > 0, "invalid source/base")
    require({b.index for b in data.branches} == {0, 1} and all(type(b.index) is int for b in data.branches),
            "explicit branch identities required")
    require(len(outages) == len(set(outages)) and all(type(i) is int and i in (0, 1) for i in outages),
            "invalid outage identity")
    for bus in data.buses:
        require(rational(bus.demand_mw) >= 0 and (bus.index == poi or bus.demand_mw == 0), "unsupported background")
    for b in data.branches:
        require((b.from_bus, b.to_bus) == (data.reference_bus, poi) and b.phase_shift_rad == 0,
                "unsupported corridor direction/shift")
        require(rational(b.reactance_pu) > 0 and rational(b.tap_ratio) > 0 and rational(b.rate_a_mw) > 0,
                "invalid line parameters")
    active = tuple(b for b in data.branches if b.in_service and b.index not in outages)
    require(bool(active), "islanded selected topology")
    return active


def poi_capacity(data, poi, outages, angle_limit):
    active = validate_corridor(data, poi, outages)
    conductance = {b.index: 1 / (rational(b.reactance_pu) * rational(b.tap_ratio)) for b in active}
    total = sum(conductance.values(), Q(0))
    background = sum((rational(b.demand_mw) for b in data.buses), Q(0))
    caps = [rational(data.generators[0].p_max_mw), angle_limit * rational(data.base_mva) * total]
    caps += [rational(b.rate_a_mw) * total / conductance[b.index] for b in active]
    result = min(caps) - background
    require(result >= 0, "fixed balance has no feasible nonnegative POI load")
    return result


def dc_witness(data, poi, load, outages=(), angle_limit=Q(1, 10), counts=None):
    active = validate_corridor(data, poi, outages)
    require(isinstance(load, Q) and load >= 0, "exact nonnegative POI load required")
    if counts is not None:
        counts["pypower_flows"] = counts.get("pypower_flows", 0) + 1
    positions = {bus.index: i for i, bus in enumerate(data.buses)}
    bus = np.zeros((2, 13))
    bus[:, BUS_I] = np.arange(2)
    branch = np.zeros((2, 13))
    for i, b in enumerate(data.branches):
        branch[i, [F_BUS, T_BUS, BR_X, TAP, SHIFT, BR_STATUS]] = (
            positions[b.from_bus], positions[b.to_bus], b.reactance_pu, b.tap_ratio, 0., int(b in active))
    bbus, bf, pbusinj, pfinj = makeBdc(data.base_mva, bus, branch)
    injections = np.array([-b.demand_mw for b in data.buses], dtype=float)
    injections[positions[poi]] -= float(load)
    generation = float(load) + sum(b.demand_mw for b in data.buses)
    ref = positions[data.reference_bus]
    injections[ref] += generation
    angles = dcpf(bbus, injections / data.base_mva - pbusinj, np.zeros(2),
                  np.array([ref]), np.array([], dtype=int), np.array([positions[poi]]))
    flows = np.asarray(bf @ angles + pfinj).reshape(-1) * data.base_mva
    if not (np.isfinite(angles).all() and np.isfinite(flows).all()):
        raise ArithmeticError("DC numerical result unresolved")
    residual = injections.copy()
    equation, thermal, outage_flow = [], [], []
    for i, b in enumerate(data.branches):
        residual[positions[b.from_bus]] -= flows[i]
        residual[positions[b.to_bus]] += flows[i]
        expected = (data.base_mva / (b.reactance_pu * b.tap_ratio)
                    * (angles[positions[b.from_bus]] - angles[positions[b.to_bus]])) if b in active else 0.
        equation.append(abs(flows[i] - expected))
        thermal.append(max(abs(flows[i]) - b.rate_a_mw, 0.) if b in active else 0.)
        outage_flow.append(abs(flows[i]) if b not in active else 0.)
    audits = dict(balance_mw=float(max(abs(residual))), flow_equation_mw=float(max(equation)),
                  thermal_mw=float(max(thermal)), outage_flow_mw=float(max(outage_flow)),
                  generation_mw=max(-generation, generation - data.generators[0].p_max_mw, 0.),
                  angle_rad=max(float(max(abs(angles))) - float(angle_limit), 0.))
    return dict(load=load, outages=outages, generation_mw=generation,
                angles_rad=tuple(float(v) for v in angles), branch_flows_mw=tuple(float(v) for v in flows),
                residuals=audits, numerical_conditions_satisfied=all(v <= TOL for v in audits.values()))


def contract_checks(config, params, observation, data, firm, conditional, counts=None, progress=None):
    total = firm + conditional
    output = {} if progress is None else progress
    output.update(firm=firm, conditional=conditional, total=total, normal=None,
                  scenarios=[], status="pending", aggregate_contract_release=False)
    normal = dc_witness(data, config.poi_bus, total, angle_limit=config.angle_limit, counts=counts)
    output["normal"] = normal
    # Counterfactual full-load CFE request, kept separate from the actual request.
    green = max(total - observation.clean_mwh / params.alpha, Q(0)) if params.alpha else Q(0)
    w_hat = (total - params.facility_factor * observation.idle_mw - params.auxiliary_mw) / params.slope
    scenarios = []
    enrolled_backing = (conditional <= params.slope * params.capacity
                        and w_hat >= 0 and conditional <= params.slope * w_hat * observation.flexible_fraction)
    for outages in ((), *((i,) for i in config.selected_outages)):
        cap = poi_capacity(data, config.poi_bus, outages, config.angle_limit)
        required = max(total - cap, Q(0)) if outages else Q(0)
        resources = (required + green) / params.slope
        backing = (w_hat >= 0 and resources <= params.capacity and resources <= w_hat * observation.flexible_fraction
                   and 0 <= w_hat - resources <= observation.compute_capacity)
        item = dict(outages=outages, physical_cap=cap, required_grid_mw=required,
                    counterfactual_cfe_mw=green, counterfactual_workload=w_hat,
                    shared_requirement=resources, business_necessary=backing,
                    firm_point=None, post_call_point=None)
        output["scenarios"].append(item)
        if outages:
            firm_point = dc_witness(data, config.poi_bus, firm, outages, config.angle_limit, counts)
            item["firm_point"] = firm_point
            after = dc_witness(data, config.poi_bus, max(total - required, Q(0)), outages, config.angle_limit, counts)
            response = (required == 0 or (required <= conditional and required <= config.max_x_call
                        and required <= config.max_x_ramp and required <= config.max_x_energy
                        and config.max_x_events >= 1 and config.max_x_duration >= 1))
            network_ok = firm_point["numerical_conditions_satisfied"] and after["numerical_conditions_satisfied"] and response
        else:
            firm_point, after, response = None, normal, True
            network_ok = normal["numerical_conditions_satisfied"]
        item.update(response_necessary=response, network_conditions_satisfied=network_ok,
                    firm_point=firm_point, post_call_point=after)
        scenarios.append(item)
    network_ok = all(s["network_conditions_satisfied"] for s in scenarios)
    backing = enrolled_backing and all(s["business_necessary"] for s in scenarios)
    output.update(scenarios=tuple(scenarios), status="evaluated", enrolled_X_backing_necessary=enrolled_backing,
                  network_conditions_satisfied=network_ok, business_necessary=backing,
                  joint_temporal_support="unresolved" if network_ok and backing else "necessary_condition_failed")
    return output


@dataclass(frozen=True)
class NetworkState:
    config: NetworkConfig
    plan: str
    business: StageState
    records: tuple[dict, ...] = ()
    previous_generation: Q | None = None
    x_previous: Q = Q(0)
    x_energy: Q = Q(0)
    x_events: int = 0
    x_duration: int = 0
    x_rest: int = 0
    stopped: bool = False


def initialize_network(config, params, plan, identity, first_hour=-2):
    require(plan in dict(config.delays), "unknown fixed plan")
    return NetworkState(config, plan, initialize(params, "full_temporal", identity, first_hour),
                        x_rest=config.x_minimum_rest)


def _advance_network(params, state, observation, counts, entry):
    require(not state.stopped and observation.hour == state.business.next_hour, "stopped/nonconsecutive network chain")
    require(state.business.parameters == params, "business parameters drift")
    if counts is not None:
        counts["network_attempts"] = counts.get("network_attempts", 0) + 1
    c, o = state.config, observation
    online = o.hour >= c.project_start + c.project_lead + dict(c.delays)[state.plan]
    require(online == o.grid_online, "business/network commissioning states differ")
    data = c.after if online else c.before
    firm, conditional = c.rights_after if online else c.rights_before
    branch = dict(c.actual_outages).get(o.hour)
    outages = () if branch is None else (branch,)
    cap = poi_capacity(data, c.poi_bus, outages, c.angle_limit)
    _, _, reference = power_mapping(params, o)
    raw_grid = max(reference - cap, Q(0))
    active_x = min(conditional, max(reference - firm, Q(0)))
    legal_x = min(active_x, c.max_x_call, max(c.max_x_energy - state.x_energy, Q(0)),
                  state.x_previous + c.max_x_ramp)
    if (state.x_duration >= c.max_x_duration or (state.x_previous == 0 and
            (state.x_events >= c.max_x_events or state.x_rest < c.x_minimum_rest))):
        legal_x = Q(0)
    entry.update(hour=o.hour, input=o, commissioned=online, outages=outages, physical_cap=cap,
                 firm=firm, conditional=conditional, reference_mw=reference, raw_grid_mw=raw_grid,
                 active_x_mw=active_x, legal_grid_cap_mw=legal_x,
                 connection_shortfall_mw=max(reference - firm - conditional, Q(0)),
                 reference_point=None, contract={}, proposal=None, actual_point=None,
                 committed=False, status="pending", failure_stage="contract_checks")
    contract_checks(c, params, o, data, firm, conditional, counts, entry["contract"])
    entry["failure_stage"] = "reference_flow"
    entry["reference_point"] = dc_witness(data, c.poi_bus, reference, outages, c.angle_limit, counts)

    def stop(code):
        entry["status"] = code
        if entry["proposal"] is not None:
            entry["proposal"] = replace(entry["proposal"], ledger_applied=False)
        return replace(state, records=state.records + (entry,), stopped=True)

    if entry["connection_shortfall_mw"]:
        return stop("reference_connection_shortfall")
    if raw_grid and not outages:
        return stop("normal_state_has_no_X_call_authority")
    if raw_grid > legal_x:
        entry["grid_unbacked_request_mw"] = raw_grid - legal_x
        return stop("request_exceeds_legal_X")
    mapped = replace(o, supply_mw=min(cap, firm + conditional))
    entry["failure_stage"] = "business_proposal"
    candidate = advance(params, state.business, mapped)
    if counts is not None:
        counts["business_steps"] = counts.get("business_steps", 0) + 1
    proposal = candidate.records[-1]
    entry["proposal"] = proposal
    entry["failure_stage"] = "actual_flow"
    actual = dc_witness(data, c.poi_bus, proposal.power_mw, outages, c.angle_limit, counts)
    entry["actual_point"] = actual
    x_call = params.slope * proposal.grid_served
    events = state.x_events + int(x_call > 0 and state.x_previous == 0)
    duration = state.x_duration + 1 if x_call else 0
    rest = 0 if x_call else state.x_rest + 1
    source = proposal.power_mw + sum((rational(b.demand_mw) for b in data.buses), Q(0))
    x_ok = (x_call <= active_x and x_call <= c.max_x_call and abs(x_call - state.x_previous) <= c.max_x_ramp
            and state.x_energy + x_call <= c.max_x_energy and events <= c.max_x_events and duration <= c.max_x_duration
            and not (x_call and not state.x_previous and state.x_rest < c.x_minimum_rest))
    source_ok = (state.previous_generation is None or abs(source - state.previous_generation) <= c.hourly_ramp)
    entry.update(x_call_mw=x_call, response_conditions_satisfied=x_ok and source_ok)
    if candidate.stopped or not proposal.ledger_applied:
        return stop("business_proposal_rejected")
    if not actual["numerical_conditions_satisfied"] or proposal.power_mw > firm + conditional:
        return stop("actual_network_point_rejected")
    if not x_ok or not source_ok:
        return stop("X_or_source_response_rejected")
    entry.update(committed=True, status="conditional_operating_point_committed", failure_stage=None)
    return replace(state, business=candidate, records=state.records + (entry,), previous_generation=source,
                   x_previous=x_call, x_energy=state.x_energy + x_call, x_events=events,
                   x_duration=duration, x_rest=rest)


def advance_network(params, state, observation, counts=None):
    entry = {}
    try:
        return _advance_network(params, state, observation, counts, entry)
    except (ArithmeticError, RuntimeError, np.linalg.LinAlgError) as error:
        if not entry or entry["failure_stage"] not in {"contract_checks", "reference_flow", "actual_flow"}:
            raise
        entry.update(status="upstream_network_unresolved", committed=False, error=str(error))
        if entry["proposal"] is not None:
            entry["proposal"] = replace(entry["proposal"], ledger_applied=False)
        return replace(state, records=state.records + (entry,), stopped=True)


def execute_network(config, params, observations, plan, identity, state=None, counts=None):
    if state is None:
        require(bool(observations), "nonempty observation prefix required")
        state = initialize_network(config, params, plan, identity, observations[0].hour)
    require(state.config == config and state.plan == plan and state.business.trajectory_id == identity,
            "network identity/config drift")
    for o in observations:
        state = advance_network(params, state, o, counts)
        if state.stopped:
            break
    return state


def load_case(config, plan, clean):
    path = ROOT / config.business_fixture
    require(hashlib.sha256(path.read_bytes()).hexdigest() == config.business_sha256, "business fixture drift")
    return load_small_case(path, plan, clean)


def save_network_checkpoint(path, state):
    payload = dict(status="DRAFT_NONAUTHORITATIVE", scope="B2 fixed_balance_DC_only", state=plain(state))
    text = json.dumps(payload, sort_keys=True, indent=2, allow_nan=False) + "\n"
    require(len(text.encode()) <= 2 * 1024**2, "network checkpoint size limit")
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(text)


def read_network_checkpoint(path, config, params, prefix, plan, identity, counts=None):
    path = Path(path)
    require(path.stat().st_size <= 2 * 1024**2, "network checkpoint size limit")
    saved = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_pairs,
                       parse_constant=lambda v: require(False, f"invalid JSON {v}"))
    state = execute_network(config, params, prefix, plan, identity, counts=counts)
    require(len(state.records) == len(prefix), "checkpoint prefix contains unconsumed hours")
    expected = dict(status="DRAFT_NONAUTHORITATIVE", scope="B2 fixed_balance_DC_only", state=plain(state))
    require(json.dumps(saved, sort_keys=True) == json.dumps(expected, sort_keys=True), "network checkpoint replay differs")
    return state
