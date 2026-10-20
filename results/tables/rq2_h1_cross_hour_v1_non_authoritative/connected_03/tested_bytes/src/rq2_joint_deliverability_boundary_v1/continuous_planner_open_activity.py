"""Build-only open-activity outer relaxation for offline prefix capacity bounds.

No solver is invoked and no assignment is a capacity certificate. Known due
hours impose hard completion after that hour's recovery; terminal debt is open.
Continuous recovery and the closed activity boundary are explicit relaxations.
This version has distinct input types and identities; it is not a solver adapter.
"""
from dataclasses import asdict, dataclass
from fractions import Fraction as Q
import hashlib
import json

from pyomo.environ import (
    Binary, ConcreteModel, ConstraintList, Expression, NonNegativeReals, Objective, Set, Var, minimize,
)

from .boundary import SERVICE_TOLERANCE
from .capacity_policy import _scalar
from .continuous_planner import ContinuousPlanningScenario, _requests
from .four_arm_replay import NETWORK, CFE, JOINT, B6, _effective_call

GRID_EXCESS = 'sealed_v4_grid_excess_cfe_exact'
REQUEST_BOUNDED = 'request_bounded_exact_fulfillment'
OFFLINE = 'offline_full_prefix_recourse'
SCOPE = 'open_activity_prefix_capacity_relaxation_v1'
ACTIVITY_RELAXATION = 'open_activity_boundary_outer_relaxation'
RECOVERY_RELAXATION = 'continuous_nonnegative_recovery_relaxation'
TEMPORAL_RULE = 'exact_fraction_floor_duration_ceil_rest'


@dataclass(frozen=True)
class OpenActivityPlanningInputs:
    scenarios: tuple[ContinuousPlanningScenario, ...]
    service_action_mode: str
    decision_information_mode: str
    accounting_period_id: str
    period_mode: str
    initialization_mode: str
    terminal_mode: str
    maximum_capacity: float
    minimum_event_power: float
    response_time_hours: float
    curtailment_ramp_per_hour: float
    maximum_recovery_power: float
    recovery_efficiency: float
    maximum_event_duration_hours: float
    maximum_event_count: int
    minimum_recovery_hours: float
    normalized_energy_budget: float
    normalized_debt_limit: float
    time_step_hours: float = 1.
    planner_scope: str = SCOPE
    evidence_class: str = 'mechanism_assumption'
    recovery_representation: str = RECOVERY_RELAXATION
    activity_representation: str = ACTIVITY_RELAXATION

    def __post_init__(self):
        if self.service_action_mode not in (GRID_EXCESS, REQUEST_BOUNDED):
            raise ValueError('explicit implemented service action mode required')
        if self.decision_information_mode != OFFLINE:
            raise ValueError('only offline full-prefix recourse is implemented; no causal certificate')
        if (self.period_mode != 'single_nonrolling' or self.initialization_mode != 'canonical_zero_period_start'
            or self.terminal_mode != 'open_carry' or self.planner_scope != SCOPE
            or self.evidence_class != 'mechanism_assumption'
            or self.recovery_representation != RECOVERY_RELAXATION
            or self.activity_representation != ACTIVITY_RELAXATION):
            raise ValueError('explicit zero-origin single-period open-prefix draft contract required')
        if type(self.accounting_period_id) is not str or not self.accounting_period_id:
            raise ValueError('explicit accounting period required')
        if type(self.scenarios) is not tuple or not self.scenarios or any(
            not isinstance(s, ContinuousPlanningScenario) for s in self.scenarios):
            raise ValueError('nonempty immutable typed scenarios required')
        if len({s.name for s in self.scenarios}) != len(self.scenarios):
            raise ValueError('scenario names must be unique')
        if len({len(s.observations) for s in self.scenarios}) != 1:
            raise ValueError('all scenarios require a common horizon')
        for name in ('maximum_capacity', 'minimum_event_power', 'response_time_hours',
                     'curtailment_ramp_per_hour', 'maximum_recovery_power', 'recovery_efficiency',
                     'maximum_event_duration_hours', 'minimum_recovery_hours',
                     'normalized_energy_budget', 'normalized_debt_limit', 'time_step_hours'):
            _scalar(getattr(self, name), name)
        if self.time_step_hours != 1. or not 0 < self.recovery_efficiency <= 1 or self.maximum_capacity > 1:
            raise ValueError('one-hour normalized capacity and valid efficiency required')
        if (self.minimum_event_power < SERVICE_TOLERANCE or self.response_time_hours <= 0
            or self.curtailment_ramp_per_hour <= 0 or self.maximum_event_duration_hours < 1):
            raise ValueError('positive response/ramp, duration >=1 and minimum event at or above activity tolerance required')
        if type(self.maximum_event_count) is not int or self.maximum_event_count < 0:
            raise ValueError('nonnegative integer event budget required')


