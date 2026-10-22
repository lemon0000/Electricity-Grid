"""D/E development field plan and lossless views of selected saved report fields.

No journal replay, numerical audit, result selection, freeze or experiment execution.
"""
from copy import deepcopy
from hashlib import sha256
import json

METHODS = ("instantaneous", "fixed_headroom", "full_temporal")
LEGACY = "results/tables/staged_rts24_journal_v1_non_authoritative/attempt_01/report.json"
COST = "results/tables/staged_rts24_append_cost_v1_non_authoritative/cost_probe_01/report.json"
BUSINESS = "results/tables/staged_rts24_business_necessary_v1_non_authoritative/audit_01/audit.json"
REPORTS = (LEGACY,COST,BUSINESS)
INSPECTION_FIELDS = ("writer_ordinal","publication_outcome","accepted_rows","accepted_state_sha",
    "terminal_present","removed_object_sha")


def require(condition,message):
    if not condition:raise ValueError(message)


def development_design():
    """Classification slots are unbound, not a numerical plan or task budget."""
    return dict(status="development_fields_only",main_network="RTS24_public_direction",
        clean_early_late_role="development_clean_paths_not_business_fast_slow_or_holdout",
        comparison_slots=[dict(business_progress=b,grid_progress=g,method=m,status="planned_schema_only",
            public_main_executed=False,run_id=None,result=None,numeric_value=None,
            method_conditions_satisfied=None,full_replay_conditions_satisfied=None,
            mathematical_infeasibility_inferred=None,stop_reason=None,
            business_input_sha256=None,shared_exogenous_input_sha256=None,equipment_plan_sha256=None,
            grid_plan_sha256=None,policy_sha256=None,D_mwc=None)
            for b in ("fast","slow") for g in ("on_time","delayed") for m in METHODS],
        slot_count_meaning="12_classification_slots_not_numerical_plans_executions_or_resource_admission",
        matched_plan_inputs=["task_arrivals_work_fractions_deadlines","external_clean_Y","service_accounting_rules",
            "safety_standard","power_mapping"],
        separate_plan_inputs=["equipment_capacity_and_idle_timing","grid_construction_and_rights_timing"],
        method_requests="same_generation_rule_with_own_continuous_physical_state_not_forced_equal_g",
        sensitivities=dict(status="levels_and_axes_not_selected",numerical_grid=None,
            source_obligations=["clean_timing_at_matched_network_and_q_req_for_recovery_attribution",
                "fix_R_fix_and_eta_before_target_results","change_K_and_idle_together_if_equipment_changes"]),
        hourly_field_groups=dict(identity=["plan","path","stage","physical_hour","input_sha256","information_history_id"],
            resources=["K","w","F","X","D","equipment_state","grid_state"],
            actions=["P0","g_raw","h_raw","c_grid","c_cfe","q","r","z","P_actual"],
            service=["Y","y","grid_call_shortfall","cfe_call_shortfall","actual_CFE_gap","network_evidence"],
            carry=["task_cohorts","debt","deadline_outcomes","business_event_budgets","X_event_budgets"]),
        terminal_axes=["scientific_outcome","publication_outcome","state_certainty","adoption_evidence",
            "coverage_complete","method_conditions_satisfied","full_replay_conditions_satisfied",
            "mathematical_infeasibility_inferred","stop_reason","observed_violations","right_censored_tasks","unaccepted_current","missing_future"],
        four_layers=["actual_conditional_trajectory","complete_static_FX_network",
            "one_hour_business_necessary","complete_counterfactual_temporal_backing"],
        public_main_executed_cells=[],
        event_fields=dict(status="not_defined",scenario_truth=None,policy_observation=None,reveal_hour=None,observation_source_ref=None),
        holdout=dict(status="not_registered_or_accessed",freeze_status="not_defined",selection_rule=None,selected_plan=None,selected_D=None,
            fixed_policy=None,freeze_input_manifest=None,split_provenance=None,event_identity=None,event_start_duration=None,
            grid_reveal_rule=None,task_and_equipment_input_identity=None,clean_input_identity=None,
            shared_service_rule_identity=None,holdout_source=None,holdout_paths=None,seed_or_sampling_rule=None,
            observation_and_deadline_coverage=None,evaluation_methods=None,
            access_rule="selection_then_freeze_then_independent_reveal_and_causal_execution_no_reselection"),
        execution_budget=dict(D_numerical_points=None,E_holdout_paths=None,total_wall_seconds=None,RAM_bytes=None,storage_bytes=None),
        formal_preregistration=False,resource_admission=False,formal_result=False)


