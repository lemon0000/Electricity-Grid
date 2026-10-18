"""Data-driven trace scenario generator for RQ2 H2 (agent.md sections 4/8/9).

Purpose and honesty boundary
----------------------------
The RQ2 out-of-sample evaluation (``src.evaluation.economic_holdout``) needs a
set of *unseen* holdout scenarios and a set of *training* scenarios. Until now
those were a hand-crafted frozen tree, which invites the reviewer question
"are the overestimation / failure-probability results just an artifact of the
scenarios you drew by hand?". This module answers that by deriving the scenario
demands from the **observed** AI-workload trace *shapes* the project already
ships:

* ``data/processed/google_power_2019``  -- 55 PDU power-utilisation series,
  a normalized (0-1) hourly *shape* of data-centre electrical load. It drives
  the network-stress demand ``grid_need_mw`` (heavier load -> a scenario that
  forces more N-1/thermal-driven curtailment).
* ``data/processed/alibaba_gpu_2020`` -- relative hourly GPU workload, a
  normalized shape of deferrable compute. It drives the green/CFE deferral call
  ``green_call_mw`` (more deferrable workload -> a larger CFE-shifting call
  competing for the same flexibility budget).

What this module does *not* claim (agent.md sections 4/8):

* The traces provide only a *normalized shape*. They carry no absolute MW, no
  deadline, no checkpoint/recovery semantics and no real calendar (the Alibaba
  ``summary.json`` records ``recovery_parameters_observed=false``,
  ``deadline_available=false``, ``calendar_dates_real=false``). Every MW here is
  therefore **derived**: ``demand = frozen_scale * mean(trace window)``. The
  frozen scale is a synthetic mechanism parameter, not a measured power.
* The two traces come from *different* clusters with anonymized relative time,
  so they are sampled as **independent marginals**; this module makes no claim
  that the grid-stress and workload shapes are temporally correlated.
* Scenario probabilities are **Monte-Carlo sampling weights** (uniform over the
  drawn windows), never empirical outage / failure probabilities.

Out-of-sample structure
------------------------
Each trace is split once, in time, at ``split_index``. Training windows are
sampled from the early segment ``[0, split_index)`` and holdout windows from the
late segment ``[split_index, T)``. Because a window is a contiguous block whose
end (train) never exceeds the split and whose start (holdout) never precedes it,
no source hour is shared between the two sets: the out-of-sample separation is
structural, not asserted. Sampling contiguous blocks (block bootstrap) preserves
the within-trace autocorrelation the shape actually exhibits, which a per-hour
i.i.d. draw would destroy.

Split-aware normalization (no holdout leakage)
----------------------------------------------
A derived demand is ``frozen_scale * mean(normalized_window)``. Because
``mean(v / peak) = mean(v) / peak``, dividing the shape by a *global* peak taken
over the whole trace (which includes the holdout segment, and whose maximum may
fall inside it) would make every training scenario's MW depend on holdout hours
through the shared divisor -- an out-of-sample leak. The Google 2019 data card
makes this explicit (``normalization_uses_future_window_peak=true``,
``normalization_allowed_use=fixed_replay_not_train_or_holdout_feature``: the
full-window peak "must not be calculated across a train/holdout split").
``TraceShape.peak_normalized`` therefore refuses a bare global peak and requires
either a *pre-frozen external constant* or a peak estimated from the *training*
segment ``[0, split_index)`` only, applied uniformly to both segments. The
generator additionally asserts that a training-segment normalization was cut at
the same ``split_fraction`` it samples on, so the divisor can never see a holdout
hour. The normalization peak and split are recorded in ``provenance``.

The draw is fully determined by ``seed`` (agent.md section 10). The returned
``provenance`` records the split index and the exact drawn windows so every
derived demand can be reproduced and hand-checked.

This module only *generates inputs*; it does not solve, certify, or relax any
security limit. It emits ordinary ``EconomicScenario`` objects that must still
pass the frozen downstream validator in ``economic_holdout``.
"""

from __future__ import annotations

import csv
import gzip
from dataclasses import dataclass, field
from math import isfinite
from numbers import Real
from pathlib import Path

import numpy as np

from ..models.economic_stochastic import EconomicScenario


# The MW quantities are derived from a normalized shape via a frozen synthetic
# scale, and the probabilities are Monte-Carlo sampling weights. This string is
# propagated so no downstream artifact can mistake them for engineering,
# contract, or empirical-outage evidence (agent.md sections 4/8).
TRACE_SCENARIO_PARAMETER_STATUS = (
    "mw_derived_from_normalized_trace_shape_via_frozen_synthetic_scale_"
    "probabilities_are_monte_carlo_sampling_weights_not_empirical_outage_"
    "and_not_engineering_or_contract_evidence"
)


