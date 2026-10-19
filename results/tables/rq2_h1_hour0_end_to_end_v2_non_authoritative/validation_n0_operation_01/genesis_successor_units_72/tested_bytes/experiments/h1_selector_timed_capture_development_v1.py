"""Explicit timed capture fork with legacy scientific wire format.

The legacy implementation field identifies the wire contract only. Actual
producer identity is retained in the external sidecar. Real use requires fresh
native authorization and an enclosing owned Job. No CLI or retry entrypoint.
"""
from dataclasses import asdict
import json
import os
from pathlib import Path
import threading
import time
import types

from experiments import h1_native_raw_capture_development_v1 as legacy
from experiments import h1_native_call_timing_development_v1 as timing

io,old,export,no_solve=legacy.io,legacy.old,legacy.export,legacy.no_solve
GurobiDirect=legacy.GurobiDirect
_capture,_complete=legacy._capture,legacy._complete
SCHEMA,FLAGS=legacy.SCHEMA,legacy.FLAGS
PRODUCER_SCHEMA='h1_selector_timed_capture_development_v1'
CAP=16384
_CLOCK,_INFO=time.perf_counter_ns,time.get_clock_info
_INIT,_APPLY,_INVOKE=timing.Measurement.__init__,timing.Measurement.apply,timing.Measurement.invoke


def implementation_identity():
    return io.digest(io.encode([PRODUCER_SCHEMA,legacy.implementation_identity(),timing.implementation_identity(),
                                io.digest(Path(__file__).read_bytes())]))


def clock_profile():
    if (os.name!='nt' or time.perf_counter_ns is not _CLOCK or time.get_clock_info is not _INFO
            or not isinstance(_CLOCK,types.BuiltinFunctionType)
            or timing.Measurement.__init__ is not _INIT or _INIT.__kwdefaults__!={'clock':_CLOCK}
            or timing.Measurement.apply is not _APPLY or timing.Measurement.invoke is not _INVOKE):
        raise ValueError('fixed default QPC measurement required')
    info=_INFO('perf_counter')
    if info.implementation!='QueryPerformanceCounter()' or not info.monotonic or info.adjustable:
        raise ValueError('fixed monotonic QPC profile required')
    return dict(implementation=info.implementation,monotonic=True,adjustable=False,
                resolution_hex=info.resolution.hex(),units='integer_nanoseconds')


def root(value):
    p=Path(value)
    if not p.is_absolute() or p!=p.resolve() or not any('non_authoritative' in part for part in p.parts):
        raise ValueError('canonical absolute non-authoritative path required')
    return p


def directory(path):
    s=path.stat(follow_symlinks=False)
    if not path.is_dir() or getattr(s,'st_file_attributes',0)&1024:
        raise ValueError('plain timed directory required')
    return s.st_dev,s.st_ino


def write(path,value):
    raw=io.encode(value)
    if len(raw)>CAP:raise ValueError('timing sidecar metadata cap')
    io.write_new(path,raw)
    return io.digest(raw)


