"""Exact one-hour business relaxations; no network, policy or ledger execution."""
from fractions import Fraction
from hashlib import sha256

import yaml

CONFIGS = (
    "configs/staged_deliverability_rts24_v1.DRAFT.yaml",
    "configs/staged_deliverability_small_case_v1.DRAFT.yaml",
    "configs/staged_deliverability_network_v1.DRAFT.yaml",
)
CONFIG_SHA = (
    "6897979b6394a20b406031e9bcc8fadf5751c7815c996dc177956535679b7791",
    "5b334398b2894da70c81baaad74da2dfcecde490ab539bacf3fdb0c988eb4ac5",
    "c6bb0cc30a330fed07a9d0b7f22dea7ce5096f20f1f58a8dc79dddc58059686b",
)
FAMILIES = ("whole_x", "normal_full_C_cfe_g0", "joint_whole_x_cfe_gX")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def exact(value):
    require(type(value) in (str, int, Fraction), "expected exact rational")
    return Fraction(value)


class UniqueLoader(yaml.SafeLoader):
    """Closed inputs must not contain duplicate keys or YAML merge aliases."""


def unique_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        require(key_node.tag != "tag:yaml.org,2002:merge", "YAML merge forbidden")
        key = loader.construct_object(key_node, deep=deep)
        require(type(key) in (str, int) and key not in result, "duplicate or invalid YAML key")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def parse(raw):
    require(set(raw) == set(CONFIGS), "exactly three source configs required")
    for name, digest in zip(CONFIGS, CONFIG_SHA):
        require(type(raw[name]) is bytes and len(raw[name]) < 16384, "config byte bound")
        require(sha256(raw[name]).hexdigest() == digest, "config SHA differs before parse")
    public, business, rights = [yaml.load(raw[name], Loader=UniqueLoader) for name in CONFIGS]
    require(public["business"]["fixture"] == rights["business_fixture"] == CONFIGS[1], "business path link")
    require(public["business"]["sha256"] == rights["business_sha256"] == CONFIG_SHA[1], "business SHA link")
    require(public["rights"]["fixture"] == CONFIGS[2] and public["rights"]["sha256"] == CONFIG_SHA[2], "rights link")
    require(all(c["status"] == "DRAFT_NONAUTHORITATIVE" for c in (public,business,rights)), "authority differs")
    scale = exact(public["business"]["dimensional_scale"])
    require(scale == 200 and public["time"]["first_hour"] == business["first_hour"] == -2
        and business["last_hour"] == 7 and public["time"]["registration_end"] == 4
        and public["time"]["observation_end"] == 8, "only the frozen ten-hour scope")
    require(public["project"]["start_hour"] == business["grid"]["start"] == rights["network"]["project_start"]
        and public["project"]["lead_hours"] == business["grid"]["lead"] == rights["network"]["project_lead"]
        and public["project"]["delays"] == business["grid"]["delays"] == rights["network"]["delays"], "timing link")
    require(set(public["project"]["delays"]) == {"on_time", "delayed"}
        and set(business["clean_paths"]) == {"early", "late"}
        and all(len(v) == 8 for v in business["clean_paths"].values()), "fixed path scope")
    for stage in ("before", "after"):
        c = scale*(exact(rights["rights"]["firm_"+stage+"_mw"])+exact(rights["rights"]["conditional_"+stage+"_mw"]))
        require(c == scale*exact(business["grid"][stage]), "numeric grid F+X crosslink")
    return public, business, rights


def inputs(raw):
    public, business, rights = parse(raw)
    scale = exact(public["business"]["dimensional_scale"])
    parameters = business["parameters"]
    rows = []
    for plan in ("on_time", "delayed"):
        commission = public["project"]["start_hour"]+public["project"]["lead_hours"]+public["project"]["delays"][plan]
        for clean in ("early", "late"):
            for hour in range(-2, 8):
                stage = "after" if hour >= commission else "before"
                online = [e for e in business["equipment"] if hour >= e["start"]+e["lead"]+e["delay"]]
                values = dict(D=scale*exact(parameters["capacity"]), alpha=exact(parameters["alpha"]),
                    beta=exact(parameters["beta"]), gamma=exact(parameters["facility_factor"]),
                    auxiliary=scale*exact(parameters["auxiliary_mw"]), dt=Fraction(1),
                    K=scale*sum((exact(e["capacity"]) for e in online), Fraction()),
                    idle=scale*sum((exact(e["idle_mw"]) for e in online), Fraction()),
                    f=exact(business["flexible_fraction"]) if hour >= 0 else Fraction(),
                    Y=scale*exact(business["clean_paths"][clean][hour] if hour >= 0 else business["prehistory_clean"]),
                    F=scale*exact(rights["rights"]["firm_"+stage+"_mw"]),
                    X=scale*exact(rights["rights"]["conditional_"+stage+"_mw"]),
                    actual_workload=scale*exact(business["workload"]["after" if hour >= business["workload"]["change_hour"] else "before"]))
                values["C"] = values["F"]+values["X"]
                rows.append(dict(plan=plan, clean_path=clean, hour=hour,
                    time_role="prehistory" if hour < 0 else "registration" if hour < 4 else "followup",
                    equipment_ids=[e["id"] for e in online], grid_commissioned=stage == "after", input=values))
    return rows


