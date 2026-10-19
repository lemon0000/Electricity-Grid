"""Private fresh bootstrap N0 controller; draft, no run authority.

The legacy execution lease stays None even inside the owned transaction.
Saved release records cannot reconstruct this live instance or its scope.
"""
from contextlib import contextmanager
from dataclasses import asdict
import os
import stat
from threading import get_ident

from experiments import h1_phase_obligation_controller_development_v1 as phase

bridge, base, binding, io = phase.bridge, phase.base, phase.binding, phase.io
old, parent, snapshot, entry = base.old, base.parent, base.snapshot, base.entry
worker = bridge.worker


def _lease_bytes(lease):
    lease.check()
    stream = lease.stream
    before = os.fstat(stream.fileno())
    position = stream.tell()
    try:
        stream.seek(0)
        raw = stream.read(2)
    finally:
        stream.seek(position)
    after = os.fstat(stream.fileno())
    if (raw != b'0' or not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
            or before.st_size != 1
            or any(getattr(before, k) != getattr(after, k) for k in
                ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns'))):
        raise ValueError('owned lock bytes or identity changed')
    lease.check()


def _lease_binding(lease):
    return (lease.root, lease.root_identity, lease.file_identity, lease.stream, lease.pid, lease.key)


class OwnedController(phase.Controller):
    def __init__(self, owner, network):
        from experiments import h1_bootstrap_integration_development_v2 as bootstrap
        if (type(owner) is not bootstrap.BootstrapOwner or not owner._operation.locked()
                or owner._operation_nonce is None or network is not owner._network
                or owner._controller is not None or owner._replay() != 'profile_verified'):
            raise ValueError('fresh owned profile-verified controller required')
        owner._check()
        self._owned_owner = owner
        self._owned_nonce = owner._operation_nonce
        self._owned_operation = owner._operation
        self._owned_thread = (os.getpid(), get_ident())
        self._owned_lease = None
        self._owned_active = self._owned_used = False
        self._owned_scope = self._owned_ticket = None
        self._owned_cleanup_leases = self._owned_original_cleanup = ()
        config = owner.declaration.run_configuration
        super().__init__(owner.roots['controller'], network, config.specification, config.limits,
            resolver=binding.open_manifest(), family=owner.declaration.family, ordinal=owner.declaration.ordinal,
            origin=owner._origin(), upstream_root=config.upstream_root, config_path=config.config_path,
            dc_bus=config.dc_bus, hours=192, budget=config.budget)
        try:
            # Capture incrementally inside cleanup coverage, before moving the
            # legacy lease or calling any tail helper that can fail.
            self._owned_original_cleanup = (self._lease,)
            self._owned_original_cleanup += (self._clock_lease,)
            self._owned_original_cleanup += (self._obligation_lease,)
            p = self._parent
            self._owned_original_cleanup += (p._root_lease,)
            self._owned_original_cleanup += (p._journal._lease,)
            self._owned_original_cleanup += (p._anchor._lease,)
            self._owned_cleanup_leases = self._owned_original_cleanup
            self._owned_lease, self._lease = self._lease, None
            self._owned_original_lease = self._owned_lease
            self._owned_parent = self._parent
            self._owned_network, self._owned_network_identity = network, network.identity
            self._owned_guards = self._guards()
            self._owned_leases = self._leases()
            self._owned_lease_bindings = tuple(_lease_binding(x) for x in self._owned_leases)
            self._owned_fixed = self._fixed()
            self._owned_cursor = self._cursor()
            self._owned_start = self._owned_intent = None
        except BaseException:
            self.close()
            raise

    def _check(self):
        raise ValueError('legacy bootstrap controller execution disabled')

    def _guards(self):
        return (self._obligation_guard, self._clock_guard, self._guard._lock, self._parent._guard._lock)

    def _leases(self):
        p = self._parent
        return (self._owned_lease, self._clock_lease, self._obligation_lease,
            p._root_lease, p._journal._lease, p._anchor._lease)

    def _fixed(self):
        return (self.clock_root, self.binding_pin, self._clock_hours,
            self.obligation_root, self.obligation_binding_pin, self._parent.identity)

    def _cursor(self):
        return (self._clock_index, self._clock_previous, self._obligation_previous, self._clock_last)

    def _owned_binding_check(self):
        o = self._owned_owner
        if ((os.getpid(), get_ident()) != self._owned_thread
                or o._operation is not self._owned_operation or not self._owned_operation.locked()
                or o._operation_nonce is not self._owned_nonce or self._owned_nonce is None
                or self._parent is not self._owned_parent or self._lease is not None
                or self._owned_lease is not self._owned_original_lease
                or self._guards() != self._owned_guards or self._leases() != self._owned_leases
                or self._owned_cleanup_leases != self._owned_original_cleanup
                or self._owned_original_cleanup != self._owned_leases
                or tuple(_lease_binding(x) for x in self._owned_leases) != self._owned_lease_bindings
                or o._network is not self._owned_network
                or self._owned_network.identity != self._owned_network_identity
                or self._parent._network.identity != self._owned_network_identity
                or o.declaration.run_configuration.network_sha256 != self._owned_network_identity
                or type(self._clock_index) is not int or type(self._clock_hours) is not int
                or type(self._clock_last) is not int
                or type(getattr(self, '_clock_start', None)) is not type(self._owned_start)
                or self._fixed() != self._owned_fixed or self._cursor() != self._owned_cursor
                or getattr(self, '_clock_start', None) != self._owned_start
                or getattr(self, '_clock_intent', None) != self._owned_intent):
            raise ValueError('owned bootstrap live binding changed')
        parent.source._network(self._owned_network)
        o._check()
        for lease in self._owned_leases:
            _lease_bytes(lease)

    @contextmanager
    def _owned_transaction(self):
        self._owned_binding_check()
        if self._owned_active or self._owned_used:
            raise ValueError('owned bootstrap transaction already used')
        acquired = []
        try:
            for guard in self._owned_guards:
                if not guard.acquire(False):
                    raise ValueError('owned bootstrap controller active')
                acquired.append(guard)
            self._owned_active = True
            self._owned_binding_check()
            yield
        finally:
            self._owned_scope = self._owned_ticket = None
            self._owned_active = False
            for guard in reversed(acquired):
                guard.release()

    def _owned_check(self, *, check_request=True):
        self._owned_binding_check()
        if (not self._owned_active or self._owned_scope is None
                or not all(g.locked() for g in self._owned_guards)):
            raise ValueError('single owned execution scope required')
        o = self._owned_owner
        if (o._bootstrap.rows(), o._global.rows()) != self._owned_scope:
            raise ValueError('owned release heads changed')
        self._parent._check()
        if parent.implementation_identity() != self._implementation:
            raise ValueError('owned parent implementation drift')
        self._clock_check()
        if (phase.implementation_identity() != self._obligation_identity or
                io.encode(dict(manifest=self._obligation_resolver.identity,
                    family=self._obligation_family, ordinal=self._obligation_ordinal,
                    budget=asdict(self._budget))) != self._obligation_configuration):
            raise ValueError('owned obligation configuration changed')
        entry.unchanged(self._obligation_views)
        worker.hour._directory(self.obligation_root, {'execution.lock'} | {p.name for p in self._obligation_views})
        if check_request and self._active_request is not None:
            entry.read(*self._active_request)

    def _owned_run(self):
        """Single N0 entry: source identity and predecessor are derived internally."""
        self._owned_binding_check()
        if not self._owned_active or self._owned_used or self._owned_scope is not None:
            raise ValueError('fresh owned bootstrap scope required')
        o = self._owned_owner
        if o._replay() != 'execution_indeterminate':
            raise ValueError('retained global release required before source')
        self._owned_used = True
        self._owned_scope = (o._bootstrap.rows(), o._global.rows())
        try:
            self._owned_check()
            p = self._parent
            state = p._restore()[0]
            anchor = p._anchor.inspect().record_sha256
            if state.status != 'ready' or state.completed_hours != 0 or self._clock_index != 0:
                raise ValueError('fresh N0 predecessor required')
            self._clock_start = bridge.tick(self._clock_last)
            self._owned_start = self._clock_start
            self._owned_headroom()
            self._owned_check()
            source = binding.source_binding.load_pinned_current(p._origin, p._upstream_root, config_path=p._config_path)
            b = binding.source_binding
            if (type(source) is not b.H1PinnedObservation or source.declaration != p._origin
                    or source.identity != b._identity(source) or source.network.identity != p._network.identity
                    or type(source.audit_payload) is not bytes
                    or len(source.audit_payload) > parent.bounded.prior.prior.old.MAX_SOURCE_AUDIT_BYTES):
                raise ValueError('owned pinned current source/network differs')
            self._owned_check()
            if p._restore()[0] != state or p._anchor.inspect().record_sha256 != anchor:
                raise ValueError('owned predecessor changed during source loading')
            result = self._owned_phase_step(expected_source_identity=source.identity, expected_head=state.head)
            self._owned_check()
            return result
        finally:
            self._owned_scope = self._owned_ticket = None

    def _owned_job(self, index, item, pending, anchor):
        self._owned_check()
        if self._owned_ticket is not None or type(index) is not int or index != 0:
            raise ValueError('single owned bootstrap Job required')
        item.validate(expected_receipt_sha256=item.receipt_sha256)
        self._owned_ticket = (index, item, io.encode(pending), anchor, item.receipt_sha256)
        self._owned_job_started = False
        try:
            return self._owned_obligation_job(index, item, pending, anchor)
        finally:
            self._owned_ticket = None

    def _owned_job_check(self, index, item, pending, anchor, *, check_request=True):
        self._owned_check(check_request=check_request)
        ticket = self._owned_ticket
        if (ticket is None or type(index) is not int or index != ticket[0] or item is not ticket[1]
                or io.encode(pending) != ticket[2] or anchor != ticket[3]
                or item.receipt_sha256 != ticket[4]):
            raise ValueError('owned Job context changed')
        item.validate(expected_receipt_sha256=ticket[4])
        p = self._parent
        root = self._owned_lease.root/f'job_{index:03d}_non_authoritative'
        request = dict(schema=entry.SCHEMA,root=str(root),implementation=self._implementation,
            parent_declaration=p._declaration,parent_identity=p.identity,anchor_record=anchor,pending_arguments=pending,
            input_receipt=old.json.loads(item.receipt),input_receipt_sha256=item.receipt_sha256,
            budget=asdict(self._budget),route='owned_timed_hour_development',**entry.FLAGS)
        expected = (root/'request.json', io.digest(io.encode(request)))
        if self._active_request != expected:
            raise ValueError('owned active request differs from Job ticket')
        if check_request:
            entry.read(*expected)
        if (pending['expected_request_key'] != old.replay.request_key(item.packet, item.specification, item.limits)
                or p._restore()[0].head != pending['expected_head'] or p._anchor.inspect().record_sha256 != anchor):
            raise ValueError('owned Job predecessor changed')

    def close(self):
        if (os.getpid(), get_ident()) != self._owned_thread or self._owned_active:
            raise ValueError('owned bootstrap close outside transaction required')
        try:
            super().close()
        finally:
            self._owned_lease = None
            errors = []
            # Independent captures preserve cleanup after one tuple drifts.
            # During partial construction only the incremental capture exists.
            candidates = []
            for name in ('_owned_original_cleanup', '_owned_leases'):
                value = getattr(self, name, ())
                if type(value) is tuple: candidates.extend(value)
            candidates.append(getattr(self, '_owned_original_lease', None))
            seen = set()
            for lease in candidates:
                if lease is None or id(lease) in seen: continue
                seen.add(id(lease))
                try:
                    if lease.stream is not None: lease.close()
                except BaseException as error: errors.append(error)
            if errors: raise errors[0]

    # Preserved base/clock/obligation transactions with separate owned entry names.

    def _owned_headroom(self):
        self._owned_check()
        binding.prevalidate_enrollment(self._obligation_resolver,self._parent._declaration,
            family=self._obligation_family,ordinal=self._obligation_ordinal,relative_hour=self._clock_index)
        self._owned_clock_headroom()
        # Three controller records per remaining finite-episode hour.
        r = base.old.process.resources
        demand = r.HostResourceBudget(self._budget.max_job_commit_bytes+256*base.old.MIB,32*base.old.MIB,(
            r.DirectoryDemand('job_content',str(self._owned_lease.root),base.job_content_bound(self._parent._stages)['logical_bytes'],32*base.old.MIB),
            r.DirectoryDemand('parent_updates',str(self._parent._root),base.parent_update_bound(),32*base.old.MIB),
            r.DirectoryDemand('clock_remaining',str(self.clock_root),3*(self._clock_hours-self._clock_index)*bridge.CAP,32*base.old.MIB),
            r.DirectoryDemand('obligation_remaining',str(self.obligation_root),3*(self._clock_hours-self._clock_index)*phase.CAP,32*base.old.MIB),
            r.DirectoryDemand('scratch',str(self._owned_lease.root),8*base.old.MIB,32*base.old.MIB)))
        identity = r.resource_identity(demand)
        observed = r.observe_headroom(demand,expected_request_identity=identity)
        if (type(observed) is not r.HostHeadroomObservation or observed.request_identity != identity
                or observed.errors or not observed.observed_headroom_sufficient
                or any(getattr(observed,k) is not False for k in ('resource_reservation_held',
                    'hard_resource_limits_enforced','whole_task_resources_verified','formal_run_authorized','formal_result'))):
            raise ValueError('combined obligation headroom unavailable')

    def _owned_clock_headroom(self):
        self._owned_check()
        # Combined same-volume demands include future clock records; observation
        # is neither reservation nor FS-allocation/full-task admission.
        r = base.old.process.resources
        budget = r.HostResourceBudget(self._budget.max_job_commit_bytes+256*base.old.MIB,32*base.old.MIB,(
            r.DirectoryDemand('job_content',str(self._owned_lease.root),base.job_content_bound(self._parent._stages)['logical_bytes'],32*base.old.MIB),
            r.DirectoryDemand('parent_updates',str(self._parent._root),base.parent_update_bound(),32*base.old.MIB),
            r.DirectoryDemand('clock_remaining',str(self.clock_root),3*(self._clock_hours-self._clock_index)*bridge.CAP,32*base.old.MIB),
            r.DirectoryDemand('scratch',str(self._owned_lease.root),8*base.old.MIB,32*base.old.MIB)))
        identity = r.resource_identity(budget)
        result = r.observe_headroom(budget,expected_request_identity=identity)
        if (type(result) is not r.HostHeadroomObservation or result.request_identity != identity
                or any(getattr(result,k) is not False for k in ('resource_reservation_held',
                    'hard_resource_limits_enforced','whole_task_resources_verified','formal_run_authorized','formal_result'))):
            raise ValueError('exact nonauthoritative headroom observation required')
        if result.errors or not result.observed_headroom_sufficient: raise ValueError('clock combined headroom unavailable')

    def _owned_parent_step(self,*,expected_source_identity,expected_head):
        p = self._parent
        with old.replay.guard.solver_calls_forbidden():
            try:
                self._owned_check()
                state,before,previous = p._restore()
                if not p._writable or state.status != 'ready' or state.head != expected_head:
                    raise ValueError('ready live timed parent required')
                hour = state.completed_hours
                source = p._load(hour,expected_source_identity)
                packet = p._packet(source,hour,before,previous)
                p._append(p._intent(hour,source,packet),source.audit_payload)
                head = p._journal.head
                pending = dict(expected_head=head,expected_source_identity=source.identity,
                    expected_request_key=old.replay.request_key(packet,p._spec,p._limits),expected_packet_audit=packet.audit_identity)
                anchor = p._anchor.inspect().record_sha256
                reader = snapshot.open_snapshot(p._declaration,expected_parent_identity=p.identity,expected_anchor_record=anchor)
                try: item = reader.pending_input(**pending)
                finally: reader.close()
                pins = self._owned_job(hour,item,pending,anchor)
                self._owned_check()
                job_root = self._owned_lease.root/f'job_{hour:03d}_non_authoritative'
                view = parent.job_view(job_root,p._stages)
                parent.inspect_job(job_root,packet,p._spec,p._limits,pins=pins,parent_declaration=p._declaration,
                    intent_head=head,lineage=source.identity)
                # All source/clock/carry facts must still match after whole-Job exit.
                reader = snapshot.open_snapshot(p._declaration,expected_parent_identity=p.identity,expected_anchor_record=anchor)
                try: fresh = reader.pending_input(**pending)
                finally: reader.close()
                if fresh.receipt != item.receipt or fresh.packet != item.packet: raise ValueError('parent source changed after Job')
                if parent.job_view(job_root,p._stages) != view: raise ValueError('Job changed before child reference')
                child_root = p._root/f'hour_{hour:03d}_non_authoritative'
                child_root.mkdir(exist_ok=False)
                pin = entry.write(child_root/'reference.json',parent.reference(child_root,job_root,p._declaration,head,source.identity,pins))
                child = p._child(hour,packet,head,source.identity,expected_head=pin)
                try: result = child.inspect()
                finally: child.close()
                p._restore();self._owned_check()
                if parent.job_view(job_root,p._stages) != view: raise ValueError('Job changed before parent outcome')
                p._append(p._outcome(hour,head,result))
                final = p._restore()[0]
                if parent.job_view(job_root,p._stages) != view: raise ValueError('Job changed before step return')
                return final
            except BaseException:
                p._poisoned = True
                raise

    def _owned_clock_step(self,*,expected_source_identity,expected_head):
        self._owned_check()
        try:
            self.last_observation = None
            self._clock_check()
            index = self._clock_index
            if index >= self._clock_hours: raise ValueError('clock hour cap')
            path = self.clock_root/f'{index:03d}';path.mkdir(exist_ok=False)
            self._clock_directories[path] = worker.hour._directory(path,set())
            intent = self._save(path/'intent.json',dict(schema=bridge.SCHEMA,binding_sha256=self.binding_pin,
                index=index,start_ns=self._clock_start,expected_head=io.pin(expected_head),
                source_identity=io.pin(expected_source_identity),previous_sha256=self._clock_previous))
            self._clock_intent = intent
            self._owned_intent = intent
            result = self._owned_parent_step(expected_source_identity=expected_source_identity,expected_head=expected_head)
            hour,item,pins,start,end,job_pin = self._clock_pending
            if hour != index or result.completed_hours != index+1: raise ValueError('clock outcome hour differs')
            job = self._owned_lease.root/f'job_{index:03d}_non_authoritative'
            view = base.parent.job_view(job,self._parent._stages)
            self._owned_check()
            finish = bridge.tick(end)
            terminal = self._save(path/'terminal.json',dict(schema=bridge.SCHEMA,intent_sha256=intent,end_ns=finish,
                job_start_ns=start,job_end_ns=end,job_pins=pins,outcome_head=result.head,
                job_record_sha256=job_pin,outcome_anchor_sha256=self._parent._anchor.inspect().record_sha256,**bridge.FLAGS))
            checked = bridge.inspect(self.clock_root,index,item.packet,item.specification,item.limits,
                binding_pin=self.binding_pin,intent_pin=intent,terminal_pin=terminal)
            if self._parent._restore()[0] != result: raise ValueError('parent changed before clock return')
            self._clock_check()
            if base.parent.job_view(job,self._parent._stages) != view: raise ValueError('Job changed before clock return')
            self._owned_check()
            final = bridge.tick(finish)
            self.last_observation = bridge.Observation((index,result.head,terminal,checked['transaction_wall_ns'],
                checked['native_total_ns'],checked['observed_non_native_ns'],final-finish,True),_token=bridge._TOKEN)
            self._clock_last = final
            self._clock_previous = terminal
            self._clock_index += 1
            self._owned_cursor = (1, terminal, self._owned_cursor[2], final)
            return result
        except BaseException:
            self._clock_poisoned = True
            self._parent._poisoned = True
            raise
        finally:
            self._clock_pending = None

    def _owned_phase_step(self,*,expected_source_identity,expected_head):
        self._owned_check()
        # Private numerical fixture path. No owner need or bootstrap authority.
        try:
            self.last_obligation_observation = None
            result = self._owned_clock_step(expected_source_identity=expected_source_identity,expected_head=expected_head)
            self._owned_check()
            hour = result.completed_hours-1
            link = self.obligation_root/f'{hour:03d}.job.json'
            pin = self._save_obligation(self.obligation_root/f'{hour:03d}.terminal.json',dict(schema=phase.SCHEMA,
                previous_sha256=self._obligation_previous,job_link_sha256=io.digest(self._obligation_views[link][1][0]),
                clock_terminal_sha256=self.last_observation.terminal_sha256,parent_head=result.head,
                parent_anchor_sha256=self._parent._anchor.inspect().record_sha256,relative_hour=hour,
                controller_live_join_checked=True,**phase.FLAGS))
            self._owned_check()
            self._obligation_previous = pin
            self._owned_cursor = (self._owned_cursor[0], self._owned_cursor[1], pin, self._owned_cursor[3])
            self.last_obligation_observation = phase.ObligationObservation(hour,self.obligation_binding_pin,pin,result.head,_token=phase._TOKEN)
            return result
        except BaseException:
            self.last_observation = None
            self.last_obligation_observation = None
            self._clock_poisoned = True
            self._parent._poisoned = True
            raise

    def _owned_obligation_job(self,index,item,pending,anchor):
        p = self._parent
        if (not self._obligation_guard.locked() or not self._clock_guard.locked() or not self._guard._lock.locked()
                or not p._guard._lock.locked() or self._active_request is not None):
            raise ValueError('owned obligation release scope required')
        self._owned_check(); self._clock_check()
        record = binding.bind(self._obligation_resolver,p._declaration,
            family=self._obligation_family,ordinal=self._obligation_ordinal,relative_hour=index,
            expected_parent_identity=p.identity,expected_anchor_record=anchor,
            pending_arguments=pending,expected_pending_receipt_sha256=item.receipt_sha256,job_budget=self._budget)
        if (record['normal_request_key'] != base.old.replay.request_key(item.packet,item.specification,item.limits)
                or record['source_parent_lineage']['pending_receipt'] != base.old.json.loads(item.receipt)):
            raise ValueError('obligation differs from typed pending input')
        root = self._owned_lease.root/f'job_{index:03d}_non_authoritative'
        # Exact same request as the inherited writer; fail closed on divergence.
        request = dict(schema=base.entry.SCHEMA,root=str(root),implementation=self._implementation,
            parent_declaration=p._declaration,parent_identity=p.identity,anchor_record=anchor,pending_arguments=pending,
            input_receipt=base.old.json.loads(item.receipt),input_receipt_sha256=item.receipt_sha256,
            budget=asdict(self._budget),route='owned_timed_hour_development',**base.entry.FLAGS)
        request_pin = io.digest(io.encode(request))
        pin = self._save_obligation(self.obligation_root/f'{index:03d}.binding.json',dict(schema=phase.SCHEMA,
            implementation=self._obligation_identity,obligation=record,expected_worker_request_sha256=request_pin,
            **phase.FLAGS))
        self._owned_check()
        if p._restore()[0].head != pending['expected_head'] or p._anchor.inspect().record_sha256 != anchor:
            raise ValueError('live obligation parent changed before Job')
        self._active_request = (root/'request.json',request_pin)
        try:
            pins = self._owned_clock_job(index,item,pending,anchor)
            self._owned_check()
            if pins['request.json'] != request_pin: raise ValueError('released request differs from obligation')
            self._save_obligation(self.obligation_root/f'{index:03d}.job.json',dict(schema=phase.SCHEMA,
                obligation_binding_sha256=pin,job_pins=pins,**phase.FLAGS))
            self._owned_check()
            return pins
        finally:
            self._active_request = None

    def _owned_clock_job(self,index,item,pending,anchor):
        self._owned_job_check(index,item,pending,anchor,check_request=False)
        if self._clock_pending is not None or not self._clock_guard.locked(): raise ValueError('single owned Job envelope required')
        self._clock_check()
        start = bridge.tick(self._clock_start)
        pins = self._owned_native_job(index,item,pending,anchor)
        end = bridge.tick(start)
        self._clock_check()
        root = self._owned_lease.root/f'job_{index:03d}_non_authoritative'
        result,_ = base.entry.read(root/'worker_result.json',pins['worker_result.json'])
        wr = root/'worker_non_authoritative'
        wb,_ = base.entry.read(wr/'binding.json',result['worker_binding_sha256'])
        wt,_ = base.entry.read(wr/'terminal.json',result['worker_terminal_sha256'])
        if not io.same(wb['clock'],self._clock_profile): raise ValueError('worker clock profile differs')
        bridge.analyse(transaction_start=self._clock_start,job_start=start,worker_start=wb['start_ns'],
            worker_end=wt['end_ns'],job_end=end,transaction_end=end,native_total=wt['native_total_ns'])
        pin = self._save(self.clock_root/f'{index:03d}'/'job.json',dict(schema=bridge.SCHEMA,
            intent_sha256=self._clock_intent,start_ns=start,end_ns=end,job_pins=pins))
        self._clock_pending = (index,item,pins,start,end,pin)
        return pins

    def _owned_native_job(self,hour,item,pending,anchor):
        self._owned_job_check(hour,item,pending,anchor,check_request=False)
        if self._owned_job_started: raise ValueError('owned Job already started')
        scratch_path = self._owned_lease.root/f'job_{hour:03d}_non_authoritative'/'scratch_non_authoritative'
        if len(str(scratch_path).encode('utf-16-le'))//2 >= 260:
            raise ValueError('owned child cwd exceeds Windows CreateProcess limit')
        self._owned_job_started = True
        lease = old.bounded.chunks.base.local._Lease(self._owned_lease.root/f'job_{hour:03d}_non_authoritative',True)
        try:
            root = lease.root;scratch = root/'scratch_non_authoritative';scratch.mkdir()
            p = self._parent
            request = dict(schema=entry.SCHEMA,root=str(root),implementation=self._implementation,
                parent_declaration=p._declaration,parent_identity=p.identity,anchor_record=anchor,pending_arguments=pending,
                input_receipt=old.json.loads(item.receipt),input_receipt_sha256=item.receipt_sha256,
                budget=asdict(self._budget),route='owned_timed_hour_development',**entry.FLAGS)
            pins = {'request.json':entry.write(root/'request.json',request)}
            resources = old.process.resources
            host = resources.HostResourceBudget(self._budget.max_job_commit_bytes+256*old.MIB,32*old.MIB,(
                resources.DirectoryDemand('timed_job',str(root),base.job_content_bound(p._stages)['logical_bytes'],32*old.MIB),
                resources.DirectoryDemand('parent_updates',str(p._root),base.parent_update_bound(),32*old.MIB),
                resources.DirectoryDemand('scratch',str(scratch),8*old.MIB,32*old.MIB)))
            env = parent.environment(scratch)
            argv = base._argv(root/'request.json',pins['request.json'])
            arguments = dict(cwd=scratch,environment=env,budget=self._budget,host_budget=host,
                expected_host_identity=resources.resource_identity(host))
            identity = old.process.task_process_identity(argv,**arguments)
            pins['launch.json'] = entry.write(root/'launch.json',dict(request_sha256=pins['request.json'],
                process_identity=identity,argv=argv,cwd=str(scratch),environment_sha256=io.digest(io.encode(env)),
                budget=asdict(self._budget),host=asdict(host)))
            views = {root/n:(entry.CAP,entry.read(root/n,h)[1]) for n,h in pins.items()}
            self._owned_job_check(hour,item,pending,anchor)
            _lease_bytes(lease)
            with old.process.normal_task_child(argv,**arguments,expected_process_identity=identity) as child:
                pid,creation = child.pid,child.creation_filetime
                initial = old.json.loads(io.encode(asdict(child.initial_observation)))
                old._validate_initial(initial,host)
                pins['initial_observation.json'] = entry.write(root/'initial_observation.json',initial)
                pins['child.json'] = entry.write(root/'child.json',dict(pid=pid,creation_filetime=creation,
                    process_identity=identity,request_sha256=pins['request.json'],initial_observation_sha256=pins['initial_observation.json']))
                self._owned_check();_lease_bytes(lease)
                if p._restore()[0].head != pending['expected_head'] or p._anchor.inspect().record_sha256 != anchor:
                    raise ValueError('parent changed before Job release')
                pins['release_intent.json'] = entry.write(root/'release_intent.json',dict(request_sha256=pins['request.json'],
                    launch_sha256=pins['launch.json'],child_sha256=pins['child.json']))
                for name,pin in pins.items():
                    if root/name not in views: views[root/name] = (entry.CAP,entry.read(root/name,pin)[1])
                entry.unchanged(views)
                self._owned_job_check(hour,item,pending,anchor)
                _lease_bytes(lease)
                child.release();observed = child.wait()
                _lease_bytes(lease)
            pins['observation.json'] = entry.write(root/'observation.json',asdict(observed))
            old._validate_observation(observed,identity,pid,creation,self._budget)
            self._owned_check();_lease_bytes(lease);entry.unchanged(views)
            # Never read or adopt worker output until live exit0/whole-Job quiet.
            for name in ('consumed.json','worker_result.json'):
                pins[name] = io.digest(io.read_stable(root/name,entry.CAP)[0])
            parent.inspect_job(root,item.packet,item.specification,item.limits,pins=pins,parent_declaration=p._declaration,
                intent_head=pending['expected_head'],lineage=pending['expected_source_identity'])
            entry.unchanged(views);self._owned_check();_lease_bytes(lease)
            return pins
        finally:
            owner,lease = lease,None
            if owner is not None: owner.close()
