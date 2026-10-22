"""Static accounting and immutable metadata reads, without scientific imports."""
import ast
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

import pytest

from experiments import staged_c_workflow_budget_v1 as budget


def expanded_calls(roles):
    calls = []
    def audit(prefix): calls.extend(roles[:prefix])
    for i in range(len(roles)):
        for _ in range(2):
            audit(i)
            calls.append(roles[i])
        audit(i+1)
    audit(len(roles)); audit(len(roles))
    return calls


@pytest.mark.parametrize("raw", [[],[0],[1],[0,1]])
@pytest.mark.parametrize("recover", [False,True])
def test_weighted_formula_matches_expanded_writer_and_terminal_replay(raw,recover):
    roles = [[budget.ROLES[0]]+([budget.ROLES[1]] if i in raw else [])+(list(budget.ROLES[2:]) if recover else []) for i in range(2)]
    expanded = expanded_calls(roles)
    expected = Counter(role for call in expanded for role in call)
    actual = budget.profile(roles)
    assert actual["calls"] == len(expanded) == 13
    assert actual["descriptions"] == sum(expected.values())
    assert actual["roles"] == {r:expected[r] for r in budget.ROLES}


def test_current_frozen_P1_roles_and_per_process_counts_reconcile():
    native = json.loads((budget.ROOT/budget.NATIVE).read_bytes())
    frames = json.loads((budget.ROOT/budget.FRAMES).read_bytes())
    result = budget.p1_accounting(native["schedule"],frames["selected"])
    assert result["single_journal"]["calls"] == 55 and result["single_journal"]["descriptions"] == 173
    assert result["phases"]["worker"]["selective"]["calls"] == 120
    assert result["phases"]["worker"]["selective"]["descriptions"] == 378
    total = result["selective_total_including_historical_registration"]
    assert total["calls"] == 185 and total["descriptions"] == 583 and total["hour_calls"] == [55,46,37,28,19]
    assert result["selective_execution_only"]["calls"] == 180 and result["selective_execution_only"]["descriptions"] == 567
    assert result["full_calls_including_registration"] == 8 and result["full_descriptions_including_registration"] == 1140
    assert result["audit_execution_calls"]["total"] == 52 and result["audit_row_visits"] == 135
    assert sum(result["audit_row_visits_per_hour"]) == 135
    assert result["fingerprints_calls"] == 131 and result["preserve_calls"] == 5
    assert result["physical_job_member_count"] is result["wall_estimate_seconds"] is None


@pytest.mark.parametrize("change", ["slot_gap","role","frame_duplicate","generator_split"])
def test_different_schedule_or_contingency_scope_cannot_reuse_accounting(change):
    native = json.loads((budget.ROOT/budget.NATIVE).read_bytes())
    frames = json.loads((budget.ROOT/budget.FRAMES).read_bytes())
    if change == "slot_gap": native["schedule"][2]["ordinal"] = 1
    elif change == "role": native["schedule"][0]["role"] = "normal_contract_C"
    elif change == "frame_duplicate": frames["selected"][0] = frames["selected"][1]
    else: frames["selected"][0]["branches"], frames["selected"][0]["generators"] = [],[999]
    with pytest.raises(ValueError): budget.p1_accounting(native["schedule"],frames["selected"])


def test_reader_checks_hash_and_retained_bytes_at_end(tmp_path):
    path = tmp_path/"input.json"
    raw = b'{"value":1}\n'
    path.write_bytes(raw)
    reader = budget.Reader(tmp_path)
    assert reader.json(path.name,sha256(raw).hexdigest()) == {"value":1}
    path.write_bytes(b'{"value":2}\n')
    with pytest.raises(ValueError,match="pin differs"): reader.bookend()


@pytest.mark.parametrize("name", ["../outside.json","/outside.json","C:/outside.json","dir\\input.json",""])
def test_reader_rejects_unregistered_root_escape_before_open(tmp_path,name):
    with pytest.raises(ValueError,match="unsafe input path"): budget.Reader(tmp_path).read(name)


def test_reader_size_cap_precedes_reading_data(tmp_path,monkeypatch):
    path = tmp_path/"oversized.json"
    with path.open("wb") as stream: stream.truncate(2*1024**2+1)
    original = Path.open
    def guarded(self,*args,**kwargs):
        if self == path: pytest.fail("oversized metadata was read")
        return original(self,*args,**kwargs)
    monkeypatch.setattr(Path,"open",guarded)
    with pytest.raises(ValueError,match="read cap"): budget.Reader(tmp_path).read(path.name)


