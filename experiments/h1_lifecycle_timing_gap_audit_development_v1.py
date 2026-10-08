"""Zero-native diagnostic of timing-window coverage; no budget verdict."""
import ast
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch

from experiments import h1_durable_timing_development_v1 as journal

SCHEMA = 'h1_lifecycle_timing_gap_audit_development_v1'
SOURCES = (
    'experiments/h1_durable_timing_development_v1.py',
    'experiments/h1_native_call_timing_development_v1.py',
    'experiments/h1_timed_hour_development_v1.py',
    'experiments/h1_saved_job_development_v1.py',
    'src/rq2_joint_deliverability_boundary_v1/normal_task_process.py',
)


def source_inventory(repo):
    result = {}
    for name in SOURCES:
        raw = (Path(repo) / name).read_bytes()
        tree = ast.parse(raw)
        result[name] = dict(sha256=sha256(raw).hexdigest(), definitions=[
            dict(name=node.name, start=node.lineno, end=node.end_lineno)
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))])
    return result


def probe(root, *, terminal_io_ns, fresh_inspection_ns):
    """Inject elapsed costs around real journal I/O in an exclusive scratch root.

    This is a single-thread test seam: patching module functions is unsuitable
    for concurrent use. No solver, process creation, or production path exists.
    """
    for value in (terminal_io_ns, fresh_inspection_ns):
        if type(value) is not int or not 0 <= value <= 10**12:
            raise ValueError('bounded exact delay required')
    tick = [0]
    original_write, original_inspect = journal.io.write_metadata, journal.inspect

    def write(path, record):
        result = original_write(path, record)
        if record.get('kind') == 'terminal':
            tick[0] += terminal_io_ns
        return result

    def inspect(*args, **kwargs):
        result = original_inspect(*args, **kwargs)
        tick[0] += fresh_inspection_ns
        return result

    with patch.object(journal.io, 'write_metadata', write), patch.object(journal, 'inspect', inspect):
        ledger = journal.Journal(root, 'a' * 64, clock=lambda: tick[0])
        with ledger.span(0, 'audit'):
            tick[0] += 100
        receipt = ledger.finish()
    assert receipt['intervals_complete']
    observed = tick[0]
    recorded = receipt['recorded_window_wall_ns']
    assert recorded == 100 and observed - recorded == terminal_io_ns + fresh_inspection_ns
    return dict(schema=SCHEMA, synthetic=True, body_ns=100,
        injected_terminal_io_ns=terminal_io_ns, injected_fresh_inspection_ns=fresh_inspection_ns,
        journal_recorded_ns=recorded, enclosing_observed_ns=observed,
        omitted_tail_ns=observed-recorded, journal_binding_sha256=ledger.binding_sha256,
        journal_terminal_sha256=ledger.terminal_sha256,
        component_budget_verified=False, instrumentation_coverage_verified=False,
        resource_admission=False, formal_execution_ready=False, formal_result=False)
