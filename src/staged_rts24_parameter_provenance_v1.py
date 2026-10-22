"""Static provenance of frozen inputs. Does not import or execute research models."""
import argparse
import ast
from collections import Counter
from fractions import Fraction
from hashlib import sha256
from importlib.metadata import distribution, version
import json
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs/literature/staged_rts24_parameter_provenance_v1.json"
CONFIGS = {
    "public": ("configs/staged_deliverability_rts24_v1.DRAFT.yaml", "6897979b6394a20b406031e9bcc8fadf5751c7815c996dc177956535679b7791", 40),
    "business": ("configs/staged_deliverability_small_case_v1.DRAFT.yaml", "5b334398b2894da70c81baaad74da2dfcecde490ab539bacf3fdb0c988eb4ac5", 60),
    "rights": ("configs/staged_deliverability_network_v1.DRAFT.yaml", "c6bb0cc30a330fed07a9d0b7f22dea7ce5096f20f1f58a8dc79dddc58059686b", 32),
}
REFERENCES = {
    "src/staged_rts24_development_v1.py": "d0c61bda61bfe4d275d2230533f2ecd74fa4fbf480f358c819f8cb86e1ba7add",
    "src/grid/rts24.py": "8c876b13fdc318ca98ab22309bae1aff0b8e56a12894f9aae98c84ed951eb8b5",
    "docs/model_spec/staged_deliverability_minimum_spec_v1.md": "024841d9a13116651d353d1e1f81e1b4bc68de512208e2cb80137e8ca7b77045",
    "src/staged_deliverability_development_v1.py": "91bbc6aaaac458c8fcb23c11d830a98af99e1d50d42b3c0489246ec1922109e0",
    "src/rq2_joint_deliverability_boundary_v1/debt_cohorts.py": "d10497c1e6ab5ff573dec8d938b5407a7e28277551b37a1e0d7f79b4241adaab",
    "src/staged_rts24_causal_v1.py": "12950e9f0ac321e7297b66aba42efb9e486e477869d767e40cd841665a7b0ead",
    "src/staged_rts24_causal_v2.py": "7d22dba435d3e89bd3062a1bd687a6584bb7ddc29c88b6bd723fa357932d1859",
    "src/staged_rts24_causal_audit_v2.py": "3344d346efc62b1bef8cbeab470eb3696a9818c4f452465394ab33806baf28d3",
    "src/staged_rts24_reference_queries_v1.py": "be02760eec2a0d010ec1a2187322edcca14af4774e7e6d0cbf4859a9375adb1a",
    "src/staged_rts24_audit_v1.py": "ac29e1fe38831b7f37fbd56ab7ceafc8d87a619c5c1ba929004f907e21aab911",
    "src/staged_rts24_child_optimality_v1.py": "27071de638bceee8f6e0631ab44d8a9c3cebdba0c169ccd702c9c3392fcde543",
    "src/staged_rts24_business_necessary_v1.py": "d03377034ab0063cbe39cf744461e99af6336ebf323748bd98cd4c93e07bded6",
    "src/staged_rts24_business_necessary_audit_v1.py": "8d8d6d1bb1c3ab94991168f3a02e714f1baa4743fea5cd4c9ef9b819fe197b8c",
}
CASE_SHA = "f61d986bf6f611e40d0a55b013616a40d059fd9700408eb81fcf41e3bbd0e3a6"
SCALE_REF = {"config": "public", "pointer": "/business/dimensional_scale"}
BASE_LIMIT = "mechanism_value_not_empirical_calibration"
SCALED_PARAMETERS = {
    "capacity": "MW_c", "auxiliary_mw": "MW", "fixed_headroom": "MW_c",
    "max_recovery": "MW_c", "max_debt": "MWh_c", "max_call_energy": "MWh_c",
    "call_ramp": "MW_c_per_hour",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def stamp(raw):
    return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


class UniqueLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node):
    result, names = {}, set()
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=True)
        require(type(key) in (str, int), "mapping keys must be strings or integers")
        name = str(key)
        require(name not in names, "duplicate or normalized-colliding YAML key")
        names.add(name)
        result[key] = loader.construct_object(value_node, deep=True)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def parse_yaml(raw):
    require(type(raw) is bytes and len(raw) <= 16384, "YAML byte bound")
    require(not any(isinstance(t, (yaml.tokens.AliasToken, yaml.tokens.AnchorToken)) for t in yaml.scan(raw)),
            "YAML anchors and aliases are outside this static input contract")
    value = yaml.load(raw, Loader=UniqueLoader)
    require(type(value) is dict, "configuration must be a mapping")
    return value