def result_view(value):
    """Preserve source nulls/false/missed histories; omit only large state/inspection."""
    require(type(value) is dict,"saved result must be an object")
    if "summary" in value:
        require(value["summary"]["method"] in METHODS,"unknown saved method")
        require(all(k in value for k in ("scientific_outcome","publication_outcome","state_certainty")),"missing saved axes")
    else:
        require(value.get("reader_refused_missing_closure") is True and value.get("state_adopted") is False,
            "result without summary must retain explicit reader refusal")
    return deepcopy({k:v for k,v in value.items() if k not in ("state","writer_inspection")})


def project(raw_reports):
    require(set(raw_reports) == set(REPORTS),"exactly three pinned report inputs")
    require(all(type(raw) is bytes and len(raw)<=1024**2 for raw in raw_reports.values()),"report byte domain/bound")
    pins={name:dict(bytes=len(raw),sha256=sha256(raw).hexdigest()) for name,raw in raw_reports.items()}
    reports={name:json.loads(raw) for name,raw in raw_reports.items()}
    def source(name,pointer):return dict(path=name,pointer=pointer,**pins[name])
    legacy,cost,business = [reports[n] for n in REPORTS]
    require(all(r["authority"] == "DRAFT_NONAUTHORITATIVE" for r in (legacy,cost,business)),"authority drift")
    require(set(legacy["success_cases"]) == set(METHODS) and set(legacy["failure_probes"]) ==
        {"actual_unresolved","missing_input","postpublish","prepublish","reference_unresolved"},"legacy report scope")
    expected_cases={(v,k,m) for v in ("v2","v3") for k,m in
        [("success",m) for m in METHODS]+[(k,"full_temporal") for k in ("unknown","deletion","reference_unresolved")]}
    require(len(cost["cases"]) == 12 and {(r["case"]["version"],r["case"]["kind"],r["case"]["method"])
        for r in cost["cases"]} == expected_cases,"saved cost report scope")
    require(business["scope"] == "source_bound_public_business_one_hour_necessary_relaxations"
        and business["formal_result"] is False and business["resource_admission"] is False
        and len(business["rows"]) == 40,"public arithmetic scope")
    regression=[]
    for method in METHODS:
        regression.append(dict(case_id="legacy.success."+method,source=source(LEGACY,"/success_cases/"+method+"/result"),
            source_class="analytic_three_bus_mechanism_regression",public_D_eligible=False,
            result=result_view(legacy["success_cases"][method]["result"])))
    for name in sorted(legacy["failure_probes"]):
        regression.append(dict(case_id="legacy.failure."+name,source=source(LEGACY,"/failure_probes/"+name),
            source_class="analytic_three_bus_mechanism_regression",public_D_eligible=False,result=result_view(legacy["failure_probes"][name])))
    for index,item in enumerate(cost["cases"]):
        inspection=item["writer_inspection"]
        require(inspection is None or type(inspection) is dict,"writer inspection must preserve object or null")
        regression.append(dict(case_id="cost."+item["case"]["name"],
            source=source(COST,"/cases/"+str(index)),source_class="analytic_three_bus_mechanism_regression",public_D_eligible=False,
            case=deepcopy(item["case"]),writer_binding=deepcopy(item["writer"]),
            writer_observation=None if inspection is None else {k:deepcopy(inspection[k]) for k in INSPECTION_FIELDS if k in inspection},
            fresh_result=result_view(item["fresh"]),writer_fresh_resolution=None))
        if type(inspection) is dict and "normalized_failure" in inspection:
            regression[-1]["writer_failure"]=deepcopy(inspection["normalized_failure"])
    require(len({r["case_id"] for r in regression}) == 20,"duplicate regression IDs")
    def not_evaluated():return dict(status="not_evaluated",value=None,reason="not_in_source_projection")
    return dict(authority="DRAFT_NONAUTHORITATIVE",scope="saved_report_projection_and_DE_development_fields",
        evidence_kind="saved_report_projection_not_new_numeric_audit",read_only_saved_report_projection=True,
        source_reports=pins,design=development_design(),
        mechanism_regressions=regression,
        regression_count_meaning="20_saved_views_with_reused_trajectories_not_independent_scenarios_or_D_cells",
        public_layers=dict(actual_conditional_trajectory=not_evaluated(),complete_static_FX_network=not_evaluated(),
            one_hour_business_necessary=dict(source=source(BUSINESS,""),status="saved_necessary_screens_only",
                pass_meaning="not_ruled_out_by_this_necessary_screen",false_meaning="necessary_condition_failed",
                scope="hypothetical_full_C_relaxations_not_actual",rows=deepcopy(business["rows"]),
                summary=deepcopy(business["summary"]),premises=deepcopy(business["provenance"])),
            complete_counterfactual_temporal_backing=not_evaluated()),
        capacity_release=None,native_authorized=False,overall_performance_review_complete=False,resource_admission=False,
        formal_preregistration=False,formal_result=False)
