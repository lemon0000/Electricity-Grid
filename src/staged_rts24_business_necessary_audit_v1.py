"""Independent raw-YAML/cross-multiplication oracle; imports no calculator."""
from fractions import Fraction as Q
import yaml


def verify(raw, result):
    """Reconstruct all inputs; compare each encoded field, then aggregate afresh."""
    names = ("configs/staged_deliverability_rts24_v1.DRAFT.yaml", "configs/staged_deliverability_small_case_v1.DRAFT.yaml",
        "configs/staged_deliverability_network_v1.DRAFT.yaml")
    p,b,n = [yaml.safe_load(raw[name]) for name in names]
    s = Q(p["business"]["dimensional_scale"])
    pars = b["parameters"]
    d,al,be,ga,aux = (s*Q(pars["capacity"]),Q(pars["alpha"]),Q(pars["beta"]),Q(pars["facility_factor"]),s*Q(pars["auxiliary_mw"]))
    slope = be*ga
    families = ("whole_x", "normal_full_C_cfe_g0", "joint_whole_x_cfe_gX")
    expected = []
    for plan in ("on_time","delayed"):
        commissioned_at = p["project"]["start_hour"]+p["project"]["lead_hours"]+p["project"]["delays"][plan]
        for clean in ("early","late"):
            for t in range(-2,8):
                equipment = [e for e in b["equipment"] if t-e["start"]-e["lead"]-e["delay"] >= 0]
                k = sum((s*Q(e["capacity"]) for e in equipment),Q(0))
                idle = sum((s*Q(e["idle_mw"]) for e in equipment),Q(0))
                stage = "after" if t >= commissioned_at else "before"
                firm, x = [s*Q(n["rights"][key+stage+"_mw"]) for key in ("firm_","conditional_")]
                c = firm+x
                flexible = Q(0) if t < 0 else Q(b["flexible_fraction"])
                y = s*Q(b["prehistory_clean"] if t < 0 else b["clean_paths"][clean][t])
                actual = s*Q(b["workload"]["before" if t < b["workload"]["change_hour"] else "after"])
                available_power = c-ga*idle-aux
                clean_shortfall = max(al*c-y,Q(0))/al if al else Q(0)
                screens = {}
                for family, reduction in zip(families,(x,clean_shortfall,x+clean_shortfall)):
                    checks = dict(baseline_nonnegative=available_power >= 0,q_nonnegative=reduction >= 0,
                        within_D=reduction <= slope*d,within_flexible=reduction <= flexible*available_power,
                        device_lower=available_power >= reduction,device_upper=available_power-reduction <= slope*k)
                    screens[family] = dict(q=reduction/slope, device_activity=(available_power-reduction)/slope,
                        conditions=checks,necessary_pass=all(checks.values()))
                whole = screens["whole_x"]
                extra = dict(device_lower=available_power >= x,device_upper=available_power-x <= slope*k)
                whole["conditions"] = dict(baseline_nonnegative=available_power >= 0,
                    within_D=x <= slope*d,within_flexible=x <= flexible*available_power)
                whole["necessary_pass"] = all(whole["conditions"].values())
                whole["additional_device_diagnostic"] = dict(conditions=extra,passed=all(extra.values()),
                    premise="hypothetical_g_X_no_CFE_not_part_of_enrolled_X_three_conditions")
                lower = max(Q(0),available_power-slope*k-clean_shortfall)
                upper = min(slope*d,flexible*available_power,available_power)-clean_shortfall
                values = dict(D=d,alpha=al,beta=be,gamma=ga,auxiliary=aux,dt=Q(1),K=k,idle=idle,f=flexible,
                    Y=y,F=firm,X=x,actual_workload=actual,C=c)
                power = ga*idle+slope*actual+aux
                expected.append(dict(plan=plan,clean_path=clean,hour=t,
                    time_role="prehistory" if t in (-2,-1) else "registration" if t in range(4) else "followup",
                    equipment_ids=[e["id"] for e in equipment],grid_commissioned=t >= commissioned_at,input=values,
                    derived=dict(a=slope,w_hat=available_power/slope,h_hat=clean_shortfall,aD=slope*d,afw=flexible*available_power),
                    screens=screens,unknown_g=dict(minimum=lower,maximum_business=upper,maximum_with_x=min(x,upper),
                        nonempty=available_power >= 0 and lower <= min(x,upper)),
                    reference_policy=dict(power=power,connection_shortfall=max(power-c,Q(0)),used_as_full_C_workload=False)))
    def wire(value):
        if type(value) is Q: return str(value)
        if type(value) is dict: return {k:wire(v) for k,v in value.items()}
        if type(value) is list: return [wire(v) for v in value]
        return value
    if result["rows"] != wire(expected):
        raise ValueError("independent raw-input row oracle differs")
    summary = {}
    for scope, hours in (("all",range(-2,8)),("prehistory",range(-2,0)),("registration",range(4)),("followup",range(4,8))):
        selected = [r for r in expected if r["hour"] in hours]
        counts = {}
        for f in families:
            passed = len([r for r in selected if r["screens"][f]["necessary_pass"]])
            counts[f] = dict(passed=passed,failed=len(selected)-passed)
        summary[scope] = dict(rows=len(selected),families=counts,
            unknown_g_nonempty=len([r for r in selected if r["unknown_g"]["nonempty"]]))
    summary["registration_path_conjunctions"] = []
    for plan in ("on_time","delayed"):
        for clean in ("early","late"):
            rs = [r for r in expected if r["plan"] == plan and r["clean_path"] == clean and 0 <= r["hour"] < 4]
            summary["registration_path_conjunctions"].append(dict(plan=plan,clean_path=clean,
                families={f:not any(not r["screens"][f]["necessary_pass"] for r in rs) for f in families}))
    if result["summary"] != summary or set(result) != {"rows","summary"}:
        raise ValueError("independent scope summary oracle differs")
    return dict(rows_checked=len(expected),independent_raw_input_cross_multiplication=True,scope_summaries_checked=True)