def planner_identity(inputs, arm):
    if not isinstance(inputs, OpenActivityPlanningInputs) or arm not in (NETWORK, CFE, JOINT, B6):
        raise ValueError('typed continuous inputs and registered arm required')
    payload = {'inputs': asdict(inputs), 'arm': arm, 'service_tolerance': SERVICE_TOLERANCE,
        'deadline_rule': 'hard_completion_after_due_hour_recovery', 'cohort_unit': 'effective_work_energy',
        'temporal_step_rule': TEMPORAL_RULE}
    return SCOPE+':'+hashlib.sha256(json.dumps(payload, sort_keys=True, allow_nan=False).encode()).hexdigest()


def build_continuous_planning_model(inputs, arm):
    """Build a scenario-robust capacity MILP, with offline recourse per scenario."""
    identity = planner_identity(inputs, arm)
    scenarios = {s.name: s for s in inputs.scenarios}
    names = tuple(scenarios)
    horizon = len(inputs.scenarios[0].observations)
    tracks = ('grid', 'cfe') if arm == B6 else ('shared',)
    points = [(s, t) for s in names for t in range(horizon)]
    tracked = [(s, k, t) for s in names for k in tracks for t in range(horizon)]
    cohorts = [(s, k, b, t) for s in names for k in tracks for b in range(horizon) for t in range(b, horizon)]
    requests = {(s, t): _requests(scenarios[s].observations[t], arm, inputs.service_action_mode) for s, t in points}
    max_duration = int(Q(str(inputs.maximum_event_duration_hours))//1)
    min_rest = int(-(-Q(str(inputs.minimum_recovery_hours))//1))
    ramp = inputs.curtailment_ramp_per_hour*min(1., inputs.response_time_hours)

    model = ConcreteModel()
    model.points = Set(initialize=points, dimen=2, ordered=True)
    model.tracked_points = Set(initialize=tracked, dimen=3, ordered=True)
    model.cohort_points = Set(initialize=cohorts, dimen=4, ordered=True)
    model.capacity = Var(domain=NonNegativeReals, bounds=(0., inputs.maximum_capacity))
    model.grid_service = Var(model.points, domain=NonNegativeReals)
    model.cfe_service = Var(model.points, domain=NonNegativeReals)
    model.track_call = Var(model.tracked_points, domain=NonNegativeReals)
    model.on = Var(model.tracked_points, domain=Binary)
    model.start = Var(model.tracked_points, domain=Binary)
    model.stop = Var(model.tracked_points, domain=Binary)
    model.recovery = Var(model.tracked_points, domain=NonNegativeReals)
    model.debt = Var(model.tracked_points, domain=NonNegativeReals, bounds=(0., inputs.normalized_debt_limit))
    model.allocation = Var(model.cohort_points, domain=NonNegativeReals)
    model.remaining = Var(model.cohort_points, domain=NonNegativeReals)
    model.service_power = Expression(model.tracked_points, rule=lambda m, s, k, t:
        scenarios[s].observations[t].observation.hour.workload_occupancy-m.track_call[s, k, t]+m.recovery[s, k, t])
    model.service = ConstraintList()
    model.temporal = ConstraintList()
    model.cohort_balance = ConstraintList()
    model.deadline = ConstraintList()

    for s, t in points:
        current = scenarios[s].observations[t]
        g, c = requests[s, t]
        if arm == CFE or inputs.service_action_mode == REQUEST_BOUNDED:
            model.service.add(model.grid_service[s, t] == g)
        else:
            model.service.add(model.grid_service[s, t] >= g)
        model.service.add(model.cfe_service[s, t] == c)
        model.service.add(model.grid_service[s, t]+model.cfe_service[s, t] <= current.observation.hour.workload_occupancy)
        for k in tracks:
            q = model.track_call[s, k, t]
            call = (model.grid_service[s, t] if k == 'grid' else model.cfe_service[s, t] if k == 'cfe'
                    else model.grid_service[s, t]+model.cfe_service[s, t])
            model.service.add(q == call)
            model.service.add(q <= current.available_flexibility)
            model.service.add(q <= current.observation.limits.call_limit)

    for s in names:
        scenario = scenarios[s]
        for k in tracks:
            for t in range(horizon):
                q, on, recovery = model.track_call[s, k, t], model.on[s, k, t], model.recovery[s, k, t]
                prev_on = model.on[s, k, t-1] if t else 0
                prev_q = model.track_call[s, k, t-1] if t else 0.
                start, stop = model.start[s, k, t], model.stop[s, k, t]
                model.temporal.add(q <= model.capacity)
                model.temporal.add(q <= inputs.maximum_capacity*on)
                model.temporal.add(q >= inputs.minimum_event_power*on)
                model.temporal.add(q-prev_q <= ramp)
                model.temporal.add(start >= on-prev_on)
                model.temporal.add(start <= on)
                model.temporal.add(start <= 1-prev_on)
                model.temporal.add(stop >= prev_on-on)
                model.temporal.add(stop <= prev_on)
                model.temporal.add(stop <= 1-on)
                limits = scenario.observations[t].observation.limits
                headroom = min(inputs.maximum_recovery_power, limits.maximum_recovery_power, limits.business_recovery_headroom)
                if arm != NETWORK and k != 'grid':
                    headroom = min(headroom, limits.cfe_compatible_surplus)
                model.temporal.add(recovery <= headroom*(1-on))
                model.cohort_balance.add(sum(model.allocation[s, k, b, t] for b in range(t+1)) == inputs.recovery_efficiency*recovery)
                model.cohort_balance.add(model.debt[s, k, t] == sum(model.remaining[s, k, b, t] for b in range(t+1)))
                for b in range(t+1):
                    prior = model.track_call[s, k, b] if t == b else model.remaining[s, k, b, t-1]
                    model.cohort_balance.add(model.remaining[s, k, b, t] == prior-model.allocation[s, k, b, t])
                due = scenario.observations[t].observation.due_hour
                if due is not None:
                    due_index = due-scenario.anchor.power_source_hour-1
                    if due_index < horizon:
                        model.deadline.add(model.remaining[s, k, t, due_index] == 0.)
            for first in range(horizon-max_duration):
                model.temporal.add(sum(model.on[s, k, t] for t in range(first, first+max_duration+1)) <= max_duration)
            for stop_t in range(horizon):
                for future in range(stop_t, min(stop_t+min_rest, horizon)):
                    model.temporal.add(model.on[s, k, future]+model.stop[s, k, stop_t] <= 1)
            model.temporal.add(sum(model.start[s, k, t] for t in range(horizon)) <= inputs.maximum_event_count)
            model.temporal.add(sum(model.track_call[s, k, t] for t in range(horizon)) <= inputs.normalized_energy_budget)

    model.minimum_capacity = Objective(expr=model.capacity, sense=minimize)
    model._continuous_inputs = inputs
    model._continuous_arm = arm
    model._continuous_planner_id = identity
    model._continuous_tracks = tracks
    model._continuous_evidence = {
        'status': 'DRAFT_NONAUTHORITATIVE', 'planner_scope': SCOPE,
        'decision_information_mode': OFFLINE, 'known_deadline_rule': 'hard_after_due_hour_recovery',
        'recovery_representation': inputs.recovery_representation, 'relaxed_prefix_capacity_interval': None,
        'temporal_step_rule': TEMPORAL_RULE,
        'activity_representation': inputs.activity_representation,
        'physical_activity_rule': 'zero_or_strictly_above_service_tolerance',
        'relaxed_incumbent_is_physical_witness': False,
        'prefix_capacity_interval': None, 'complete_capacity_lower_bound': None,
        'complete_capacity_upper_bound': None, 'complete_capacity_status': 'unresolved_open_terminal',
        'causal_policy_capacity_certificate': None, 'formal_result': False, 'security_certified': False,
    }
    return model
