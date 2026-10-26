"""Public staged DC query compiler. Builds models; never obtains a solver."""
from dataclasses import asdict, dataclass, is_dataclass, replace
from fractions import Fraction as Q
import hashlib
from importlib.metadata import distribution, version
import json
from math import isfinite
from pathlib import Path

import yaml

from src.staged_deliverability_development_v1 import Parameters, METHODS

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/staged_deliverability_rts24_v1.DRAFT.yaml"
SCOPE = "staged_rts24_static_dc_query_development_v1"
SCALED_PARAMETERS = {"capacity", "auxiliary_mw", "fixed_headroom", "max_recovery",
                     "max_debt", "max_call_energy", "call_ramp"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def plain(value):
    if isinstance(value, Q): return str(value)
    if is_dataclass(value): return plain(asdict(value))
    if isinstance(value, dict): return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)): return [plain(v) for v in value]
    return value


def digest(value):
    return hashlib.sha256(json.dumps(plain(value), sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode("utf-8")).hexdigest()


def quantity(value):
    require(type(value) is str and value.strip() == value, "exact string quantity required")
    result = Q(value)
    require(result >= 0, "negative input quantity")
    return result


def keys(value, names):
    require(type(value) is dict and set(value) == set(names.split()), "fixture schema differs")


def read_source(path):
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= 1024**2,
            "invalid source file")
    return path.read_bytes()


def source_section(section):
    path = (ROOT / section["fixture"]).resolve()
    require(path.is_relative_to(ROOT), "source outside repository")
    data = read_source(path)
    require(hashlib.sha256(data).hexdigest() == section["sha256"], "bound source SHA differs")
    return yaml.safe_load(data)


def connected(data, outages=()):
    adjacency = {b.index: set() for b in data.buses}
    for branch in data.branches:
        if branch.in_service and branch.index not in outages:
            adjacency[branch.from_bus].add(branch.to_bus)
            adjacency[branch.to_bus].add(branch.from_bus)
    reached, pending = set(), [data.reference_bus]
    while pending:
        bus = pending.pop()
        if bus not in reached:
            reached.add(bus)
            pending.extend(adjacency[bus] - reached)
    return reached == set(adjacency)


@dataclass(frozen=True)
class Outage:
    name: str
    branches: tuple[int, ...] = ()
    generators: tuple[int, ...] = ()


@dataclass(frozen=True)
class PublicObservation:
    hour: int
    due: int
    workload: Q
    flexible_fraction: Q
    compute_capacity: Q
    idle_mw: Q
    clean_mwh: Q
    equipment_online: tuple[str, ...]
    commissioned: bool


@dataclass(frozen=True)
class Fixture:
    before: object
    after: object
    poi_bus: int
    parameters: Parameters
    scale: Q
    business_json: str
    rights_before: tuple[Q, Q]
    rights_after: tuple[Q, Q]
    x_envelope_json: str
    selected: tuple[Outage, ...]
    project_start: int
    project_lead: int
    delays: tuple[tuple[str, int], ...]
    actual_hour: int
    actual_duration: int
    first_hour: int
    registration_end: int
    observation_end: int
    redispatch_fraction: Q
    source_identity: str


