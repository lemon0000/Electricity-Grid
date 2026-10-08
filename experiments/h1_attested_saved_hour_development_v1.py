"""Saved-only scientific hour with linked guard/audit receipts and fresh replay.

Create once, fail stop, no resume. External retention of returned terminal pins
is a prerequisite, not a property inferred from files left by a failed writer.
This development archive supplies neither native nor formal-run authority.
"""
import json
import os
from pathlib import Path

from experiments import h1_guarded_ingress_development_v1 as prior

io, timing, guard = prior.ingress, prior.timing, prior.guard
SCHEMA = 'h1_attested_saved_hour_development_v1'
PROJECTION_CAP = 256 * 1024
MAPPING_CAP = 256 * 1024


def implementation_pins():
    return dict(prior.implementation_pins(), **{
        Path(__file__).name: io.digest(io.read_stable(Path(__file__), 1024*1024)[0])})


def summary(result):
    return dict(stage_identity=result['stage_identity'], lock_hex=result['lock'].hex(),
        raw_sha256=result['native_sha256'], numeric_sha256=result['numeric_sha256'],
        assignment_sha256=io.digest(io.encode(sorted((n, v.hex()) for n, v in result['assignment'].items()))),
        generation_mapping_sha256=io.digest(io.encode(result['generation_mapping'])))


def guard_receipt(key, binding, previous, index, raw_receipt, checked, stage_identity):
    return dict(schema=SCHEMA, kind='guard', request_sha256=key,
        binding_sha256=binding, previous_commit_sha256=previous, stage=index,
        raw_receipt_sha256=raw_receipt, result=checked, stage_identity=stage_identity)


def vector_pin(projection):
    return io.digest(io.encode(dict(reports=projection.report_sha256,
        stages=projection.stage_identities, numeric=projection.numeric_sha256)))


def science_receipt(key, index, guard_sha, replay_pin, result):
    return dict(schema=SCHEMA, kind='scientific_replay', request_sha256=key,
        stage=index, guard_sha256=guard_sha, replay_implementation=replay_pin,
        result=summary(result))


def commit_receipt(key, index, science_sha, outcome_sha, timing_head):
    return dict(schema=SCHEMA, kind='stage_commit', request_sha256=key, stage=index,
        science_sha256=science_sha, raw_outcome_sha256=outcome_sha,
        timing_stage_end_sha256=timing_head)


