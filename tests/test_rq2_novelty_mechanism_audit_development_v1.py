from copy import deepcopy
from fractions import Fraction as Q
from hashlib import sha256
from itertools import product
import json

import pytest
import yaml

from experiments import rq2_novelty_mechanism_audit_development_v1 as m


@pytest.fixture(scope="module")
def config():
    return yaml.safe_load((m.ROOT/m.CONFIG).read_text(encoding="utf-8"))


def test_timing_changes_capacity_with_identical_requests_and_clean_marginals(config):
    toy=config["toy"]
    good=m.make_case(toy,(2,3),3,Q(1))
    late=m.make_case(toy,(3,5),3,Q(1))
    assert good["q"] == late["q"] == [Q(1,10),Q(1,10),0,0,0,0]
    assert sorted(good["R"]) == sorted(late["R"])
    assert sum(good["allowance"]) == sum(late["allowance"])
    assert m.analyze_case(good)["minimum_D"] == "1/10"
    assert m.analyze_case(late)["minimum_D"] == "1/5"


def test_efficiency_makes_late_supply_insufficient_for_every_capacity(config):
    case=m.make_case(config["toy"],(3,5),3,Q(17,20))
    result=m.analyze_case(case)
    assert result["minimum_D"] is None
    cut=result["cuts"][-1]
    assert Q(cut["recovery_energy"]) > Q(cut["total_supply"])
    assert not result["causal_edf"]["success"]


def test_longer_deadline_removes_the_matched_timing_effect(config):
    assert [m.analyze_case(m.make_case(config["toy"],slots,4,Q(1)))["minimum_D"]
            for slots in ((2,3),(3,5))] == ["1/10","1/10"]


def test_policy_failure_is_not_infeasibility(config):
    result=m.analyze_case(m.make_case(config["toy"],(2,3),3,Q(1)))
    assert result["causal_edf"]["success"]
    assert not result["wait_until_deadline_policy"]["success"]
    assert result["maxflow_recovery_energy"] == "1/5"


def test_all_constructed_cases_preserve_controls_and_causal_prefixes(config):
    result=m.toy_audit(config["toy"])
    assert len(result["cases"]) == 36
    assert result["common_prefix_future_perturbation_checks"] == 432
    assert not result["full_support_causal_policy_proven"]
    assert all(c["minimum_D"] == "1/10" for c in result["clean_limit_controls"])
    bridge={(tuple(c["clean_slots"]),c["installed_capacity"]):c["minimum_D"]
            for c in result["installed_capacity_headroom_examples"]}
    assert bridge[(2,3),"3/10"] == "1/10"
    assert bridge[(3,5),"3/10"] is None
    assert bridge[(3,5),"2/5"] == "1/5"


def test_due_hour_recovery_allowed_but_birth_hour_recovery_not_allowed():
    jobs=[dict(birth=0,due=1,recovery_energy=Q(1))]
    assert m.flow_schedule(jobs,[Q(1),Q(0)],Q(1))[0] == 0
    assert m.flow_schedule(jobs,[Q(0),Q(1)],Q(1))[0] == 1


def test_discrete_independent_assignment_oracle_checks_maxflow_and_cut_bound():
    # Four possible slots, two one-unit jobs. Enumerate assignments directly;
    # neither the Hall bound nor the residual graph participates in this oracle.
    jobs=[dict(birth=0,due=2,recovery_energy=Q(1)),
          dict(birth=1,due=3,recovery_energy=Q(1))]
    for capacities in product((0,1,2),repeat=3):
        u=[Q(0),*map(Q,capacities)]
        expected=False
        for first,second in product((1,2),(2,3)):
            used=[0]*4;used[first]+=1;used[second]+=1
            if all(a <= b for a,b in zip(used,u)):
                expected=True
        sent,_=m.flow_schedule(jobs,u,Q(2))
        D,_=m.minimum_capacity(jobs,[Q(0)]*4,u)
        assert (sent == 2) == expected == (D is not None)


@pytest.mark.parametrize("source,f,excluded",[
    ("0.000001","0",False),
    ("0.2","0.2",False),
    ("0.200002","0.2",False),
    ("0.200002000000000001","0.2",True),
])
def test_exact_activity_and_relaxed_gap_boundaries(source,f,excluded):
    value=m.local_arithmetic("1",1-Q(source),"1",f,"0"*64)
    assert value["local_relaxation_empty"] is excluded


def test_projection_uses_half_even_and_rejects_unmapped_rows():
    assert m.exact_projection("0.1234567890125") == Q("0.123456789012")
    assert m.exact_projection("0.1234567890135") == Q("0.123456789014")
    for value in ("1.1","0","0.00000000000001"):
        with pytest.raises(ValueError):m.exact_projection(value)


def test_independent_saved_source_and_1900_cell_reconstruction(config):
    def read(name,pin=None):
        raw=(m.ROOT/name).read_bytes()
        assert pin is None or sha256(raw).hexdigest() == pin
        return raw
    result=m.audit_sources(config,read)
    assert (result["excluded_cells"],result["unresolved_cfe_cells"],result["unresolved_network_cells"]) == (1856,44,1900)
    assert result["source_hours"] == {"power":354,"workload":570}
    assert result["exact_arithmetic_groups"] == 300
    by_fraction={}
    for t in result["per_theta"]:
        by_fraction.setdefault(t["flexible_fraction"],set()).add(t["unresolved"])
    assert by_fraction == {"0.05":{2},"0.20":{2},"0.50":{4}}
    assert not result["runtime_reachability_proven"]
    assert result["identity_sets_closed"]
    inventory=result["identity_inventories"]
    assert tuple(len(inventory[k]) for k in ("cell_sha256","arithmetic_group_sha256","proof_sha256")) == (1900,300,292)
    assert result["identity_inventory_sha256"] == m.digest(inventory)
    for key in inventory:
        assert {c[key] for c in result["cells"] if c[key] is not None} == set(inventory[key])
    assert result["source_clocks"]["power"]["utc_hour_rows_verified"] == 168
    assert not result["source_clocks"]["workload"]["absolute_utc_timestamp_available"]


