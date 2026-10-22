"""Independent anchors and counterexamples for the closed arithmetic audit."""
import ast
from copy import deepcopy
from fractions import Fraction as Q
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
import time
import runpy

import pytest
import yaml

from src import staged_rts24_business_necessary_v1 as c
from src import staged_rts24_business_necessary_audit_v1 as independent

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def raw():
    return {name:(ROOT/name).read_bytes() for name in c.CONFIGS}


@pytest.fixture(scope="module")
def result(raw):
    return c.evaluate(raw)


def row(result, plan="on_time", clean="early", hour=1):
    return next(r for r in result["rows"] if (r["plan"],r["clean_path"],r["hour"]) == (plan,clean,hour))


def test_complete_coordinates_and_time_roles(result):
    assert {(r["plan"],r["clean_path"],r["hour"]) for r in result["rows"]} == {
        (p,y,h) for p in ("on_time","delayed") for y in ("early","late") for h in range(-2,8)}
    assert [result["summary"][s]["rows"] for s in ("prehistory","registration","followup")] == [8,16,16]
    assert all(r["input"]["f"] == "0" for r in result["rows"] if r["hour"] < 0)


def test_grid_and_equipment_commission_independent(result):
    assert [row(result,hour=h)["grid_commissioned"] for h in (1,2,3,4)] == [False,True,True,True]
    assert [row(result,plan="delayed",hour=h)["grid_commissioned"] for h in (1,2,3,4)] == [False,False,False,True]
    for plan in ("on_time","delayed"):
        assert [row(result,plan=plan,hour=h)["input"]["K"] for h in (1,2)] == ["160","240"]
        assert [row(result,plan=plan,hour=h)["input"]["idle"] for h in (1,2)] == ["16","24"]


def test_full_C_workload_not_actual_and_power_reference(result):
    assert row(result,hour=1)["derived"]["w_hat"] == "108"
    assert row(result,plan="delayed",hour=2)["derived"]["w_hat"] == "100"
    assert row(result,hour=2)["derived"]["w_hat"] == "180"
    assert [row(result,hour=h)["input"]["actual_workload"] for h in (1,2,3)] == ["100","100","140"]
    assert [row(result,hour=h)["reference_policy"]["power"] for h in (1,2,3)] == ["150","160","210"]
    assert row(result,plan="delayed",hour=3)["reference_policy"]["connection_shortfall"] == "50"


def test_scaling_and_independent_numeric_grid_link(result, raw):
    v = row(result)["input"]
    assert [v[k] for k in ("D","alpha","beta","gamma","auxiliary")] == ["40","4/5","1","5/4","5"]
    assert [row(result,hour=h)["input"]["C"] for h in (1,2)] == ["160","260"]
    _,b,n = c.parse(raw)
    assert Q(b["grid"]["before"])*200 == (Q(n["rights"]["firm_before_mw"])+Q(n["rights"]["conditional_before_mw"]))*200 == 160


def test_independent_addition_counterexample(result):
    r = row(result)
    x,green,joint = [r["screens"][f] for f in c.FAMILIES]
    assert (x["q"],green["q"],joint["q"]) == ("32","28","60")
    assert x["necessary_pass"] and green["necessary_pass"] and not joint["necessary_pass"]
    assert Q(joint["q"]) == Q(x["q"])+Q(green["q"]) > Q(r["input"]["D"])
    assert max(Q(x["q"]),Q(green["q"])) <= Q(r["input"]["D"])


def test_unknown_g_positive_can_break_g0(result):
    r = row(result)
    assert r["screens"][c.FAMILIES[1]]["necessary_pass"]
    assert r["unknown_g"] == dict(minimum="0",maximum_business="15",maximum_with_x="15",nonempty=True)
    q10 = (Q(10)+Q(r["derived"]["h_hat"]))/Q(r["derived"]["a"])
    q20 = (Q(20)+Q(r["derived"]["h_hat"]))/Q(r["derived"]["a"])
    assert q10 <= 40 < q20


