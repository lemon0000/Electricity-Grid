"""Owned direct-adapter capture boundary, development only.

This code can solve when invoked: its caller MUST own new explicit run authority
and hard Job/resource supervision. Tests replace the adapter with a synthetic
implementation. There is no command-line entry point, resume or retry API.
"""
import os
from dataclasses import asdict
from pathlib import Path
import threading
import struct
from types import MappingProxyType

from pyomo.solvers.plugins.solvers.gurobi_direct import GurobiDirect

from experiments import h1_raw_ingress_development_v1 as io
from experiments import h1_linear_export_guard_development_v1 as export
from experiments import h1_native_export_guard_development_v1 as inherited_guard
from experiments import h1_native_call_timing_development_v1 as timing
from src.solvers import rq2_objective_provenance_run_v1 as old
from src.rq2_joint_deliverability_boundary_v1 import normal_h1_resource_shape as no_solve

SCHEMA = 'h1_timed_native_capture_development_v1'
FLAGS = MappingProxyType(dict(collector_integrated=False, native_export_coverage=False,
    instrumentation_coverage_verified=False, observer_overhead_separated=False, component_budget_verified=False,
    producer_coverage_proven=False, resource_admission=False, formal_execution_ready=False,
    formal_result=False, native_execution_authorized=False, native_execution_authenticated=False,
    scientific_acceptance=False))
ATTRIBUTES = ('Status', 'SolCount', 'ModelSense', 'NumVars', 'NumConstrs',
              'ObjVal', 'ObjBound', 'ObjBoundC', 'Runtime', 'MIPGap')


def implementation_identity():
    return io.digest(io.encode(dict(schema=SCHEMA, adapter=old.provenance.adapter.implementation_identity(),
        old_audit=old.implementation_identity(), files={Path(m.__file__).name:
        io.digest(Path(m.__file__).read_bytes()) for m in
        (io, export, inherited_guard, inherited_guard.syntax, inherited_guard.grammar, no_solve, timing)},
        own=io.digest(Path(__file__).read_bytes()))))


def _atom(value):
    # Preserve nonfinite binary64 outputs as strings; acceptance is downstream.
    if type(value) is float:
        return dict(kind='binary64', value=value.hex(), bits=struct.pack('>d', value).hex())
    if type(value) is int:
        return dict(kind='integer', value=value)
    if type(value) is str:
        return dict(kind='string', value=value)
    raise TypeError('unsupported native attribute type')


def _read(getter):
    try:
        return dict(available=True, atom=_atom(getter()), error=None)
    except Exception as error:
        # Do not copy exception messages (which can contain external paths).
        # A failed channel is retained and never interpreted as zero. The later
        # independent view rereads channels for drift detection, not recovery.
        return dict(available=False, atom=None, error=type(error).__name__[:64])


def _capture(native, pairs, *, binding, export_sha, apply_error):
    rows = []
    for canonical, handle in pairs:
        rows.append(dict(canonical_name=canonical.name,
            attributes={name: _read(lambda name=name, handle=handle: getattr(handle, name))
                        for name in ('index', 'VarName', 'VType', 'LB', 'UB', 'X')}))
    objective = dict(constant=None, count=None, terms=[], error=None)
    try:
        expression = native.getObjective()
        count = expression.size()
        objective['count'] = _atom(count)
        if type(count) is not int or not 0 <= count <= 362:
            raise ValueError('native objective outside capture envelope')
        objective['constant'] = _read(expression.getConstant)
        for i in range(count):
            objective['terms'].append(dict(
                index=_read(lambda i=i: expression.getVar(i).index),
                coefficient=_read(lambda i=i: expression.getCoeff(i))))
    except Exception as error:
        objective['error'] = type(error).__name__[:64]
    return io.encode(dict(schema=SCHEMA, binding_sha256=binding,
        export_sha256=export_sha, apply_error=apply_error,
        attributes={name: _read(lambda name=name: getattr(native, name)) for name in ATTRIBUTES},
        variables=rows, objective=objective, values_transformed=False,
        **FLAGS))


def _complete(doc):
    """Capture completeness only; no finite/status/feasibility interpretation."""
    # Optional native diagnostic attributes can be unavailable (e.g. MIPGap).
    required = [doc['attributes'][n] for n in ('Status', 'SolCount', 'ModelSense', 'NumVars', 'NumConstrs')]
    required.extend(v['attributes'][n] for v in doc['variables']
                    for n in ('index', 'VarName', 'VType', 'LB', 'UB'))
    objective = doc['objective']
    required += [objective['constant']]
    required.extend(channel for row in objective['terms'] for channel in row.values())
    if doc['apply_error'] is not None or objective['error'] is not None:
        return False
    if any(channel is None or channel['available'] is not True for channel in required):
        return False
    count = doc['attributes']['SolCount']['atom']
    if count['kind'] != 'integer' or count['value'] < 1:
        return False
    return all(row['attributes']['X']['available'] is True for row in doc['variables'])