@pytest.mark.parametrize("field",["raw_workload","cell_status","network_status"])
def test_rehashed_saved_report_tampering_is_rejected(config,field):
    config=deepcopy(config)
    name=config["source_audit"]["exclusion_report"]
    report=json.loads((m.ROOT/name).read_bytes())
    if field == "raw_workload":
        report["witness"]["whole_enrollment_source_windows"]["workload"]["rows"][0]["workload_fraction"]="0.5"
        report["witness_sha256"]=m.digest(report["witness"])
    elif field == "cell_status":
        report["cells"][0]["status"]="cell_local_relaxation_contradiction"
    else:
        report["cells"][0]["network_only_conclusion"]="excluded"
    raw=m.canonical(report)
    config["source_audit"]["exclusion_sha256"]=sha256(raw).hexdigest()
    def read(path,pin=None):
        value=raw if path == name else (m.ROOT/path).read_bytes()
        assert pin is None or sha256(value).hexdigest() == pin
        return value
    with pytest.raises(ValueError):m.audit_sources(config,read)


@pytest.mark.parametrize("section,field",[
    ("toy",key) for key in ("debt_initial","recovery_release","deadline_check","capacity_rule",
                           "minimum_capacity_domain","controls","construction_link","deadline_lags")
]+[("resource_plan",key) for key in m.SUPPORTED_PLAN])
def test_configuration_drift_is_rejected_before_execution(config,section,field):
    changed=deepcopy(config)
    value=changed[section][field]
    changed[section][field]=value+1 if isinstance(value,int) else "unsupported"
    with pytest.raises(ValueError):m.validate_config(changed)


@pytest.mark.parametrize("section,field,value",[
    ("business_anchor","service_tolerance","0.00001"),
    ("business_anchor","minimum_event_power","0"),
    ("source_mapping","workload_projection_decimal_places",11),
    ("source_mapping","workload_projection_rounding","floor"),
    ("window","enrollment_hours",24),
])
def test_source_protocol_drift_does_not_reuse_fixed_arithmetic(config,section,field,value):
    protocol=yaml.safe_load((m.ROOT/config["source_audit"]["protocol"]).read_bytes())
    protocol[section][field]=value
    with pytest.raises(ValueError):m.validate_source_protocol(protocol)


@pytest.mark.parametrize("timestamp",[
    "2020-01-01T01:00:00+08:00", "2020-01-01T01:30:00+00:00",
    "2020-01-01T02:00:00+00:00", "2020-01-01T01:00:00",
])
def test_independent_utc_clock_rejects_bad_offset_alignment_and_gaps(timestamp):
    rows=[dict(source_hour="0",timestamp="2020-01-01T00:00:00+00:00"),
          dict(source_hour="1",timestamp=timestamp)]
    with pytest.raises(ValueError):m.validate_power_clock(rows)


@pytest.mark.parametrize("field,value",[
    ("affected_arms",["network-only"]),
    ("policy_quantifier","only this selected fixed policy"),
    ("registered_capacity_domain",["0","2"]),
    ("normal_reference_feasibility_not_assumed",False),
])
def test_rehashed_proof_envelope_tampering_is_rejected(config,field,value):
    config=deepcopy(config)
    name=config["source_audit"]["exclusion_report"]
    report=json.loads((m.ROOT/name).read_bytes())
    old=next(iter(report["proofs"]))
    proof=report["proofs"].pop(old);proof[field]=value
    new=m.digest(proof);report["proofs"][new]=proof
    for cell in report["cells"]:
        if cell["proof_sha256"] == old:cell["proof_sha256"]=new
    raw=m.canonical(report);config["source_audit"]["exclusion_sha256"]=sha256(raw).hexdigest()
    def read(path,pin=None):
        value=raw if path == name else (m.ROOT/path).read_bytes()
        assert pin is None or sha256(value).hexdigest() == pin
        return value
    with pytest.raises(ValueError,match="envelope"):m.audit_sources(config,read)


def test_component_requests_and_clean_marginals_are_retained(config):
    good=m.analyze_case(m.make_case(config["toy"],(2,3),3,Q(1)))
    late=m.analyze_case(m.make_case(config["toy"],(3,5),3,Q(1)))
    assert good["grid_request"] == late["grid_request"] == ["1/10","0","0","0","0","0"]
    assert good["cfe_request"] == late["cfe_request"] == ["0","1/10","0","0","0","0"]
    assert sorted(good["clean_share"]) == sorted(late["clean_share"])
    assert sum(map(Q,good["allowance"])) == sum(map(Q,late["allowance"]))
    assert max(map(Q,good["allowance"])) == max(map(Q,late["allowance"]))


def test_late_completion_keeps_the_deadline_violation():
    result=m.causal_edf(dict(eta=Q(1),lag=1,q=[Q(1),Q(0),Q(0)],u=[Q(0),Q(0),Q(1)]),Q(1))
    assert result["recovered_work"] == "1"
    assert not result["success"]
    assert result["deadline_violations"] == [dict(hour=1,birth=0,due=1,unfinished_work="1")]