def test_positive_g_can_fix_device_upper_without_false_global_failure(raw):
    r = deepcopy(c.inputs(raw)[2])  # h=0 before stage, w=108, h_CFE=10
    r["input"].update(K=Q(60),D=Q(100),f=Q(1),X=Q(100),F=Q(60))
    value = c.calculate(r)
    assert not value["screens"][c.FAMILIES[1]]["necessary_pass"]
    assert not value["screens"][c.FAMILIES[1]]["conditions"]["device_upper"]
    assert value["unknown_g"]["nonempty"] and value["unknown_g"]["minimum"] == 50
    g = value["unknown_g"]["minimum"]
    activity = value["derived"]["w_hat"]-(g+value["derived"]["h_hat"])/value["derived"]["a"]
    assert activity == 60


def test_enrolled_X_three_conditions_separate_device_diagnostic(raw):
    r=deepcopy(c.inputs(raw)[2]);r["input"]["K"]=0
    whole=c.calculate(r)["screens"][c.FAMILIES[0]]
    assert set(whole["conditions"]) == {"baseline_nonnegative","within_D","within_flexible"}
    assert whole["necessary_pass"] and not whole["additional_device_diagnostic"]["passed"]


def test_negative_upper_is_retained_and_all_nonnegative_g_ruled_out(result):
    r = row(result,clean="late",hour=2)
    assert r["screens"][c.FAMILIES[1]]["q"] == "80"
    assert r["unknown_g"]["maximum_business"] == "-50" and not r["unknown_g"]["nonempty"]
    assert all(not row(result,hour=h)["unknown_g"]["nonempty"] for h in (-2,-1))


def test_clean_changes_CFE_not_whole_X(result):
    for plan in ("on_time","delayed"):
        for h in range(-2,8):
            assert row(result,plan,"early",h)["screens"][c.FAMILIES[0]] == row(result,plan,"late",h)["screens"][c.FAMILIES[0]]
    assert row(result,hour=2)["screens"][c.FAMILIES[1]]["necessary_pass"]
    assert not row(result,clean="late",hour=2)["screens"][c.FAMILIES[1]]["necessary_pass"]


def test_scope_counts_and_registration_conjunctions(result):
    summary = result["summary"]
    assert [(summary["all"]["families"][f]["passed"],summary["all"]["families"][f]["failed"]) for f in c.FAMILIES] == [(12,28),(31,9),(8,32)]
    assert [summary["registration"]["families"][f]["passed"] for f in c.FAMILIES] == [12,15,8]
    assert [summary["followup"]["families"][f]["passed"] for f in c.FAMILIES] == [0,16,0]
    assert summary["all"]["unknown_g_nonempty"] == 31
    for r in summary["registration_path_conjunctions"]:
        assert not r["families"][c.FAMILIES[2]]
        assert r["families"][c.FAMILIES[0]] == (r["plan"] == "delayed")


def test_alpha_zero_avoids_division(raw):
    r = deepcopy(c.inputs(raw)[2]); r["input"]["alpha"] = 0
    assert c.calculate(r)["derived"]["h_hat"] == 0


def test_negative_full_C_baseline_is_failed_screen(raw):
    r = deepcopy(c.inputs(raw)[2]); r["input"].update(C=0,F=0,X=0)
    value = c.calculate(r)
    assert value["derived"]["w_hat"] < 0
    assert not any(x["necessary_pass"] for x in value["screens"].values())
    assert not value["unknown_g"]["nonempty"]


@pytest.mark.parametrize("key,bad",[("alpha","6/5"),("f","-1/4"),("beta",0),("gamma",0),("dt",0),("D",-1),("Y",0.5),("K",True)])
def test_invalid_domains_rejected(raw,key,bad):
    r = deepcopy(c.inputs(raw)[2]); r["input"][key] = bad
    with pytest.raises(ValueError): c.calculate(r)


def test_primary_does_not_mutate_input(raw):
    r = c.inputs(raw)[2]; before=deepcopy(r)
    c.calculate(r)
    assert r == before


def test_duplicate_and_merge_yaml_keys_rejected():
    for text in ("a: 1\na: 2\n","base: &base {a: 1}\nb: {<<: *base}\n"):
        with pytest.raises(ValueError): yaml.load(text,Loader=c.UniqueLoader)


def test_hash_drift_rejected_before_yaml_parser(raw,monkeypatch):
    changed=raw.copy(); changed[c.CONFIGS[0]] += b"\n"
    def forbidden(*args,**kwargs): raise AssertionError("must reject before parser")
    monkeypatch.setattr(c.yaml,"load",forbidden)
    with pytest.raises(ValueError,match="before parse"): c.parse(changed)