class SavedHour(prior.SavedHour):
    def __init__(self, root, packet, specification, limits):
        super().__init__(root, packet, specification, limits)
        self.root = self.stages.root
        self.attest = self.root/'attestation'
        self.attest.mkdir(exist_ok=False)
        self.pins = implementation_pins()
        self.packet_audit_identity = packet.audit_identity
        self.binding = dict(schema=SCHEMA, request_sha256=self.key, stages=len(self.order),
            packet_audit_identity=self.packet_audit_identity,
            implementation_pins=self.pins, replay_implementation=self.replay_pin,
            adapter_binding_sha256=self.stages.binding_sha256,
            raw_binding_sha256=io.digest(io.encode(self.stages.raw.binding)),
            timing_binding_sha256=self.stages.timing.binding_sha256)
        self.binding_sha256 = io.write_metadata(self.root/'attestation_binding.json', self.binding)
        self.head = self.binding_sha256
        self.terminal_sha256 = None
        self.closed = False

    def _check(self):
        if self.poisoned or self.closed:
            raise ValueError('closed or poisoned attested hour')
        self.stages._check()
        if (implementation_pins() != self.pins
                or io.digest(io.read_stable(self.root/'attestation_binding.json', io.META_CAP)[0]) != self.binding_sha256
                or self.replay.request_key(self.packet, self.specification, self.limits) != self.key
                or self.packet.audit_identity != self.packet_audit_identity
                or self.replay.implementation_identity() != self.replay_pin):
            raise ValueError('attested scientific binding/implementation drift')

    def deliver(self, raw):
        try:
            self._check()
            index = len(self.locks)
            with self.replay.guard.solver_calls_forbidden():
                with self.stages.timing.span(index, 'build'):
                    api = self.replay.native.model_api
                    request = api.H1StageRequest(self.packet.inputs, self.locks)
                    model = api.build_h1_stage_model(request, expected_identity=api.h1_stage_identity(request))
                with self.stages.timing.span(index, 'capture'):
                    def consume(fresh):
                        with self.stages.timing.span(index, 'audit'):
                            checked = guard.saved_report(fresh, model)
                            receipt_raw = io.read_stable(self.stages.raw.root/f'{index:03d}'/'raw_receipt.json', io.META_CAP)[0]
                            guard_sha = io.write_metadata(self.attest/f'{index:03d}.guard.json',
                                guard_receipt(self.key, self.binding_sha256, self.head, index,
                                              io.digest(receipt_raw), checked, api.h1_stage_identity(request)))
                            try:
                                result = self.replay._audit_stage(self.packet, self.specification,
                                                                 self.limits, index, self.locks, fresh)
                            except self.replay.H1ReportAuditRejected as error:
                                if error.generation_mapping is not None:
                                    self._mapping(index, error.generation_mapping)
                                raise
                            self._check()
                            self._mapping(index, result['generation_mapping'])
                            io.write_metadata(self.attest/f'{index:03d}.science.json',
                                science_receipt(self.key, index, guard_sha, self.replay_pin, result))
                            return result
                    result = self.stages.raw.deliver(index, lambda: raw, consume)
                self._check()
                science_sha = io.digest(io.read_stable(self.attest/f'{index:03d}.science.json', io.META_CAP)[0])
                outcome_sha = io.digest(io.read_stable(self.stages.raw.root/f'{index:03d}'/'outcome.json', io.META_CAP)[0])
                head = io.write_metadata(self.attest/f'{index:03d}.commit.json',
                    commit_receipt(self.key, index, science_sha, outcome_sha, self.stages.timing.head))
                self._check()
                self.head = head
                self.locks = (*self.locks, result['lock'])
                return result
        except BaseException:
            self.poisoned = self.stages.poisoned = True
            raise

    def _mapping(self, index, mapping):
        raw = io.encode(mapping)
        if len(raw) > MAPPING_CAP:
            raise ValueError('generation mapping byte cap')
        io.write_new(self.attest/f'{index:03d}.mapping.json', raw)

    def finish(self):
        try:
            self._check()
            projection, prior_evidence = super().finish()
            payload = projection.projection_payload
            if len(payload) > PROJECTION_CAP:
                raise ValueError('projection byte cap')
            io.write_new(self.root/'projection.bin', payload)
            terminal = dict(schema=SCHEMA, request_sha256=self.key,
                binding_sha256=self.binding_sha256, last_commit_sha256=self.head,
                projection_sha256=io.digest(payload), projection_identity=projection.projection_identity,
                replay_vector_sha256=vector_pin(projection),
                raw_terminal_sha256=io.digest(io.read_stable(self.stages.raw.root/'terminal.json', io.META_CAP)[0]),
                timing_terminal_sha256=prior_evidence['timing']['terminal_sha256'],
                stages=len(self.locks))
            terminal_sha = io.write_metadata(self.root/'attestation_terminal.json', terminal)
            # An independent reader recomputes all guard and numerical results.
            result = inspect(self.root, self.packet, self.specification, self.limits,
                expected_binding_sha256=self.binding_sha256, expected_terminal_sha256=terminal_sha)
            if not result['saved_hour_evidence_complete']:
                raise ValueError('attested fresh inspection failed: '+str(result['errors']))
            self.terminal_sha256 = terminal_sha
            self.closed = True
            return projection, result
        except BaseException:
            self.poisoned = self.stages.poisoned = True
            raise


def _names(path, cap):
    names = set()
    with os.scandir(path) as entries:
        for entry in entries:
            names.add(entry.name)
            if len(names) > cap:
                raise ValueError('directory entry cap')
    return names


