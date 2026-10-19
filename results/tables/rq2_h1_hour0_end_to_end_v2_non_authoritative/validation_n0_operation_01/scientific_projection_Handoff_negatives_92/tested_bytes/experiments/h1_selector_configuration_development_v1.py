"""Pure Rref/A run declarations; no executable manifest or resource admission."""
from dataclasses import asdict, dataclass
from fractions import Fraction
import math
from pathlib import Path

from experiments import h1_selector_raw_science_inspect_development_v1 as inspector
from src.rq2_joint_deliverability_boundary_v1 import normal_task_process as process

selection = inspector.bridge.selector
io = inspector.io
SCHEMA = 'h1_selector_configuration_development_v1'


def implementation_identity():
    if SCHEMA != 'h1_selector_configuration_development_v1':
        raise ValueError('selector configuration schema changed')
    return io.digest(io.encode([SCHEMA, io.digest(Path(__file__).read_bytes()),
        inspector.implementation_identity(), io.digest(Path(process.__file__).read_bytes())]))


@dataclass(frozen=True)
class SelectorRunConfiguration:
    network_sha256: str
    generation_uids: tuple
    reference_selector: selection.reference.ReferenceSelectorSpec
    actual_selector: selection.actual.ActualDispatchSpec
    specification: selection.native.capture.Rq2SolverSpec
    limits: selection.ReplayLimits
    reference_job_budget: process.TaskProcessBudget
    actual_job_budget: process.TaskProcessBudget
    reference_non_solver_seconds: float
    actual_non_solver_seconds: float

    def __post_init__(self):
        io.pin(self.network_sha256)
        uids = self.generation_uids
        if (type(uids) is not tuple or not uids
                or any(type(uid) is not str or not uid for uid in uids)
                or uids != tuple(sorted(set(uids)))):
            raise ValueError('complete sorted unique generation UID declaration required')
        if (type(self.specification) is not selection.native.capture.Rq2SolverSpec
                or self.specification.name != 'gurobi'):
            raise ValueError('exact Gurobi selector specification required')
        # Match the actual capture adapter, not merely the generic replay API.
        inspector.bridge.capture.old.provenance.adapter.validate_spec(self.specification)
        for role, lane, selector in (
                ('reference', selection.RREF, self.reference_selector),
                ('actual', selection.physical.Lane('A', 'joint_correct_shared'), self.actual_selector)):
            count = len(uids) + (2 if role == 'reference' else 1)
            selection._configuration(lane, selector, self.specification, self.limits, count)
            if count * self.limits.max_record_bytes > self.limits.max_total_bytes:
                raise ValueError('complete selector record envelope exceeds total byte declaration')
            budget = getattr(self, role + '_job_budget')
            if type(budget) is not process.TaskProcessBudget:
                raise ValueError('exact selector Job budget required')
            budget.__post_init__()
            allowance = getattr(self, role + '_non_solver_seconds')
            if (type(allowance) not in (int, float) or not math.isfinite(allowance)
                    or allowance <= 0):
                raise ValueError('explicit positive non-solver allowance required')
            # Exact arithmetic over the declared decimal forms, not measured time.
            required = count * Fraction(str(self.specification.time_limit_seconds)) + Fraction(str(allowance))
            if required > Fraction(str(budget.max_elapsed_seconds)):
                raise ValueError('full selector time declaration exceeds Job elapsed budget')

    @property
    def stage_orders(self):
        self.__post_init__()
        generation = tuple('generation:' + uid for uid in self.generation_uids)
        return dict(reference=('grid_request', 'l1_normal_deviation', *generation),
                    actual=('l1_normal_deviation', *generation))

    def validate_normal(self, network_sha256, stage_order):
        """Match declarations only; the enclosing owner validates N's order first."""
        self.__post_init__()
        if (self.network_sha256 != network_sha256
                or self.generation_uids != tuple(uid for kind, uid in stage_order if kind == 'generation')):
            raise ValueError('N and selector network or complete UID declarations differ')

    def binding(self):
        self.__post_init__()
        return dict(schema=SCHEMA, configuration=asdict(self), stage_orders=self.stage_orders,
            implementation=implementation_identity(), configuration_declared=True,
            network_inventory_verified=False, producer_archive_bound_proven=False,
            non_solver_allowance_verified=False, host_resources_verified=False,
            executable_manifest=False, owner_consumption_authorized=False,
            resource_admission=False, formal_execution_ready=False,
            formal_result=False, native_execution_authorized=False)
