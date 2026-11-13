"""Build D-tier cases from observed RTS-GMLC and Google data.

DRAFT_NONAUTHORITATIVE. Zero solver, zero downloads. Reads only
`data/processed/model_inputs/`, both pinned by SHA256SUMS.

What is measured and what is declared
-------------------------------------
Measured (drives the hour-to-hour dynamics):
  - `workload`: Google PowerData 2019 realized PDU power shape, rescaled to the declared
    site peak. The *shape* is observed; the MW magnitude is declared.
  - `clean_mwh`: RTS-GMLC v0.2.3 hourly renewable availability at one site bus. Both
    shape and MW are observed, used as-is with no normalization.

Declared (assumptions, not observations):
  - site peak, PUE, standby/auxiliary draw, per-hour call cap, recovery parameters;
  - the interconnection limit and the hour at which it expands.

Why the earlier version was wrong
---------------------------------
The first adapter normalized the clean budget to `alpha * reference * renew/renew_min`.
That made the lowest-renewable hour sit exactly at the CFE feasibility bound and left
every other hour with surplus, so the clean constraint never bound and the only binding
constraint was a declared constant. Five windows came out identical. Normalization here
is removed: the real MW values are used, so low-wind hours genuinely bind.

Scope
-----
Not a network study (no power flow, `security_certified=false`), not an outage study,
and not a multi-month interconnection ramp: a 24-hour window cannot carry commissioning
stages, so those are declared constants and must not be read as stage transitions.
"""
from __future__ import annotations

import csv
import gzip
from fractions import Fraction as Q
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JOINT = ROOT / "data/processed/model_inputs/rq2_joint_data_v1"
GOOGLE = ROOT / "data/processed/model_inputs/m6_google_power_shape_no_flex_250mw_v1"

# --- declared scenario constants -------------------------------------------------
SITE_PEAK_MW = 300                      # declared IT peak at full ramp
# Interconnection sized so that pre-expansion hours are *servable but tight*: the grid
# request stays inside the deferral room (no outright shortfall), while the ramp still
# forces real deferral. Recovery only becomes possible after the limit steps up.
# Calibrated against the observed window: reference load spans ~368-398 MW across
# windows, so 340 keeps grid/slope in ~23-46 against a room of 60, and 430 lifts the
# supply above every observed reference.
GRID_LIMIT_BEFORE = 340                 # MW interconnection before expansion
GRID_LIMIT_AFTER = 430                  # MW after expansion
GRID_EXPANSION_HOUR = 13
CLEAN_BUS = "122_WIND_1"                # RTS-GMLC bus with an observed wind unit
FLEXIBLE_FRACTION = Q(2, 5)
ALPHA = Q(4, 5)
PUE = Q(5, 4)
IDLE_FRACTION = Q(1, 25)
AUX_FRACTION = Q(1, 40)
CAPACITY_FRACTION = Q(1, 5)
MAX_RECOVERY_FRACTION = Q(1, 5)
DEBT_FRACTION = Q(2, 5)
ENERGY_FRACTION = Q(2, 5)
RAMP_FRACTION = Q(1, 5)
MAX_EVENTS = 2
MAX_DURATION = 1
MINIMUM_REST = 0
DEADLINE_LAG = 3


def google_shape(hours: int = 24):
    """Realized Google PDU power, rescaled to unit mean, as Fractions."""
    with (GOOGLE / "business_chronology.csv").open(encoding="utf-8") as handle:
        values = [Q(row["requested_demand_mw"])
                  for row in csv.DictReader(handle)]
    window = values[:hours]
    mean = sum(window) / len(window)
    return [v / mean for v in window]


def renewable_at_bus(bus: str, start_hour: int, hours: int):
    """Observed hourly renewable availability at one bus, used as-is."""
    out = {}
    with gzip.open(JOINT / "hourly_renewable_availability.csv.gz", "rt",
                   encoding="utf-8") as handle:
        reader = csv.reader(handle)
        next(reader)
        for row in reader:
            if row[4] != bus:
                continue
            hour = int(row[0])
            if start_hour <= hour < start_hour + hours:
                out[hour - start_hour] = out.get(hour - start_hour, Q(0)) + Q(row[6])
    missing = [i for i in range(hours) if i not in out]
    if missing:
        raise ValueError(f"renewable series missing hours {missing}")
    return [out[i] for i in range(hours)]


def site_load(hours: int):
    """Declared IT load = unit-mean observed shape scaled to the declared peak."""
    shape = google_shape(hours)
    peak = max(shape)
    return [SITE_PEAK_MW * s / peak for s in shape]


def parameters():
    from src.staged_deliverability_development_v1 import Parameters

    def scaled(fraction):
        return Q(str(round(float(fraction * SITE_PEAK_MW), 6)))

    return Parameters(
        capacity=scaled(CAPACITY_FRACTION), alpha=ALPHA, eta=Q(1), beta=Q(1),
        facility_factor=PUE, auxiliary_mw=scaled(AUX_FRACTION),
        fixed_headroom=scaled(MAX_RECOVERY_FRACTION),
        max_recovery=scaled(MAX_RECOVERY_FRACTION),
        max_debt=scaled(DEBT_FRACTION), max_call_energy=scaled(ENERGY_FRACTION),
        call_ramp=scaled(RAMP_FRACTION),
        max_events=MAX_EVENTS, max_duration=MAX_DURATION, minimum_rest=MINIMUM_REST,
    )


def build_observations(start_hour: int, hours: int = 24):
    from src.staged_deliverability_development_v1 import HourInput

    it = site_load(hours)
    clean = renewable_at_bus(CLEAN_BUS, start_hour, hours)
    idle = Q(str(round(float(IDLE_FRACTION * SITE_PEAK_MW), 6)))
    observations = []
    for i in range(hours):
        supply = GRID_LIMIT_BEFORE if i < GRID_EXPANSION_HOUR else GRID_LIMIT_AFTER
        observations.append(HourInput(
            hour=i,
            due=min(i + DEADLINE_LAG, hours - 1),
            workload=it[i],
            flexible_fraction=FLEXIBLE_FRACTION,
            compute_capacity=Q(SITE_PEAK_MW),
            idle_mw=idle,
            clean_mwh=clean[i],
            supply_mw=Q(str(supply)),
            equipment_online=("dc",),
            grid_online=i >= GRID_EXPANSION_HOUR,
        ))
    return observations, it, clean
