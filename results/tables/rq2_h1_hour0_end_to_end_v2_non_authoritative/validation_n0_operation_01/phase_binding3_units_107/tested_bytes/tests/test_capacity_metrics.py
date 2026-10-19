import pytest

from src.evaluation import calculate_capacity_milestones


def _calculate(
    capacities,
    *,
    validated=None,
    validation_hours=None,
    application_capacity_mw=100.0,
    minimum_operational_block_mw=30.0,
    minimum_validation_hours=1.0,
):
    quarter_names = tuple(capacities)
    return calculate_capacity_milestones(
        quarter_names=quarter_names,
        total_capacity_mw=capacities,
        model_validated_by_quarter=(
            {name: True for name in quarter_names}
            if validated is None
            else validated
        ),
        continuous_validation_hours=(
            {name: 1.0 for name in quarter_names}
            if validation_hours is None
            else validation_hours
        ),
        application_capacity_mw=application_capacity_mw,
        minimum_operational_block_mw=minimum_operational_block_mw,
        minimum_validation_hours=minimum_validation_hours,
    )


def test_capacity_milestones_use_operational_block_and_application_thresholds():
    result = _calculate(
        {"q0": 1.0, "q1": 30.0, "q2": 50.0, "q3": 80.0, "q4": 100.0}
    )

    assert result.metric_scope == (
        "released_capacity_threshold_in_static_dc_state_set_with_declared_window_assumption"
    )
    assert result.t_module.threshold_mw == pytest.approx(30.0)
    assert result.t_module.quarter == "q1"
    assert result.t20.threshold_mw == pytest.approx(30.0)
    assert result.t20.quarter == "q1"
    assert result.t50.threshold_mw == pytest.approx(50.0)
    assert result.t50.quarter == "q2"
    assert result.t100.threshold_mw == pytest.approx(100.0)
    assert result.t100.quarter == "q4"
    for milestone in (result.t_module, result.t20, result.t50, result.t100):
        assert milestone.reached
        assert not milestone.right_censored
        assert milestone.censor_quarter is None
        assert milestone.display_label == milestone.quarter


def test_one_mw_does_not_trigger_first_operational_milestone():
    result = _calculate({"q0": 1.0, "q1": 30.0})

    assert result.t_module.quarter == "q1"
    assert result.t20.quarter == "q1"


def test_model_validation_and_continuous_hours_block_early_milestone():
    result = _calculate(
        {"q0": 30.0, "q1": 30.0, "q2": 30.0},
        validated={"q0": False, "q1": True, "q2": True},
        validation_hours={"q0": 2.0, "q1": 0.5, "q2": 1.0},
    )

    assert result.t_module.quarter == "q2"
    assert result.t20.quarter == "q2"


def test_unreached_t100_is_structurally_right_censored():
    result = _calculate({"q0": 1.0, "q1": 30.0, "q2": 50.0, "q3": 80.0})

    assert result.t50.reached
    assert result.t50.quarter == "q2"
    assert not result.t100.reached
    assert result.t100.quarter is None
    assert result.t100.right_censored
    assert result.t100.censor_quarter == "q3"
    assert result.t100.display_label == "q3+"


@pytest.mark.parametrize(
    ("field", "values"),
    (
        ("total_capacity_mw", {"q0": 30.0}),
        ("model_validated_by_quarter", {"q0": True}),
        ("continuous_validation_hours", {"q0": 1.0}),
    ),
)
def test_input_mapping_keys_must_match_quarters(field, values):
    kwargs = {
        "quarter_names": ("q0", "q1"),
        "total_capacity_mw": {"q0": 30.0, "q1": 50.0},
        "model_validated_by_quarter": {"q0": True, "q1": True},
        "continuous_validation_hours": {"q0": 1.0, "q1": 1.0},
        "application_capacity_mw": 100.0,
        "minimum_operational_block_mw": 30.0,
        "minimum_validation_hours": 1.0,
    }
    kwargs[field] = values

    with pytest.raises(ValueError, match="keys must match"):
        calculate_capacity_milestones(**kwargs)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("application_capacity_mw", 0.0),
        ("minimum_operational_block_mw", -1.0),
        ("minimum_validation_hours", 0.0),
        ("tolerance_mw", -1.0),
    ),
)
def test_scalar_inputs_require_valid_ranges(field, value):
    kwargs = {
        "quarter_names": ("q0",),
        "total_capacity_mw": {"q0": 30.0},
        "model_validated_by_quarter": {"q0": True},
        "continuous_validation_hours": {"q0": 1.0},
        "application_capacity_mw": 100.0,
        "minimum_operational_block_mw": 30.0,
        "minimum_validation_hours": 1.0,
    }
    kwargs[field] = value

    with pytest.raises(ValueError):
        calculate_capacity_milestones(**kwargs)


@pytest.mark.parametrize(
    "overrides",
    (
        {"quarter_names": ()},
        {"quarter_names": ("q0", "q0")},
        {"total_capacity_mw": {"q0": -1.0}},
        {"total_capacity_mw": {"q0": 101.0}},
        {"model_validated_by_quarter": {"q0": 1}},
        {"continuous_validation_hours": {"q0": -1.0}},
        {
            "application_capacity_mw": 20.0,
            "minimum_operational_block_mw": 30.0,
        },
    ),
)
def test_invalid_quarter_values_and_ranges_are_rejected(overrides):
    kwargs = {
        "quarter_names": ("q0",),
        "total_capacity_mw": {"q0": 30.0},
        "model_validated_by_quarter": {"q0": True},
        "continuous_validation_hours": {"q0": 1.0},
        "application_capacity_mw": 100.0,
        "minimum_operational_block_mw": 30.0,
        "minimum_validation_hours": 1.0,
    }
    kwargs.update(overrides)

    with pytest.raises(ValueError):
        calculate_capacity_milestones(**kwargs)


def test_total_capacity_must_not_retreat():
    with pytest.raises(ValueError, match="nondecreasing"):
        _calculate({"q0": 50.0, "q1": 40.0})
