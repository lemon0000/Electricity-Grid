"""Independent direct-JSON-pointer verification; no project or journal imports."""
from hashlib import sha256
import json
import os
from pathlib import Path
import stat
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
LEGACY="results/tables/staged_rts24_journal_v1_non_authoritative/attempt_01/report.json"
COST="results/tables/staged_rts24_append_cost_v1_non_authoritative/cost_probe_01/report.json"
BUSINESS="results/tables/staged_rts24_business_necessary_v1_non_authoritative/audit_01/audit.json"
METHODS=("instantaneous","fixed_headroom","full_temporal")
SOURCES={"src/staged_deliverability_evaluation_records_v1.py","experiments/staged_deliverability_evaluation_projection_v1.py",
    "tests/test_staged_deliverability_evaluation_records_v1.py","docs/plan/staged_deliverability_de_evidence_fields_contract_v1.md",
    "results/tables/staged_deliverability_evaluation_records_v1_non_authoritative/postcheck.py"}
KNOWN={LEGACY:"2540cde1d16f68971e3fa39191af543c166539c6bc4e6725459bfec3d786a7d4",
    COST:"7d974a2fe6d34009465be54601524104395e9a301299f9fd2a9dc327369b0c11",
    BUSINESS:"c55fbc77676e22ac8aff91f09d801fdc83e4ae0838b47bd215cadfe7637f708d",
    "docs/model_spec/staged_deliverability_minimum_spec_v1.md":"024841d9a13116651d353d1e1f81e1b4bc68de512208e2cb80137e8ca7b77045",
    "docs/plan/staged_deliverability_b3_c_next_steps_v1.md":"208cdf5549142b8219b02a5bc1836d9ca389ac87f3d7d01377e656cf75487f7d",
    "experiments/staged_c_workflow_budget_v1.py":"5bc19005ef1f0812a7d566dfc30bb6cef05f43ef21b9ed4f50262917034cfa82"}
CORE_KEYS={"authority","scope","evidence_kind","read_only_saved_report_projection","source_reports","design",
    "mechanism_regressions","regression_count_meaning","public_layers","capacity_release","native_authorized",
    "overall_performance_review_complete","resource_admission","formal_preregistration","formal_result"}


def require(ok,message):
    if not ok:raise ValueError(message)


