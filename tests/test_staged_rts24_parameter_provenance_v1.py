"""Independent anchors and corruption checks for the static input provenance."""
import builtins
from copy import deepcopy
from hashlib import sha256
from importlib.metadata import distribution
import json
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

from src import staged_rts24_parameter_provenance_v1 as p


@pytest.fixture(scope="module")
def inputs():
    raw = {k:(p.ROOT/v[0]).read_bytes() for k,v in p.CONFIGS.items()}
    refs = {name:(p.ROOT/name).read_bytes() for name in p.REFERENCES}
    case = Path(distribution("PYPOWER").locate_file("pypower/case24_ieee_rts.py")).read_bytes()
    document = p.parse_registry(p.REGISTRY.read_bytes())
    return document, raw, case, refs


def find(document, config, pointer):
    return next(r for r in document["rows"] if (r["config"], r["pointer"]) == (config, pointer))


def test_all_scalar_leaves_covered_once_and_typed(inputs):
    document, raw, case, refs = inputs
    report = p.validate(document, raw, case, refs)
    assert report["counts_by_config"] == dict(public=40, business=60, rights=32)
    assert report["scalar_leaves"] == 132 and report["scaled_fields"] == 37
    expected = {(name, pointer) for name, data in raw.items() for pointer, _, _ in p.leaves(p.parse_yaml(data))}
    assert {(r["config"], r["pointer"]) for r in document["rows"]} == expected
    integer_key = find(document, "rights", "/network/actual_outages/1")
    assert integer_key["yaml_leaf_key_kind"] == "int" and integer_key["original_value"] == 0
    assert report["independent_scientific_oracle"] is False
    assert report["public_points_built"] == report["native_highs_calls"] == report["solver_calls"] == 0


@pytest.mark.parametrize("config,pointer,value,unit", [
    ("business", "/parameters/capacity", "40", "MW_c"),
    ("business", "/parameters/auxiliary_mw", "5", "MW"),
    ("business", "/parameters/max_debt", "80", "MWh_c"),
    ("business", "/parameters/call_ramp", "40", "MW_c_per_hour"),
    ("business", "/equipment/1/capacity", "80", "MW_c"),
    ("business", "/equipment/1/idle_mw", "8", "MW"),
    ("business", "/workload/after", "140", "MW_c"),
    ("business", "/prehistory_clean", "120", "MWh"),
    ("business", "/clean_paths/late/2", "128", "MWh"),
    ("business", "/clean_paths/early/7", "168", "MWh"),
    ("rights", "/rights/firm_before_mw", "120", "MW"),
    ("rights", "/rights/conditional_after_mw", "100", "MW"),
    ("rights", "/x_envelope/max_energy_mwh", "100", "MWh"),
])
def test_scaled_values_match_independent_hand_anchors(inputs, config, pointer, value, unit):
    row = find(inputs[0], config, pointer)
    assert row["public_value_record"] == dict(kind="exact_scaled_derivation", value=value, unit=unit,
                                              factor=dict(config="public", pointer="/business/dimensional_scale"))
    assert row["origin_class"] == "mechanism_assumption"
    assert row["empirical_status"] == "not_an_empirical_calibration"


@pytest.mark.parametrize("config,pointer,original", [
    ("business", "/parameters/alpha", "4/5"), ("business", "/parameters/eta", "1"),
    ("business", "/parameters/beta", "1"), ("business", "/parameters/facility_factor", "5/4"),
    ("business", "/parameters/max_events", 2), ("business", "/equipment/1/lead", 2),
    ("public", "/network/background_load_multiplier", "4/5"),
    ("public", "/project/rate_a_increase_mw", "100"),
    ("public", "/network/redispatch_fraction_of_pmax", "1/2"),
    ("rights", "/x_envelope/max_duration_hours", 1),
])
def test_non_scaled_values_keep_original_types(inputs, config, pointer, original):
    row = find(inputs[0], config, pointer)
    assert row["operation"] == "identity"
    assert type(row["public_value_record"]["value"]) is type(original)
    assert row["public_value_record"]["value"] == original


def test_legacy_fields_guards_labels_and_retained_attributes_are_distinct(inputs):
    rows = inputs[0]["rows"]
    old = [r for r in rows if r["config"] == "rights" and r["pointer"].startswith("/network/")]
    assert len(old) == 17
    assert all(r["public_runtime_use"] == "not_adopted" and r["public_value_record"] is None for r in old)
    for name in ("before", "after"):
        row = find(inputs[0], "business", "/grid/"+name)
        assert row["public_runtime_use"] == "not_adopted" and row["operation"] == "none"
        assert row["auxiliary_uses"] == ["saved_business_necessary_audit_checks_scaled_value_equals_firm_plus_conditional"]
    assert find(inputs[0], "business", "/grid/start")["public_runtime_use"] == "cross_source_guard"
    assert find(inputs[0], "rights", "/business_fixture")["public_runtime_use"] == "bound_only"
    assert find(inputs[0], "rights", "/x_envelope/response_model")["public_runtime_use"] == "source_label_only"
    assert find(inputs[0], "public", "/project/rate_c_increase_mw")["public_runtime_use"] == "retained_network_attribute_not_active_limit"
    assert find(inputs[0], "public", "/network/economic_regularization_quadratic")["public_runtime_use"] == "guard_matches_fixed_query_constant"
    assert find(inputs[0], "public", "/status")["public_runtime_use"] == "scope_guard"
    assert find(inputs[0], "public", "/actual_event/rule")["public_runtime_use"] == "fixed_implementation_guard"
    for name in ("project_start", "project_lead", "delays/on_time", "delays/delayed"):
        assert find(inputs[0], "rights", "/network/"+name)["auxiliary_uses"] == [
            "saved_business_necessary_audit_three_source_project_timing_guard"]