def load_fixture(path=CONFIG):
    raw_bytes = read_source(Path(path))
    c = yaml.safe_load(raw_bytes)
    keys(c, "status source_class case business rights network project contingencies actual_event time methods")
    require(c["status"] == "DRAFT_NONAUTHORITATIVE" and c["source_class"] ==
            "public_static_dc_with_synthetic_stage_and_business_assumptions", "wrong development scope")
    keys(c["case"], "package version name sha256")
    require(c["case"]["package"] == "PYPOWER" and c["case"]["name"] == "case24_ieee_rts", "unsupported case")
    require(version("PYPOWER") == c["case"]["version"], "public package version differs")
    case_path = Path(distribution("PYPOWER").locate_file("pypower/case24_ieee_rts.py"))
    require(hashlib.sha256(read_source(case_path)).hexdigest() == c["case"]["sha256"], "public case source drift")
    keys(c["business"], "fixture sha256 dimensional_scale")
    keys(c["rights"], "fixture sha256")
    b, old_network = source_section(c["business"]), source_section(c["rights"])
    require(old_network["business_sha256"] == c["business"]["sha256"], "rights/business source mismatch")
    scale = quantity(c["business"]["dimensional_scale"])
    require(scale > 0, "positive dimensional scale required")
    p = {k: (v if type(v) is int else quantity(v)) for k, v in b["parameters"].items()}
    params = Parameters(**{k: v * scale if k in SCALED_PARAMETERS else v for k, v in p.items()})
    n, project, selection, event, t = (c[k] for k in ("network", "project", "contingencies", "actual_event", "time"))
    keys(n, "poi_bus background_load_multiplier sustained_rating redispatch_fraction_of_pmax economic_regularization_quadratic dispatch_policy response_model")
    require(n["sustained_rating"] == "rate_a" and n["dispatch_policy"] ==
            "independent_hourly_regularized_economic_base_with_bounded_same_hour_corrective", "unsupported dispatch contract")
    require(n["response_model"] == "static_hourly_declared_branch_or_generator_outage_same_hour_redispatch", "unsupported X response contract")
    require(quantity(n["economic_regularization_quadratic"]) == Q(1, 100000000), "economic tie break differs")
    keys(project, "branches rate_a_increase_mw rate_c_increase_mw start_hour lead_hours delays")
    keys(project["delays"], "on_time delayed")
    require(all(type(v) is int for v in (project["start_hour"], project["lead_hours"], *project["delays"].values()))
            and project["lead_hours"] >= 0 and all(v >= 0 for v in project["delays"].values()), "invalid project timing")
    require(project["start_hour"] == b["grid"]["start"] and project["lead_hours"] == b["grid"]["lead"]
            and project["delays"] == b["grid"]["delays"], "business/project timing differs")
    from src.grid.rts24 import load_rts24, scale_rts24_demand
    original = load_rts24()
    require((len(original.buses), len(original.generators), len(original.branches)) == (24, 33, 38), "public shape differs")
    before = scale_rts24_demand(original, float(quantity(n["background_load_multiplier"])))
    require(type(n["poi_bus"]) is int and n["poi_bus"] in {b.index for b in before.buses}, "invalid POI")
    branches = tuple(project["branches"])
    require(branches and len(set(branches)) == len(branches) and all(type(i) is int for i in branches)
            and set(branches) <= {b.index for b in before.branches}, "invalid project branches")
    da, dc = quantity(project["rate_a_increase_mw"]), quantity(project["rate_c_increase_mw"])
    require(da > 0 and dc > 0, "positive project increases required")
    after = replace(before, branches=tuple(replace(v, rate_a_mw=v.rate_a_mw + float(da),
        rate_c_mw=v.rate_c_mw + float(dc)) if v.index in branches else v for v in before.branches))
    keys(selection, "branches generators expected_excluded_branches expected_excluded_generators")
    require(selection["branches"] == "all_non_islanding_in_service" and
            selection["generators"] == "all_in_service_positive_pmax", "unsupported contingency selection")
    included_b = tuple(v.index for v in before.branches if v.in_service and connected(before, (v.index,)))
    included_g = tuple(v.index for v in before.generators if v.in_service and v.p_max_mw > 0)
    require([v.index for v in before.branches if v.index not in included_b] == selection["expected_excluded_branches"]
            and [v.index for v in before.generators if v.index not in included_g] == selection["expected_excluded_generators"],
            "excluded contingency identities differ")
    selected = tuple(Outage(f"branch_{i}", (i,)) for i in included_b) + tuple(Outage(f"generator_{i}", (), (i,)) for i in included_g)
    require(connected(before) and all(connected(after, (i,)) for i in included_b), "unsupported islanded stage")
    keys(event, "rule hour duration_hours")
    require(event["rule"] == "lowest_selected_branch_index" and type(event["hour"]) is int
            and type(event["duration_hours"]) is int and event["duration_hours"] > 0, "invalid actual event")
    keys(t, "first_hour registration_end observation_end deadline_rule")
    require(all(type(t[k]) is int for k in ("first_hour", "registration_end", "observation_end"))
            and t["first_hour"] == b["first_hour"] and t["observation_end"] == b["last_hour"] + 1
            and t["first_hour"] <= 0 < t["registration_end"] < t["observation_end"]
            and t["deadline_rule"] == "arrival_plus_source_lag_without_observation_clipping", "invalid time boundaries")
    require(tuple(c["methods"]) == METHODS, "evaluation methods differ")
    fraction = quantity(n["redispatch_fraction_of_pmax"])
    require(fraction <= 1, "redispatch fraction exceeds one")
    rights = old_network["rights"]
    x = old_network["x_envelope"]
    scaled_x = {k: str(quantity(v) * scale) if k in ("max_call_mw", "max_ramp_mw_per_hour", "max_energy_mwh")
                else v for k, v in x.items()}
    scaled_x.update(source_response_model=x["response_model"], response_model=n["response_model"],
                    parameter_status="scaled_mechanism_envelope_not_response_certification")
    identity = digest(dict(scope=SCOPE, config_sha=hashlib.sha256(raw_bytes).hexdigest(), case=c["case"],
                           business=c["business"], rights=c["rights"], before=before, after=after,
                           compiler_sha=hashlib.sha256(read_source(Path(__file__))).hexdigest()))
    return Fixture(before, after, n["poi_bus"], params, scale, json.dumps(b, sort_keys=True),
        tuple(quantity(rights[k]) * scale for k in ("firm_before_mw", "conditional_before_mw")),
        tuple(quantity(rights[k]) * scale for k in ("firm_after_mw", "conditional_after_mw")),
        json.dumps(scaled_x, sort_keys=True), selected, project["start_hour"], project["lead_hours"],
        tuple(sorted(project["delays"].items())), event["hour"], event["duration_hours"],
        t["first_hour"], t["registration_end"], t["observation_end"], fraction, identity)