def calculate(row):
    v = row["input"]
    require(set(v) == {"D","alpha","beta","gamma","auxiliary","dt","K","idle","f","Y","F","X","actual_workload","C"}, "input fields")
    v = {k:exact(x) for k,x in v.items()}
    require(all(x >= 0 for x in v.values()) and v["dt"] > 0 and v["beta"] > 0 and v["gamma"] > 0
        and 0 <= v["alpha"] <= 1 and 0 <= v["f"] <= 1 and v["C"] == v["F"]+v["X"], "input domain")
    a = v["gamma"]*v["beta"]
    w = (v["C"]-v["gamma"]*v["idle"]-v["auxiliary"])/a
    h = max(v["C"]-v["Y"]/(v["alpha"]*v["dt"]), Fraction()) if v["alpha"] else Fraction()

    def screen(q):
        checks = dict(baseline_nonnegative=w >= 0, q_nonnegative=q >= 0, within_D=q <= v["D"],
            within_flexible=q <= v["f"]*w, device_lower=w-q >= 0, device_upper=w-q <= v["K"])
        return dict(q=q, device_activity=w-q, conditions=checks, necessary_pass=all(checks.values()))

    g_low = max(Fraction(), a*(w-v["K"])-h)
    g_business = a*min(v["D"],v["f"]*w,w)-h
    g_high = min(v["X"],g_business)
    reference = v["gamma"]*(v["idle"]+v["beta"]*v["actual_workload"])+v["auxiliary"]
    whole = screen(v["X"]/a)
    device = {k:whole["conditions"][k] for k in ("device_lower","device_upper")}
    # Preserve the enrolled-X definition; the additional device observation is separate.
    whole["conditions"] = {k:whole["conditions"][k] for k in ("baseline_nonnegative","within_D","within_flexible")}
    whole["necessary_pass"] = all(whole["conditions"].values())
    whole["additional_device_diagnostic"] = dict(conditions=device,passed=all(device.values()),
        premise="hypothetical_g_X_no_CFE_not_part_of_enrolled_X_three_conditions")
    return {**row, "input":v, "derived":dict(a=a, w_hat=w, h_hat=h, aD=a*v["D"], afw=a*v["f"]*w),
        "screens":dict(zip(FAMILIES,(whole,screen(h/a),screen((v["X"]+h)/a)))),
        "unknown_g":dict(minimum=g_low,maximum_business=g_business,maximum_with_x=g_high,
            nonempty=w >= 0 and g_low <= g_high),
        "reference_policy":dict(power=reference,connection_shortfall=max(reference-v["C"],Fraction()),
            used_as_full_C_workload=False)}


def encode(value):
    if isinstance(value, Fraction):
        return str(value)
    if isinstance(value, dict):
        return {k:encode(v) for k,v in value.items()}
    if isinstance(value, (list,tuple)):
        return [encode(v) for v in value]
    return value


def summarize(rows):
    require(len(rows) == 40 and len({(r["plan"],r["clean_path"],r["hour"]) for r in rows}) == 40, "row scope")
    result = {}
    for scope in ("all", "prehistory", "registration", "followup"):
        selected = [r for r in rows if scope == "all" or r["time_role"] == scope]
        result[scope] = dict(rows=len(selected), families={f:dict(passed=sum(r["screens"][f]["necessary_pass"] for r in selected),
            failed=sum(not r["screens"][f]["necessary_pass"] for r in selected)) for f in FAMILIES},
            unknown_g_nonempty=sum(r["unknown_g"]["nonempty"] for r in selected))
    result["registration_path_conjunctions"] = [dict(plan=plan,clean_path=clean,
        families={f:all(r["screens"][f]["necessary_pass"] for r in rows
            if r["plan"] == plan and r["clean_path"] == clean and r["time_role"] == "registration") for f in FAMILIES})
        for plan in ("on_time", "delayed") for clean in ("early", "late")]
    return result


def evaluate(raw):
    rows = [calculate(row) for row in inputs(raw)]
    return encode(dict(rows=rows,summary=summarize(rows)))