def _finite(name: str, value: object) -> float:
    if not isinstance(value, Real) or isinstance(value, bool):
        raise ValueError(f"{name} must be a real number")
    number = float(value)
    if not isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def _positive(name: str, value: object) -> float:
    number = _finite(name, value)
    if number <= 0.0:
        raise ValueError(f"{name} must be strictly positive")
    return number


def _nonnegative(name: str, value: object) -> float:
    number = _finite(name, value)
    if number < 0.0:
        raise ValueError(f"{name} must be nonnegative")
    return number


@dataclass(frozen=True)
class TraceShape:
    """A normalized (0-1) hourly load/workload shape read from a real trace.

    ``values`` is the ordered per-hour normalized series; ``source`` records the
    provenance (dataset id + column) so the derivation is auditable. No absolute
    MW is stored -- the caller supplies the frozen scale.

    ``normalization_peak`` / ``normalization_split_fraction`` record how a raw
    series was turned into this shape when ``peak_normalized`` built it:
    ``normalization_peak`` is the divisor actually used and
    ``normalization_split_fraction`` is the fraction at which the *training*
    segment used to estimate that peak was cut (``None`` when the peak is a
    pre-frozen external constant that carries no split dependency, or when the
    shape was supplied already normalized). The generator uses
    ``normalization_split_fraction`` to prove the divisor never saw a holdout
    hour.
    """

    name: str
    source: str
    values: tuple[float, ...]
    normalization_peak: float | None = None
    normalization_split_fraction: float | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("TraceShape.name must be nonempty")
        if not self.source:
            raise ValueError("TraceShape.source must be nonempty")
        if len(self.values) < 2:
            raise ValueError("TraceShape.values must have at least two hours")
        for i, v in enumerate(self.values):
            _nonnegative(f"{self.name}.values[{i}]", v)
        if self.normalization_peak is not None:
            _positive(f"{self.name}.normalization_peak", self.normalization_peak)
        if self.normalization_split_fraction is not None:
            split = _finite(
                f"{self.name}.normalization_split_fraction",
                self.normalization_split_fraction,
            )
            if not 0.0 < split < 1.0:
                raise ValueError(
                    f"{self.name}.normalization_split_fraction must lie strictly "
                    "in (0, 1)"
                )

    @classmethod
    def peak_normalized(
        cls,
        *,
        name: str,
        source: str,
        raw_values: tuple[float, ...],
        split_fraction: float | None = None,
        external_peak: float | None = None,
    ) -> "TraceShape":
        """Build a 0-1 shape by dividing a raw (unbounded) series by a *leak-free*
        peak.

        Some traces (e.g. Alibaba ``requested_gpu_equivalents``) are not already
        normalized. Peak-normalization is made an explicit, auditable step here
        rather than an ad-hoc caller division, so the shape a scenario is built
        from is unambiguous.

        Because a derived demand is ``frozen_scale * mean(values)`` and
        ``mean(v / peak) = mean(v) / peak``, the divisor is shared by every
        window: a peak taken over the whole series (which includes the holdout
        segment) would make training-window MW depend on holdout hours. This is
        exactly the leak the Google 2019 data card forbids
        (``normalization_uses_future_window_peak``: the full-window peak must not
        be computed across a train/holdout split). A *bare global peak is
        therefore rejected fail-closed*; the caller must pick one leak-free
        divisor:

        * ``split_fraction`` -- estimate the peak from the training segment
          ``[0, split_index)`` only and apply it to the whole series. The split
          is stored so the generator can assert it matches its own sampling
          split. Holdout hours may then exceed 1.0, which is honest (a future
          spike above the training peak), not clipped.
        * ``external_peak`` -- a pre-frozen constant (e.g. a nameplate capacity)
          decided before any split; it carries no data dependency on the
          holdout, so no split coupling is needed.

        Exactly one of the two must be given. A degenerate all-zero (or
        all-zero-training) series is rejected fail-closed.
        """

        if (split_fraction is None) == (external_peak is None):
            raise ValueError(
                "peak_normalized requires exactly one of split_fraction "
                "(training-segment peak) or external_peak (pre-frozen constant); "
                "a bare global peak over the full series would leak holdout hours"
            )
        if len(raw_values) < 2:
            raise ValueError("peak_normalized needs at least two hours")
        for i, v in enumerate(raw_values):
            _nonnegative(f"{name}.raw_values[{i}]", v)

        if external_peak is not None:
            peak = _positive(f"{name}.external_peak", external_peak)
            split_used: float | None = None
            source_tag = f"{source}::peak_normalized(external_peak={peak:g})"
        else:
            split = _finite(f"{name}.split_fraction", split_fraction)
            if not 0.0 < split < 1.0:
                raise ValueError("split_fraction must lie strictly in (0, 1)")
            split_index = _split_index(len(raw_values), split)
            if split_index < 1:
                raise ValueError(
                    "split_fraction leaves an empty training segment; the peak "
                    "cannot be estimated without a holdout hour"
                )
            train_peak = max(raw_values[:split_index])
            if train_peak <= 0.0:
                raise ValueError(
                    "peak_normalized requires a positive training-segment peak"
                )
            peak = train_peak
            split_used = split
            source_tag = (
                f"{source}::peak_normalized("
                f"train_peak={peak:g},split_fraction={split:g})"
            )

        return cls(
            name=name,
            source=source_tag,
            values=tuple(v / peak for v in raw_values),
            normalization_peak=peak,
            normalization_split_fraction=split_used,
        )