def observe(fixture, plan, clean, hour):
    require(plan in dict(fixture.delays) and type(hour) is int
            and fixture.first_hour <= hour < fixture.observation_end, "unknown plan or hour")
    b, s = json.loads(fixture.business_json), fixture.scale
    require(clean in b["clean_paths"], "unknown clean path")
    online = [m for m in b["equipment"] if hour >= m["start"] + m["lead"] + m["delay"]]
    commissioned = hour >= fixture.project_start + fixture.project_lead + dict(fixture.delays)[plan]
    return PublicObservation(hour, hour + b["deadline_lag"],
        quantity(b["workload"]["before" if hour < b["workload"]["change_hour"] else "after"]) * s,
        Q(0) if hour < 0 else quantity(b["flexible_fraction"]),
        sum((quantity(m["capacity"]) * s for m in online), Q(0)),
        sum((quantity(m["idle_mw"]) * s for m in online), Q(0)),
        quantity(b["prehistory_clean"] if hour < 0 else b["clean_paths"][clean][hour]) * s,
        tuple(m["id"] for m in online), commissioned)


@dataclass(frozen=True)
class PointRequest:
    data: object
    fixture_identity: str
    plan: str
    clean_path: str
    hour: int
    method: str
    role: str
    poi_bus: int
    meter_min: Q
    meter_max: Q
    curtailment_max: Q
    connection_capacity: Q
    rights: tuple[Q, Q]
    outages: Outage
    objective: str
    anchor_id: str | None
    redispatch_fraction: Q
    economic_regularization_quadratic: Q = Q(1, 100000000)

    def __post_init__(self):
        roles = {"normal_contract_C": ("economic", False), "reference_base_P0": ("economic", False),
                 "fault_firm_F": ("economic", True), "fault_raw_need": ("min_curtailment", True),
                 "reference_raw_need": ("min_curtailment", True), "actual_P": ("economic", True),
                 "recovery_min_meter": ("min_meter", True), "recovery_max_meter": ("max_meter", True)}
        require(self.role in roles and (self.objective, self.anchor_id is not None) == roles[self.role], "role/objective/anchor differs")
        require(self.economic_regularization_quadratic == Q(1, 100000000), "fixed economic regularization required")
        require(self.method in METHODS and type(self.hour) is int and bool(self.fixture_identity)
                and bool(self.plan) and type(self.clean_path) is str and bool(self.clean_path), "invalid query frame")
        require(type(self.rights) is tuple and len(self.rights) == 2 and all(isinstance(v, Q) and v >= 0 for v in self.rights)
                and sum(self.rights) == self.connection_capacity, "invalid exact F/X decomposition")
        require(all(isinstance(v, Q) and v >= 0 for v in (self.meter_min, self.meter_max, self.curtailment_max,
                self.connection_capacity, self.redispatch_fraction)) and self.meter_min <= self.meter_max
                and self.curtailment_max <= self.meter_max and self.redispatch_fraction <= 1, "invalid exact query bounds")
        require(len(self.outages.branches) + len(self.outages.generators) <= 1, "selected N-1 query required")
        require(all(type(i) is int for i in (*self.outages.branches, *self.outages.generators)), "invalid outage index")
        require(self.meter_min == self.meter_max or self.objective in ("min_meter", "max_meter"), "variable meter needs interval objective")
        require(self.curtailment_max == 0 or self.objective == "min_curtailment", "unexpected curtailment authority")
        require(not self.role.startswith("fault_") or self.outages.branches or self.outages.generators, "fault role requires outage")
        require(self.anchor_id is not None or not self.outages.branches and not self.outages.generators, "base must be healthy")
        if self.role == "normal_contract_C": require(self.meter_min == self.meter_max == self.connection_capacity, "normal full C required")
        if self.role == "fault_firm_F": require(self.meter_min == self.meter_max == self.rights[0], "firm F point required")
        if self.role == "fault_raw_need": require(self.meter_min == self.meter_max == self.curtailment_max == self.connection_capacity, "complete raw request required")
        if self.role == "reference_raw_need": require(self.meter_min == self.meter_max == self.curtailment_max, "complete reference raw request required")
        if self.role in ("recovery_min_meter", "recovery_max_meter"):
            require(self.meter_min == 0 and self.meter_max == self.connection_capacity and self.curtailment_max == 0, "complete recovery projection domain required")
        d = self.data
        bus_ids, gen_ids, branch_ids = ({v.index for v in values} for values in (d.buses, d.generators, d.branches))
        require(len(bus_ids) == len(d.buses) and len(gen_ids) == len(d.generators) and len(branch_ids) == len(d.branches)
                and all(type(i) is int for i in (*bus_ids, *gen_ids, *branch_ids))
                and self.poi_bus in bus_ids and d.reference_bus in bus_ids, "invalid network indices")
        require(isfinite(d.base_mva) and d.base_mva > 0 and all(isfinite(b.demand_mw) and b.demand_mw >= 0 for b in d.buses), "invalid base/demand")
        require(all(g.bus in bus_ids and all(isfinite(v) for v in (g.p_min_mw, g.p_max_mw, g.cost_quadratic,
                g.cost_linear, g.cost_constant)) and 0 <= g.p_min_mw <= g.p_max_mw and g.cost_quadratic >= 0 for g in d.generators), "invalid generator")
        require(all(b.from_bus in bus_ids and b.to_bus in bus_ids and b.from_bus != b.to_bus
                and all(isfinite(v) for v in (b.reactance_pu, b.tap_ratio, b.phase_shift_rad, b.rate_a_mw))
                and b.reactance_pu > 0 and b.tap_ratio > 0 and b.rate_a_mw > 0 for b in d.branches), "invalid branch")
        require(set(self.outages.branches) <= branch_ids and set(self.outages.generators) <= gen_ids, "unknown outage")

    @property
    def identity(self): return digest(self)


