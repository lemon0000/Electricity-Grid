"""Saved counterexamples and direct-source correspondence, without scientific replay."""
import ast
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import time
import runpy

import pytest

from src import staged_deliverability_evaluation_records_v1 as c
from experiments import staged_deliverability_evaluation_projection_v1 as runner

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def raw():return {name:(ROOT/name).read_bytes() for name in c.REPORTS}


@pytest.fixture(scope="module")
def projected(raw):return c.project(raw)


def item(projected,name):return next(v for v in projected["mechanism_regressions"] if v["case_id"] == name)


def resolve(raw,path,pointer):
    value=json.loads(raw[path])
    for part in pointer.split("/")[1:]:value=value[int(part)] if type(value) is list else value[part]
    return value


def test_classification_slots_do_not_execute_or_bind_parameters(projected):
    slots=projected["design"]["comparison_slots"]
    assert len(slots)==12 and {(r["business_progress"],r["grid_progress"],r["method"]) for r in slots} == {
        (b,g,m) for b in ("fast","slow") for g in ("on_time","delayed") for m in c.METHODS}
    assert all(r["status"]=="planned_schema_only" and r["public_main_executed"] is False
        and all(r[k] is None for k in ("run_id","result","numeric_value","business_input_sha256","D_mwc",
            "method_conditions_satisfied","full_replay_conditions_satisfied","mathematical_infeasibility_inferred","stop_reason")) for r in slots)


def test_regression_observations_cannot_fill_public_comparison_slots(projected):
    rows=projected["mechanism_regressions"]
    assert len(rows)==20 and len({r["case_id"] for r in rows})==20
    assert sum(r["case_id"].startswith("cost.") for r in rows)==12
    assert all(r["public_D_eligible"] is False and "business_progress" not in r and "comparison_slot" not in r for r in rows)
    assert projected["design"]["public_main_executed_cells"]==[]


def test_complete_and_zero_debt_do_not_erase_deadline_miss(projected):
    r=item(projected,"legacy.success.full_temporal")["result"]
    s=r["summary"]
    assert r["scientific_outcome"]=="complete" and s["coverage_complete"] is True and s["remaining_debt"]=="0"
    assert s["observed_primary_deadline_miss"]=="40"
    assert s["method_conditions_satisfied"] is False and s["full_replay_conditions_satisfied"] is False
    task=next(t for t in s["tasks"] if t["birth"]==1)
    assert (task["status"],task["recovered"],task["remaining"],task["deadline_miss"])==("deadline_missed","40","0","40")


@pytest.mark.parametrize("method",["instantaneous","fixed_headroom"])
def test_simplified_method_pass_does_not_become_full_replay_pass(projected,method):
    s=item(projected,"legacy.success."+method)["result"]["summary"]
    assert s["method_conditions_satisfied"] is True and s["full_replay_conditions_satisfied"] is False
    assert s["ledger_scope"]=="hypothetical_approximation"


def test_missing_future_retains_censor_and_null_conditions(projected):
    r=item(projected,"cost.v3_full_temporal")["fresh_result"]
    s=r["summary"]
    assert r["scientific_outcome"]=="missing_input" and s["coverage_complete"] is False
    assert s["primary_right_censored"] is True and s["remaining_debt"]=="40"
    assert s["method_conditions_satisfied"] is None and s["full_replay_conditions_satisfied"] is None
    task=next(t for t in s["tasks"] if t["birth"]==1)
    assert task["deadline_miss"] is None and task["status"]=="right_censored_before_deadline"


def test_unaccepted_current_is_not_a_missing_future_task(projected):
    r=item(projected,"cost.v3_reference_unresolved")["fresh_result"]
    assert r["summary"]["tasks"]==[] and r["summary"]["accepted_through"]==-1
    attempt=r["unaccepted_attempt"]
    assert attempt["observation"]["hour"]==0 and attempt["observation"]["workload"]=="100"
    assert attempt["adopted"] is False and attempt["mathematical_infeasibility_inferred"] is False
    assert attempt["after_state_sha"] is None


