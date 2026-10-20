"""Envelope-bound process budget reusing the existing Job lifecycle unchanged.

Declaration and identity do not grant long-run or formal execution authority.
"""
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path

from . import normal_task_process as legacy, execution_resource_contract as contract

SCHEMA = 'draft_envelope_bound_task_process_v1'


@dataclass(frozen=True)
class DeclaredTaskProcessBudget:
    resource_contract_identity: str
    envelope: contract.TaskEnvelope
    max_elapsed_seconds: float
    sample_interval_seconds: float
    max_process_commit_bytes: int
    max_job_commit_bytes: int
    max_quiescence_seconds: float

    def __post_init__(self):
        pin = self.resource_contract_identity
        if type(pin) is not str or len(pin) != 64 or any(c not in '0123456789abcdef' for c in pin):
            raise ValueError('original resource contract SHA256 required')
        if type(self.envelope) is not contract.TaskEnvelope:
            raise ValueError('typed complete task envelope required')
        if type(self.envelope.task_id) is not str or not self.envelope.task_id.strip():
            raise ValueError('explicit declared task ID required')
        contract._validate_positive_fields(self.envelope, ('task_id',))
        # Only reuse unchanged sample/quiet/native-memory validation. This short
        # object is never passed to a child; the actual budget remains self.
        self._validation_budget()
        if (type(self.max_elapsed_seconds) not in (int, float) or not isfinite(self.max_elapsed_seconds)
                or self.max_elapsed_seconds <= 0
                or self.max_elapsed_seconds+self.max_quiescence_seconds > self.envelope.max_wall_seconds
                or self.max_job_commit_bytes > self.envelope.max_job_commit_bytes):
            raise ValueError('declared process exceeds its task envelope')

    def _validation_budget(self):
        return legacy.TaskProcessBudget(1., self.sample_interval_seconds, self.max_process_commit_bytes,
                                        self.max_job_commit_bytes, self.max_quiescence_seconds)


def task_process_identity(argv, *, cwd, environment, budget, host_budget, expected_host_identity):
    if type(budget) is not DeclaredTaskProcessBudget:
        raise ValueError('typed envelope-bound process budget required')
    budget.__post_init__()
    command_identity = legacy.task_process_identity(argv, cwd=cwd, environment=environment,
        budget=budget._validation_budget(), host_budget=host_budget, expected_host_identity=expected_host_identity)
    payload = (SCHEMA, command_identity, asdict(budget),
        sha256(Path(__file__).read_bytes()).hexdigest(), sha256(Path(contract.__file__).read_bytes()).hexdigest())
    return sha256(json.dumps(payload, sort_keys=True, ensure_ascii=True, allow_nan=False).encode()).hexdigest()


class _DeclaredTaskChild(legacy.NormalTaskChild):
    def _identity_check(self):
        if task_process_identity(self._argv, cwd=self._cwd, environment=self._environment, budget=self._budget,
                host_budget=self._host_budget, expected_host_identity=self._host_identity) != self._identity:
            raise ValueError('declared task process implementation/request drift')


@contextmanager
def declared_task_child(argv, *, cwd, environment, budget, host_budget, expected_host_identity,
                        expected_process_identity):
    owner = object.__new__(_DeclaredTaskChild)
    try:
        owner._initialize(argv, cwd=cwd, environment=environment, budget=budget, host_budget=host_budget,
            expected_host_identity=expected_host_identity, expected_process_identity=expected_process_identity)
        yield owner
    finally:
        owner.close()