def leaves(value, pointer="", key_kind="root"):
    if type(value) is dict:
        for key, child in value.items():
            token = str(key).replace("~", "~0").replace("/", "~1")
            yield from leaves(child, pointer + "/" + token, type(key).__name__)
    elif type(value) is list:
        for index, child in enumerate(value):
            yield from leaves(child, pointer + "/" + str(index), "index")
    else:
        require(type(value) in (str, int), "only exact string/integer scalar leaves are supported")
        yield pointer, value, key_kind


def rules():
    """Reviewed use map; origin and runtime adoption are separate dimensions."""
    result = {}

    def put(config, pointers, unit, origin, use, operation="none", limits=(), auxiliary=()):
        for pointer in pointers.split():
            key = config, pointer
            require(key not in result, "duplicate policy pointer")
            result[key] = dict(unit=unit, origin_class=origin, public_runtime_use=use,
                               operation=operation, claim_limits=list(limits), auxiliary_uses=list(auxiliary))

    for config in CONFIGS:
        put(config, "/status /source_class", "declaration", "scope_metadata",
            "scope_guard" if config == "public" else "bound_only",
            limits=("scope_label_not_scientific_or_empirical_value",))
        result[config, "/status"]["auxiliary_uses"] = ["saved_business_necessary_audit_development_status_guard"]
    put("public", "/case/package /case/version /case/name /case/sha256 /business/fixture /business/sha256 /rights/fixture /rights/sha256",
        "source_reference", "binding_metadata", "source_binding",
        limits=("source_pin_not_site_observation_or_numeric_calibration",))
    put("public", "/business/dimensional_scale", "ratio", "mechanism_scaling_choice", "transform_control",
        "identity", (BASE_LIMIT, "exact_scaling_does_not_upgrade_source_class"))
    put("public", "/network/poi_bus", "bus_id", "synthetic_site_or_project_selection", "adopted_value",
        "identity", (BASE_LIMIT, "not_public_case_native_data_center_location"))
    put("public", "/network/background_load_multiplier", "ratio", "mechanism_assumption", "adopted_value",
        "identity", (BASE_LIMIT, "only_public_background_PD_plus_GS_is_multiplied_not_generation_or_ratings"))
    put("public", "/network/sustained_rating /network/dispatch_policy", "enum", "method_or_policy_assumption",
        "fixed_implementation_guard", limits=("static_dc_policy_not_dynamic_response_certification",))
    put("public", "/network/economic_regularization_quadratic", "objective_unit_per_MW_squared",
        "method_or_policy_assumption", "guard_matches_fixed_query_constant",
        limits=("declared_regularized_objective_not_strict_lexicographic_original_cost",))
    put("public", "/network/redispatch_fraction_of_pmax", "ratio", "method_or_policy_assumption",
        "adopted_value", "identity", ("same_hour_corrective_not_interhour_ramp_or_unit_commitment",))
    put("public", "/network/response_model", "enum", "method_or_policy_assumption", "effective_response_label",
        "identity", ("static_same_hour_not_dynamic_or_service_certification",))
    put("public", "/project/branches/0 /project/branches/1", "branch_index", "synthetic_site_or_project_selection",
        "adopted_value", "identity", (BASE_LIMIT, "not_observed_candidate_project"))
    put("public", "/project/rate_a_increase_mw", "MW_DC_limit_increment", "synthetic_site_or_project_selection",
        "adopted_value", "identity", (BASE_LIMIT, "direct_increment_not_multiplied_by_200"))
    put("public", "/project/rate_c_increase_mw", "MW_labelled_attribute_increment", "synthetic_site_or_project_selection",
        "retained_network_attribute_not_active_limit", "identity",
        (BASE_LIMIT, "rate_c_changes_network_identity_but_active_dc_constraint_uses_rate_a"))
    put("public", "/project/start_hour /project/lead_hours /project/delays/on_time /project/delays/delayed",
        "hour", "synthetic_site_or_project_selection", "adopted_value", "identity",
        (BASE_LIMIT, "compressed_stage_time_not_real_construction_or_delay_probability"))
    put("public", "/contingencies/branches /contingencies/generators", "selection_rule", "topology_selection_rule",
        "adopted_selection_rule", "identity", ("declared_case_subset_not_full_n_minus_1_or_event_probability",))
    put("public", "/contingencies/expected_excluded_branches/0", "branch_index", "derived_topology_identity",
        "derived_identity_guard", limits=("static_provenance_does_not_recompute_topology_or_solve",))
    put("public", "/contingencies/expected_excluded_generators/0", "generator_index", "derived_topology_identity",
        "derived_identity_guard", limits=("static_provenance_does_not_recompute_topology_or_solve",))
    put("public", "/actual_event/rule", "selection_rule", "synthetic_event", "fixed_implementation_guard",
        limits=("synthetic_actual_path_not_observed_outage_or_frequency",
                "guarded_label_runtime_uses_selected_zero_without_interpreting_string"))
    put("public", "/actual_event/hour /actual_event/duration_hours", "hour", "synthetic_event", "adopted_value",
        "identity", ("synthetic_actual_path_not_observed_outage_or_frequency",))
    put("public", "/time/first_hour /time/registration_end /time/observation_end", "hour", "analysis_design",
        "adopted_value", "identity", ("finite_observation_does_not_clip_task_deadlines",))
    put("public", "/time/deadline_rule", "enum", "method_or_policy_assumption", "fixed_implementation_guard",
        limits=("arrival_plus_uncalibrated_source_lag_without_observation_clipping",))
    put("public", "/methods/0 /methods/1 /methods/2", "method_label", "method_or_policy_assumption",
        "method_set_guard", limits=("method_declaration_not_executed_result",))
    put("business", "/first_hour /last_hour", "hour", "analysis_design", "cross_source_guard",
        limits=("runtime_window_comes_from_public_config",))
    put("business", "/deadline_lag", "hour", "mechanism_assumption", "adopted_value", "identity",
        (BASE_LIMIT, "two_hour_deadline_not_empirical_task_sla"))
    put("business", "/flexible_fraction", "ratio", "mechanism_assumption", "adopted_value", "identity",
        (BASE_LIMIT, "implementation_overrides_fraction_to_zero_before_hour_zero"))
    put("business", "/prehistory_clean", "MWh", "mechanism_assumption", "adopted_scaled_value", "multiply_scale",
        (BASE_LIMIT, "prehistory_only_not_clean_path_indexing"))
    for name, unit in SCALED_PARAMETERS.items():
        put("business", "/parameters/" + name, unit, "mechanism_assumption", "adopted_scaled_value",
            "multiply_scale", (BASE_LIMIT, "exact_scaling_does_not_upgrade_source_class"))
    for name, unit in dict(alpha="ratio", eta="work_completion_ratio", beta="MW_per_MW_c",
                           facility_factor="ratio", max_events="event_count", max_duration="hour",
                           minimum_rest="hour").items():
        put("business", "/parameters/" + name, unit, "mechanism_assumption", "adopted_value",
            "identity", (BASE_LIMIT, "not_equipment_measurement_or_service_contract"))
    for index in range(2):
        prefix = f"/equipment/{index}/"
        put("business", prefix+"id", "module_label", "mechanism_assumption", "adopted_value",
            "identity", (BASE_LIMIT,))
        for name, unit in dict(capacity="MW_c", idle_mw="MW").items():
            put("business", prefix+name, unit, "mechanism_assumption", "adopted_scaled_value", "multiply_scale",
                (BASE_LIMIT, "not_nameplate_or_measured_power"))
        put("business", " ".join(prefix+n for n in ("start", "lead", "delay")), "hour",
            "mechanism_assumption", "adopted_value", "identity",
            (BASE_LIMIT, "compressed_stage_time_not_observed_equipment_schedule"))
    put("business", "/workload/before /workload/after", "MW_c", "mechanism_assumption",
        "adopted_scaled_value", "multiply_scale",
        (BASE_LIMIT, "one_development_workload_shape_not_fast_slow_business_paths"))
    put("business", "/workload/change_hour", "hour", "mechanism_assumption", "adopted_value",
        "identity", (BASE_LIMIT, "compressed_business_change_not_observed_ramp"))
    put("business", "/grid/start /grid/lead /grid/delays/on_time /grid/delays/delayed", "hour",
        "mechanism_assumption", "cross_source_guard",
        limits=("commissioning_uses_public_project_fields_not_legacy_scalar_network",))
    put("business", "/grid/before /grid/after", "MW", "legacy_mechanism_assumption", "not_adopted",
        limits=("legacy_scalar_supply_not_public_network_capacity",),
        auxiliary=("saved_business_necessary_audit_checks_scaled_value_equals_firm_plus_conditional",))
    put("business", "/grid/temporary_hour", "hour", "legacy_mechanism_assumption", "not_adopted",
        limits=("legacy_scalar_event_not_public_actual_outage",))
    put("business", "/grid/temporary_limit", "MW", "legacy_mechanism_assumption", "not_adopted",
        limits=("legacy_scalar_supply_not_public_network_capacity",))
    for clean in ("early", "late"):
        put("business", " ".join(f"/clean_paths/{clean}/{i}" for i in range(8)), "MWh",
            "mechanism_assumption", "adopted_scaled_value", "multiply_scale",
            (BASE_LIMIT, "development_clean_timing_not_business_pace_holdout_or_empirical_cfe"))
    put("rights", "/business_fixture", "source_path", "binding_metadata", "bound_only",
        limits=("path_not_dereferenced_by_public_loader",),
        auxiliary=("saved_business_necessary_audit_business_path_equality_guard",))
    put("rights", "/business_sha256", "source_digest", "binding_metadata", "cross_source_guard",
        limits=("matches_public_business_source_digest_not_numeric_evidence",))
    old_units = dict(base_mva="MVA", source_bus="bus_id", poi_bus="bus_id", background_mw="MW",
                     generator_max_mw="MW", hourly_generator_ramp_mw="MW_per_hour", reactance_pu="per_unit",
                     angle_limit_rad="radian", line_rating_before_mw="MW", line_rating_after_mw="MW",
                     project_start="hour", project_lead="hour", **{"delays/on_time":"hour", "delays/delayed":"hour",
                     "actual_outages/1":"branch_index", "selected_outages/0":"branch_index", "selected_outages/1":"branch_index"})
    for name, unit in old_units.items():
        put("rights", "/network/"+name, unit, "legacy_mechanism_assumption", "not_adopted",
            limits=("legacy_two_bus_field_not_used_in_public_successor",))
        if name in ("project_start", "project_lead", "delays/on_time", "delays/delayed"):
            result["rights", "/network/"+name]["auxiliary_uses"] = [
                "saved_business_necessary_audit_three_source_project_timing_guard"]
    put("rights", "/rights/firm_before_mw /rights/conditional_before_mw /rights/firm_after_mw /rights/conditional_after_mw",
        "MW", "mechanism_assumption", "adopted_scaled_value", "multiply_scale",
        (BASE_LIMIT, "access_rights_not_public_network_derived_or_project_contract"))
    put("rights", "/x_envelope/response_model", "enum", "legacy_mechanism_assumption", "source_label_only",
        limits=("retained_as_source_response_model_overridden_by_public_effective_response_model",))
    for name, unit in dict(max_call_mw="MW", max_ramp_mw_per_hour="MW_per_hour", max_energy_mwh="MWh").items():
        put("rights", "/x_envelope/"+name, unit, "mechanism_assumption", "adopted_scaled_value",
            "multiply_scale", (BASE_LIMIT, "scaled_envelope_not_dynamic_response_or_service_certification"))
    for name, unit in dict(max_duration_hours="hour", max_events="event_count", minimum_rest_hours="hour").items():
        put("rights", "/x_envelope/"+name, unit, "mechanism_assumption", "adopted_value",
            "identity", (BASE_LIMIT, "scaled_envelope_not_dynamic_response_or_service_certification"))
    return result


