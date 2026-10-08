"""Scheme A: a common, current-hour clean allowance fixed before any action.

Exact arithmetic on declared/projected inputs. No procurement or causal
certificate is inferred; no action, arm, capacity or future input sets y.
"""
from dataclasses import asdict, dataclass
from fractions import Fraction as Q
from hashlib import sha256
import json
from pathlib import Path

from .boundary import SERVICE_TOLERANCE

RULE = 'baseline_proportional_preaction_clean_allowance_v1'


def activity_threshold():
    if type(SERVICE_TOLERANCE) is not float or SERVICE_TOLERANCE != 1e-6:
        raise ValueError('existing activity threshold drift')
    return Q(str(SERVICE_TOLERANCE))


def _q(value):
    if type(value) not in (str, Q):
        raise ValueError('explicit exact decimal/rational string or Fraction required')
    return Q(value)


def _hash(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


@dataclass(frozen=True)
class PreallocatedCFE:
    workload: Q
    renewable_share: Q
    target: Q
    allowance: Q
    raw_request: Q
    effective_request: Q
    compatible_surplus: Q
    rule: str = RULE

    def __post_init__(self):
        numbers = (self.workload, self.renewable_share, self.target, self.allowance,
                   self.raw_request, self.effective_request, self.compatible_surplus)
        if any(type(x) is not Q for x in numbers):
            raise ValueError('exact Fraction allocation fields required')
        w, R, alpha = self.workload, self.renewable_share, self.target
        if self.rule != RULE or not (0 <= w <= 1 and 0 <= R <= 1 and 0 < alpha <= 1):
            raise ValueError('mapped workload, renewable share and target outside declared domain')
        q, s = max(Q(0), w-R*w/alpha), max(Q(0), R*w/alpha-w)
        effective = q if q > activity_threshold() else Q(0)
        if (self.allowance, self.raw_request, self.effective_request, self.compatible_surplus) != (R*w, q, effective, s):
            raise ValueError('allocation, request and recovery surplus must share the same pre-action allowance')

    def record(self):
        return {k: str(v) if type(v) is Q else v for k, v in asdict(self).items()}

    @property
    def identity(self):
        return _hash(dict(allocation=self.record(), implementation_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
            service_tolerance=str(SERVICE_TOLERANCE)))


def allocate(workload, source_cfe_at_alpha_one, target):
    w, source, alpha = map(_q, (workload, source_cfe_at_alpha_one, target))
    if not (0 <= w <= 1 and 0 <= source <= 1 and 0 < alpha <= 1):
        raise ValueError('mapped workload, source CFE and target outside declared domain')
    R = 1-source
    q, s = max(Q(0), w-R*w/alpha), max(Q(0), R*w/alpha-w)
    return PreallocatedCFE(w, R, alpha, R*w, q,
        q if q > activity_threshold() else Q(0), s)


def necessary_conditions(allocation, flexible_fraction, *, grid_request='0'):
    """Pointwise diagnostics for the existing additive service commitment only."""
    if type(allocation) is not PreallocatedCFE:
        raise ValueError('exact scheme-A allocation required')
    allocation.__post_init__()
    f, g = _q(flexible_fraction), _q(grid_request)
    if not 0 <= f <= 1 or g < 0:
        raise ValueError('valid flexibility fraction and nonnegative grid request required')
    threshold = activity_threshold()
    combined = g+allocation.raw_request
    combined_effective = combined if combined > threshold else Q(0)
    g = g if g > threshold else Q(0)
    q, available = allocation.effective_request, f*allocation.workload
    return dict(available_flexibility=str(available), request_exceeds_baseline=q > allocation.workload,
        separate_shared_activity_mismatch=g+q != combined_effective,
        network_only_conflict=g > available, cfe_only_conflict=q > available,
        joint_additive_conflict=g+q > available,
        b6_planning_track_conflict=(g > available or q > available),
        b6_shared_execution_necessary_conflict=g+q > available,
        absence_of_conflict_is_service_success=False, formal_result=False)