def test_independent_reconstruction(result,raw):
    assert independent.verify(raw,result)["rows_checked"] == 40


@pytest.mark.parametrize("target",["input","derived","condition","summary"])
def test_independent_oracle_rejects_tamper(result,raw,target):
    changed=deepcopy(result)
    if target == "input": changed["rows"][3]["input"]["D"]="41"
    elif target == "derived": changed["rows"][3]["derived"]["w_hat"]="100"
    elif target == "condition": changed["rows"][3]["screens"][c.FAMILIES[2]]["necessary_pass"]=True
    else: changed["summary"]["registration"]["families"][c.FAMILIES[2]]["passed"]=16
    with pytest.raises(ValueError): independent.verify(raw,changed)


def test_runner_wrong_root_rejected_without_output(tmp_path):
    from experiments.staged_rts24_business_necessary_audit_v1 import audit
    with pytest.raises(ValueError,match="fixed root"): audit(tmp_path)
    assert not list(tmp_path.iterdir())


def test_runner_frozen_binding_map_matches_actual_bytes():
    from experiments.staged_rts24_business_necessary_audit_v1 import CONFIGS, CONTEXT, SOURCES, BOOTSTRAP
    assert all(sha256((ROOT/name).read_bytes()).hexdigest() == digest for name,digest in {**CONFIGS,**CONTEXT,**BOOTSTRAP}.items())
    assert len(SOURCES) == 5 and all((ROOT/name).is_file() for name in SOURCES)


def test_shadowed_module_origin_rejected(monkeypatch,tmp_path):
    from experiments import staged_rts24_business_necessary_audit_v1 as runner
    monkeypatch.setattr(runner.importlib,"import_module",lambda _:SimpleNamespace(__file__=str(tmp_path/"foreign.py")))
    with pytest.raises(ValueError,match="imported module differs"): runner.owned_module("anything",runner.SOURCES[0])


def test_bootstrap_source_drift_rejected_before_import(tmp_path,monkeypatch):
    from experiments import staged_rts24_business_necessary_audit_v1 as runner
    (tmp_path/"helper.py").write_bytes(b"changed")
    monkeypatch.setattr(runner,"ROOT",tmp_path)
    monkeypatch.setattr(runner,"BOOTSTRAP",{"helper.py":sha256(b"original").hexdigest()})
    with pytest.raises(ValueError,match="before import"):runner.bootstrap_sources()


@pytest.mark.parametrize("tamper",["omit_oracle","wrong_stage","performance_claim"])
def test_postcheck_rejects_missing_binding_and_authority_drift(tamper):
    checker=runpy.run_path(str(ROOT/"results/tables/staged_rts24_business_necessary_v1_non_authoritative/postcheck.py"))
    header=dict(authority="DRAFT_NONAUTHORITATIVE",formal_result=False,resource_admission=False,source_and_environment_bookends=True,
        review_stage="PRE_SEAL_AUDIT",scope="source_bound_public_business_one_hour_necessary_relaxations",
        overall_performance_review_complete=False,imported_project_module_paths_checked=True,fixed_repository_cwd=True,
        input_pins={name:{} for name in checker["PROJECT_NAMES"]})
    checker["check_scope"](header)
    if tamper == "omit_oracle":header["input_pins"].pop("src/staged_rts24_business_necessary_audit_v1.py")
    elif tamper == "wrong_stage":header["review_stage"]="SEALED_READY_FOR_INDEPENDENT_REVIEW"
    else:header["overall_performance_review_complete"]=True
    with pytest.raises(ValueError):checker["check_scope"](header)


@pytest.mark.parametrize("kind",["runner","postcheck"])
@pytest.mark.parametrize("module",["yaml.loader","experiments.staged_c_workflow_budget_v1"])
def test_preloaded_repo_or_parser_rejected_before_binding(kind,module):
    from experiments import staged_rts24_business_necessary_audit_v1 as runner
    checker=runpy.run_path(str(ROOT/"results/tables/staged_rts24_business_necessary_v1_non_authoritative/postcheck.py"))
    guard=runner.fresh_scope if kind == "runner" else checker["fresh_scope"]
    guard(None,{"sys":None,"pathlib":None})
    with pytest.raises(ValueError,match="fresh repo/parser"):guard(None,{module:None})
    with pytest.raises(ValueError,match="file-path"):guard("experiments",{})