def public_components(raw):
    """Read literal arrays from the pinned case AST without executing it or numpy."""
    require(sha256(raw).hexdigest() == CASE_SHA, "public source bytes drift")
    found = {}
    for node in ast.walk(ast.parse(raw)):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not (isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name)
                and target.value.id == "ppc" and isinstance(target.slice, ast.Constant)):
            continue
        name = target.slice.value
        if name not in ("baseMVA", "bus", "gen", "branch", "gencost"):
            continue
        require(name not in found, "duplicate public literal component")
        value = node.value
        if name != "baseMVA":
            require(isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "array"
                    and len(value.args) == 1 and not value.keywords, "nonliteral public array")
            value = value.args[0]
        found[name] = ast.literal_eval(value)
    shapes = {"baseMVA": [], "bus": [24, 13], "gen": [33, 21], "branch": [38, 13], "gencost": [33, 7]}
    require(set(found) == set(shapes), "public literal components incomplete")
    rows = []
    for name in shapes:
        value = found[name]
        if name == "baseMVA":
            require(value == 100.0, "base MVA differs")
        else:
            require(len(value) == shapes[name][0] and all(len(r) == shapes[name][1] for r in value),
                    "public array shape differs")
        rows.append(dict(component=name, shape=shapes[name], literal_sha256=sha256(canonical(value).encode()).hexdigest(),
                         origin_class="public_static_benchmark_data",
                         source_ref="PYPOWER/pypower/case24_ieee_rts.py",
                         claim_limit="pinned_static_benchmark_not_site_observation_or_ac_dynamic_security"))
        if name == "baseMVA":
            rows[-1]["literal_value"] = value
    return rows