def test_clean_deadline_and_prehistory_claim_limits_are_not_implicit(inputs):
    document = inputs[0]
    assert "implementation_overrides_fraction_to_zero_before_hour_zero" in find(document, "business", "/flexible_fraction")["claim_limits"]
    assert "two_hour_deadline_not_empirical_task_sla" in find(document, "business", "/deadline_lag")["claim_limits"]
    clean = [r for r in document["rows"] if r["config"] == "business" and r["pointer"].startswith("/clean_paths/")]
    assert len(clean) == 16
    assert all("development_clean_timing_not_business_pace_holdout_or_empirical_cfe" in r["claim_limits"] for r in clean)
    assert all(r["origin_class"] != "public_static_benchmark_data" for r in document["rows"])


@pytest.mark.parametrize("change", [
    "drop_row", "duplicate_row", "unknown_pointer", "public_class_for_synthetic", "wrong_unit",
    "wrong_scaled_value", "scaled_time", "adopt_legacy_network", "erase_clean_limit",
    "erase_deadline_limit", "change_direct_reference", "value_bool_instead_of_int",
    "value_float_instead_of_int", "change_typed_key", "extra_column", "grant_authority", "change_public_component",
])
def test_full_record_rejects_corruption(inputs, change):
    document, raw, case, refs = inputs
    bad = deepcopy(document)
    row = find(bad, "business", "/parameters/capacity")
    if change == "drop_row": bad["rows"].pop()
    elif change == "duplicate_row": bad["rows"].append(deepcopy(bad["rows"][0]))
    elif change == "unknown_pointer": row["pointer"] = "/parameters/not_a_field"
    elif change == "public_class_for_synthetic": row["origin_class"] = "public_static_benchmark_data"
    elif change == "wrong_unit": row["unit"] = "MW"
    elif change == "wrong_scaled_value": row["public_value_record"]["value"] = "41"
    elif change == "scaled_time": find(bad, "business", "/deadline_lag")["operation"] = "multiply_scale"
    elif change == "adopt_legacy_network": find(bad, "rights", "/network/poi_bus")["public_runtime_use"] = "adopted_value"
    elif change == "erase_clean_limit": find(bad, "business", "/clean_paths/late/2")["claim_limits"] = []
    elif change == "erase_deadline_limit": find(bad, "business", "/deadline_lag")["claim_limits"] = []
    elif change == "change_direct_reference": row["direct_source_ref"]["path"] = "configs/not_a_source.yaml"
    elif change == "value_bool_instead_of_int": find(bad, "rights", "/network/actual_outages/1")["original_value"] = False
    elif change == "value_float_instead_of_int": find(bad, "rights", "/network/actual_outages/1")["original_value"] = 0.0
    elif change == "change_typed_key": find(bad, "rights", "/network/actual_outages/1")["yaml_leaf_key_kind"] = "str"
    elif change == "extra_column": row["unreviewed"] = True
    elif change == "grant_authority": bad["native_authorized"] = True
    elif change == "change_public_component": bad["public_source"]["components"][1]["literal_sha256"] = "0"*64
    with pytest.raises(ValueError, match="provenance content"):
        p.validate(bad, raw, case, refs)


@pytest.mark.parametrize("name", ["public", "business", "rights"])
def test_frozen_configuration_drift_rejected(inputs, name):
    doc, raw, case, refs = inputs
    altered = dict(raw); altered[name] += b"\n"
    with pytest.raises(ValueError, match="configuration source drift"):
        p.validate(doc, altered, case, refs)


@pytest.mark.parametrize("name", sorted(p.REFERENCES))
def test_every_selected_reference_drift_rejected(inputs, name):
    doc, raw, case, refs = inputs
    altered = dict(refs); altered[name] += b"\n"
    with pytest.raises(ValueError, match="reference source drift"): p.validate(doc, raw, case, altered)


def test_case_drift_rejected(inputs):
    doc, raw, case, refs = inputs
    with pytest.raises(ValueError, match="public source bytes drift"): p.validate(doc, raw, case+b"\n", refs)


