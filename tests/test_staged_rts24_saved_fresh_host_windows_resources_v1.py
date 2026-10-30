"""Prepared native bodies, fake DLL only; no project Windows HANDLE is created."""
import copy
import ctypes
import json
import pickle
from pathlib import Path
import unittest
import importlib.util

ROOT=Path(__file__).absolute().parents[1]
path=ROOT/'tests/saved_fresh_host_windows_fixture_v1.py'
spec=importlib.util.spec_from_file_location('_windows_test_fixture',path);F=importlib.util.module_from_spec(spec);spec.loader.exec_module(F)
FAULTS=[]


class WindowsTests(unittest.TestCase):
    def failed_prepare(self,w):
        w.acked()
        with self.assertRaises(w.m.HostUnresolved) as error:w.m.prepare(w.host)
        return error.exception

    def test_01_original_issuers_closed(self):
        p=F.load(F.PROVIDER,'_closed_provider_original')
        for fn in (lambda:p.WindowsResources(),lambda:p.open_windows_resources(),lambda:p._mechanical_resources(None,100.,280.,lambda:100.)):
            with self.assertRaises(p.NativeUnavailable):fn()

    def test_02_independent_win64_layout_oracle(self):
        p=F.load(F.PROVIDER,'_provider_layout_only')
        expected={'_Basic':64,'_IO':48,'_Limits':144,'_Startup':104,'_StartupEx':112,'_ProcessInfo':24,'_Accounting':48,'_MemoryInfo':48}
        self.assertEqual({n:ctypes.sizeof(getattr(p,n)) for n in expected},expected)
        for name,field,offset in (('_Basic','flags',16),('_Basic','affinity',48),('_Limits','io',64),('_Limits','job_memory',120),
            ('_Startup','stdin',80),('_StartupEx','attributes',104),('_ProcessInfo','pid',16),('_Accounting','active',40),('_MemoryInfo','region_size',24),('_MemoryInfo','state',32)):
            self.assertEqual(getattr(getattr(p,name),field).offset,offset)

    def test_03_full_host_protocol_uses_prepared_native_bodies(self):
        w=F.World();binding=w.active();root=w.provider_root();w.m.close(w.host)
        self.assertEqual(root['resume'],['DONE',1]);self.assertEqual(root['quiet'][:2],['DONE',1])
        self.assertTrue(all(state==['CLOSED',1] for state in root['states'].values()))
        self.assertEqual(w.k.count('CreateProcessW'),1);self.assertEqual(w.k.count('ResumeThread'),1)
        self.assertEqual(w.m.decode(binding)['child']['pid'],w.k.rootpid);self.assertEqual(w.k.attribute_deleted,1)

    def test_04_exact_child_argv_and_noninherit(self):
        w=F.World();w.bound()
        self.assertEqual(w.k.startup[0],w.root()['built'][0]['command']);self.assertEqual(w.k.startup[2],0x08080404)
        self.assertEqual(w.k.count('CreateJobObjectW'),1);self.assertEqual(w.k.count('UpdateProcThreadAttribute'),1);w.m.close(w.host)

    def test_05_process_information_survives_return_exception(self):
        w=F.World();w.k.after='CreateProcessW';failure=self.failed_prepare(w)
        self.assertIs(failure.primary,w.k.error);self.assertTrue(w.k.info_written)
        self.assertEqual(w.root()['acquisitions']['process'],202);self.assertEqual(w.root()['acquisitions']['thread'],203)
        self.assertTrue({101,102,201,202,203}<=w.k.closed);self.assertTrue(w.k.unmapped)

    def test_06_create_only_mapping_collision(self):
        w=F.World();w.k.exists='mapping';self.failed_prepare(w)
        self.assertEqual(w.k.count('CreateMutexW'),0);self.assertEqual(w.k.closed,{101})

    def test_07_create_only_mutex_collision(self):
        w=F.World();w.k.exists='mutex';self.failed_prepare(w)
        self.assertEqual(w.k.count('MapViewOfFile'),0);self.assertEqual(w.k.closed,{101,102})

    def test_08_inheritable_handles_rejected_and_cleaned(self):
        for handle in (101,102,201,202,203):
            w=F.World();w.k.inherit={handle};FAULTS.append('inherit_'+str(handle));self.failed_prepare(w)
            self.assertIn(handle,w.k.closed);self.assertEqual(w.k.count('ResumeThread'),0)

    def test_09_endpoint_never_zeroes_nonempty_mapping(self):
        w=F.World();ctypes.memmove(w.k.view,b'x',1);self.failed_prepare(w)
        self.assertEqual(ctypes.string_at(w.k.view,1),b'x');self.assertEqual(w.k.count('CreateProcessW'),0)

    def test_10_mutex_timeout_does_not_release(self):
        w=F.World();w.k.wait=258;self.failed_prepare(w)
        self.assertEqual(w.k.count('ReleaseMutex'),0);self.assertTrue(w.k.unmapped)

    def test_11_abandoned_mutex_released_once_and_rejected(self):
        w=F.World();w.k.wait=128;self.failed_prepare(w)
        self.assertEqual(w.k.count('ReleaseMutex'),1);self.assertTrue(w.k.unmapped)

    def test_12_release_mutex_uncertainty_never_retried(self):
        w=F.World();w.k.fail='ReleaseMutex';failure=self.failed_prepare(w);before=list(w.k.calls)
        with self.assertRaises(w.m.HostUnresolved) as repeat:w.m.close(w.host)
        self.assertIs(failure,repeat.exception);self.assertEqual(before,w.k.calls);self.assertEqual(w.k.count('ReleaseMutex'),1)
        self.assertNotIn(102,w.k.closed)

    def test_13_attribute_stage_failure_matrix(self):
        for stage in ('InitQuery','InitAttributes','UpdateProcThreadAttribute'):
            w=F.World();w.k.fail=stage;FAULTS.append(stage);self.failed_prepare(w)
            self.assertEqual(w.k.count('CreateProcessW'),0);self.assertIn(201,w.k.closed)
            self.assertLessEqual(w.k.attribute_deleted,1)

    def test_14_attribute_delete_return_exception_is_retained(self):
        w=F.World();w.k.after='DeleteProcThreadAttributeList';failure=self.failed_prepare(w)
        self.assertIs(failure.primary,w.k.error);self.assertEqual(w.k.attribute_deleted,1)
        self.assertEqual(w.provider_root()['attribute_delete'],['UNCERTAIN',1]);self.assertIn(202,w.k.closed)

    def test_15_native_constructor_failure_matrix(self):
        for stage in ('CreateFileMappingW','CreateMutexW','MapViewOfFile','CreateJobObjectW','SetInformationJobObject','CreateProcessW'):
            w=F.World();w.k.fail=stage;FAULTS.append(stage);self.failed_prepare(w)
            self.assertEqual(w.k.count('ResumeThread'),0)
            self.assertTrue(all(state[1]<=1 for state in w.provider_root()['states'].values()))

    def test_16_child_image_mismatch_prevents_header(self):
        w=F.World();w.k.image='D:\\wrong.exe';self.failed_prepare(w)
        self.assertIsNone(w.provider_root()['header'][0]);self.assertEqual(w.k.count('ResumeThread'),0);self.assertIn(202,w.k.closed)

    def test_17_actual_identity_query_failure_retains_live_resources(self):
        w=F.World();w.k.fail='GetProcessTimes:202';self.failed_prepare(w)
        self.assertNotIn(202,w.k.closed);self.assertFalse(w.k.unmapped);self.assertEqual(w.k.count('TerminateJobObject'),1)

    def test_18_header_marker_written_last(self):
        w=F.World();writes=[];original=w.p.C.memmove
        def move(dest,src,length):writes.append((dest-w.k.view,bytes(src),length));return original(dest,src,length)
        w.p.C.memmove=move;w.bound()
        self.assertEqual([(offset,length) for offset,raw,length in writes],[(0,4088),(4088,8)])
        self.assertEqual(writes[-1][1],b'FEPv1OK!');self.assertEqual(w.provider_root()['header_state'],['DONE',1]);w.m.close(w.host)

    def test_19_header_commit_after_marker_failure_is_single_attempt(self):
        w=F.World();original=w.p.C.memmove
        def move(dest,src,length):
            result=original(dest,src,length)
            if length==8:raise w.k.error
            return result
        w.p.C.memmove=move;self.failed_prepare(w)
        self.assertEqual(ctypes.string_at(w.k.view+4088,8),b'FEPv1OK!')
        self.assertEqual(w.provider_root()['header_state'],['UNCERTAIN',1]);self.assertIn(202,w.k.closed)

    def test_20_resume_return_uncertainty_stops_and_closes(self):
        w=F.World();binding=w.bound();w.k.after='ResumeThread'
        with self.assertRaises(w.m.HostUnresolved) as failure:w.m.release(w.host,w.m.release_ack_bytes(binding))
        self.assertIs(failure.exception.primary,w.k.error);self.assertEqual(w.provider_root()['resume'],['UNCERTAIN',1])
        self.assertEqual(w.k.count('ResumeThread'),1);self.assertIn(202,w.k.closed)

    def test_21_unexpected_suspend_counts_reject(self):
        for value in (0,2,0xffffffff):
            w=F.World();binding=w.bound();w.k.resume_value=value
            with self.assertRaises(w.m.HostUnresolved):w.m.release(w.host,w.m.release_ack_bytes(binding))
            self.assertEqual(w.provider_root()['resume'],['UNCERTAIN',1]);self.assertEqual(w.k.count('ResumeThread'),1)

    def test_22_terminate_return_uncertainty_still_observes_quiet(self):
        w=F.World();w.bound();w.k.after='TerminateJobObject'
        with self.assertRaises(w.m.HostUnresolved):w.m.close(w.host)
        self.assertEqual(w.provider_root()['termination'],['UNCERTAIN',1]);self.assertEqual(w.provider_root()['quiet'][0],'DONE')
        self.assertIn(202,w.k.closed)

    def test_23_observed_descendant_is_retained_signaled_and_closed(self):
        w=F.World();w.active();w.k.add_member();w.p.capture_members(w.provider);w.m.close(w.host)
        witness=w.p.decode(w.provider_root()['quiet'][2]);self.assertEqual(witness['observed_count'],2)
        self.assertIn(301,w.k.closed);self.assertEqual(w.k.count('OpenProcess'),1)

    def test_24_missed_ephemeral_member_is_not_quiet(self):
        w=F.World();w.active();w.k.accounting_extra=1
        with self.assertRaises(w.m.HostUnresolved):w.m.close(w.host)
        self.assertEqual(w.provider_root()['quiet'][0],'UNCERTAIN');self.assertFalse(w.k.closed);self.assertFalse(w.k.unmapped)

    def test_25_pending_member_closed_on_identity_failure(self):
        w=F.World();w.active();w.k.add_member();w.k.fail='GetProcessTimes:301'
        with self.assertRaises(OSError):w.p.capture_members(w.provider)
        self.assertIn(301,w.k.closed);self.assertIsNone(w.provider_root()['pending'][0])

    def test_26_handle_value_reuse_has_independent_acquisition_generation(self):
        w=F.World();w.active();w.k.add_member();w.k.fail='GetProcessTimes:301'
        with self.assertRaises(OSError):w.p.capture_members(w.provider)
        w.k.fail=None;w.k.next_handle=301;w.p.capture_members(w.provider)
        with self.assertRaises(w.m.HostUnresolved):w.m.close(w.host)
        records=w.provider_root()['member_records'];self.assertEqual([(r[0],r[1],r[3][0]) for r in records],[(1,301,'CLOSED'),(2,301,'CLOSED')])
        self.assertEqual(sum(name=='CloseHandle' and args[0]==301 for name,args in w.k.calls),2)

    def test_27_every_resource_close_failure_continues_independent_domains(self):
        for target in (101,102,201,202,203,'view'):
            w=F.World();w.bound();w.k.fail='UnmapViewOfFile' if target=='view' else 'CloseHandle:'+str(target);FAULTS.append('close_'+str(target))
            with self.assertRaises(w.m.HostUnresolved):w.m.close(w.host)
            self.assertTrue(all(state[1]<=1 for state in w.provider_root()['states'].values()))
            if target!='view':self.assertTrue(w.k.unmapped)
            self.assertGreaterEqual(len(w.k.closed),4)

    def test_28_close_success_then_exception_never_retries(self):
        w=F.World();w.bound();w.k.after='CloseHandle:202'
        with self.assertRaises(w.m.HostUnresolved) as first:w.m.close(w.host)
        before=list(w.k.calls)
        with self.assertRaises(w.m.HostUnresolved) as second:w.m.close(w.host)
        self.assertIs(first.exception,second.exception);self.assertEqual(before,w.k.calls);self.assertIn(202,w.k.closed)

    def test_29_close_witness_unknown_retains_uncertainty(self):
        w=F.World();w.bound();w.k.unknown_witness=202
        with self.assertRaises(w.m.HostUnresolved):w.m.close(w.host)
        self.assertEqual(w.provider_root()['states']['process'],['UNCERTAIN',1])

    def test_30_invalid_witness_request_cannot_poison_unissued_state(self):
        w=F.World();w.bound();before=copy.deepcopy(w.provider_root()['states'])
        for name,value in (('missing',1),('process',999),('process',202)):
            with self.assertRaises(ValueError):w.p.closed_witness(w.provider,name,value)
        self.assertEqual(before,w.provider_root()['states']);w.m.close(w.host)

    def test_31_quiet_is_single_attempt(self):
        w=F.World();w.bound();root=w.provider_root();w.p.terminate(w.provider,dict(root['handles']))
        first=w.p.quiet(w.provider,dict(root['handles']),105.0);before=list(w.k.calls)
        with self.assertRaises(ValueError):w.p.quiet(w.provider,dict(root['handles']),105.0)
        self.assertEqual(before,w.k.calls);self.assertEqual(root['quiet'][2],w.p.canonical(first))

    def test_32_job_only_constructor_failure_requires_zero_member_quiet(self):
        w=F.World();w.k.fail='SetInformationJobObject';self.failed_prepare(w)
        self.assertEqual(w.p.decode(w.provider_root()['quiet'][2])['member_identities'],[]);self.assertIn(201,w.k.closed)

    def test_33_clock_reentry_stops_before_native_effects(self):
        w=F.World();w.acked();fired=[]
        def clock():
            if not fired:
                fired.append(True)
                try:w.p.resource_snapshot(w.provider)
                except ValueError:pass
            return 100.0
        root=dict(w.provider._root);root['clock']=clock;object.__setattr__(w.provider,'_root',tuple(root.items()))
        with self.assertRaises(w.m.HostUnresolved):w.m.prepare(w.host)
        self.assertEqual(w.k.calls,[])

    def test_34_native_reentry_preserves_primary_and_partial_info_cleanup(self):
        w=F.World()
        def hook(name,args):
            if name=='CreateProcessW':
                try:w.p.resource_snapshot(w.provider)
                except ValueError:pass
        w.k.hook=hook;self.failed_prepare(w)
        self.assertTrue(w.k.info_written);self.assertIn(202,w.k.closed);self.assertTrue(w.k.unmapped)

    def test_35_census_timeout_still_issues_stop(self):
        w=F.World();w.active();w.k.add_member()
        def hook(name,args):
            if name=='OpenProcess':w.now=101.0
        w.k.hook=hook
        with self.assertRaises(w.m.HostUnresolved):w.m.close(w.host)
        self.assertEqual(w.k.count('TerminateJobObject'),1);self.assertIn(301,w.k.closed)

    def test_36_metadata_drift_blocks_that_leaf_only(self):
        w=F.World();w.bound();w.k.leaves['UnmapViewOfFile'].restype=object
        with self.assertRaises(w.m.HostUnresolved):w.m.close(w.host)
        self.assertEqual(w.k.count('UnmapViewOfFile'),0);self.assertTrue({101,102,201,202,203}<=w.k.closed)

    def test_37_provider_cannot_be_copied_serialized_or_deleted(self):
        w=F.World()
        for fn in (lambda:copy.copy(w.provider),lambda:copy.deepcopy(w.provider),lambda:pickle.dumps(w.provider),lambda:delattr(w.provider,'_root')):
            with self.assertRaises(TypeError):fn()

    def test_38_process_info_observer_republishes_held_outputs(self):
        w=F.World();w.bound();root=w.provider_root();root['handles']['process']=None;root['handles']['thread']=None
        snapshot,pending=w.p.resource_snapshot(w.provider)
        self.assertEqual(dict(snapshot)['process'],202);self.assertEqual(dict(snapshot)['thread'],203);self.assertEqual(pending,())
        w.m.close(w.host)

    def test_39_return_before_first_handle_capture_remains_explicitly_unresolved(self):
        w=F.World();w.k.after='CreateFileMappingW';self.failed_prepare(w)
        self.assertEqual(w.root()['state'][0],'UNRESOLVED');self.assertEqual(w.provider_root()['endpoint'][0],'UNCERTAIN')
        self.assertNotIn(101,w.k.closed)  # Known gap, synthetic only; no physical HANDLE exists.

    def test_40_active_census_cannot_reopen_after_terminal_quiet(self):
        w=F.World();w.bound();w.m.close(w.host);before=list(w.k.calls)
        with self.assertRaises(ValueError):w.p.capture_members(w.provider)
        self.assertEqual(before,w.k.calls)

    def test_41_cleanup_reentry_is_new_failure_but_other_resources_close(self):
        w=F.World();w.bound()
        def hook(name,args):
            if name=='CloseHandle' and args[0]==202:
                try:w.p.resource_snapshot(w.provider)
                except ValueError:pass
        w.k.hook=hook
        with self.assertRaises(w.m.HostUnresolved):w.m.close(w.host)
        self.assertEqual(w.provider_root()['states']['process'],['UNCERTAIN',1])
        self.assertTrue({101,102,201,202,203}<=w.k.closed);self.assertTrue(w.k.unmapped)

    def test_42_sticky_reentry_cannot_open_more_member_handles(self):
        w=F.World();w.active();w.k.add_member()
        def hook(name,args):
            if name=='GetProcessTimes' and args[0]==301:
                try:w.p.resource_snapshot(w.provider)
                except ValueError:pass
        w.k.hook=hook
        with self.assertRaises(ValueError):w.p.capture_members(w.provider)
        w.k.hook=None;before=list(w.k.calls);records=len(w.provider_root()['member_records'])
        with self.assertRaises(ValueError):w.p.capture_members(w.provider)
        self.assertEqual(before,w.k.calls);self.assertEqual(records,len(w.provider_root()['member_records']))
        with self.assertRaises(w.m.HostUnresolved):w.m.close(w.host)
        self.assertEqual(w.root()['state'][0],'UNRESOLVED');self.assertIn(202,w.k.closed)


def contract():
    assert len(FAULTS)==len(set(FAULTS))==20
    return dict(schema='staged_saved_F_windows_resources_synthetic_contract_v1',synthetic_only=True,
        private_gates_removed=['_mechanical_host','_mechanical_resources'],test_methods=42,fault_cases=sorted(FAULTS),
        resource_source_bodies_executed=True,full_host_protocol_connected_in_private_copy=True,
        ctypes_memory_buffers_synthetic=True,
        native_return_gap_explicit_unresolved=True,ephemeral_member_gap_explicit_unresolved=True,
        native_equivalence_verified=False,source_authenticated_host_issuer=False,full_role_entry_connected=False,
        physical_host_provider_implemented=False,actual_entry_authenticated=False,real_broker_cancel_ack_verified=False,
        real_transport_payload_equivalence_verified=False,core51_full_manifest_validated=False,new_startup_profile_verified=False,
        native_return_to_publication_window_verified=False,continuous_RSS_measured=False,
        project_native_calls=0,source49_modules_executed=0,P1_reads=0,validation_child_processes=0,target_child_processes=0,
        native_authorized=False,public_P2_execution_enabled=False,resource_admission=False,run_authority=False,actual_F=False,formal_result=False)