def stamp(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def expected_design():
    """Independent v1 field contract, including every information/selection boundary."""
    slots=[]
    for business in ("fast","slow"):
        for grid in ("on_time","delayed"):
            for method in METHODS:
                slots.append(dict(business_progress=business,grid_progress=grid,method=method,status="planned_schema_only",
                    public_main_executed=False,run_id=None,result=None,numeric_value=None,method_conditions_satisfied=None,
                    full_replay_conditions_satisfied=None,mathematical_infeasibility_inferred=None,stop_reason=None,
                    business_input_sha256=None,shared_exogenous_input_sha256=None,equipment_plan_sha256=None,
                    grid_plan_sha256=None,policy_sha256=None,D_mwc=None))
    return {
        "status":"development_fields_only","main_network":"RTS24_public_direction",
        "clean_early_late_role":"development_clean_paths_not_business_fast_slow_or_holdout",
        "comparison_slots":slots,"slot_count_meaning":"12_classification_slots_not_numerical_plans_executions_or_resource_admission",
        "matched_plan_inputs":["task_arrivals_work_fractions_deadlines","external_clean_Y","service_accounting_rules","safety_standard","power_mapping"],
        "separate_plan_inputs":["equipment_capacity_and_idle_timing","grid_construction_and_rights_timing"],
        "method_requests":"same_generation_rule_with_own_continuous_physical_state_not_forced_equal_g",
        "sensitivities":{"status":"levels_and_axes_not_selected","numerical_grid":None,"source_obligations":[
            "clean_timing_at_matched_network_and_q_req_for_recovery_attribution","fix_R_fix_and_eta_before_target_results",
            "change_K_and_idle_together_if_equipment_changes"]},
        "hourly_field_groups":{
            "identity":["plan","path","stage","physical_hour","input_sha256","information_history_id"],
            "resources":["K","w","F","X","D","equipment_state","grid_state"],
            "actions":["P0","g_raw","h_raw","c_grid","c_cfe","q","r","z","P_actual"],
            "service":["Y","y","grid_call_shortfall","cfe_call_shortfall","actual_CFE_gap","network_evidence"],
            "carry":["task_cohorts","debt","deadline_outcomes","business_event_budgets","X_event_budgets"]},
        "terminal_axes":["scientific_outcome","publication_outcome","state_certainty","adoption_evidence","coverage_complete",
            "method_conditions_satisfied","full_replay_conditions_satisfied","mathematical_infeasibility_inferred","stop_reason",
            "observed_violations","right_censored_tasks","unaccepted_current","missing_future"],
        "four_layers":["actual_conditional_trajectory","complete_static_FX_network","one_hour_business_necessary","complete_counterfactual_temporal_backing"],
        "public_main_executed_cells":[],"event_fields":{"status":"not_defined","scenario_truth":None,"policy_observation":None,
            "reveal_hour":None,"observation_source_ref":None},
        "holdout":{"status":"not_registered_or_accessed","freeze_status":"not_defined","selection_rule":None,"selected_plan":None,
            "selected_D":None,"fixed_policy":None,"freeze_input_manifest":None,"split_provenance":None,"event_identity":None,
            "event_start_duration":None,"grid_reveal_rule":None,"task_and_equipment_input_identity":None,"clean_input_identity":None,
            "shared_service_rule_identity":None,"holdout_source":None,"holdout_paths":None,"seed_or_sampling_rule":None,
            "observation_and_deadline_coverage":None,"evaluation_methods":None,
            "access_rule":"selection_then_freeze_then_independent_reveal_and_causal_execution_no_reselection"},
        "execution_budget":{"D_numerical_points":None,"E_holdout_paths":None,"total_wall_seconds":None,"RAM_bytes":None,"storage_bytes":None},
        "formal_preregistration":False,"resource_admission":False,"formal_result":False}


def check_projection(value,raw):
    """Independent structural/source correspondence, without calling the producer."""
    require(set(value)==CORE_KEYS,"projection core schema")
    require(value["authority"]=="DRAFT_NONAUTHORITATIVE" and value["scope"]=="saved_report_projection_and_DE_development_fields"
        and value["evidence_kind"]=="saved_report_projection_not_new_numeric_audit"
        and value["read_only_saved_report_projection"] is True,"projection scope")
    require(all(value[k] is False for k in ("native_authorized","overall_performance_review_complete","resource_admission",
        "formal_preregistration","formal_result")) and value["capacity_release"] is None,"projection acquired authority")
    require(value["regression_count_meaning"]=="20_saved_views_with_reused_trajectories_not_independent_scenarios_or_D_cells","regression denominator meaning changed")
    require(set(raw)=={LEGACY,COST,BUSINESS} and value["source_reports"]=={n:stamp(r) for n,r in raw.items()},"source report byte identities")
    source={n:json.loads(r) for n,r in raw.items()}
    refs={"legacy.success."+m:(LEGACY,"/success_cases/"+m+"/result",source[LEGACY]["success_cases"][m]["result"]) for m in METHODS}
    refs.update({"legacy.failure."+k:(LEGACY,"/failure_probes/"+k,v) for k,v in source[LEGACY]["failure_probes"].items()})
    refs.update({"cost."+r["case"]["name"]:(COST,"/cases/"+str(i),r) for i,r in enumerate(source[COST]["cases"])})
    rows=value["mechanism_regressions"]
    require(len(refs)==len(rows)==20 and {r["case_id"] for r in rows}==set(refs),"saved view identities")
    for row in rows:
        name,pointer,original=refs[row["case_id"]]
        require(row["source"]==dict(path=name,pointer=pointer,**stamp(raw[name])),"view source reference")
        require(row["source_class"]=="analytic_three_bus_mechanism_regression" and row["public_D_eligible"] is False,"mechanism entered public scope")
        common={"case_id","source","source_class","public_D_eligible"}
        if name==LEGACY:
            require(set(row)==common|{"result"} and row["result"]==original,"legacy fields changed")
        else:
            require(row["case"]==original["case"] and row["writer_binding"]==original["writer"]
                and row["writer_fresh_resolution"] is None,"writer view or resolution changed")
            require(row["fresh_result"]=={k:v for k,v in original["fresh"].items() if k not in ("state","writer_inspection")},"fresh fields changed or defaulted")
            inspection=original["writer_inspection"]
            selected={"writer_ordinal","publication_outcome","accepted_rows","accepted_state_sha","terminal_present","removed_object_sha"}
            expected=None if inspection is None else {k:v for k,v in inspection.items() if k in selected}
            require(row["writer_observation"]==expected,"inspection null/fields changed")
            has_failure=isinstance(inspection,dict) and "normalized_failure" in inspection
            require(("writer_failure" in row)==has_failure,"failure field presence changed")
            if has_failure:require(row["writer_failure"]==inspection["normalized_failure"],"writer failure changed")
            require(set(row)==common|{"case","writer_binding","writer_observation","fresh_result","writer_fresh_resolution"}
                |({"writer_failure"} if has_failure else set()),"cost view schema")
    layers=value["public_layers"]
    require(set(layers)=={"actual_conditional_trajectory","complete_static_FX_network","one_hour_business_necessary",
        "complete_counterfactual_temporal_backing"},"four layer names")
    for k in set(layers)-{"one_hour_business_necessary"}:
        require(layers[k]==dict(status="not_evaluated",value=None,reason="not_in_source_projection"),"unevaluated layer acquired a result")
    local=layers["one_hour_business_necessary"];b=source[BUSINESS]
    expected=dict(source=dict(path=BUSINESS,pointer="",**stamp(raw[BUSINESS])),status="saved_necessary_screens_only",
        pass_meaning="not_ruled_out_by_this_necessary_screen",false_meaning="necessary_condition_failed",
        scope="hypothetical_full_C_relaxations_not_actual",rows=b["rows"],summary=b["summary"],premises=b["provenance"])
    require(local==expected,"public local screens/premises changed")
    require(value["design"]==expected_design(),"complete development field contract differs")
    return dict(saved_views_checked=20,public_necessary_rows_checked=40,classification_slots_checked=12,
        all_selected_source_fields_exact=True,null_false_absent_preserved=True,no_new_numeric_audit=True)


def verify():
    require(Path.cwd().resolve()==ROOT and sys.dont_write_bytecode and sys.flags.no_user_site==1,"fixed cwd -B -s required")
    started=time.perf_counter();pins={};operations=0;byte_count=0
    def read(path,expected=None):
        nonlocal operations,byte_count
        path=Path(path)
        require(path.resolve(strict=True).is_relative_to(ROOT) or path.resolve()==Path(sys.executable).resolve(),"postcheck input root")
        for parent in (path,*path.parents):
            info=parent.lstat();require(not stat.S_ISLNK(info.st_mode) and not getattr(info,"st_file_attributes",0)&0x400,"linked postcheck input")
        before=path.stat();operations+=1;byte_count+=before.st_size
        require(stat.S_ISREG(before.st_mode) and before.st_size<=2*1024**2 and operations<=50 and byte_count<=6*1024**2
            and time.perf_counter()-started<20,"postcheck cap")
        with path.open("rb") as stream:
            opened=os.fstat(stream.fileno());raw=stream.read(before.st_size+1);after=os.fstat(stream.fileno())
        require(os.path.samestat(before,opened) and os.path.samestat(opened,path.stat()) and before.st_size==after.st_size==len(raw),"postcheck input changed")
        pin=stamp(raw)
        if expected is not None:require(pin==expected if type(expected) is dict else pin["sha256"]==expected,"postcheck input SHA/bytes")
        require(path not in pins or pins[path]==pin,"postcheck bookend changed")
        pins[path]=pin;return raw
    raw_output=read(HERE/"projection_01/projection.json");value=json.loads(raw_output)
    require(set(value)==CORE_KEYS|{"input_pins","source_bookends","execution"} and value["source_bookends"] is True,"saved schema/bookends")
    require(set(value["input_pins"])==SOURCES|set(KNOWN),"exact source/input keyset")
    raw={name:read(ROOT/name,pin) for name,pin in value["input_pins"].items()}
    for name,digest in KNOWN.items():require(sha256(raw[name]).hexdigest()==digest,"historical input anchor")
    execution=value["execution"]
    require(Path(execution["executable"]).resolve()==Path(sys.executable).resolve() and execution["exact_verified_source_bytes"] is True
        and execution["no_user_site"]==1 and execution["dont_write_bytecode"] is True,"execution identity")
    require(set(execution["interpreter_pins"])=={Path(sys.executable).name},"interpreter keyset")
    for name,pin in execution["interpreter_pins"].items():read(Path(sys.executable).parent/name,pin)
    require(all(execution[k]==0 for k in ("scientific_compiler_calls","native_calls","journal_reopen_calls","model_builds"))
        and execution["explicit_reader_reads"]==2*(len(value["input_pins"])+1)==24
        and execution["explicit_reader_bytes"]==2*(sum(p["bytes"] for p in value["input_pins"].values())
            +sum(p["bytes"] for p in execution["interpreter_pins"].values()))<=4*1024**2
        and execution["bootstrap_reads"]==1 and execution["bootstrap_bytes"]==value["input_pins"]["experiments/staged_c_workflow_budget_v1.py"]["bytes"]
        and execution["prepublication_body_seconds"]<20,"saved execution budget")
    checked=check_projection({k:value[k] for k in CORE_KEYS},{n:raw[n] for n in (LEGACY,COST,BUSINESS)})
    for path,pin in list(pins.items()):read(path,pin)
    require(not (ROOT/"results/tables/staged_rts24_native_v1_non_authoritative/p1_01").exists(),"P1 appeared")
    return dict(authority="DRAFT_NONAUTHORITATIVE",scope="independent_saved_report_pointer_correspondence",
        projection=stamp(raw_output),**checked,source_and_interpreter_bookends=True,
        explicit_reads=operations,explicit_bytes=byte_count,body_wall_seconds=time.perf_counter()-started,
        scientific_compiler_calls=0,journal_reopen_calls=0,native_calls=0,official_verdict=None,seal=None,receipt=None,formal_result=False)


if __name__=="__main__":
    require(len(sys.argv)==1,"no postcheck options")
    target=HERE/"verification_01.json";require(not target.exists(),"create-only verification exists")
    result=verify()
    with target.open("x",encoding="utf-8",newline="\n") as stream:json.dump(result,stream,sort_keys=True,separators=(",",":"));stream.write("\n")
    print(json.dumps(result,sort_keys=True))