class StageCapture(legacy.StageCapture):
    """Internal producer; inherited completion is not an execution credential."""
    def __init__(self,path,*,timing_root,stage_index,stage_label,producer_implementation,
                 request_sha256,expected_structure,expected_implementation):
        path=root(path);side=root(timing_root)
        if path.exists() or side.exists():raise FileExistsError('fresh capture and timing roots required')
        if side==path.parent or path.parent in side.parents or side in path.parent.parents:
            raise ValueError('timing sidecar must be outside scientific stage')
        if type(stage_index) is not int or not 0<=stage_index<232:
            raise ValueError('bounded timed selector index required')
        if type(stage_label) is not str or not stage_label:raise ValueError('explicit selector label required')
        io.pin(producer_implementation)
        if expected_implementation!=implementation_identity():raise ValueError('timed producer implementation differs')
        profile=clock_profile();timing.validate_vendor()
        self._timed_implementation=expected_implementation
        self.side=side;self.stage_index=stage_index;self.stage_label=stage_label
        super().__init__(path,request_sha256=request_sha256,expected_structure=expected_structure,
                         expected_implementation=legacy.implementation_identity())
        self._original_guard=self.guard
        side.mkdir(exist_ok=False);self._side_identity=directory(side)
        self.measurement=timing.Measurement(side/'native',request_sha256,stage_index)
        self._original_measurement=self.measurement
        self._measurement_guard=self.measurement.guard
        self._binding=dict(schema=PRODUCER_SCHEMA,new_producer_implementation=producer_implementation,
            capture_implementation=expected_implementation,legacy_wire_implementation=self.expected_implementation,
            scientific_root=str(path.parent),scientific_directory_identity=directory(path.parent),
            timing_root=str(side),request_sha256=request_sha256,stage_index=stage_index,stage_label=stage_label,
            capture_binding_sha256=self.binding_sha,measurement_binding_sha256=self.measurement.binding_pin,
            pid=self.owner[0],thread_id=self.owner[1],clock=profile,
            legacy_producer_execution_authenticated=False,old_owned_return_observed=False,**FLAGS)
        self.side_binding_pin=write(side/'binding.json',self._binding)
        self._side_binding=io.read_stable(side/'binding.json',CAP)
        self._timing_views={'binding.json':io.read_stable(self.measurement.root/'binding.json',io.META_CAP)}
        self.timing_receipt=None
        self._configuration=(self.root,self.side,self.stage_index,self.stage_label,self.expected_implementation,
            self.expected_structure,self.binding_sha,self.side_binding_pin,self._side_binding)

    def _check(self):
        super()._check()
        if (self.guard is not self._original_guard or self.measurement is not self._original_measurement
                or self.measurement.guard is not self._measurement_guard or self.measurement.clock is not _CLOCK
                or self.measurement.owner!=self.owner or self.measurement.root!=self.side/'native'
                or directory(self.side)!=self._side_identity
                or directory(self.root.parent)!=tuple(self._binding['scientific_directory_identity'])
                or self._timed_implementation!=implementation_identity()
                or (self.root,self.side,self.stage_index,self.stage_label,self.expected_implementation,
                    self.expected_structure,self.binding_sha,self.side_binding_pin,self._side_binding)!=self._configuration
                or clock_profile()!=self._binding['clock']
                or io.read_stable(self.side/'binding.json',CAP)!=self._side_binding
                or io.encode(self._binding)!=self._side_binding[0]
                or {p.name for p in self.side.iterdir()}!={'binding.json','native'}
                or any(io.read_stable(self.measurement.root/n,io.META_CAP)!=v for n,v in self._timing_views.items())):
            raise ValueError('timed capture owner, clock or sidecar changed')

    def _timed_apply(self,solver):
        self._check()
        result,receipt=self.measurement.apply(solver)
        if not self.measurement.closed or self.measurement.poisoned:
            raise ValueError('owned native measurement incomplete')
        timing.inspect(self.measurement.root,expected_binding_sha=self.measurement.binding_pin,
            expected_terminal_sha=receipt['terminal_sha256'],expected_implementation=timing.implementation_identity())
        self._timing_views={n:io.read_stable(self.measurement.root/n,io.META_CAP) for n in
                            ('binding.json','intent.json','completion.json','terminal.json')}
        if (io.digest(self._timing_views['binding.json'][0])!=self.measurement.binding_pin
                or io.digest(self._timing_views['completion.json'][0])!=self.measurement.completion_pin
                or io.digest(self._timing_views['terminal.json'][0])!=receipt['terminal_sha256']):
            raise ValueError('owned measurement pins changed')
        self.timing_receipt=receipt
        self._check()
        return result

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
            apply = solver._apply_solver
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
                        apply_result = self._timed_apply(solver)
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