@dataclass(frozen=True)
class PointWitness:
    query_sha: str
    meter_load_mw: float
    curtailment_mw: float
    generation_mw: tuple[tuple[int, float], ...]
    angles_rad: tuple[tuple[int, float], ...]
    flows_mw: tuple[tuple[int, float], ...]


@dataclass(frozen=True)
class EconomicEvidence:
    query_sha: str
    point_sha: str
    balance_duals: tuple[tuple[int, float], ...]
    flow_equation_duals: tuple[tuple[int, float], ...]
    generation_lower_duals: tuple[tuple[int, float], ...]
    generation_upper_duals: tuple[tuple[int, float], ...]
    flow_lower_duals: tuple[tuple[int, float], ...]
    flow_upper_duals: tuple[tuple[int, float], ...]


@dataclass(frozen=True)
class BoundQuery:
    request: PointRequest
    base_query: object | None = None
    base_point: PointWitness | None = None
    base_economic: EconomicEvidence | None = None

    @property
    def anchor_generation(self): return () if self.base_point is None else self.base_point.generation_mw

    @property
    def anchor_sha(self): return None if self.base_point is None else digest(self.base_point)

    @property
    def identity(self):
        return digest(dict(request=self.request.identity, base_query=None if self.base_query is None else self.base_query.request.identity,
                           base_point=self.base_point, base_economic=self.base_economic))