class StageCapture:
    """One stage, one solver owner, durable raw before Pyomo postsolve/consumer.

    Consumer receives fresh raw bytes, unloaded Pyomo results and the owned
    canonical model; it receives no solver handle. Its return is not a verdict.
    """
    def __init__(self, root, *, request_sha256, expected_structure, expected_implementation, stage_index):
        if type(stage_index) is not int or not 0 <= stage_index < 232:
            raise ValueError('bounded timed stage index required')
        for pin in (request_sha256, expected_structure, expected_implementation):
            io.pin(pin)
        if implementation_identity() != expected_implementation:
            raise ValueError('capture implementation mismatch')
        self.root = Path(root).resolve()
        self.root.mkdir(exist_ok=False)
        self.owner = (os.getpid(), threading.get_ident())
        self.guard = threading.Lock()
        self.started = self.poisoned = self.complete = False
        self.records = {}
        self.expected_structure = expected_structure
        self.expected_implementation = expected_implementation
        self.binding = dict(schema=SCHEMA, request_sha256=request_sha256, stage_index=stage_index,
            expected_structure=expected_structure, implementation=expected_implementation,
            **FLAGS)
        self.binding_sha = io.write_metadata(self.root/'binding.json', self.binding)
        self.raw = io.Ingress(self.root/'native_raw', request_sha256, stages=1)
        self.measurement = timing.Measurement(self.root/'native_timing', request_sha256, stage_index)
        self.records['native_timing/binding.json'] = self.measurement.binding_pin
        self.timing_views = {'binding.json': io.read_stable(self.measurement.root/'binding.json', io.META_CAP)}
        self.timing_receipt = None

    def _check(self):
        if self.owner != (os.getpid(), threading.get_ident()):
            raise ValueError('capture owner mismatch')
        if (implementation_identity() != self.expected_implementation
                or io.read_stable(self.root/'binding.json', io.META_CAP)[0] != io.encode(self.binding)):
            raise ValueError('capture binding/implementation changed')
        for name, pin in self.records.items():
            if io.digest(io.read_stable(self.root/name, io.META_CAP)[0]) != pin:
                raise ValueError('capture record changed: ' + name)
        if any(io.read_stable(self.measurement.root/name, io.META_CAP) != view
               for name, view in self.timing_views.items()):
            raise ValueError('fixed timing view changed')

    def run(self, builder, specification, consumer):
        if not self.guard.acquire(blocking=False):
            raise ValueError('capture already active')
        solver = None
        close_attempted = False
        try:
            self._check()
            if self.started or self.poisoned or self.complete:
                raise ValueError('capture already consumed')
            self.started = True
            old.provenance.adapter.validate_spec(specification)
            declared_options = old.audit.solver_options(specification)
            specification_sha = io.write_metadata(self.root/'specification.json',
                dict(specification=asdict(specification), options=declared_options,
                     binding_sha256=self.binding_sha))
            self.records['specification.json'] = specification_sha
            model = builder()
            if old.audit._structure(model) != self.expected_structure:
                raise ValueError('canonical model structure differs')
            before = old.audit._snapshot(model)
            solver, options = old.provenance.adapter.create_solver(specification)
            if (type(solver) is not GurobiDirect or '_apply_solver' in vars(solver)
                    or io.encode(options) != io.encode(declared_options)):
                raise ValueError('fresh exact direct adapter required')
            applied = False
            native_raw = None
            export_check = None
            recapture = None

            def intercepted():
                nonlocal applied, native_raw, export_check, recapture
                if applied:
                    raise ValueError('second apply forbidden')
                applied = True
                self._check()
                if (solver._pyomo_model is not model or solver._callback is not None
                        or solver._tee is not False or solver._keepfiles is not False
                        or io.encode(dict(solver.options)) != io.encode(declared_options)
                        or old.audit._structure(model) != self.expected_structure
                        or old.audit._snapshot(model) != before):
                    raise ValueError('direct adapter/model state changed before apply')
                native = solver._solver_model
                native.update()
                pairs = tuple(solver._pyomo_var_to_solver_var_map.items())
                def check_export():
                    return export.check(model, native_model=native,
                        variable_forward=tuple(solver._pyomo_var_to_solver_var_map.items()),
                        variable_reverse=tuple(solver._solver_var_to_pyomo_var_map.items()),
                        constraint_forward=tuple(solver._pyomo_con_to_solver_con_map.items()),
                        constraint_reverse=tuple(solver._solver_con_to_pyomo_con_map.items()))
                export_check = check_export
                checked = export_check()
                export_sha = io.write_metadata(self.root/'export.json', dict(binding_sha256=self.binding_sha,
                    specification_sha256=specification_sha,
                    model_structure=self.expected_structure, result=checked))
                self.records['export.json'] = export_sha
                self._check()
                recapture = lambda: _capture(native, pairs, binding=self.binding_sha,
                                             export_sha=export_sha, apply_error=None)
                apply_result = None
                apply_error = None

                def produce():
                    nonlocal apply_result, apply_error
                    try:
                        apply_result, self.timing_receipt = self.measurement.apply(solver)
                        if not self.measurement.closed or self.measurement.poisoned or self.measurement.owner != self.owner:
                            raise ValueError('owned timing invocation incomplete')
                        self._check()
                        timing.inspect(self.measurement.root, expected_binding_sha=self.measurement.binding_pin,
                            expected_terminal_sha=self.timing_receipt['terminal_sha256'],
                            expected_implementation=timing.implementation_identity())
                        import json
                        completed = io.read_stable(self.measurement.root/'completion.json', io.META_CAP)
                        if io.digest(completed[0]) != self.measurement.completion_pin:
                            raise ValueError('timing completion changed after owned return')
                        expected = {'intent.json': json.loads(completed[0])['intent_sha256'],
                            'completion.json': self.measurement.completion_pin,
                            'terminal.json': self.timing_receipt['terminal_sha256']}
                        for name, pin in expected.items():
                            view = io.read_stable(self.measurement.root/name, io.META_CAP)
                            if io.digest(view[0]) != pin: raise ValueError('owned timing pin differs')
                            self.timing_views[name] = view
                            self.records['native_timing/'+name] = pin
                    except BaseException as error:
                        apply_error = error
                    return _capture(native, pairs, binding=self.binding_sha, export_sha=export_sha,
                                    apply_error=None if apply_error is None else type(apply_error).__name__[:64])

                native_raw = self.raw.deliver(0, produce, lambda fresh: fresh)
                if apply_error is not None:
                    raise apply_error
                import json
                if not _complete(json.loads(native_raw)):
                    raise ValueError('native output capture incomplete; raw retained')
                return apply_result

            solver._apply_solver = intercepted
            results = solver.solve(model, load_solutions=False, options=options, tee=False)
            if not applied or native_raw is None:
                raise ValueError('direct adapter bypassed capture boundary')
            self._check()
            if old.audit._structure(model) != self.expected_structure or old.audit._snapshot(model) != before:
                raise ValueError('canonical model changed before consumer')
            export_check()
            if recapture() != native_raw:
                raise ValueError('native output changed during postsolve')
            fresh = io.read_stable(self.raw.root/'000'/'raw.bin', io.RAW_CAP)[0]
            if fresh != native_raw:
                raise ValueError('native raw changed after postsolve')
            with no_solve.solver_calls_forbidden():
                result = consumer(fresh, results, model)
            self._check()
            if old.audit._structure(model) != self.expected_structure:
                raise ValueError('canonical structure changed during consumer')
            if io.read_stable(self.raw.root/'000'/'raw.bin', io.RAW_CAP)[0] != native_raw:
                raise ValueError('native raw changed during consumer')
            close_attempted = True
            solver.close()
            self._check()
            if io.read_stable(self.raw.root/'000'/'raw.bin', io.RAW_CAP)[0] != native_raw:
                raise ValueError('native raw changed during close')
            terminal = self.raw.finish()
            io.write_metadata(self.root/'complete.json', dict(schema=SCHEMA,
                binding_sha256=self.binding_sha, raw_sha256=io.digest(native_raw),
                timing_binding_sha256=self.measurement.binding_pin,
                timing_terminal_sha256=self.timing_receipt['terminal_sha256'],
                raw_terminal_sha256=io.digest(io.read_stable(self.raw.root/'terminal.json', io.META_CAP)[0]),
                callback_sequence_complete=terminal['callback_sequence_complete'],
                **FLAGS))
            self.complete = True
            return result
        except BaseException:
            self.poisoned = True
            if self.raw.next_stage == 1 and not self.raw.closed and not self.raw.poisoned:
                self.raw.abort()
            raise
        finally:
            try:
                if solver is not None and not close_attempted:
                    close_attempted = True
                    solver.close()
            finally:
                self.guard.release()