@dataclass(frozen=True)
class TraceScenarioConfig:
    """Frozen configuration for one generated (training, holdout) draw.

    ``grid_stress_scale_mw`` / ``green_call_scale_mw`` are the synthetic scales
    that turn a normalized window mean into a derived MW demand. ``window_hours``
    is the contiguous block length. ``n_train`` / ``n_holdout`` are the number of
    windows drawn from the early / late segment. ``seed`` fixes the draw.
    """

    grid_stress_shape: TraceShape
    green_workload_shape: TraceShape
    grid_stress_scale_mw: float
    green_call_scale_mw: float
    connected_demand_mw: float
    window_hours: int
    n_train: int
    n_holdout: int
    seed: int
    parameter_status: str
    split_fraction: float = 0.5


@dataclass(frozen=True)
class GeneratedScenarioSet:
    """Result of one draw: training + holdout scenarios and full provenance."""

    training_scenarios: tuple[EconomicScenario, ...]
    holdout_scenarios: tuple[EconomicScenario, ...]
    parameter_status: str
    provenance: dict = field(default_factory=dict)


def _validate_config(cfg: TraceScenarioConfig) -> None:
    if not cfg.parameter_status:
        raise ValueError("parameter_status must be explicit")
    _positive("grid_stress_scale_mw", cfg.grid_stress_scale_mw)
    _positive("green_call_scale_mw", cfg.green_call_scale_mw)
    _nonnegative("connected_demand_mw", cfg.connected_demand_mw)
    if cfg.window_hours < 1:
        raise ValueError("window_hours must be a positive integer")
    if cfg.n_train < 1 or cfg.n_holdout < 1:
        raise ValueError("n_train and n_holdout must be positive integers")
    split = _finite("split_fraction", cfg.split_fraction)
    if not 0.0 < split < 1.0:
        raise ValueError("split_fraction must lie strictly in (0, 1)")
    # No-leak guard: if a shape was peak-normalized from a *training segment*
    # (``normalization_split_fraction`` set), that segment must have been cut at
    # the same fraction this draw samples on. Otherwise the divisor could have
    # been estimated over hours that fall in this draw's holdout segment, which
    # would leak the holdout into every training MW through the shared peak.
    _assert_normalization_split_matches("grid_stress_shape", cfg.grid_stress_shape, split)
    _assert_normalization_split_matches(
        "green_workload_shape", cfg.green_workload_shape, split
    )


def _assert_normalization_split_matches(
    field_name: str, shape: TraceShape, split: float
) -> None:
    shape_split = shape.normalization_split_fraction
    if shape_split is None:
        # Either supplied already normalized, or normalized by a pre-frozen
        # external constant -- neither carries a holdout dependency.
        return
    if not _isclose(shape_split, split):
        raise ValueError(
            f"{field_name} ({shape.name}) was peak-normalized on a training "
            f"segment cut at split_fraction={shape_split:g}, but the draw samples "
            f"at split_fraction={split:g}; the normalization peak could see "
            "holdout hours. Re-normalize with the draw's split_fraction or use a "
            "pre-frozen external_peak"
        )


def _isclose(a: float, b: float) -> bool:
    return abs(a - b) <= 1.0e-12 + 1.0e-9 * abs(b)


def _split_index(length: int, split_fraction: float) -> int:
    # Integer split point of a length-``length`` series.
    return int(round(length * split_fraction))