def bind(request, anchor_query=None, anchor_witness=None, economic_evidence=None):
    if request.anchor_id is None:
        require(anchor_query is None and anchor_witness is None and economic_evidence is None, "unexpected anchor")
        return BoundQuery(request)
    require(anchor_query is not None and anchor_witness is not None
            and anchor_query.request.identity == request.anchor_id
            and anchor_query.request.anchor_id is None, "missing or wrong economic base anchor")
    base = anchor_query.request
    require((base.fixture_identity, base.plan, base.clean_path, base.hour, base.method, base.data, base.connection_capacity, base.rights) ==
            (request.fixture_identity, request.plan, request.clean_path, request.hour, request.method, request.data, request.connection_capacity, request.rights), "anchor frame differs")
    expected_role = "normal_contract_C" if request.role.startswith("fault_") else "reference_base_P0"
    require(base.role == expected_role and (expected_role != "normal_contract_C" or base.meter_min == base.meter_max == request.connection_capacity), "wrong parent role/load")
    if request.role == "reference_raw_need":
        require(request.meter_min == request.meter_max == request.curtailment_max == base.meter_min == base.meter_max, "reference raw/P0 differs")
    from src.staged_rts24_audit_v1 import audit_economic_base
    require(economic_evidence is not None, "missing economic optimality evidence")
    require(audit_economic_base(anchor_query, anchor_witness, economic_evidence)["economic_kkt_satisfied"], "invalid economic base anchor")
    return BoundQuery(request, anchor_query, anchor_witness, economic_evidence)


def hour_requests(fixture, plan, clean, method, hour):
    require(method in METHODS, "unknown evaluation method")
    o = observe(fixture, plan, clean, hour)
    data = fixture.after if o.commissioned else fixture.before
    firm, conditional = fixture.rights_after if o.commissioned else fixture.rights_before
    capacity = firm + conditional
    reference = fixture.parameters.facility_factor * (o.idle_mw + fixture.parameters.beta * o.workload) + fixture.parameters.auxiliary_mw
    actual = fixture.selected[0] if fixture.actual_hour <= hour < fixture.actual_hour + fixture.actual_duration else Outage("normal")

    def request(role, load, outage=Outage("normal"), objective="economic", anchor=None, curtail=Q(0), lower=None):
        return PointRequest(data, fixture.source_identity, plan, clean, hour, method, role, fixture.poi_bus,
            load if lower is None else lower, load, curtail, capacity, (firm, conditional), outage, objective, anchor, fixture.redispatch_fraction)

    normal = request("normal_contract_C", capacity)
    reference_base = request("reference_base_P0", reference)
    normal_id, reference_id = normal.identity, reference_base.identity
    requests = [normal]
    for state in fixture.selected:
        requests.extend((request("fault_firm_F", firm, state, anchor=normal_id),
                         request("fault_raw_need", capacity, state, "min_curtailment", normal_id, capacity)))
    requests.append(reference_base)
    if actual.branches or actual.generators:
        requests.append(request("reference_raw_need", reference, actual, "min_curtailment", reference_id, reference))
    if method != "instantaneous":
        for objective in ("min_meter", "max_meter"):
            requests.append(request("recovery_" + objective, capacity, actual, objective, reference_id, lower=Q(0)))
    return dict(observation=o, reference_mw=reference, firm=firm, conditional=conditional,
                reference_connection_shortfall_mw=max(reference-capacity, Q(0)), actual_outage=actual,
                requests=tuple(requests), solver_node_upper_bound_including_actual=len(requests)+1)


def actual_request(fixture, plan, clean, method, hour, actual_power):
    require(isinstance(actual_power, Q) and actual_power >= 0, "exact actual power required")
    h = hour_requests(fixture, plan, clean, method, hour)
    base = next(r for r in h["requests"] if r.role == "reference_base_P0")
    return replace(base, role="actual_P", meter_min=actual_power, meter_max=actual_power,
                   outages=h["actual_outage"], anchor_id=base.identity)


