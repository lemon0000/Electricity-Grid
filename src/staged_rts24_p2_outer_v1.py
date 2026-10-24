"""Draft outer source/startup binding and finalization; no P2 execute entrypoint."""
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
from threading import get_ident

from src import staged_rts24_p2_package_check_v1 as kernel
from src import staged_rts24_p2_outer_observation_v2 as parent
from src import staged_rts24_process_guard_v3 as guard

codec, require = kernel.codec, kernel.require
SOURCES = ('src/staged_rts24_p2_outer_v1.py', 'src/staged_rts24_p2_package_check_v2.py',
    'tests/test_staged_rts24_p2_outer_v1.py', 'docs/plan/staged_deliverability_c_p2_outer_binding_contract_v1.md',
    'src/staged_rts24_process_guard_v3.py', 'src/staged_rts24_p2_outer_observation_v2.py',
    'tests/test_staged_rts24_process_guard_v3.py', 'tests/test_staged_rts24_p2_outer_observation_v2.py',
    'docs/plan/staged_deliverability_c_p2_terminal_budget_contract_v1.md')


def digest(value): return sha256(codec.canonical(value)).hexdigest()


def validate_context(value):
    kernel.keys(value, 'schema authority public_execution_enabled native_authorized resource_admission kernel_context source_pins environment_sha parent_context')
    require(value['schema'] == 'staged_rts24_P2_outer_binding_development_v1' and value['authority'] == 'DRAFT_NONAUTHORITATIVE'
        and all(value[n] is False for n in ('public_execution_enabled', 'native_authorized', 'resource_admission')), 'outer context authority differs')
    kernel.validate_context(value['kernel_context'])
    require(type(value['source_pins']) is dict and set(value['source_pins']) == set(SOURCES), 'successor source group differs')
    for pin in value['source_pins'].values(): kernel.checked_pin(pin)
    kernel.sha(value['environment_sha'])
    parent.canonical_context(value['parent_context'])
    base = value['kernel_context']; p = value['parent_context']
    require(all(p[n] == base[n] for n in ('worker_root', 'parent_root')) and p['limits'] == kernel.CAPS
        and p['kernel_registration_sha'] == base['registration']['pin']['sha256'], 'parent context binding differs')
    return codec.canonical(value)


def read_inputs(context):
    """Selected source/executable bookend only; no runtime or scientific adoption."""
    from src import staged_rts24_p2_package_check_v2 as checker
    inputs, registration, packet = kernel.read_inputs(context['kernel_context'])
    repo = Path(context['kernel_context']['repo_root'])
    for name, pin in context['source_pins'].items():
        raw = codec.read_bytes(repo/name)
        require(kernel.pin(raw) == pin, 'outer source changed: '+name)
        inputs[str(repo/name)] = raw
    for name, module in ((SOURCES[0], __import__(__name__, fromlist=['*'])), (SOURCES[1], checker),
            (SOURCES[4], guard), (SOURCES[5], parent)):
        require(kernel.pin(codec.read_bytes(module.__file__)) == context['source_pins'][name], 'loaded outer source differs')
    require(digest(guard.controlled_environment()) == context['environment_sha'], 'controlled environment changed')
    return inputs, registration, packet


def context_bytes(kernel_context):
    base = codec.parse(kernel_context)
    require(kernel.validate_context(base) == kernel_context, 'held kernel context differs')
    repo = Path(base['repo_root'])
    p = dict(schema='staged_rts24_P2_parent_observation_development_v2', authority='DRAFT_NONAUTHORITATIVE',
        public_execution_enabled=False, native_authorized=False, resource_admission=False,
        worker_root=base['worker_root'], parent_root=base['parent_root'], limits=dict(kernel.CAPS),
        kernel_registration_sha=base['registration']['pin']['sha256'], terminal_record_cap_bytes=131072,
        parent_record_cap_bytes=131072, terminal_reserved_files=1, parent_reserved_files=1, max_member_handles=1024)
    value = dict(schema='staged_rts24_P2_outer_binding_development_v1', authority='DRAFT_NONAUTHORITATIVE',
        public_execution_enabled=False, native_authorized=False, resource_admission=False, kernel_context=base,
        source_pins={name: kernel.pin(codec.read_bytes(repo/name)) for name in SOURCES},
        environment_sha=digest(guard.controlled_environment()), parent_context=p)
    raw = validate_context(value)
    before, _, _ = read_inputs(value); after, _, _ = read_inputs(value)
    require(before == after, 'outer input construction bookend differs')
    return raw


def startup_image(value):
    raw = codec.canonical(value)
    require(len(raw) <= 16384, 'startup fact byte cap')
    return raw