def consumer_coverage(reference_bytes):
    """Lexical witnesses plus exact source pins; not execution or a data-flow proof."""
    trees = {k:ast.parse(v) for k,v in reference_bytes.items() if k.endswith(".py")}
    definitions = trees["src/staged_deliverability_development_v1.py"]
    parameters = next(n for n in definitions.body if isinstance(n, ast.ClassDef) and n.name == "Parameters")
    fields = {n.target.id for n in parameters.body if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)}
    expected = set(SCALED_PARAMETERS) | {"alpha", "eta", "beta", "facility_factor", "max_events", "max_duration", "minimum_rest"}
    require(fields == expected, "Parameters schema coverage differs")
    methods = [ast.literal_eval(n.value) for n in definitions.body if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == "METHODS" for t in n.targets)]
    require(methods == [("instantaneous", "fixed_headroom", "full_temporal")], "METHODS declaration differs")
    def attributes(tree, function_names):
        selected = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in function_names]
        require(len(selected) == len(function_names), "consumer function missing")
        return {n.attr for root in selected for n in ast.walk(root) if isinstance(n, ast.Attribute)
                and ((isinstance(n.value, ast.Name) and n.value.id in ("p", "parameters", "params"))
                     or (isinstance(n.value, ast.Attribute) and n.value.attr == "parameters"))} & fields
    policy_refs = {
        "src/staged_deliverability_development_v1.py": {"power_mapping", "initialize"},
        "src/staged_rts24_causal_v1.py": {"propose_hour", "initialize_execution"},
        "src/staged_rts24_reference_queries_v1.py": {"reference_requests"},
    }
    policy = {name:sorted(attributes(trees[name], functions)) for name, functions in policy_refs.items()}
    independent = attributes(trees["src/staged_rts24_causal_audit_v2.py"], {"audit_execution"})
    require(set().union(*(set(v) for v in policy.values())) == fields, "policy parameter usage coverage differs")
    require(independent == fields, "independent audit parameter usage coverage differs")
    x_keys = {"max_call_mw", "max_ramp_mw_per_hour", "max_energy_mwh", "max_duration_hours", "max_events", "minimum_rest_hours"}
    x_reads = {}
    for name in ("src/staged_rts24_causal_v2.py", "src/staged_rts24_causal_audit_v2.py"):
        found = {n.slice.value for n in ast.walk(trees[name]) if isinstance(n, ast.Subscript)
                 and isinstance(n.value, ast.Name) and n.value.id == "x" and isinstance(n.slice, ast.Constant)}
        require(found == x_keys, "X envelope consumer coverage differs")
        x_reads[name] = sorted(found)
    links = [
        ("src/staged_rts24_development_v1.py", "src.staged_deliverability_development_v1", {"Parameters", "METHODS"}),
        ("src/staged_rts24_causal_v2.py", "src.staged_rts24_causal_v1", {"propose_hour", "initialize_execution", "_root", "_child"}),
        ("src/staged_rts24_causal_v2.py", "src.staged_rts24_reference_queries_v1", {"reference_requests"}),
        ("src/staged_rts24_causal_v2.py", "src.staged_rts24_causal_audit_v2", {"audit_execution"}),
        ("src/staged_rts24_causal_audit_v2.py", "src.staged_rts24_reference_queries_v1", {"reference_requests"}),
    ]
    for source, module, names in links:
        found = {a.name for n in ast.walk(trees[source]) if isinstance(n, ast.ImportFrom)
                 and n.module == module for a in n.names}
        require(names <= found, "effective consumer import link missing")
    return dict(parameters_fields=sorted(fields), methods=list(methods[0]), policy_parameter_reads=policy,
                independent_audit_parameter_reads=sorted(independent), x_envelope_reads=x_reads,
                checked_selected_import_links=len(links),
                limits="selected_lexical_witnesses_not_execution_dataflow_or_full_environment_closure")