def build_point_model(query):
    """Construct only. Corrective requests must already have a checked parent."""
    q, d = query.request, query.request.data
    bind(q, query.base_query, query.base_point, query.base_economic)
    require((q.anchor_id is None) == (query.anchor_sha is None), "unbound corrective query")
    require(q.objective in {"economic", "min_curtailment", "min_meter", "max_meter"}, "unknown objective")
    require(all(isinstance(v, Q) and v >= 0 for v in (q.meter_min, q.meter_max, q.curtailment_max, q.connection_capacity))
            and q.meter_min <= q.meter_max and q.curtailment_max <= q.meter_max, "invalid meter/curtailment bounds")
    require(connected(d, q.outages.branches), "islanded query rejected")
    buses, gens, branches = ({v.index: v for v in values} for values in (d.buses, d.generators, d.branches))
    require(len(buses) == len(d.buses) and len(gens) == len(d.generators) and len(branches) == len(d.branches)
            and q.poi_bus in buses and set(q.outages.branches) <= set(branches)
            and set(q.outages.generators) <= set(gens), "network/query indices differ")
    anchor = dict(query.anchor_generation)
    require(not query.anchor_generation or len(anchor) == len(query.anchor_generation) == len(gens)
            and set(anchor) == set(gens) and all(isfinite(v) for v in anchor.values()), "invalid anchor generation")
    require(q.anchor_id is None or set(anchor) == set(gens), "missing anchor generation")
    from pyomo.environ import ConcreteModel, Constraint, Objective, Set, Var, minimize, maximize
    model = ConcreteModel()
    model.BUS = Set(initialize=tuple(buses), ordered=True)
    model.GEN = Set(initialize=tuple(gens), ordered=True)
    model.BRANCH = Set(initialize=tuple(branches), ordered=True)

    def gen_bounds(_m, i):
        g = gens[i]
        if not g.in_service or i in q.outages.generators: return 0., 0.
        lo, hi = g.p_min_mw, g.p_max_mw
        if anchor:
            limit = float(q.redispatch_fraction) * g.p_max_mw
            lo, hi = max(lo, anchor[i]-limit), min(hi, anchor[i]+limit)
        require(lo <= hi, "inconsistent generation bounds")
        return lo, hi

    model.generation = Var(model.GEN, bounds=gen_bounds)
    model.angle = Var(model.BUS)
    model.flow = Var(model.BRANCH, bounds=lambda m, i: (-branches[i].rate_a_mw, branches[i].rate_a_mw))
    model.meter = Var(bounds=(float(q.meter_min), float(q.meter_max)))
    model.curtailment = Var(bounds=(0., float(q.curtailment_max)))
    model.curtailment_bound = Constraint(expr=model.curtailment <= model.meter)
    model.angle[d.reference_bus].fix(0.)

    def flow_rule(m, i):
        b = branches[i]
        if not b.in_service or i in q.outages.branches: return m.flow[i] == 0.
        require(isfinite(b.reactance_pu) and b.reactance_pu != 0 and b.tap_ratio > 0, "invalid branch parameters")
        return m.flow[i] == d.base_mva/(b.reactance_pu*b.tap_ratio) * (m.angle[b.from_bus]-m.angle[b.to_bus]-b.phase_shift_rad)

    model.branch_flow = Constraint(model.BRANCH, rule=flow_rule)

    def balance(m, i):
        generation = sum(m.generation[g.index] for g in d.generators if g.bus == i)
        outgoing = sum(m.flow[b.index] for b in d.branches if b.from_bus == i)
        incoming = sum(m.flow[b.index] for b in d.branches if b.to_bus == i)
        meter = m.meter-m.curtailment if i == q.poi_bus else 0.
        return generation-buses[i].demand_mw-meter == outgoing-incoming

    model.power_balance = Constraint(model.BUS, rule=balance)
    if q.role != "reference_base_P0" and q.role != "reference_raw_need":
        model.connection = Constraint(expr=model.meter-model.curtailment <= float(q.connection_capacity))
    if q.objective == "economic":
        expression = sum((g.cost_quadratic+float(q.economic_regularization_quadratic))*model.generation[g.index]**2 + g.cost_linear*model.generation[g.index]
                         + g.cost_constant for g in d.generators if g.in_service and g.index not in q.outages.generators)
    elif q.objective == "min_curtailment": expression = model.curtailment
    else: expression = model.meter
    model.objective = Objective(expr=expression, sense=maximize if q.objective == "max_meter" else minimize)
    return model


def point_from_model(query, model):
    def number(v):
        require(v.value is not None and isfinite(v.value), "unresolved model value")
        return float(v.value)
    return PointWitness(query.identity, number(model.meter), number(model.curtailment),
        tuple((i, number(model.generation[i])) for i in model.GEN),
        tuple((i, number(model.angle[i])) for i in model.BUS), tuple((i, number(model.flow[i])) for i in model.BRANCH))