def check_startup(raw, context, context_sha, process=None):
    value = codec.parse(raw)
    kernel.keys(value, 'schema authority context_sha parent_pid owner_pid owner_creation_filetime argv command_line cwd environment_sha created_suspended_in_owned_job actual_os_commandline_independently_verified')
    require(value['schema'] == 'staged_rts24_parent_CreateProcess_inputs_v1' and value['authority'] == 'DRAFT_NONAUTHORITATIVE'
        and value['context_sha'] == context_sha and value['created_suspended_in_owned_job'] is True
        and value['actual_os_commandline_independently_verified'] is False, 'startup fact scope differs')
    for name, cap in (('parent_pid', parent.U32), ('owner_pid', parent.U32), ('owner_creation_filetime', parent.U64)):
        require(parent.uint(value[name], cap, 1), 'startup identity differs')
    expected = context['kernel_context']['startup']
    require(value['argv'] == expected['argv'] and value['cwd'] == str(Path(expected['cwd']).resolve())
        and value['command_line'] == subprocess.list2cmdline(expected['argv'])
        and value['environment_sha'] == context['environment_sha'], 'startup invocation differs')
    if process is not None:
        require((value['owner_pid'], value['owner_creation_filetime']) ==
            (process['owner_pid'], process['owner_creation_filetime']), 'startup/process owner differs')
    require(startup_image(value) == raw, 'noncanonical startup fact')
    return value


class StartupCaptureUnresolved(OSError):
    """A retained cleanup capability plus both errors; never a quiet receipt."""
    def __init__(self, owner, capture, cleanup):
        self.owner = owner
        self.capture_error, self.cleanup_error = guard.error_details(capture), guard.error_details(cleanup)
        def attribute(name, default):
            try: return getattr(capture, name, default)
            except BaseException: return default
        phase = attribute('phase', None)
        self.phase = phase if type(phase) is str and 0 < len(phase) <= 64 else 'startup_capture'
        expected = attribute('expected_sha', None)
        self.expected_sha = expected if type(expected) is str and len(expected) == 64 and all(c in '0123456789abcdef' for c in expected) else None
        may = attribute('may_have_published', True)
        self.may_have_published = may if type(may) is bool else True
        self.cleanup_unknown = True
        self.job_quiet_confirmed = False
        # Keep phase/SHA and both error types inside the guard's message cap.
        super().__init__('capture_phase='+self.phase+'; expected_sha='+str(self.expected_sha)+
            '; may_have_published='+str(self.may_have_published)+'; cleanup_unknown; capture_type='+
            self.capture_error['type']+'; cleanup_type='+self.cleanup_error['type'])

    def __reduce__(self): raise TypeError('live cleanup capability cannot be serialized')


class StartupOwner(guard.OwnedChild):
    """Capture actual parent-owned creation inputs before any release."""
    def __init__(self, argv, *, expected, context_sha, environment_sha, sink, before_release, **kwargs):
        args = list(argv)
        require(args == expected['argv'] and str(Path(kwargs['cwd']).absolute()) == expected['cwd'], 'owner argv/cwd differs')
        require(kwargs['max_process_commit_bytes'] == 1024**3 and kwargs['max_job_commit_bytes'] == 2*1024**3,
            'owner commit limits differ')
        require(digest(kwargs['environment']) == environment_sha, 'owner environment differs')
        kernel.sha(context_sha)
        self._before_release = before_release
        super().__init__(args, **kwargs)
        try:
            self.startup_bytes = startup_image(dict(schema='staged_rts24_parent_CreateProcess_inputs_v1', authority='DRAFT_NONAUTHORITATIVE',
                context_sha=context_sha, parent_pid=os.getpid(), owner_pid=self.pid, owner_creation_filetime=self.creation_filetime,
                argv=args, command_line=subprocess.list2cmdline(args), cwd=str(Path(kwargs['cwd']).resolve()), environment_sha=environment_sha,
                created_suspended_in_owned_job=True, actual_os_commandline_independently_verified=False))
            sink(self.startup_bytes)
        except BaseException as capture:
            try: self.close()
            except BaseException as cleanup: raise StartupCaptureUnresolved(self, capture, cleanup) from capture
            raise

    def release(self):
        self._before_release()
        super().release()


