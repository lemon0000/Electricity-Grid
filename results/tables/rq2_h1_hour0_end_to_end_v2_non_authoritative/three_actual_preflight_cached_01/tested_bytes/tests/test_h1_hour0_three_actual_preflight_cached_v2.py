"""Three-Actual orchestration preflight with static dependency bookends.

Only static source/package metadata is reused within this test. Numerical inputs,
assignments, residuals and persistence views are still freshly evaluated. This
test does not cover transient file/package drift or ABA and is not a production
performance benchmark. The uncached preflight remains separately available.
"""
import pytest

from src.rq2_joint_deliverability_boundary_v1 import (
    continuous_grid_normal, current_grid_step, continuous_grid_candidate,
    hourly_transaction)
from tests import test_h1_hour0_three_actual_preflight_v2 as uncached
from tests.test_h1_hour0_three_actual_preflight_v2 import (
    common_case, case, context, phase_setup, setup, legacy_setup, no_solver)


@pytest.fixture(autouse=True)
def static_dependency_bookends():
    modules = (continuous_grid_normal, current_grid_step,
               continuous_grid_candidate, hourly_transaction)
    original = continuous_grid_normal._dependencies
    code, defaults, kwdefaults = (original.__code__, original.__defaults__,
                                 original.__kwdefaults__)
    assert all(module._dependencies is original for module in modules)
    before = original()
    assert type(before) is tuple
    assert all(type(group) is tuple for group in before)
    assert all(type(pair) is tuple and len(pair) == 2
               and all(type(value) is str for value in pair)
               for group in before for pair in group)

    def cached():
        return before

    patch = pytest.MonkeyPatch()
    try:
        for module in modules:
            patch.setattr(module, '_dependencies', cached)
        yield
        assert all(module._dependencies is cached for module in modules)
    finally:
        patch.undo()
        assert all(module._dependencies is original for module in modules)
        assert original.__code__ is code
        assert original.__defaults__ is defaults
        assert original.__kwdefaults__ is kwdefaults
        assert original() == before


def test_three_actual_paired_commit_and_reopen(context, monkeypatch, tmp_path):
    uncached.test_actual_helper_three_lanes_paired_commit_and_reopen(
        context, monkeypatch, tmp_path)
