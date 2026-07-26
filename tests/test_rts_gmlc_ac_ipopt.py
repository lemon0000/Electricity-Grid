from copy import deepcopy

import numpy as np
import pytest
from pypower.api import case9, ppoption, runopf
from pypower.idx_brch import RATE_A, SHIFT, TAP
from pypower.idx_bus import BS, BUS_I, VA, VM
from pypower.idx_gen import GEN_BUS, GEN_STATUS, PG

from src.grid.rts_gmlc_ac_ipopt import (
    AcIpoptEnvelope,
    _FROZEN_IPOPT_OPTIONS,
    solve_ac_feasibility_ipopt,
)
from src.grid.rts_gmlc_ac_recovery import prepare_ac_recovery_case


@pytest.fixture(scope="module")
def prepared_case9():
    source = case9()
    source["bus"][:, BUS_I] += 100
    source["gen"][:, GEN_BUS] += 100
    source["branch"][:, :2] += 100
    source["branch"][:, RATE_A] = np.maximum(source["branch"][:, RATE_A], 250.0)
    source["branch"][0, TAP] = 1.03
    source["branch"][0, SHIFT] = 2.0
    source["bus"][4, BS] = 5.0
    baseline = runopf(deepcopy(source), ppoption(VERBOSE=0, OUT_ALL=0, OPF_ALG=560))
    assert baseline["success"]
    source["gen"][:, PG] = baseline["gen"][:, PG]
    source["bus"][:, (VM, VA)] = baseline["bus"][:, (VM, VA)]
    targets = tuple(float(value) for value in baseline["gen"][:, PG])
    active_rows = tuple(np.flatnonzero(source["gen"][:, GEN_STATUS] > 0.0))
    return prepare_ac_recovery_case(
        source,
        target_generation_mw_by_row=targets,
        generator_uid_by_row=("g1", "g2", "g3"),
        branch_uid_by_row=tuple(f"b{row}" for row in range(len(source["branch"]))),
        mode="distributed_committable",
        adjustable_generator_rows=active_rows,
        reference_generator_row=0,
        reference_generator_uid="g1",
        reference_bus=int(source["gen"][0, GEN_BUS]),
    )


def test_ipopt_finds_and_audits_original_case9_feasibility(prepared_case9):
    result = solve_ac_feasibility_ipopt(prepared_case9)

    assert result.solver_success
    assert result.return_status == "Solve_Succeeded"
    assert result.original_envelope_feasibility_witnessed
    assert result.maximum_nlp_constraint_violation <= 1.0e-6
    assert result.maximum_nlp_variable_bound_violation <= 1.0e-8
    assert result.audit.postsolve_network_equation_reconstruction_audit_passed
    assert result.audit.nonunity_tap_count == 1
    assert result.audit.nonzero_shift_count == 1
    assert result.audit.nonzero_bs_count == 1


@pytest.mark.parametrize("strategy", ("midpoint", "flat_target_midq"))
def test_ipopt_registered_initial_strategies_are_audited(prepared_case9, strategy):
    result = solve_ac_feasibility_ipopt(prepared_case9, initial_strategy=strategy)

    assert result.solver_success
    assert result.original_envelope_feasibility_witnessed
    assert result.initial_strategy == strategy


def test_ipopt_relaxed_probe_cannot_be_labeled_original_witness(prepared_case9):
    result = solve_ac_feasibility_ipopt(
        prepared_case9,
        envelope=AcIpoptEnvelope(branch_rate_multiplier=1.05),
    )

    assert result.solver_success
    assert not result.original_envelope_feasibility_witnessed
    assert result.branch_rate_multiplier == 1.05


def test_ipopt_rejects_input_and_solver_protocol_drift(prepared_case9):
    prepared = deepcopy(prepared_case9)
    prepared.case["bus"][0, 2] += 1.0
    with pytest.raises(ValueError, match="changed before solve"):
        solve_ac_feasibility_ipopt(prepared)

    options = dict(_FROZEN_IPOPT_OPTIONS)
    options["ipopt.max_iter"] = 999
    with pytest.raises(ValueError, match="solver options drifted"):
        solve_ac_feasibility_ipopt(prepared_case9, solver_options=options)