def construct(raw_configs, raw_case, reference_bytes):
    require(set(raw_configs) == set(CONFIGS), "configuration input set differs")
    require(set(reference_bytes) == set(REFERENCES), "implementation reference set differs")
    for name, expected in REFERENCES.items():
        require(sha256(reference_bytes[name]).hexdigest() == expected, "reference source drift: "+name)
    parsed, pins = {}, {}
    for config, (path, expected, count) in CONFIGS.items():
        raw = raw_configs[config]
        require(sha256(raw).hexdigest() == expected, "configuration source drift: "+config)
        parsed[config] = parse_yaml(raw)
        require(len(list(leaves(parsed[config]))) == count, "configuration leaf count differs")
        pins[config] = dict(path=path, **stamp(raw), scalar_leaves=count)
    scale = Fraction(parsed["public"]["business"]["dimensional_scale"])
    require(scale == 200, "scaling control differs")
    policy = rules()
    result = []
    for config, value in parsed.items():
        for pointer, original, key_kind in leaves(value):
            require((config, pointer) in policy, "unclassified input: "+config+pointer)
            rule = policy[config, pointer]
            operation = rule["operation"]
            transformed = None
            if operation == "multiply_scale":
                transformed = dict(kind="exact_scaled_derivation", value=str(Fraction(original)*scale),
                                   unit=rule["unit"], factor=SCALE_REF)
            elif operation == "identity":
                transformed = dict(kind="unchanged_input", value=original, unit=rule["unit"])
            result.append(dict(config=config, pointer=pointer, original_value=original, yaml_leaf_key_kind=key_kind,
                               direct_source_ref=dict(path=CONFIGS[config][0], pointer=pointer),
                               semantic_role=semantic_role(config, pointer, rule["public_runtime_use"]),
                               empirical_status="not_an_empirical_calibration",
                               public_value_record=transformed, **rule))
    require(len(result) == len(policy) == 132, "coverage is not bijective")
    return dict(schema="staged_rts24_parameter_provenance_v1", authority="DRAFT_NONAUTHORITATIVE",
                scope="three_frozen_yaml_leaf_fields_and_five_public_literal_groups",
                config_pins=pins, reference_pins={k:stamp(v) for k,v in reference_bytes.items()},
                selected_consumer_coverage=consumer_coverage(reference_bytes),
                auxiliary_use_scope="selected_source_consistency_guards_not_exhaustive_auxiliary_numeric_consumption",
                public_source=dict(package="PYPOWER", version="5.1.19", source_sha256=CASE_SHA,
                                   components=public_components(raw_case),
                                   citation_status="references_declared_in_pinned_case_docstring_not_reverified_online",
                                   license_status="local_source_declares_BSD_style_not_a_new_license_or_online_review"),
                implementation_boundaries=[
                    "public_bus_demand_is_PD_plus_GS_times_four_fifths_not_business_scale_200",
                    "raw_branch_rating_columns_are_MVA_labelled_numeric_values_used_as_MW_limits_in_declared_DC_model",
                    "public_loader_uses_reference_bus_from_bus_type_and_zero_based_gen_branch_enumeration",
                    "tap_zero_becomes_one_and_phase_shift_degrees_becomes_radians",
                    "rate_B_C_and_generator_ramp_attributes_may_be_retained_but_current_query_uses_RATE_A_and_half_Pmax",
                    "prehistory_f_is_zero_and_Y_uses_prehistory_clean_not_clean_path_array",
                    "runtime_actual_g_and_electrical_feasibility_not_evaluated_by_provenance",
                    "non_YAML_policy_choices_are_not_exhaustively_classified_by_this_leaf_inventory"],
                rows=sorted(result, key=lambda r:(r["config"], r["pointer"])),
                formal_result=False, empirical_calibration=False, resource_admission=False,
                native_authorized=False, official_verdict=None, receipt=None, seal=None)