def test_unknown_writer_and_saved_reader_observation_stay_separate(projected):
    r=item(projected,"cost.v3_unknown")
    assert r["writer_binding"]["publication_outcome"]=="unknown" and r["writer_binding"]["known_entries"]==0
    assert r["writer_failure"]["publication_outcome"]=="unknown"
    assert r["fresh_result"]["publication_outcome"]=="committed" and r["fresh_result"]["final_entries"]==1
    assert r["fresh_result"]["state_certainty"]=="known" and r["writer_fresh_resolution"] is None
    assert r["fresh_result"]["failure"]["observed_scope"]=="writer_diagnostic_only_not_an_accepted_arrival"


def test_reader_refusal_does_not_gain_empty_summary_or_zero_metrics(projected):
    r=item(projected,"cost.v3_deletion")["fresh_result"]
    assert r["reader_refused_missing_closure"] is True and r["state_adopted"] is False
    assert all(k not in r for k in ("summary","remaining_debt","scientific_outcome","state_certainty"))


def test_prepublish_and_actual_unresolved_preserve_original_axes(projected):
    r=item(projected,"legacy.failure.prepublish")["result"]
    assert r["publication_outcome"]=="not_published" and r["scientific_outcome"]=="persistence_failure"
    assert r["unaccepted_status"]=="observed_pending_unaccepted"
    r=item(projected,"legacy.failure.actual_unresolved")["result"]
    assert r["scientific_outcome"]=="actual_unresolved" and r["summary"]["method_conditions_satisfied"] is None


def test_every_saved_view_matches_its_own_source_without_default_fields(projected,raw):
    for row in projected["mechanism_regressions"]:
        ref=row["source"];data=raw[ref["path"]]
        assert (ref["bytes"],ref["sha256"])==(len(data),sha256(data).hexdigest())
        source=resolve(raw,ref["path"],ref["pointer"])
        if row["case_id"].startswith("legacy."):
            assert row["result"]==source
        else:
            assert row["fresh_result"]=={k:v for k,v in source["fresh"].items() if k not in ("state","writer_inspection")}
            assert row["writer_binding"]==source["writer"]
            inspection=source["writer_inspection"]
            if inspection is None:
                assert row["writer_observation"] is None and "writer_failure" not in row
            else:
                assert row["writer_observation"]=={k:v for k,v in inspection.items() if k in c.INSPECTION_FIELDS}
                assert row["writer_failure"]==inspection["normalized_failure"]


def test_public_layers_only_contain_source_bound_necessary_screens(projected,raw):
    layers=projected["public_layers"]
    for k in ("actual_conditional_trajectory","complete_static_FX_network","complete_counterfactual_temporal_backing"):
        assert layers[k]==dict(status="not_evaluated",value=None,reason="not_in_source_projection")
    local=layers["one_hour_business_necessary"];source=json.loads(raw[c.BUSINESS])
    assert local["rows"]==source["rows"] and local["summary"]==source["summary"]
    assert local["pass_meaning"]=="not_ruled_out_by_this_necessary_screen" and projected["capacity_release"] is None
    assert projected["formal_result"] is False and projected["resource_admission"] is False


def test_holdout_and_sensitivities_do_not_acquire_selection_or_freeze(projected):
    d=projected["design"]
    assert d["holdout"]["freeze_status"]=="not_defined"
    assert all(d["holdout"][k] is None for k in ("selected_plan","selected_D","fixed_policy","freeze_input_manifest","holdout_paths"))
    assert d["sensitivities"]["numerical_grid"] is None and all(v is None for v in d["execution_budget"].values())
    assert d["event_fields"]["scenario_truth"] is None and d["event_fields"]["policy_observation"] is None