def _draw_windows(
    rng: np.random.Generator,
    *,
    low: int,
    high: int,
    window_hours: int,
    n_windows: int,
    label: str,
) -> list[tuple[int, int]]:
    """Draw ``n_windows`` contiguous [start, end) blocks whose start lies in
    ``[low, high - window_hours]`` so the whole block stays inside ``[low, high)``.

    The block is fully contained in one segment, which is what keeps training
    and holdout windows on disjoint source hours (out-of-sample by construction).
    """

    last_start = high - window_hours
    if last_start < low:
        raise ValueError(
            f"{label} segment [{low}, {high}) is too short for window_hours="
            f"{window_hours}; shorten the window or lengthen the trace"
        )
    # ``integers`` is inclusive of ``low`` and exclusive of ``high`` argument,
    # so pass ``last_start + 1`` to allow the last valid start.
    starts = rng.integers(low=low, high=last_start + 1, size=n_windows)
    return [(int(start), int(start) + window_hours) for start in starts]


def _window_mean(values: tuple[float, ...], start: int, end: int) -> float:
    return sum(values[start:end]) / (end - start)


def _build_scenarios(
    *,
    prefix: str,
    grid_windows: list[tuple[int, int]],
    green_windows: list[tuple[int, int]],
    cfg: TraceScenarioConfig,
) -> tuple[EconomicScenario, ...]:
    grid_values = cfg.grid_stress_shape.values
    green_values = cfg.green_workload_shape.values
    n = len(grid_windows)
    probability = 1.0 / n
    scenarios: list[EconomicScenario] = []
    for i, (gw, ww) in enumerate(zip(grid_windows, green_windows)):
        grid_need = cfg.grid_stress_scale_mw * _window_mean(grid_values, gw[0], gw[1])
        green_call = cfg.green_call_scale_mw * _window_mean(green_values, ww[0], ww[1])
        scenarios.append(
            EconomicScenario(
                name=f"{prefix}_{i:03d}",
                probability=probability,
                grid_need_mw=grid_need,
                green_call_mw=green_call,
                connected_demand_mw=cfg.connected_demand_mw,
                hours=float(cfg.window_hours),
            )
        )
    return tuple(scenarios)


def generate_holdout_scenarios(cfg: TraceScenarioConfig) -> GeneratedScenarioSet:
    """Generate reproducible training + holdout scenarios from real trace shapes.

    Each trace is split once in time; training windows are block-sampled from the
    early segment and holdout windows from the late segment, so no source hour is
    shared. All MW are derived from the frozen scale and the actual window mean;
    the draw is determined by ``cfg.seed``.
    """

    _validate_config(cfg)

    grid = cfg.grid_stress_shape
    green = cfg.green_workload_shape
    grid_split = _split_index(len(grid.values), cfg.split_fraction)
    green_split = _split_index(len(green.values), cfg.split_fraction)

    rng = np.random.default_rng(cfg.seed)

    # Draw train windows from the early segments, holdout from the late segments.
    grid_train = _draw_windows(
        rng, low=0, high=grid_split, window_hours=cfg.window_hours,
        n_windows=cfg.n_train, label="grid train",
    )
    green_train = _draw_windows(
        rng, low=0, high=green_split, window_hours=cfg.window_hours,
        n_windows=cfg.n_train, label="green train",
    )
    grid_holdout = _draw_windows(
        rng, low=grid_split, high=len(grid.values), window_hours=cfg.window_hours,
        n_windows=cfg.n_holdout, label="grid holdout",
    )
    green_holdout = _draw_windows(
        rng, low=green_split, high=len(green.values), window_hours=cfg.window_hours,
        n_windows=cfg.n_holdout, label="green holdout",
    )

    training = _build_scenarios(
        prefix="train", grid_windows=grid_train, green_windows=green_train, cfg=cfg
    )
    holdout = _build_scenarios(
        prefix="holdout", grid_windows=grid_holdout, green_windows=green_holdout, cfg=cfg
    )

    provenance = {
        "seed": cfg.seed,
        "window_hours": cfg.window_hours,
        "split_fraction": cfg.split_fraction,
        "split_index": {"grid": grid_split, "green": green_split},
        "sources": {"grid": grid.source, "green": green.source},
        # The normalization divisor and the split it was estimated on, so a
        # reviewer can confirm no training MW depends on a holdout hour. ``None``
        # peak means the shape arrived already normalized; ``None`` split means
        # a pre-frozen external constant with no holdout dependency.
        "normalization": {
            "grid": {
                "peak": grid.normalization_peak,
                "split_fraction": grid.normalization_split_fraction,
            },
            "green": {
                "peak": green.normalization_peak,
                "split_fraction": green.normalization_split_fraction,
            },
        },
        "scales_mw": {
            "grid_stress": cfg.grid_stress_scale_mw,
            "green_call": cfg.green_call_scale_mw,
        },
        "windows": {
            "train": {
                "grid": [{"start": s, "end": e} for s, e in grid_train],
                "green": [{"start": s, "end": e} for s, e in green_train],
            },
            "holdout": {
                "grid": [{"start": s, "end": e} for s, e in grid_holdout],
                "green": [{"start": s, "end": e} for s, e in green_holdout],
            },
        },
    }

    # The output status always carries the module honesty tag (MW derived,
    # probabilities are sampling weights, not empirical outage) *and* the
    # caller's own status, so neither can be dropped downstream.
    combined_status = f"{TRACE_SCENARIO_PARAMETER_STATUS}::{cfg.parameter_status}"

    return GeneratedScenarioSet(
        training_scenarios=training,
        holdout_scenarios=holdout,
        parameter_status=combined_status,
        provenance=provenance,
    )