def semantic_role(config, pointer, use):
    if use in ("not_adopted", "bound_only", "source_label_only"):
        return {"not_adopted":"no_runtime_value_from_this_field", "bound_only":"raw_source_binding_only",
                "source_label_only":"legacy_label_retained_as_source_response_model"}[use]
    if config == "business":
        if pointer.startswith("/parameters/"):
            name = pointer.rsplit("/", 1)[1]
            return "Fixture.parameters." + name
        if pointer.startswith("/equipment/"):
            return "equipment_online_ids_compute_capacity_and_idle_projection"
        if pointer.startswith("/workload/"):
            return "workload_projection_with_piecewise_change_hour"
        if pointer.startswith("/clean_paths/") or pointer == "/prehistory_clean":
            return "external_clean_mwh_projection_by_declared_hour"
        if pointer.startswith("/grid/"):
            return "load_fixture_equality_guard_against_public_project_timing"
        return {"/first_hour":"window_start_equality_guard", "/last_hour":"observation_end_minus_one_equality_guard",
                "/deadline_lag":"due_projection_equals_hour_plus_lag",
                "/flexible_fraction":"flexible_fraction_projection_with_zero_prehistory"}[pointer]
    if config == "rights":
        if pointer.startswith("/rights/"):
            return "firm_conditional_rights_projection_before_or_after"
        if pointer.startswith("/x_envelope/"):
            return "x_envelope_json_field:" + pointer.rsplit("/", 1)[1]
        return "source_section_business_sha256_equality_guard"
    return "public_configuration_field:" + pointer