def test_projection_returns_isolated_views(raw):
    before=dict(raw);a=c.project(raw);b=c.project(raw)
    a["mechanism_regressions"][0]["result"]["summary"]["tasks"].clear()
    a["design"]["comparison_slots"][0]["D_mwc"]="1"
    assert b["mechanism_regressions"][0]["result"]["summary"]["tasks"] and raw==before
    assert b["design"]["comparison_slots"][0]["D_mwc"] is None


@pytest.fixture(scope="module")
def independent():
    return runpy.run_path(str(ROOT/"results/tables/staged_deliverability_evaluation_records_v1_non_authoritative/postcheck.py"))["check_projection"]


def test_independent_pointer_checker_accepts_all_preserved_fields(independent,projected,raw):
    assert independent(projected,raw)["all_selected_source_fields_exact"] is True


@pytest.mark.parametrize("mutation",["sha","bytes","cost_to_D","public_denominator","unknown_writer","fill_missing",
    "local_sufficient","null_to_pass","invent_holdout","invent_method_verdict","infeasibility_from_unresolved",
    "hourly_field","terminal_axis","access_rule","extra_holdout","denominator_meaning"])
def test_independent_checker_rejects_scope_and_field_tamper(independent,projected,raw,mutation):
    changed=deepcopy(projected)
    if mutation=="sha":changed["mechanism_regressions"][0]["source"]["sha256"]="0"*64
    elif mutation=="bytes":changed["source_reports"][c.LEGACY]["bytes"]+=1
    elif mutation=="cost_to_D":changed["design"]["comparison_slots"][0]["result"]=item(changed,"cost.v3_full_temporal")
    elif mutation=="public_denominator":changed["mechanism_regressions"][0]["public_D_eligible"]=True
    elif mutation=="unknown_writer":item(changed,"cost.v3_unknown")["writer_binding"]["publication_outcome"]="committed"
    elif mutation=="fill_missing":item(changed,"cost.v3_deletion")["fresh_result"]["summary"]={}
    elif mutation=="local_sufficient":changed["public_layers"]["one_hour_business_necessary"]["pass_meaning"]="satisfied"
    elif mutation=="null_to_pass":changed["public_layers"]["actual_conditional_trajectory"]["value"]=True
    elif mutation=="invent_holdout":changed["design"]["holdout"]["selected_D"]="40"
    elif mutation=="invent_method_verdict":changed["design"]["comparison_slots"][0]["method_conditions_satisfied"]=True
    elif mutation=="infeasibility_from_unresolved":changed["design"]["comparison_slots"][0]["mathematical_infeasibility_inferred"]=True
    elif mutation=="hourly_field":changed["design"]["hourly_field_groups"]["identity"].remove("information_history_id")
    elif mutation=="terminal_axis":changed["design"]["terminal_axes"].remove("full_replay_conditions_satisfied")
    elif mutation=="access_rule":changed["design"]["holdout"]["access_rule"]="reselect_after_reveal"
    elif mutation=="extra_holdout":changed["design"]["holdout"]["unregistered_selection"]="chosen"
    else:changed["regression_count_meaning"]="20 independent D cells"
    with pytest.raises(ValueError):independent(changed,raw)


@pytest.mark.parametrize("mutation",["missing_input","authority","missing_case","duplicate_id"])
def test_scope_corruption_rejected(raw,mutation):
    changed=dict(raw)
    if mutation=="missing_input":changed.pop(c.BUSINESS)
    else:
        name=c.LEGACY if mutation=="authority" else c.COST
        r=json.loads(changed[name])
        if mutation=="authority":r["authority"]="FORMAL"
        elif mutation=="missing_case":r["cases"].pop()
        else:r["cases"][1]["case"]["name"]=r["cases"][0]["case"]["name"]
        changed[name]=json.dumps(r).encode()
    with pytest.raises(ValueError):c.project(changed)


def test_result_without_summary_requires_explicit_nonadoption():
    with pytest.raises(ValueError):c.result_view(dict(error="missing"))
    assert "summary" not in c.result_view(dict(reader_refused_missing_closure=True,state_adopted=False))