class Binding:
    """One development parent binding; callers supply the monitor invocation."""
    def __init__(self, raw, expected_sha):
        require(type(raw) is bytes and sha256(raw).hexdigest() == expected_sha, 'outer context SHA differs')
        self.context = codec.parse(raw)
        require(validate_context(self.context) == raw, 'outer context canonical bytes differ')
        self.raw, self.sha = raw, expected_sha
        self._creator = os.getpid(), get_ident()
        self.inputs, _, _ = read_inputs(self.context)
        base = self.context['kernel_context']
        self.worker, self.parent = Path(base['worker_root']), Path(base['parent_root'])
        self.worker_identity = codec.directory_identity(self.worker)
        self.parent_identity = codec.directory_identity(self.parent)
        self.startup_bytes = None
        self._attempted = self._finished = False
        self._owner_identity = None
        self.construction_unresolved = None

    def _creating_parent(self):
        require((os.getpid(), get_ident()) == self._creator, 'creating parent process/thread required')

    def _entry(self):
        self._creating_parent()
        require(sha256(self.raw).hexdigest() == self.sha and validate_context(self.context) == self.raw, 'held outer context changed')
        require(codec.directory_identity(self.worker) == self.worker_identity and codec.directory_identity(self.parent) == self.parent_identity,
            'held outer directories changed')
        again, _, _ = read_inputs(self.context)
        require(again == self.inputs, 'held outer inputs changed')

    def _bookend(self):
        self._entry()
        require(codec.read_bytes(self.worker/'outer_context.json') == self.raw, 'held outer context file changed')
        if self.startup_bytes is not None:
            require(codec.read_bytes(self.worker/'outer_startup.json') == self.startup_bytes, 'held startup fact changed')

    def owner_factory(self, argv, **kwargs):
        self._creating_parent()
        require(not self._attempted and not self._finished, 'outer creation already attempted')
        self._attempted = True
        self._entry()
        require(not list(self.worker.iterdir()) and not list(self.parent.iterdir()), 'new empty outer directories required')
        codec.publish(self.worker/'outer_context.json', self.raw)
        base = self.context['kernel_context']
        codec.publish(self.worker/'launcher_start.json', codec.canonical(dict(package='staged_rts24_P2_v1', limits=kernel.CAPS,
            registration_sha=base['registration']['pin']['sha256'])))
        for name in ('launcher.stdout.log', 'launcher.stderr.log'): codec.publish(self.worker/name, b'')
        self._bookend()
        def capture(raw):
            self._bookend()
            value = check_startup(raw, self.context, self.sha)
            require(value['parent_pid'] == self._creator[0], 'startup creating parent differs')
            self.startup_bytes = raw
            self._owner_identity = value['owner_pid'], value['owner_creation_filetime']
            codec.publish(self.worker/'outer_startup.json', raw)
        try:
            return StartupOwner(argv, expected=base['startup'], context_sha=self.sha, environment_sha=self.context['environment_sha'],
                sink=capture, before_release=self._bookend, **kwargs)
        except StartupCaptureUnresolved as exc:
            self.construction_unresolved = exc
            raise

    def finish(self, process_record):
        self._creating_parent()
        require(sha256(self.raw).hexdigest() == self.sha and validate_context(self.context) == self.raw, 'held outer context changed')
        require(codec.directory_identity(self.parent) == self.parent_identity, 'held parent directory changed')
        require(self._attempted, 'outer creation was never attempted')
        require(not self._finished, 'outer finalization already attempted')
        self._finished = True
        assessment = parent.assess_process(process_record, kernel.CAPS)
        record = assessment['process_snapshot']
        held_parent = parent.canonical_context(self.context['parent_context'])
        # Unknown ownership cannot read or publish anything inside worker.
        if assessment['ownership_status'] != 'quiet_verified':
            return parent.save_observation(self.parent, held_parent, sha256(held_parent).hexdigest(), record,
                lambda root: require(False, 'unknown ownership inspected'))
        self._bookend()
        require(self.startup_bytes is not None, 'parent-held startup fact required')
        check_startup(self.startup_bytes, self.context, self.sha, record)
        require(self._owner_identity == (record['owner_pid'], record['owner_creation_filetime'])
            and codec.parse(self.startup_bytes)['parent_pid'] == self._creator[0], 'held creating owner differs')
        codec.publish(self.worker/'launcher.json', guard.record_image(record))
        from src import staged_rts24_p2_package_check_v2 as checker
        result = None
        def inspect(root):
            nonlocal result
            result = checker.inspect_package(self.raw, self.sha, record, self.startup_bytes)
            return dict(inspection_scope='caller_supplied_mechanical', completion_core_sha=None if result['completion_core_pin'] is None else result['completion_core_pin']['sha256'],
                inventory_sha=result['inventory_sha'], report_sha=None if result['report_pin'] is None else result['report_pin']['sha256'],
                point_references=result['point_reference_count'] or 0, contract_rows=result['contract_row_reference_count'] or 0,
                mechanical_package_integrity=result['mechanical_package_integrity'], unverified_worker_claims=result['unverified_worker_claims'] or dict(full_139_executed=None, package_complete=None))
        if not assessment['inspection_permitted']: result = checker.inspect_package(self.raw, self.sha, record, self.startup_bytes)
        saved = parent.save_observation(self.parent, held_parent, sha256(held_parent).hexdigest(), record, inspect)
        try:
            self._bookend()
            require(codec.read_bytes(self.worker/'launcher.json') == guard.record_image(record), 'outer launcher final bookend differs')
            require(codec.read_bytes(self.parent/'parent_observation.json') == codec.canonical(saved['observation']), 'outer parent final bookend differs')
        except Exception as exc:
            raise parent.OuterObservationUnresolved('outer_final_bookend', saved['parent_record_sha'], True, exc) from exc
        return dict(**saved, package_inspection=result, parent_CreateProcess_inputs_recorded=True,
            actual_os_commandline_independently_verified=False, full_runtime_closure_verified=False)