def test_publish_success_and_existing_output_not_overwritten(tmp_path):
    from experiments import staged_rts24_business_necessary_audit_v1 as runner
    target=tmp_path/"audit"; data=b'{"development":true}\n'
    answer=runner.publish(data,target,time.perf_counter())
    assert answer["sha256"] == sha256(data).hexdigest() and (target/"audit.json").read_bytes() == data
    with pytest.raises(ValueError,match="create-only"): runner.publish(b"replace",target,time.perf_counter())
    assert (target/"audit.json").read_bytes() == data


def test_concurrent_mkdir_race_preserves_other_creator(tmp_path,monkeypatch):
    from experiments import staged_rts24_business_necessary_audit_v1 as runner
    target=tmp_path/"race"; original=Path.mkdir
    def raced(path,*args,**kwargs):
        if path == target:
            original(path);(path/"other").write_bytes(b"keep");raise FileExistsError("concurrent creation")
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,"mkdir",raced)
    with pytest.raises(FileExistsError): runner.publish(b"ours",target,time.perf_counter())
    assert (target/"other").read_bytes() == b"keep" and not (target/"audit.json").exists()


@pytest.mark.parametrize("failure",["mkdir","open","partial_write","short_write","readback_error","readback_diff","terminal_wall"])
def test_publish_failure_windows_retained_and_retry_refused(tmp_path,monkeypatch,failure):
    from experiments import staged_rts24_business_necessary_audit_v1 as runner
    target=tmp_path/failure; file=target/"audit.json"; data=b"development evidence"
    original_mkdir,original_open,original_read=Path.mkdir,Path.open,Path.read_bytes
    if failure == "mkdir":
        def broken_mkdir(path,*args,**kwargs):
            if path == target:raise OSError("injected mkdir")
            return original_mkdir(path,*args,**kwargs)
        monkeypatch.setattr(Path,"mkdir",broken_mkdir)
    elif failure in ("open","partial_write","short_write"):
        class BrokenStream:
            def __enter__(self):
                self.stream=original_open(file,"xb");return self
            def __exit__(self,*args):self.stream.close()
            def write(self,value):
                self.stream.write(value[:4])
                if failure == "partial_write":raise OSError("injected partial write")
                return 4
        def broken_open(path,*args,**kwargs):
            if path == file:
                if failure == "open":raise OSError("injected open")
                return BrokenStream()
            return original_open(path,*args,**kwargs)
        monkeypatch.setattr(Path,"open",broken_open)
    elif failure in ("readback_error","readback_diff"):
        def broken_read(path):
            if path == file:
                if failure == "readback_error":raise OSError("injected readback")
                return b"different"
            return original_read(path)
        monkeypatch.setattr(Path,"read_bytes",broken_read)
    else:
        ticks=iter([0.0,31.0]);monkeypatch.setattr(runner.time,"perf_counter",lambda:next(ticks))
    with pytest.raises((OSError,ValueError)):
        runner.publish(data,target,0 if failure == "terminal_wall" else time.perf_counter())
    monkeypatch.undo()
    if failure == "mkdir":assert not target.exists()
    else:
        assert target.exists()
        expected=None if failure == "open" else data[:4] if failure in ("partial_write","short_write") else data
        assert (file.read_bytes() if file.exists() else None) == expected
        with pytest.raises(ValueError,match="create-only"):runner.publish(b"retry",target,time.perf_counter())
        assert (file.read_bytes() if file.exists() else None) == expected


def test_new_import_closure_excludes_scientific_components():
    names=("src/staged_rts24_business_necessary_v1.py","src/staged_rts24_business_necessary_audit_v1.py",
        "experiments/staged_rts24_business_necessary_audit_v1.py")
    forbidden=("pyomo","pypower","highspy","staged_rts24_development_v1","staged_rts24_native")
    for name in names:
        imports=[]
        for node in ast.walk(ast.parse((ROOT/name).read_text(encoding="utf-8"))):
            if isinstance(node,ast.Import): imports.extend(n.name for n in node.names)
            if isinstance(node,ast.ImportFrom): imports.append(node.module or "")
        assert not any(any(s in item for s in forbidden) for item in imports)
    assert "staged_rts24_business_necessary_v1" not in (ROOT/names[1]).read_text(encoding="utf-8")