def parse_registry(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "duplicate JSON key")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique)


def validate(document, raw_configs, raw_case, reference_bytes):
    expected = construct(raw_configs, raw_case, reference_bytes)
    require(canonical(document) == canonical(expected), "provenance content or typed values differ from reviewed mapping")
    return dict(authority="DRAFT_NONAUTHORITATIVE", scope="parameter_source_provenance_static_audit",
                scalar_leaves=132, counts_by_config={k:v[2] for k,v in CONFIGS.items()},
                scaled_fields=sum(r["operation"] == "multiply_scale" for r in expected["rows"]),
                public_runtime_uses=dict(sorted(Counter(r["public_runtime_use"] for r in expected["rows"]).items())),
                public_source_components=5, formal_result=False, empirical_calibration=False,
                public_points_built=0, native_highs_calls=0, solver_calls=0,
                independent_scientific_oracle=False, resource_admission=False,
                official_verdict=None, receipt=None, seal=None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    args = parser.parse_args()
    require(distribution("PYPOWER").version == "5.1.19", "public package version differs")
    case_path = Path(distribution("PYPOWER").locate_file("pypower/case24_ieee_rts.py"))
    paths = {k:ROOT/v[0] for k,v in CONFIGS.items()}
    paths.update({k:ROOT/k for k in REFERENCES})
    paths.update(case=case_path, registry=args.registry, checker=Path(__file__))
    before = {k:p.read_bytes() for k,p in paths.items()}
    require(len(before["registry"]) <= 512*1024, "registry byte bound")
    document = parse_registry(before["registry"])
    result = validate(document, {k:before[k] for k in CONFIGS}, before["case"], {k:before[k] for k in REFERENCES})
    require(all(p.read_bytes() == before[k] for k,p in paths.items()), "source bookend drift")
    result.update(input_pins={k:stamp(v) for k,v in before.items()},
                  pyyaml_version=version("PyYAML"), python_version=sys.version,
                  read_only=True, configuration_parses=3, public_case_execution=False,
                  selected_reference_files=len(REFERENCES),
                  reference_ast_files=sum(name.endswith(".py") for name in REFERENCES),
                  explicit_input_files=len(paths), explicit_file_reads=2*len(paths),
                  research_model_imports=False)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