def test_all_pinned_external_input_bytes_and_schema_sources_exist():
    assert all(sha256((ROOT/n).read_bytes()).hexdigest()==h for n,h in runner.PINS.items())
    assert all((ROOT/n).is_file() for n in runner.SOURCES)


def test_verified_namespace_executes_read_bytes_without_import_cache(tmp_path):
    path=tmp_path/"module.py";path.write_text("answer=99",encoding="utf-8")
    value=runner.verified_namespace(b"answer=7\ndef origin(): return answer\n","_isolated_test",path)
    assert value["origin"]()==7 and value["origin"].__code__.co_filename==str(path)


def test_helper_drift_rejected_before_execution(tmp_path,monkeypatch):
    (tmp_path/"helper.py").write_bytes(b"changed")
    monkeypatch.setattr(runner,"ROOT",tmp_path);monkeypatch.setattr(runner,"HELPER","helper.py")
    with pytest.raises(ValueError,match="before execution"):runner.bounded_helper()


def test_no_scientific_or_package_import_in_projection_core():
    tree=ast.parse((ROOT/runner.CORE).read_bytes())
    imports=[node.module for node in ast.walk(tree) if isinstance(node,ast.ImportFrom)]
    imports += [alias.name for node in ast.walk(tree) if isinstance(node,ast.Import) for alias in node.names]
    assert set(imports)<={"copy","hashlib","json"}


def test_create_only_projection_not_overwritten(tmp_path):
    out=tmp_path/"projection";runner.publish(b"original",out,time.perf_counter())
    with pytest.raises(ValueError,match="create-only"):runner.publish(b"replace",out,time.perf_counter())
    assert (out/"projection.json").read_bytes()==b"original"


@pytest.mark.parametrize("failure",["mkdir","race","open","partial_write","short_write","readback","different","terminal_wall"])
def test_publication_failures_preserve_artifacts(tmp_path,monkeypatch,failure):
    out=tmp_path/failure;file=out/"projection.json";data=b"development"
    original_mkdir,original_open,original_read=Path.mkdir,Path.open,Path.read_bytes
    if failure in ("mkdir","race"):
        def mkdir(path,*args,**kwargs):
            if path==out:
                if failure=="race":original_mkdir(path);(out/"other").write_bytes(b"keep")
                raise OSError("injected mkdir")
            return original_mkdir(path,*args,**kwargs)
        monkeypatch.setattr(Path,"mkdir",mkdir)
    elif failure in ("open","partial_write","short_write"):
        class Stream:
            def __enter__(self):self.file=original_open(file,"xb");return self
            def __exit__(self,*args):self.file.close()
            def write(self,payload):
                self.file.write(payload[:3])
                if failure=="partial_write":raise OSError("injected partial write")
                return 3
        def opened(path,*args,**kwargs):
            if path==file:
                if failure=="open":raise OSError("injected open")
                return Stream()
            return original_open(path,*args,**kwargs)
        monkeypatch.setattr(Path,"open",opened)
    elif failure in ("readback","different"):
        def read(path):
            if path==file:
                if failure=="readback":raise OSError("injected readback")
                return b"different"
            return original_read(path)
        monkeypatch.setattr(Path,"read_bytes",read)
    else:
        ticks=iter([0.0,21.0]);monkeypatch.setattr(runner.time,"perf_counter",lambda:next(ticks))
    with pytest.raises((ValueError,OSError)):runner.publish(data,out,0 if failure=="terminal_wall" else time.perf_counter())
    monkeypatch.undo()
    if failure=="mkdir":assert not out.exists()
    elif failure=="race":assert (out/"other").read_bytes()==b"keep" and not file.exists()
    else:
        expected=None if failure=="open" else data[:3] if failure in ("partial_write","short_write") else data
        assert (file.read_bytes() if file.exists() else None)==expected
        with pytest.raises(ValueError,match="create-only"):runner.publish(b"retry",out,time.perf_counter())