def _read_csv_column(path: Path, column: str) -> tuple[float, ...]:
    """Read one numeric column from a (possibly gzipped) CSV in file order.

    Rows are read in file order, which for these traces is chronological
    (relative-hour ordering), so the block-bootstrap autocorrelation is real.
    """

    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, mode="rt", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or column not in reader.fieldnames:
            raise ValueError(f"column {column!r} not found in {path}")
        values: list[float] = []
        for row in reader:
            raw = row[column]
            if raw is None or raw == "":
                raise ValueError(f"empty value for column {column!r} in {path}")
            values.append(float(raw))
    return tuple(values)


# Columns known to be *pre-normalized against a full-window (future-inclusive)
# peak*. Loading one as a shape re-introduces exactly the holdout leak that
# ``TraceShape.peak_normalized`` refuses (agent.md section 4/8; Google 2019 data
# card ``normalization_uses_future_window_peak``). ``load_trace_shape_from_csv``
# rejects them fail-closed and directs the caller to the raw column plus a
# split-aware re-normalization.
_FULL_WINDOW_PRENORMALIZED_COLUMNS = {
    "peak_normalized_unweighted_mean": "measured_power_util_unweighted_mean",
}


def load_trace_shape_from_csv(
    path: str | Path, *, column: str, name: str, source: str | None = None
) -> TraceShape:
    """Read one *already-normalized* shape column from a (possibly gzipped) CSV.

    The value is used *as a shape only*; the caller supplies the frozen MW scale.
    Use this only for a column that is already a leak-free 0-1 shape. A column
    known to be normalized against a full-window (future-inclusive) peak is
    rejected fail-closed, because using it would leak the holdout segment into
    every training scenario through the shared divisor -- the exact defect the
    Google 2019 data card forbids. Load the raw column with
    ``load_peak_normalized_shape_from_csv`` instead, which re-normalizes with a
    training-only (or pre-frozen external) peak.
    """

    path = Path(path)
    if column in _FULL_WINDOW_PRENORMALIZED_COLUMNS:
        raw_column = _FULL_WINDOW_PRENORMALIZED_COLUMNS[column]
        raise ValueError(
            f"column {column!r} is pre-normalized against a full-window "
            "(future-inclusive) peak; loading it as a shape would leak the "
            "holdout segment into training scenarios. Use "
            "load_peak_normalized_shape_from_csv(path, column="
            f"{raw_column!r}, split_fraction=...) or pass an external_peak"
        )
    return TraceShape(
        name=name,
        source=source or f"{path.name}::{column}",
        values=_read_csv_column(path, column),
    )


def load_peak_normalized_shape_from_csv(
    path: str | Path,
    *,
    column: str,
    name: str,
    split_fraction: float | None = None,
    external_peak: float | None = None,
    source: str | None = None,
) -> TraceShape:
    """Read a *raw* (unbounded) column and peak-normalize it leak-free.

    This is the leak-free way to turn a raw trace column (e.g. Google
    ``measured_power_util_unweighted_mean`` or Alibaba
    ``requested_gpu_equivalents``) into a 0-1 shape: the divisor is either the
    training-segment peak (``split_fraction``) or a pre-frozen constant
    (``external_peak``), never the full-window peak. See
    ``TraceShape.peak_normalized`` for the argument contract; exactly one of the
    two divisor modes must be given. The ``split_fraction`` used here must match
    the ``split_fraction`` of the draw that consumes the shape, or the generator
    rejects it fail-closed.
    """

    path = Path(path)
    return TraceShape.peak_normalized(
        name=name,
        source=source or f"{path.name}::{column}",
        raw_values=_read_csv_column(path, column),
        split_fraction=split_fraction,
        external_peak=external_peak,
    )
