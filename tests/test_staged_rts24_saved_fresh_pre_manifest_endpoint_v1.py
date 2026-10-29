"""Bounded synthetic publication/cleanup tests; no target Native invocation."""
import ast
import copy
import contextlib
import dis
import io
import importlib.util
import os
from pathlib import Path
import sys
from threading import get_ident
from types import CodeType, FunctionType, SimpleNamespace
import unittest

ROOT=Path(__file__).absolute().parents[1]


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


EP=load(ROOT/'tests/saved_fresh_endpoint_fixture_v1.py','_endpoint_kernel_fixture')
CLEAN=load(ROOT/'tests/test_staged_rts24_saved_fresh_source_cleanup_v7.py','_endpoint_runtime_fixture')


def globals_read(code):
    found={op.argval for op in dis.get_instructions(code) if op.opname=='LOAD_GLOBAL'}
    for item in code.co_consts:
        if type(item) is CodeType:found.update(globals_read(item))
    return sorted(found)


class EndpointTests(unittest.TestCase):
    def fixture(self,**kwargs):
        core=EP.load_core();kernel=EP.Kernel(core,**kwargs);kernel.acquire()
        return core,kernel

    def failed_acquire(self,kernel):
        owner=object.__new__(kernel.core.LocalPreEntryLease)
        with self.assertRaises(kernel.core.LocalPreEntryConstructionFailed) as caught:
            kernel.core.capture_pre_manifest_endpoint(owner,kernel.core.canonical(kernel.descriptor))
        self.assertIs(caught.exception.owner,owner)
        return owner,caught.exception

    def test_01_source_compilation_and_held_global_oracle(self):
        core=EP.load_core();core.check_compiled_namespace(core._TEST_PAYLOAD)
        for name in ('run_endpoint_cleanup','endpoint_transfer_state','run_runtime_cleanup','cleanup_root_image'):
            self.assertEqual(globals_read(getattr(core,name).__code__),[],name)
        self.assertFalse(any(core.FALSE_GATES.values()))
        combined=EP.load_core(probe=True);combined.check_compiled_namespace(combined._TEST_PAYLOAD)
        self.assertEqual(combined.pre_manifest_entry_probe_main.__globals__,vars(combined))

    def test_02_success_exact_reverse_close_and_repeat(self):
        core,k=self.fixture();core.bookend_pre_manifest_endpoint(k.owner)
        k.close();before=list(k.calls);k.close();self.assertEqual(before,k.calls)
        self.assertEqual(k.effects()[-3:],[('UnmapViewOfFile',k.view),('CloseHandle',202),('CloseHandle',201)])
        self.assertEqual(dict(k.anchor)['resources'],([201,'CLOSED',1],[202,'CLOSED',1],[k.view,'CLOSED',1]))

    def test_03_all_acquisition_failures_preserve_partial_owner(self):
        for index,name in enumerate(('OpenFileMappingW','OpenMutexW','MapViewOfFile')):
            with self.subTest(name=name):
                core=EP.load_core();k=EP.Kernel(core,fail=name);owner,error=self.failed_acquire(k)
                self.assertEqual(error.secondary,())
                self.assertEqual(k.effects(),[] if index==0 else [('CloseHandle',201)] if index==1 else [('CloseHandle',202),('CloseHandle',201)])
                self.assertEqual(dict(owner._endpoint_anchor)['ledger'][0],'CLOSED')

    def test_04_noninherit_checked_before_next_acquisition(self):
        for handle,forbidden in ((201,'OpenMutexW'),(202,'MapViewOfFile')):
            with self.subTest(handle=handle):
                core=EP.load_core();k=EP.Kernel(core,inherit=(handle,));self.failed_acquire(k)
                self.assertNotIn(forbidden,[name for name,_ in k.calls])

    def test_05_mutex_timeout_never_releases(self):
        core=EP.load_core();k=EP.Kernel(core,wait=258);self.failed_acquire(k)
        self.assertNotIn('ReleaseMutex',[name for name,_ in k.calls])
        self.assertEqual(len(k.effects()),3)

    def test_06_mutex_abandoned_releases_once_then_rejects(self):
        core=EP.load_core();k=EP.Kernel(core,wait=128);self.failed_acquire(k)
        self.assertEqual(sum(name=='ReleaseMutex' for name,_ in k.calls),1)
        self.assertEqual(k.effects()[0],('ReleaseMutex',202))

    def test_07_release_failure_is_sticky_and_other_resources_attempted(self):
        core=EP.load_core();k=EP.Kernel(core,fail='ReleaseMutex');owner,error=self.failed_acquire(k)
        self.assertEqual(len(error.secondary),1);before=list(k.calls)
        with self.assertRaises(core.PreManifestEndpointUnresolved) as repeated:
            core.close_pre_manifest_endpoint(owner._endpoint_anchor,owner)
        self.assertIs(repeated.exception,error.secondary[0]);self.assertEqual(before,k.calls)
        self.assertEqual(len([name for name,_ in k.calls if name in ('UnmapViewOfFile','CloseHandle')]),3)

    def test_08_header_relations_reject_before_manifest(self):
        variants=('schema','nonce','descriptor','owner_pid','owner_creation_filetime','slots','slot_bytes','extra')
        for field in variants:
            with self.subTest(field=field):
                core=EP.load_core();k=EP.Kernel(core)
                if field=='descriptor':k.header[field]={**k.descriptor,'ack_sha':'0'*64}
                elif field in ('owner_pid','owner_creation_filetime','slots','slot_bytes'):k.header[field]+=1
                else:k.header[field]='changed'
                k.write_header();owner,error=self.failed_acquire(k)
                self.assertEqual(error.secondary,());self.assertEqual(dict(owner._endpoint_anchor)['ledger'][0],'CLOSED')

    def test_09_initial_tail_zero_then_progress_does_not_change_header(self):
        core=EP.load_core();k=EP.Kernel(core);k.buffer[5000]=b'x';self.failed_acquire(k)
        core,k=self.fixture();k.buffer[5000]=b'x'
        self.assertIs(core.bookend_pre_manifest_endpoint(k.owner),k.capsule)
        k.close()

    def test_10_header_hash_marker_padding_and_bookend_drift(self):
        for offset in (100,4080,4095,4000):
            with self.subTest(offset=offset):
                core=EP.load_core();k=EP.Kernel(core);k.buffer[offset]=b'x';self.failed_acquire(k)
        core,k=self.fixture();k.header['owner_pid']+=1;k.write_header()
        with self.assertRaises(ValueError):core.bookend_pre_manifest_endpoint(k.owner)
        k.close()

    def test_11_each_close_failure_is_single_attempt_and_continues(self):
        for which in ('view','mutex','mapping'):
            with self.subTest(which=which):
                core,k=self.fixture();handle={'view':k.view,'mutex':202,'mapping':201}[which];k.close_fail=(handle,)
                with self.assertRaises(core.PreManifestEndpointUnresolved) as caught:k.close()
                before=list(k.calls)
                with self.assertRaises(core.PreManifestEndpointUnresolved) as repeated:k.close()
                self.assertIs(caught.exception,repeated.exception);self.assertEqual(before,k.calls)
                self.assertEqual(len([name for name,_ in k.calls if name in ('UnmapViewOfFile','CloseHandle')]),3)
                self.assertEqual(dict(k.anchor)['resources'][{'view':2,'mutex':1,'mapping':0}[which]],[handle,'UNCERTAIN',1])

    def test_12_witness_uncertainty_never_retries_close(self):
        for handle in (201,202):
            core,k=self.fixture();k.witness_unknown=(handle,)
            with self.assertRaises(core.PreManifestEndpointUnresolved):k.close()
            self.assertEqual(sum(name=='CloseHandle' and args[0]==handle for name,args in k.calls),1)

    def test_13_reentry_poison_preserves_physical_attempts(self):
        core,k=self.fixture();seen=[]
        def hook(name,args):
            if name=='UnmapViewOfFile':
                k.hook=None
                try:k.close()
                except ValueError as error:seen.append(error)
        k.hook=hook
        with self.assertRaises(core.PreManifestEndpointUnresolved) as caught:k.close()
        self.assertEqual(len(seen),1);self.assertIn(('reentry',seen[0]),caught.exception.secondary)
        self.assertEqual(len([name for name,_ in k.calls if name in ('UnmapViewOfFile','CloseHandle')]),3)

    def test_14_close_metadata_failure_cannot_block_other_domains(self):
        core,k=self.fixture();k.leaves['UnmapViewOfFile'].restype=object
        with self.assertRaises(core.PreManifestEndpointUnresolved):k.close()
        self.assertNotIn(('UnmapViewOfFile',k.view),k.effects())
        self.assertEqual(k.effects()[-2:],[('CloseHandle',202),('CloseHandle',201)])

    def test_15_terminal_coordinated_mirror_and_mutex_drift_rejected(self):
        for case in ('mirrors','mutex'):
            core,k=self.fixture();k.close();before=list(k.calls);owned=dict(k.anchor)
            if case=='mirrors':owned['opened'][0]=999;owned['resources'][0][0]=999
            else:owned['mutex_state'][0]=True
            with self.assertRaises(core.PreManifestEndpointUnresolved):k.close()
            self.assertEqual(before,k.calls)
        for case in ('resources','opened','both','capsule_live','capsule_anchor'):
            with self.subTest(live_drift=case):
                core,k=self.fixture();owned=dict(k.anchor)
                if case in ('resources','both'):owned['resources'][0][0]=999
                if case in ('opened','both'):owned['opened'][0]=999
                if case=='capsule_live':object.__setattr__(k.capsule,'_live',(999,202,k.view))
                if case=='capsule_anchor':object.__setattr__(k.capsule,'_anchor',())
                with self.assertRaises(core.PreManifestEndpointUnresolved):k.close()
                self.assertEqual(k.effects()[-3:],[('UnmapViewOfFile',k.view),('CloseHandle',202),('CloseHandle',201)])
                self.assertNotIn(('CloseHandle',999),k.effects())

    def test_16_live_owner_transfer_pending_and_commit(self):
        core,k=self.fixture();resource=SimpleNamespace(owner=k.owner);k.owner._resource=resource
        core.bind_endpoint_resource_once(k.owner,resource)
        target=SimpleNamespace(_resource=resource,_endpoint=k.capsule,_endpoint_anchor=k.anchor)
        core.endpoint_transfer_record(k.owner,target,resource)
        with self.assertRaises(ValueError):core.bookend_pre_manifest_endpoint(k.owner)
        self.assertTrue(core.endpoint_transfer_state(k.anchor,k.owner,True))
        resource.owner=target;self.assertFalse(core.endpoint_transfer_state(k.anchor,target,False))
        core.bookend_pre_manifest_endpoint(target)
        with self.assertRaises(ValueError):k.close()
        k.close(target)
        core,k=self.fixture();resource=SimpleNamespace(owner=k.owner);k.owner._resource=resource
        core.bind_endpoint_resource_once(k.owner,resource)
        target=SimpleNamespace(_resource=resource,_endpoint=k.capsule,_endpoint_anchor=k.anchor)
        core.endpoint_transfer_record(k.owner,target,resource)
        with self.assertRaises(core.PreManifestEndpointUnresolved) as pending:k.close()
        self.assertIn('transfer_pending',dict(pending.exception.secondary));before=list(k.calls)
        with self.assertRaises(core.PreManifestEndpointUnresolved) as repeated:k.close()
        self.assertIs(repeated.exception,pending.exception);self.assertEqual(before,k.calls)
        self.assertEqual(k.effects()[-3:],[('UnmapViewOfFile',k.view),('CloseHandle',202),('CloseHandle',201)])

    def test_17_bad_transfer_journal_still_closes_resources(self):
        core,k=self.fixture();dict(k.anchor)['transfers'].append(('broken',))
        with self.assertRaises(core.PreManifestEndpointUnresolved) as caught:k.close()
        self.assertEqual(caught.exception.secondary[0][0],'transfer')
        self.assertEqual(k.effects()[-3:],[('UnmapViewOfFile',k.view),('CloseHandle',202),('CloseHandle',201)])

    def test_18_runtime_cleanup_shared_endpoint_and_native(self):
        f=CLEAN.Fixture();self.assertIs(f.owner._endpoint,f.source._endpoint)
        self.assertIs(dict(f.owner._runtime_cleanup_anchor)['endpoint_anchor'],f.source._endpoint_anchor)
        f.close();self.assertEqual(f.resource.close_calls,[1,1]);self.assertEqual(dict(f.source._endpoint_anchor)['ledger'][0],'CLOSED')
        before=list(f.endpoint.calls);f.close();self.assertEqual(before,f.endpoint.calls)

    def test_19_runtime_endpoint_failure_does_not_block_native(self):
        f=CLEAN.Fixture();f.endpoint.close_fail=(202,)
        with self.assertRaises(f.core.LocalRuntimeUnresolved) as caught:f.close()
        self.assertIn('endpoint',dict(caught.exception.secondary));self.assertEqual(f.resource.close_calls,[1,1])
        self.assertEqual(f.resource.phase,'CLOSED');before=list(f.endpoint.calls)
        with self.assertRaises(f.core.LocalRuntimeUnresolved) as repeated:f.close()
        self.assertIs(repeated.exception,caught.exception);self.assertEqual(before,f.endpoint.calls)

    def test_20_runtime_native_failure_does_not_block_endpoint(self):
        f=CLEAN.Fixture(failed=(102,))
        with self.assertRaises(f.core.LocalRuntimeUnresolved):f.close()
        self.assertEqual(dict(f.source._endpoint_anchor)['ledger'][0],'CLOSED')
        self.assertEqual(f.resource.close_calls,[1,1])

    def test_21_runtime_pre_and_postcommit_keep_actual_owner(self):
        for event in ('transfer_prepared','owner_committed'):
            with self.subTest(event=event):
                f=CLEAN.Fixture(False,audit_error=event)
                with self.assertRaises((RuntimeError,f.core.LocalRuntimeUnresolved)):f.transfer()
                target=f.state['target']
                if event=='transfer_prepared':
                    self.assertIs(f.resource.owner,f.source);f.source.close()
                else:
                    self.assertIs(f.resource.owner,target);f.owner=target
                    with self.assertRaises(f.core.LocalRuntimeUnresolved):f.close()
                self.assertEqual(dict(f.source._endpoint_anchor)['ledger'][0],'CLOSED')
                self.assertEqual(f.resource.close_calls,[1,1])

    def test_22_partial_endpoint_constructors_remain_closed(self):
        core=EP.load_core()
        with self.assertRaises(TypeError):core.PreManifestEndpoint()
        with self.assertRaises(ValueError):core.open_bound_local_pre_entry_lease()
        core,k=self.fixture()
        for operation in (copy.copy,copy.deepcopy):
            with self.assertRaises(TypeError):operation(k.capsule)
        k.close()

    def test_23_factory_manifest_failure_closes_endpoint(self):
        core=EP.load_core();k=EP.Kernel(core);events=[];error=ValueError('synthetic manifest rejected')
        core.__name__='__main__';core._EARLY=dict(active=True,endpoint_ready=False,sources_allowed=False,blocked=[])
        core.full_role_entry_binding=lambda:core.canonical(k.descriptor)
        core.check_compiled_namespace=lambda raw:None;core._PAYLOAD_RAW=core._TEST_PAYLOAD
        core.Path=lambda value:SimpleNamespace(lstat=lambda:SimpleNamespace(st_size=2))
        def reader(path,pin):
            self.assertTrue(core._EARLY['endpoint_ready']);self.assertIn('ReleaseMutex',[n for n,_ in k.calls])
            events.append('manifest');return b'{}'
        core.read_file=reader
        def reject(raw):raise error
        core.check_plan=reject
        with self.assertRaises(core.LocalPreEntryConstructionFailed) as caught:core.open_bound_local_pre_entry_lease()
        self.assertIs(caught.exception.primary,error);self.assertEqual(caught.exception.secondary,())
        self.assertEqual(events,['manifest']);self.assertEqual(caught.exception.owner._phase,'CLOSED')
        self.assertFalse(core._EARLY['active']);self.assertFalse(core._EARLY['endpoint_ready'])
        self.assertEqual(k.effects()[-3:],[('UnmapViewOfFile',k.view),('CloseHandle',202),('CloseHandle',201)])
        fragment=EP.load_core(probe=True);owner=SimpleNamespace();primary=ValueError('primary')
        cleanup=RuntimeError('synthetic owner-retaining cleanup');cleanup.owner=owner;cleanup.primary=primary
        fragment.open_bound_local_pre_entry_lease=lambda:owner
        fragment.LocalPreEntryLease=type(owner);owner._resource=SimpleNamespace(owner=owner)
        def reject_bookend(value):raise primary
        def reject_close():raise cleanup
        fragment.bookend_pre_manifest_endpoint=reject_bookend;owner.close=reject_close
        with self.assertRaises(RuntimeError) as result:fragment.pre_manifest_entry_probe_main()
        self.assertIs(result.exception,cleanup);self.assertIs(result.exception.__cause__,primary)

    def test_24_manifest_projection_has_no_hash_cycle(self):
        core=EP.load_core();k=EP.Kernel(core);data=k.descriptor
        projection={key:value for key,value in data.items() if key!='manifest_sha'}
        raw=core.canonical(dict(pre_manifest_binding=projection))
        data['manifest_sha']=core.pin(raw)['sha256']
        self.assertEqual(core.canonical({key:value for key,value in data.items() if key!='manifest_sha'}),core.canonical(projection))
        self.assertNotIn('manifest_sha',projection)
        tree=ast.parse(EP.SOURCE.read_bytes());factory=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='open_bound_local_pre_entry_lease')
        self.assertIn("k != 'manifest_sha'",ast.unparse(factory))

    def test_25_real_scalar_parser_rejects_nonce_and_clock_drift(self):
        core=EP.load_core();k=EP.Kernel(core);d=k.descriptor
        core.__name__='__main__';core.sys=SimpleNamespace(**vars(sys))
        path=str(core.ROOT/'results/tables/staged_rts24_saved_fresh_full_role_entry_native_v1_non_authoritative/transport'/d['channel_nonce']/'parent.plan.json')
        values=['--full-role-pre-entry',path,d['manifest_sha'],d['channel_name'],d['channel_nonce'],'parent',
            d['request_sha'],d['offer_sha'],d['context_sha'],d['ack_sha'],d['invocation_started'].hex(),d['deadline'].hex()]
        core.sys.argv=['-c',*values];core.sys.orig_argv=[str(core.EXE),'-P','-B','-s','-S','-c','pass',*values]
        core._MODULE_CODE=compile(b'pass','<string>','exec',dont_inherit=True,optimize=0)
        core._PAYLOAD_RAW=core._TEST_PAYLOAD;core._PAYLOAD_CODE=compile(core._PAYLOAD_RAW,'<pre_entry_payload>','exec',dont_inherit=True,optimize=0)
        actual=core.decode(core.full_role_entry_binding());self.assertEqual(actual['channel_nonce'],d['channel_nonce'])
        for index,value in ((4,'Local\\saved_F_pre_entry_v1_'+'9'*64),(12,(d['deadline']+1).hex())):
            before=core.sys.argv[index];core.sys.argv[index]=value;core.sys.orig_argv[index+6]=value
            with self.assertRaises(ValueError):core.full_role_entry_binding()
            core.sys.argv[index]=before;core.sys.orig_argv[index+6]=before

    def test_26_factory_success_and_lease_transfer_use_exact_code(self):
        f=EP.Factory()
        try:
            owner=f.open();self.assertEqual(f.events.count('manifest'),1);self.assertEqual(f.events.count('source'),98)
            target=owner.transfer();self.assertIs(target._resource.owner,target)
            self.assertIs(target._endpoint,owner._endpoint);self.assertEqual(len(dict(target._endpoint_anchor)['transfers']),1)
            owner.close();self.assertEqual(f.closed,set());target.close();self.assertEqual(f.closed,{101,102})
            before=list(f.kernel.calls);target.close();self.assertEqual(before,f.kernel.calls)
            self.assertFalse(f.core._EARLY['active']);self.assertFalse(target._resource.guard['active'])
        finally:f.finish()
        f=EP.Factory();combined=EP.load_core(probe=True);stream=io.StringIO()
        f.core.pre_manifest_entry_probe_main=FunctionType(combined.pre_manifest_entry_probe_main.__code__,vars(f.core))
        try:
            with contextlib.redirect_stdout(stream):f.core.pre_manifest_entry_probe_main()
            result=f.core.decode(stream.getvalue().strip().encode('ascii'))
            self.assertTrue(result['closed']);self.assertFalse(result['full_role_entry_connected'])
            self.assertFalse(result['run_authority']);self.assertFalse(result['actual_F'])
            self.assertEqual(f.closed,{101,102});self.assertEqual(f.events.count('manifest'),1)
            self.assertEqual(len([n for n,_ in f.kernel.calls if n in ('UnmapViewOfFile','CloseHandle')]),3)
        finally:f.finish()

    def test_27_factory_partial_self_open_and_source_failures(self):
        for fail,expected in (('OpenProcess',set()),('OpenThread',{101}),('source',{101,102})):
            with self.subTest(fail=fail):
                f=EP.Factory(fail)
                try:
                    with self.assertRaises(f.core.LocalPreEntryConstructionFailed) as caught:f.open()
                    self.assertEqual(caught.exception.secondary,());self.assertEqual(f.closed,expected)
                    self.assertEqual(dict(caught.exception.owner._endpoint_anchor)['ledger'][0],'CLOSED')
                    self.assertFalse(f.core._EARLY['active'])
                    if fail!='source':self.assertNotIn('source',f.events)
                finally:f.finish()
        f=EP.Factory();primary=RuntimeError('pre-ownership constructor rejected')
        def reject_kernel():raise primary
        f.core.kernel_api=reject_kernel
        try:
            with self.assertRaises(f.core.LocalPreEntryConstructionFailed) as caught:f.open()
            self.assertIs(caught.exception.primary,primary);self.assertEqual(caught.exception.secondary,())
            self.assertNotIn('_ownership',caught.exception.owner.__dict__);self.assertEqual(f.native_calls,[])
            self.assertEqual(dict(caught.exception.owner._endpoint_anchor)['ledger'][0],'CLOSED')
        finally:f.finish()

    def test_28_constructor_cleanup_factory_failure_still_closes_endpoint(self):
        f=EP.Factory();original=f.core.read_file;primary=ValueError('source rejected');cleanup_error=RuntimeError('cleanup factory rejected')
        def reject_factory(*args):raise cleanup_error
        def reader(path,pin,**kwargs):
            if Path(path).name.startswith('synthetic_'):
                owner=f.core._test_actual_owner
                owner._ownership=(*owner._ownership[:3],reject_factory,*owner._ownership[4:])
                raise primary
            return original(path,pin,**kwargs)
        original_bind=f.core.bind_endpoint_resource_once
        def bind(owner,resource):f.core._test_actual_owner=owner;return original_bind(owner,resource)
        f.core.bind_endpoint_resource_once=bind;f.core.read_file=reader
        try:
            with self.assertRaises(f.core.LocalPreEntryConstructionFailed) as caught:f.open()
            self.assertIs(caught.exception.primary,primary);self.assertIn(cleanup_error,caught.exception.secondary)
            self.assertEqual(dict(caught.exception.owner._endpoint_anchor)['ledger'][0],'CLOSED')
            self.assertFalse(f.core._EARLY['active']);self.assertFalse(caught.exception.owner._resource.guard['active'])
            self.assertEqual(f.closed,set())
        finally:f.finish()
        f=EP.Factory();original=f.core.read_file;original_early=f.core._EARLY
        def corrupt_early(path,pin,**kwargs):
            if Path(path).name.startswith('synthetic_'):
                f.core._EARLY=None;raise primary
            return original(path,pin,**kwargs)
        f.core.read_file=corrupt_early
        try:
            with self.assertRaises(f.core.LocalPreEntryConstructionFailed) as caught:f.open()
            self.assertIs(caught.exception.primary,primary)
            self.assertIn('early_retirement',[item[0] for item in caught.exception.secondary if type(item) is tuple])
            self.assertFalse(original_early['active']);self.assertFalse(caught.exception.owner._resource.guard['active'])
            self.assertEqual(f.closed,{101,102});self.assertEqual(dict(caught.exception.owner._endpoint_anchor)['ledger'][0],'CLOSED')
        finally:f.finish()
        f=EP.Factory()
        try:
            owner=f.open();owner._ownership=(*owner._ownership[:3],reject_factory,*owner._ownership[4:])
            r=owner._resource
            owner._cleanup_seal=(id(r),id(owner._ownership),id(owner._ownership[2]),id(owner._ownership[3]),id(owner._ownership[4]),r.creator)
            with self.assertRaises(f.core.LocalPreEntryUnresolved) as caught:owner.close()
            self.assertIs(dict(caught.exception.secondary)['native'],cleanup_error)
            self.assertEqual(dict(owner._endpoint_anchor)['ledger'][0],'CLOSED')
            self.assertFalse(r.guard['active']);self.assertFalse(f.core._EARLY['active'])
        finally:f.finish()

    def test_29_selected_root_drift_rejects_before_bookend_effect(self):
        for module_name,attr in (('subprocess','list2cmdline'),('time','monotonic'),('C','string_at')):
            f=EP.Factory()
            try:
                owner=f.open();module=getattr(f.core,module_name);original=getattr(module,attr)
                setattr(module,attr,lambda *args:'wrong')
                try:
                    with self.assertRaises(ValueError):owner.entry()
                    with self.assertRaises(f.core.LocalPreEntryUnresolved):owner.close()
                finally:setattr(module,attr,original)
                self.assertEqual(f.closed,{101,102});self.assertEqual(dict(owner._endpoint_anchor)['ledger'][0],'CLOSED')
            finally:f.finish()

    def test_30_real_append_before_owner_store_failure(self):
        f=EP.Factory();primary=RuntimeError('before actual owner store')
        try:
            owner=f.open();code=owner.transfer.__func__.__code__
            stores=[item.offset for item in dis.get_instructions(code) if item.opname=='STORE_ATTR' and item.argval=='owner']
            self.assertEqual(len(stores),1);seen=[]
            def trace(frame,event,arg):
                if frame.f_code is code:
                    frame.f_trace_opcodes=True
                    if event=='opcode' and frame.f_lasti==stores[0]:seen.append(True);raise primary
                return trace
            try:
                sys.settrace(trace)
                with self.assertRaises(RuntimeError) as caught:owner.transfer()
            finally:sys.settrace(None)
            self.assertIs(caught.exception,primary);self.assertEqual(seen,[True])
            self.assertIs(owner._resource.owner,owner);self.assertEqual(len(dict(owner._endpoint_anchor)['transfers']),1)
            with self.assertRaises(f.core.LocalPreEntryUnresolved):owner.close()
            self.assertEqual(f.closed,{101,102});self.assertEqual(dict(owner._endpoint_anchor)['ledger'][0],'UNRESOLVED')
        finally:f.finish()


def contract():
    core=EP.load_core()
    return dict(methods=30,synthetic_kernel=True,held_global_reads={name:globals_read(getattr(core,name).__code__)
        for name in ('run_endpoint_cleanup','endpoint_transfer_state','run_runtime_cleanup','cleanup_root_image')},
        source49_modules_executed=0,project_native_calls=0,P1_reads=0,child_processes=0,
        native_return_to_publication_window_verified=False,actual_entry_authenticated=False,
        full_role_entry_connected=False,run_authority=False,actual_F=False)
