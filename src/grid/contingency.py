"""N-1 branch-contingency screening for the DC-OPF model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .dc_opf import DcOpfResult, solve_dc_opf
from .rts24 import Rts24Data


@dataclass(frozen=True)
class ContingencyOutcome:
    outaged_branch_index: int
    from_bus: int
    to_bus: int
    result: DcOpfResult
    max_loaded_branch_index: int | None
    max_loading_fraction: float | None
    max_redispatch_mw: float | None


@dataclass(frozen=True)
class GeneratorContingencyOutcome:
    outaged_generator_index: int
    bus: int
    result: DcOpfResult
    max_loaded_branch_index: int | None
    max_loading_fraction: float | None
    max_redispatch_mw: float | None


def _loading_metrics(
    data: Rts24Data,
    result: DcOpfResult,
    excluded_branch_index: int | None = None,
) -> tuple[int | None, float | None]:
    if not result.feasible:
        return None, None
    monitored = tuple(
        branch
        for branch in data.branches
        if branch.in_service and branch.index != excluded_branch_index
    )
    max_loaded = max(
        monitored,
        key=lambda branch: abs(result.branch_flows_mw[branch.index])
        / branch.rating_mw(result.branch_rating),
    )
    loading = (
        abs(result.branch_flows_mw[max_loaded.index])
        / max_loaded.rating_mw(result.branch_rating)
    )
    return max_loaded.index, loading


def _max_redispatch(
    data: Rts24Data,
    result: DcOpfResult,
    reference_generation_mw: Mapping[int, float] | None,
) -> float | None:
    if not result.feasible or reference_generation_mw is None:
        return None
    available = (
        generator.index
        for generator in data.generators
        if generator.index not in result.outaged_generator_indices
    )
    return max(
        abs(result.generation_mw[index] - reference_generation_mw[index])
        for index in available
    )


def screen_n_minus_one(
    data: Rts24Data,
    *,
    branch_indices: Iterable[int] | None = None,
    branch_rating: str = "rate_a",
    reference_generation_mw: Mapping[int, float] | None = None,
    redispatch_up_mw: Mapping[int, float] | None = None,
    redispatch_down_mw: Mapping[int, float] | None = None,
    allow_islanding: bool = False,
    solver_name: str = "highs",
) -> tuple[ContingencyOutcome, ...]:
    """Screen selected single-branch outages under explicit response limits."""

    branch_by_index = {branch.index: branch for branch in data.branches}
    selected = (
        tuple(branch.index for branch in data.branches if branch.in_service)
        if branch_indices is None
        else tuple(int(index) for index in branch_indices)
    )
    unknown = set(selected) - branch_by_index.keys()
    if unknown:
        raise ValueError(f"Unknown branch indices: {sorted(unknown)}")

    outcomes = []
    for branch_index in selected:
        branch = branch_by_index[branch_index]
        if not branch.in_service:
            raise ValueError(f"Branch {branch_index} is already out of service")
        result = solve_dc_opf(
            data,
            outaged_branch_indices=(branch_index,),
            branch_rating=branch_rating,
            reference_generation_mw=reference_generation_mw,
            redispatch_up_mw=redispatch_up_mw,
            redispatch_down_mw=redispatch_down_mw,
            allow_islanding=allow_islanding,
            solver_name=solver_name,
        )
        max_loaded_branch_index, max_loading = _loading_metrics(
            data,
            result,
            excluded_branch_index=branch_index,
        )
        outcomes.append(
            ContingencyOutcome(
                outaged_branch_index=branch_index,
                from_bus=branch.from_bus,
                to_bus=branch.to_bus,
                result=result,
                max_loaded_branch_index=max_loaded_branch_index,
                max_loading_fraction=max_loading,
                max_redispatch_mw=_max_redispatch(
                    data,
                    result,
                    reference_generation_mw,
                ),
            )
        )
    return tuple(outcomes)


def screen_generator_n_minus_one(
    data: Rts24Data,
    *,
    reference_generation_mw: Mapping[int, float],
    redispatch_up_mw: Mapping[int, float],
    redispatch_down_mw: Mapping[int, float],
    generator_indices: Iterable[int] | None = None,
    branch_rating: str = "rate_a",
    solver_name: str = "highs",
) -> tuple[GeneratorContingencyOutcome, ...]:
    """Screen positive-capacity generator outages with bounded redispatch."""

    generator_by_index = {generator.index: generator for generator in data.generators}
    selected = (
        tuple(
            generator.index
            for generator in data.generators
            if generator.in_service and generator.p_max_mw > 0.0
        )
        if generator_indices is None
        else tuple(int(index) for index in generator_indices)
    )
    unknown = set(selected) - generator_by_index.keys()
    if unknown:
        raise ValueError(f"Unknown generator indices: {sorted(unknown)}")

    outcomes = []
    for generator_index in selected:
        generator = generator_by_index[generator_index]
        if not generator.in_service or generator.p_max_mw <= 0.0:
            raise ValueError(
                f"Generator {generator_index} is not an active-power contingency"
            )
        result = solve_dc_opf(
            data,
            outaged_generator_indices=(generator_index,),
            branch_rating=branch_rating,
            reference_generation_mw=reference_generation_mw,
            redispatch_up_mw=redispatch_up_mw,
            redispatch_down_mw=redispatch_down_mw,
            solver_name=solver_name,
        )
        max_loaded_branch_index, max_loading = _loading_metrics(data, result)
        outcomes.append(
            GeneratorContingencyOutcome(
                outaged_generator_index=generator_index,
                bus=generator.bus,
                result=result,
                max_loaded_branch_index=max_loaded_branch_index,
                max_loading_fraction=max_loading,
                max_redispatch_mw=_max_redispatch(
                    data,
                    result,
                    reference_generation_mw,
                ),
            )
        )
    return tuple(outcomes)