def test_consumer_field_schema_methods_and_selected_links_cover_runtime_mapping(inputs):
    coverage = inputs[0]["selected_consumer_coverage"]
    assert len(inputs[0]["reference_pins"]) == 13
    assert len(coverage["parameters_fields"]) == len(coverage["independent_audit_parameter_reads"]) == 14
    assert set().union(*(set(v) for v in coverage["policy_parameter_reads"].values())) == set(coverage["parameters_fields"])
    assert coverage["methods"] == ["instantaneous", "fixed_headroom", "full_temporal"]
    assert coverage["checked_selected_import_links"] == 5
    assert all(len(names) == 6 for names in coverage["x_envelope_reads"].values())
    assert inputs[0]["public_source"]["components"][0]["literal_value"] == 100.0


def test_parameter_semantic_roles_reference_exact_declared_runtime_fields(inputs):
    doc = inputs[0]
    rows = [r for r in doc["rows"] if r["config"] == "business" and r["pointer"].startswith("/parameters/")]
    declared = set(doc["selected_consumer_coverage"]["parameters_fields"])
    assert len(rows) == len(declared) == 14
    for row in rows:
        name = row["pointer"].rsplit("/", 1)[1]
        assert name in declared and row["semantic_role"] == "Fixture.parameters."+name


@pytest.mark.parametrize("name,old,new,message", [
    ("src/staged_deliverability_development_v1.py", b"capacity: Q", b"unreviewed_capacity: Q", "Parameters schema"),
    ("src/staged_deliverability_development_v1.py", b'"full_temporal"', b'"unreviewed_method"', "METHODS"),
    ("src/staged_rts24_causal_v1.py", b"p.max_call_energy", b"p.unreviewed_energy", "policy parameter"),
    ("src/staged_rts24_causal_audit_v2.py", b"p.max_debt", b"p.unreviewed_debt", "independent audit parameter"),
    ("src/staged_rts24_causal_v2.py", b'x["max_call_mw"]', b'x["unreviewed_max_call"]', "X envelope"),
    ("src/staged_rts24_causal_v2.py", b"import reference_requests", b"import unrelated_reference", "import link"),
])
def test_static_consumer_coverage_rejects_symbol_omission_without_executing_sources(inputs, name, old, new, message):
    altered = dict(inputs[3])
    assert old in altered[name]
    altered[name] = altered[name].replace(old, new)
    with pytest.raises(ValueError, match=message):
        p.consumer_coverage(altered)


@pytest.mark.parametrize("raw", [
    b"a: 1\na: 2\n", b"1: a\n'1': b\n", b"true: 1\n",
    b"a: &x 1\nb: *x\n",
])
def test_ambiguous_yaml_rejected_without_mutating_default_loader(raw):
    with pytest.raises(ValueError): p.parse_yaml(raw)
    assert yaml.safe_load(b"a: 1\na: 2") == {"a": 2}


@pytest.mark.parametrize("raw", [b"a: true\n", b"a: 1.2\n", b"a: null\n"])
def test_non_exact_scalar_types_rejected(raw):
    with pytest.raises(ValueError): list(p.leaves(p.parse_yaml(raw)))


def test_duplicate_json_and_pointer_escaping():
    with pytest.raises(ValueError, match="duplicate JSON"): p.parse_registry(b'{"a":1,"a":2}')
    assert list(p.leaves({"a/b": {"~key": "1"}})) == [("/a~1b/~0key", "1", "str")]


def test_public_case_is_read_as_literals_and_never_executed(inputs, monkeypatch):
    source = inputs[2] + b"\nraise RuntimeError('must_not_execute_case_source')\n"
    monkeypatch.setattr(p, "CASE_SHA", sha256(source).hexdigest())
    original = builtins.__import__
    def guarded(name, *args, **kwargs):
        if name == "numpy" or name.startswith(("pypower", "pyomo", "highspy")):
            raise AssertionError("scientific package import attempted")
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", guarded)
    parts = p.public_components(source)
    assert {r["component"]:r["shape"] for r in parts} == {
        "baseMVA": [], "bus":[24,13], "gen":[33,21], "branch":[38,13], "gencost":[33,7]}


def test_read_only_cli_and_optimized_corrupt_record_rejection(inputs, tmp_path):
    source = p.ROOT / "src/staged_rts24_parameter_provenance_v1.py"
    before = p.REGISTRY.read_bytes()
    valid = subprocess.run([sys.executable, "-B", "-s", str(source)], cwd=tmp_path, capture_output=True, timeout=15)
    assert valid.returncode == 0, valid.stderr
    report = json.loads(valid.stdout)
    assert report["read_only"] and report["scalar_leaves"] == 132 and report["configuration_parses"] == 3
    assert not report["public_case_execution"] and not report["research_model_imports"]
    bad = deepcopy(inputs[0]); bad["rows"].pop()
    target = tmp_path / "bad.json"; target.write_text(json.dumps(bad), encoding="utf-8")
    rejected = subprocess.run([sys.executable, "-B", "-s", "-O", str(source), "--registry", str(target)],
                              cwd=tmp_path, capture_output=True, timeout=15)
    assert rejected.returncode != 0 and b"provenance content" in rejected.stderr
    assert p.REGISTRY.read_bytes() == before