def test_budget_module_has_no_scientific_or_subprocess_import_path():
    tree = ast.parse(Path(budget.__file__).read_text(encoding="utf-8"))
    allowed = {"collections","hashlib","json","os","pathlib","stat","sys","time"}
    for node in ast.walk(tree):
        if isinstance(node,ast.Import): assert all(a.name.split('.')[0] in allowed for a in node.names)
        elif isinstance(node,ast.ImportFrom): assert node.module.split('.')[0] in allowed


def test_reader_checks_wall_after_terminal_read(tmp_path,monkeypatch):
    (tmp_path/"input.json").write_bytes(b"{}")
    with monkeypatch.context() as isolated:
        clock = iter((0,0,21))
        isolated.setattr(budget.time,"perf_counter",lambda:next(clock))
        reader = budget.Reader(tmp_path)
        with pytest.raises(ValueError,match="read cap"): reader.read("input.json")


def test_public_declared_package_caps_keep_actual_and_contract_layers_separate():
    table = budget.public_request_caps(69)
    assert table["three_method_actual_representative"]["per_method"] == [21,41,41]
    for key,expected in (("P2_two_contract_frames",(41,278,319,160,159)),
        ("single_method_all_ten_frames",(41,1390,1431,720,711)),
        ("three_methods_all_ten_frames",(103,4170,4273,2160,2113))):
        row = table[key]
        assert tuple(row[k] for k in ("actual","contract","total","qp","lp")) == expected
        assert row["total"] == row["actual"]+row["contract"] == row["qp"]+row["lp"]
        assert row["wall_estimate_seconds"] is None and row["runtime_implemented"] is False
    assert table["D_points"] is table["E_holdout_paths"] is table["total_resource_estimate"] is None


def test_reconciliation_uses_final_worker_timing_and_keeps_admission_closed(tmp_path,monkeypatch):
    native = json.loads((budget.ROOT/budget.NATIVE).read_bytes())
    frames = json.loads((budget.ROOT/budget.FRAMES).read_bytes())
    base = budget.COST_BASE
    values = {budget.NATIVE:native,budget.FRAMES:frames,
        budget.COST:dict(combined_counts=[198,548],source_pins={"saved_source.py":{}},resource_admission=False,
            result_files={},core_files=571,terminal_files=579,terminal_bytes=1660401),
        base+"cost_probe_01/report.json":dict(phases=[],group_seconds={"report":0}),
        base+"cost_probe_01/worker_timing.json":dict(phases=[dict(stage="saved_report")],group_seconds={"report":.25}),
        base+"execution_observations_01/verification_v2.json":dict(all_files_hash_matched=True,
            exact_core_and_controller_maps=True,per_case_parent_and_fresh_roles_checked=True)}
    for role,target in (("preparation","cost_preparation_01"),("measurement","cost_probe_01")):
        values[base+"execution_observations_01/"+role+"_01/capture.json"] = dict(accepted_success=True,exit_code=0,external_wall_seconds=10)
        values[base+target+"/controller_timings.json"] = dict(accepted_success=True)
        values[base+target+"/launcher.json"] = dict(job_quiet_confirmed=True,outer_seconds=8,
            sampled_tree_peak_rss_bytes=100,peak_job_commit_bytes=80)
    instances = []
    class RetainedMetadata:
        def __init__(self,root):
            self.root,self.started,self.pins,self.operations,self.bytes,self.checked = tmp_path,budget.time.perf_counter(),{},0,0,False
            instances.append(self)
        def read(self,name,expected=None): self.operations += 1
        def json(self,name,expected=None): self.read(name,expected); return values[name]
        def bookend(self): self.checked = True
    monkeypatch.setattr(budget,"Reader",RetainedMetadata)
    result = budget.reconcile(tmp_path)
    assert instances[0].checked
    assert result["saved_group_seconds"] == {"report":.25}
    assert result["scientific_compiler_calls_in_this_audit"] == result["native_calls_in_this_audit"] == 0
    assert result["resource_admission"] is result["overall_performance_review_complete"] is result["environment_revalidated"] is False
