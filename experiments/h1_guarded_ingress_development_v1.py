"""Saved-capture stage adapter with retained raw, fixed guard and durable timing.

This is not a native worker or a scientific collector. The caller must supply
the actual stage model and a full scientific consumer. Callback success alone
does not establish any scientific or execution gate.
"""
from experiments import h1_durable_timing_development_v1 as timing
from experiments import h1_native_export_guard_development_v1 as guard
from experiments import h1_raw_ingress_development_v1 as ingress
from pathlib import Path


def implementation_pins():
    modules = (__file__, guard.__file__, guard.grammar.__file__, guard.syntax.__file__,
               ingress.__file__, timing.__file__, timing.prior_timing.__file__)
    return {Path(p).name: ingress.digest(ingress.read_stable(Path(p), 1024*1024)[0])
            for p in modules}


class SavedStages:
    def __init__(self, root, request_sha256, *, stages):
        self.root = Path(root).resolve()
        self.root.mkdir(exist_ok=False)
        self.poisoned = self.closed = False
        self.timing = timing.Journal(self.root/'timing', request_sha256)
        self.raw = ingress.Ingress(self.root/'raw', request_sha256, stages=stages)
        self.pins = implementation_pins()
        self.binding = dict(request_sha256=request_sha256, stages=stages,
                            implementation_pins=self.pins)
        self.binding_sha256 = ingress.write_metadata(self.root/'adapter_binding.json', self.binding)

    def _check(self):
        if (implementation_pins() != self.pins
                or ingress.digest(ingress.read_stable(self.root/'adapter_binding.json', 2048)[0])
                    != self.binding_sha256):
            raise ValueError('adapter implementation/binding drift')

    def deliver(self, index, raw, model, scientific_consumer):
        if self.poisoned or self.closed:
            raise ValueError('closed or poisoned saved stage adapter')
        try:
            self._check()
            with self.timing.span(index, 'capture'):
                def consumer(fresh):
                    with self.timing.span(index, 'audit'):
                        guard.saved_report(fresh, model)
                        result = scientific_consumer(fresh)
                        self._check()
                        return result
                return self.raw.deliver(index, lambda: raw, consumer)
        except BaseException:
            self.poisoned = True
            raise

    def finish(self):
        if self.poisoned or self.closed:
            raise ValueError('closed or poisoned saved stage adapter')
        try:
            self._check()
            with self.timing.span(-1, 'terminal'):
                raw_result = self.raw.finish()
            timing_result = self.timing.finish()
            self.closed = True
            return dict(schema='h1_guarded_ingress_development_v1',
                raw=raw_result, timing=timing_result,
                collector_integrated=False, native_export_coverage=False,
                guard_execution_durably_attested=False,
                scientific_acceptance=False, resource_admission=False,
                formal_execution_ready=False, formal_result=False)
        except BaseException:
            self.poisoned = True
            raise


def storage_bound(stages):
    """Logical byte/file ceiling for this adapter only, excluding directory cost.

    Raw cap is the retained 16 MiB envelope, even when the fixed guard rejects
    its narrower grammar. Three spans per stage is conservative (actual two),
    plus fresh-replay and terminal spans. Partial writes cannot add a second attempt.
    """
    if type(stages) is not int or not 1 <= stages <= 232:
        raise ValueError('bounded stages required')
    raw_files = 4*stages+3
    raw_bytes = stages*ingress.RAW_CAP+(3*stages+3)*ingress.META_CAP
    timing_files = 2*(3*stages+2)+2
    return dict(logical_bytes=raw_bytes+(timing_files+1)*timing.EVENT_CAP,
        files=raw_files+timing_files+1, directories=stages+3,
        filesystem_allocation_bound_proven=False, resource_admission=False)


class SavedHour:
    """Sequential scientific stage replay, with immutable raw retained first.

    Partial hour has no projection and cannot resume. Full fresh replay remains
    necessary before using any resulting projection as a carry parent.
    """
    def __init__(self, root, packet, specification, limits):
        from src.rq2_joint_deliverability_boundary_v1 import normal_h1_hour_replay_v3 as replay
        self.replay = replay
        self.packet, self.specification, self.limits = packet, specification, limits
        self.key = replay.request_key(packet, specification, limits)
        self.replay_pin = replay.implementation_identity()
        self.order = replay.native.model_api.stage_order(packet.inputs)
        self.stages = SavedStages(root, self.key, stages=len(self.order))
        self.locks = ()
        self.poisoned = False

    def deliver(self, raw):
        if self.poisoned:
            raise ValueError('poisoned saved hour')
        try:
            with self.replay.guard.solver_calls_forbidden():
                if (self.replay.request_key(self.packet, self.specification, self.limits) != self.key
                        or self.replay.implementation_identity() != self.replay_pin):
                    raise ValueError('scientific request/implementation drift')
                index = len(self.locks)
                with self.stages.timing.span(index, 'build'):
                    api = self.replay.native.model_api
                    request = api.H1StageRequest(self.packet.inputs, self.locks)
                    model = api.build_h1_stage_model(request, expected_identity=api.h1_stage_identity(request))
                def scientific(fresh):
                    return self.replay._audit_stage(self.packet, self.specification,
                                                   self.limits, index, self.locks, fresh)
                result = self.stages.deliver(index, raw, model, scientific)
                if (self.replay.request_key(self.packet, self.specification, self.limits) != self.key
                        or self.replay.implementation_identity() != self.replay_pin):
                    raise ValueError('scientific request/implementation drift after audit')
                self.locks = (*self.locks, result['lock'])
                return result
        except BaseException:
            self.poisoned = True
            self.stages.poisoned = True
            raise

    def finish(self):
        if self.poisoned:
            raise ValueError('poisoned saved hour')
        try:
            if len(self.locks) != len(self.order):
                raise ValueError('incomplete scientific stage sequence')
            if self.replay.implementation_identity() != self.replay_pin:
                raise ValueError('scientific implementation drift')
            with self.stages.timing.span(-1, 'fresh_reopen'):
                def reports():
                    for index in range(len(self.order)):
                        yield ingress.read_stable(self.stages.raw.root/f'{index:03d}'/'raw.bin',
                                                  ingress.RAW_CAP)[0]
                projection = self.replay.replay_stream(self.packet, self.specification,
                    self.limits, reports(), expected_key=self.key)
                if projection.canonical_locks != self.locks:
                    raise ValueError('fresh scientific replay differs')
            evidence = self.stages.finish()
            return projection, evidence
        except BaseException:
            self.poisoned = True
            self.stages.poisoned = True
            raise