def inspect(root, packet, specification, limits, *, expected_binding_sha256,
            expected_terminal_sha256=None):
    from src.rq2_joint_deliverability_boundary_v1 import normal_h1_hour_replay_v3 as replay
    io.pin(expected_binding_sha256)
    if expected_terminal_sha256 is not None:
        io.pin(expected_terminal_sha256)
    root = Path(root).resolve()
    result = dict(schema=SCHEMA, saved_hour_evidence_complete=False,
        saved_guard_receipts_recomputed=False, stages_recomputed=0, errors=[],
        binding_sha256=expected_binding_sha256, terminal_sha256=None,
        native_execution_authenticated=False, native_export_coverage=False,
        live_reverse_map_checked=False, exact_mathematical_certificate=False,
        producer_coverage_proven=False, collector_integrated=False,
        resource_admission=False, formal_execution_ready=False, formal_result=False)
    observed, listings = [], []

    def read(path, cap=io.META_CAP, *, decode=True):
        raw, stamp = io.read_stable(path, cap)
        observed.append((path, stamp, io.digest(raw), cap))
        if not decode:
            return raw
        doc = json.loads(raw)
        if io.encode(doc) != raw:
            raise ValueError('noncanonical attestation JSON')
        return doc

    def names(path, expected):
        actual = _names(path, len(expected))
        if actual != expected:
            raise ValueError('unexpected/missing attestation files')
        listings.append((path, actual))

    def same(doc, wanted):
        if not io.same(doc, wanted):
            raise ValueError('attestation chain or recomputation mismatch')

    try:
        with replay.guard.solver_calls_forbidden():
            key = replay.request_key(packet, specification, limits)
            replay_pin = replay.implementation_identity()
            order = replay.native.model_api.stage_order(packet.inputs)
            count = len(order)
            names(root, {'raw','timing','attestation','adapter_binding.json','attestation_binding.json',
                         'projection.bin','attestation_terminal.json'})
            binding = read(root/'attestation_binding.json')
            if io.digest(io.encode(binding)) != expected_binding_sha256:
                raise ValueError('attestation binding pin mismatch')
            adapter = read(root/'adapter_binding.json')
            same(adapter, dict(request_sha256=key, stages=count, implementation_pins=prior.implementation_pins()))
            raw_binding = read(root/'raw'/'binding.json')
            timing_binding = read(root/'timing'/'binding.json')
            same(binding, dict(schema=SCHEMA, request_sha256=key, stages=count,
                packet_audit_identity=packet.audit_identity,
                implementation_pins=implementation_pins(), replay_implementation=replay_pin,
                adapter_binding_sha256=io.digest(io.encode(adapter)),
                raw_binding_sha256=io.digest(io.encode(raw_binding)),
                timing_binding_sha256=io.digest(io.encode(timing_binding))))
            terminal = read(root/'attestation_terminal.json')
            terminal_sha = io.digest(io.encode(terminal))
            if expected_terminal_sha256 is None or terminal_sha != expected_terminal_sha256:
                raise ValueError('independently retained attestation terminal pin required')
            names(root/'raw', {'binding.json','terminal.json'} | {f'{i:03d}' for i in range(count)})
            names(root/'attestation', {f'{i:03d}.{kind}.json' for i in range(count)
                                      for kind in ('guard','mapping','science','commit')})
            # A successful internal path uses build/capture/audit per stage,
            # fresh_reopen and terminal globally: 6*n+5 timing events.
            names(root/'timing', {'binding.json'} | {f'{i:05d}.json' for i in range(6*count+5)})
            raw_check = io.inspect(root/'raw', expected_request=key,
                                   expected_binding_sha256=binding['raw_binding_sha256'])
            if not raw_check['callback_sequence_complete']:
                raise ValueError('raw chain unresolved')
            time_check = timing.inspect(root/'timing', expected_binding_sha256=binding['timing_binding_sha256'],
                                         expected_terminal_sha256=terminal['timing_terminal_sha256'])
            if not time_check['intervals_complete']:
                raise ValueError('timing chain unresolved')
            timing_events = [read(root/'timing'/f'{i:05d}.json') for i in range(6*count+5)]
            # Match the exact internal schedule, not merely any valid ledger.
            expected_events = []
            for i in range(count):
                for kind, span, phase, parent in (
                    ('begin',3*i,'build',None), ('end',3*i,None,None),
                    ('begin',3*i+1,'capture',None), ('begin',3*i+2,'audit',3*i+1),
                    ('end',3*i+2,None,None), ('end',3*i+1,None,None)):
                    expected = dict(kind=kind, span=span)
                    if kind == 'begin': expected.update(stage=i, phase=phase, parent=parent)
                    expected_events.append(expected)
            for offset, phase in ((0,'fresh_reopen'),(1,'terminal')):
                expected_events.extend([dict(kind='begin',span=3*count+offset,
                    parent=None,stage=-1,phase=phase),dict(kind='end',span=3*count+offset)])
            expected_events.append(dict(kind='terminal',spans=3*count+2))
            for event, expected in zip(timing_events, expected_events):
                same({k:event[k] for k in expected}, expected)
            locks, hashes, stage_pins, numeric_pins = (), [], [], []
            previous = expected_binding_sha256
            for i in range(count):
                stage = root/'raw'/f'{i:03d}'
                names(stage, {'intent.json','raw.bin','raw_receipt.json','outcome.json'})
                read(stage/'intent.json')
                raw = read(stage/'raw.bin', io.RAW_CAP, decode=False)
                raw_receipt = read(stage/'raw_receipt.json')
                request = replay.native.model_api.H1StageRequest(packet.inputs, locks)
                model = replay.native.model_api.build_h1_stage_model(request,
                    expected_identity=replay.native.model_api.h1_stage_identity(request))
                checked = guard.saved_report(raw, model)
                guarded = read(root/'attestation'/f'{i:03d}.guard.json')
                same(guarded, guard_receipt(key, expected_binding_sha256, previous, i,
                    io.digest(io.encode(raw_receipt)), checked, replay.native.model_api.h1_stage_identity(request)))
                science = replay._audit_stage(packet, specification, limits, i, locks, raw)
                mapping = read(root/'attestation'/f'{i:03d}.mapping.json', MAPPING_CAP)
                same(mapping, science['generation_mapping'])
                scientific = read(root/'attestation'/f'{i:03d}.science.json')
                same(scientific, science_receipt(key, i, io.digest(io.encode(guarded)), replay_pin, science))
                outcome = read(stage/'outcome.json')
                commit = read(root/'attestation'/f'{i:03d}.commit.json')
                end = read(root/'timing'/f'{6*i+5:05d}.json')
                if end['kind'] != 'end' or end['span'] != 3*i+1:
                    raise ValueError('stage capture interval mismatch')
                same(commit, commit_receipt(key, i, io.digest(io.encode(scientific)),
                                           io.digest(io.encode(outcome)), io.digest(io.encode(end))))
                previous = io.digest(io.encode(commit))
                locks = (*locks, science['lock'])
                hashes.append(science['native_sha256'])
                stage_pins.append(science['stage_identity'])
                numeric_pins.append(science['numeric_sha256'])
                result['stages_recomputed'] += 1
            projection = replay.replay_stream(packet, specification, limits,
                (read(root/'raw'/f'{i:03d}'/'raw.bin', io.RAW_CAP, decode=False) for i in range(count)),
                expected_key=key)
            if (projection.canonical_locks != locks or projection.report_sha256 != tuple(hashes)
                    or projection.stage_identities != tuple(stage_pins)
                    or projection.numeric_sha256 != tuple(numeric_pins)):
                raise ValueError('full replay differs from stage summaries')
            payload = read(root/'projection.bin', PROJECTION_CAP, decode=False)
            if payload != projection.projection_payload:
                raise ValueError('fresh scientific projection mismatch')
            raw_terminal = read(root/'raw'/'terminal.json')
            same(terminal, dict(schema=SCHEMA, request_sha256=key, binding_sha256=expected_binding_sha256,
                last_commit_sha256=previous, projection_sha256=io.digest(payload),
                projection_identity=projection.projection_identity,
                replay_vector_sha256=vector_pin(projection),
                raw_terminal_sha256=io.digest(io.encode(raw_terminal)),
                timing_terminal_sha256=time_check['terminal_sha256'], stages=count))
            if (replay.request_key(packet, specification, limits) != key
                    or packet.audit_identity != binding['packet_audit_identity']
                    or replay.implementation_identity() != replay_pin
                    or implementation_pins() != binding['implementation_pins']):
                raise ValueError('implementation/input changed during inspection')
            for path, stamp, digest, cap in observed:
                fresh, fresh_stamp = io.read_stable(path, cap)
                if stamp != fresh_stamp or io.digest(fresh) != digest:
                    raise ValueError('attestation view changed during inspection')
            if any(_names(path, len(wanted)) != wanted for path, wanted in listings):
                raise ValueError('attestation directory view changed')
            result.update(saved_hour_evidence_complete=True, saved_guard_receipts_recomputed=True,
                          terminal_sha256=terminal_sha, request_sha256=key,
                          projection_identity=projection.projection_identity,
                          timing=time_check, raw=raw_check)
    except (ValueError, TypeError, KeyError, AttributeError, OSError, OverflowError) as error:
        result['errors'].append(str(error))
    return result


def storage_bound(stages):
    result = prior.storage_bound(stages)
    # Three metadata records and one full mapping per stage, plus terminal data.
    result['logical_bytes'] += (3*stages+2)*io.META_CAP+PROJECTION_CAP+stages*MAPPING_CAP
    result['files'] += 4*stages+3
    result['directories'] += 1
    return result
