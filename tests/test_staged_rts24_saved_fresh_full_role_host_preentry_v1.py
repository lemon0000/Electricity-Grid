"""Private synthetic effect domain for the exact host orchestration bodies."""
import ast
import copy
import ctypes
import importlib.util
import json
import os
from pathlib import Path
from types import ModuleType, SimpleNamespace
import unittest

ROOT = Path(__file__).absolute().parents[1]
SOURCE = ROOT/'experiments/staged_rts24_saved_fresh_full_role_host_preentry_v1.py'
CONTROL = ROOT/'results/tables/staged_rts24_saved_fresh_machinery_transition_v1_non_authoritative/checks_01/admission_repair.json'
EP_PATH = ROOT/'tests/saved_fresh_endpoint_fixture_v1.py'
FAULT_CASES = []


def load(path, name):
    spec = importlib.util.spec_from_file_location(name,path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


def private_copy():
    tree = ast.parse(SOURCE.read_bytes()); changed = []
    for node in tree.body:
        if type(node) is ast.FunctionDef and node.name == '_mechanical_host':
            assert type(node.body[0]) is ast.Raise and node.body[0].exc.func.id == 'FullHostUnavailable'
            del node.body[0]; changed.append(node.name)
    assert changed == ['_mechanical_host']
    module = ModuleType('_synthetic_full_host'); module.__file__ = str(SOURCE)
    exec(compile(tree,str(SOURCE),'exec',dont_inherit=True,optimize=0),vars(module))
    return module


class World:
    def __init__(self, module=None):
        self.m = m = module or private_copy()
        self.now = 100.0; self.events = []; self.files = {}; self.image = None
        self.fail = None; self.callback = None; self.closed = []; self.context_count = 0
        self.child = dict(pid=os.getpid(),creation_filetime=1234567890)
        self.resume_value = 1; self.accepted = True; self.quiet_ok = True
        self.error = RuntimeError('held synthetic primary')
        pins = json.loads(CONTROL.read_bytes())['source_pins']
        inputs = {f'synthetic/{n:04d}.json':m.pin(b'synthetic') for n in range(683)}
        caller = dict(files=inputs,source=pins)
        self.context = dict(schema='staged_rts24_saved_P1_fresh_context_development_v1',authority=m.AUTHORITY,scope=m.SCOPE,
            repo_root=str(ROOT),input_root=str(m.P1),output_root=str(m.ENTRY_ROOT/'synthetic_full_F'),
            source_pins=pins,executable=dict(path=str(Path('D:/Miniconda3/envs/compute/python.exe')),pin=m.pin(b'exe'),identity=[1,2,3,4],python='synthetic'),
            environment=dict(PATH='synthetic',PYTHONHASHSEED='0'),anchor_sha='c6a25cd96c8a4a2cf293d41fe51bc7905db63fbc35253076f97e9239a4f22473',
            input_files=inputs,invocation_started=100.0,deadline=280.0,stage_seconds=m.STAGES,limits=m.CAPS,
            inherited_sources_pin=m.pin(b'synthetic inherited'),caller_core=caller,caller_sha=m.digest(caller),
            output_mode='saved_P1_F_validation',output_parent_directories=[[str(m.ENTRY_ROOT),[1,2,3,4]]],**{key:False for key in m.GATES})
        self.context_raw = m.canonical(self.context)
        self.request = dict(schema='staged_saved_F_full_host_request_v1',authority=m.AUTHORITY,scope=m.SCOPE,role='controller',
            context_pin=m.pin(self.context_raw),source_epoch=m.SOURCE_EPOCH,invocation_started=100.0,deadline=280.0,
            nonce='3'*64,host_identity=dict(pid=1,creation_filetime=11),broker_identity=dict(pid=2,creation_filetime=22))
        self.request_raw = m.canonical(self.request)
        self.transport = b'print("synthetic transport never executed")'; self.payload = b'synthetic payload never executed'
        self.template = dict(schema='staged_saved_F_complete_bootstrap_manifest_v2',authority=m.AUTHORITY,nonce='3'*32,
            source_pins=pins,source_epoch=m.SOURCE_EPOCH,bootstrap_pin=m.pin(self.transport),executable_pin=self.context['executable']['pin'],
            python='synthetic',environment=self.context['environment'],cwd=str(ROOT),initial_paths=[],selected_runtime_file_observations={},
            startup_absent=[],startup_profile=None,namespace_helper={},import_helper={},import_policy={},import_profile=None,
            producer_helpers={},graph_contract={},case='discovery')
        self.template_raw = m.canonical(self.template)
        self.host = m._mechanical_host(self.request_raw,self.context_raw,self.template_raw,self.transport,self.payload,
            tuple(getattr(self,name) for name in m.EFFECTS))

    def hit(self, name):
        self.events.append(name)
        if self.callback: self.callback(name)
        if self.fail == name: raise self.error

    def clock(self): return self.now
    def check_context(self, raw):
        assert raw == self.context_raw
        self.context_count += 1; self.hit('context_'+str(self.context_count)); return True
    def check_manifest(self, raw):
        self.hit('check_manifest'); value=self.m.decode(raw)
        assert value['pre_manifest_binding']['context_sha'] == self.m.pin(self.context_raw)['sha256']; return True
    def check_transport(self, transport, payload):
        self.hit('check_transport');assert transport==self.transport and payload==self.payload;return True
    def receipt(self,path):return dict(path=path,pin=self.m.pin(self.files[path]),identity=[1,2,3,len(self.files[path])],create_only=True)
    def publish(self, path, raw):
        self.hit('publish_before'); assert path not in self.files
        self.files[path] = raw; self.hit('publish_after'); return self.receipt(path)
    def published_read(self,path):self.hit('published_read');return self.files[path],self.receipt(path)
    def endpoint_create(self, escrow, raw):
        descriptor = self.m.decode(raw); assert descriptor['context_sha'] == self.m.pin(self.context_raw)['sha256']
        for name,number in (('mapping',101),('mutex',102),('view',103)):
            self.hit('before_'+name); escrow[name]=number; self.hit('after_'+name)
    def create_suspended(self, escrow, argv, cwd, env, limits):
        self.hit('create_before'); assert tuple(self.m.decode(self.m.canonical(list(argv)))) == argv
        assert cwd == str(ROOT) and env == self.m.canonical(self.context['environment']) and limits == self.m.canonical(self.context['limits'])
        for name,number in (('job',201),('process',202),('thread',203)):
            self.hit('before_'+name); escrow[name]=number; self.hit('after_'+name)
        self.hit('create_after')
    def child_identity(self, escrow): self.hit('child_identity'); return dict(self.child)
    def endpoint_commit(self, escrow, header):
        self.hit('commit_before'); self.image=header+b'\0'*(69632-4096); self.hit('commit_after'); return True
    def endpoint_read(self, escrow): self.hit('endpoint_read'); return self.image
    def accept_binding(self, binding, ack): self.hit('accept_binding'); return self.accepted
    def resume(self, escrow):
        assert self.root()['release'] == ['ISSUED',1]
        self.hit('resume'); return self.resume_value
    def terminate(self, escrow):
        assert self.root()['termination'] == ['ISSUED',1]
        self.hit('terminate'); return True
    def quiet(self, escrow, deadline):
        self.hit('quiet'); self.quiet_deadline=deadline
        members=[dict(self.child)] if 'process' in escrow or 'thread' in escrow else []
        return dict(complete=self.quiet_ok,job_handle=escrow['job'],member_identities=members,
            active_processes=0,retained_handles_signaled=True,observed_total=len(members),observed_count=len(members),final_pids=[])
    def close(self, name, handle):
        assert self.root()['close_states'][name] == ['ISSUED',1]
        self.hit('close_'+name); self.closed.append((name,handle)); return True
    def closed_witness(self, name, handle): self.hit('witness_'+name); return True
    def root(self): return dict(object.__getattribute__(self.host,'_anchor'))
    def acked(self):
        raw=self.m.offer(self.host); ack=self.m.ack_bytes(self.request_raw,self.context_raw,raw)
        self.m.acknowledge(self.host,ack); return ack
    def bound(self): self.acked(); return self.m.prepare(self.host)
    def active(self):
        raw=self.bound(); self.m.release(self.host,self.m.release_ack_bytes(raw)); return raw


class HostTests(unittest.TestCase):
    def test_01_public_and_mechanical_issuers_remain_closed(self):
        m=load(SOURCE,'_original_closed_host')
        for call in (lambda:m.Host(),lambda:m.open_full_role_host(),lambda:m._mechanical_host(None,None,None,None,None,None)):
            with self.assertRaises(m.FullHostUnavailable):call()

    def test_02_full_context_preserves_683_inputs_and_49_sources(self):
        w=World(); context=w.m.context_data(w.context_raw)
        self.assertEqual(len(context['input_files']),683); self.assertEqual(len(context['source_pins']),49)
        self.assertEqual(context['caller_core']['files'],context['input_files']); w.m.close(w.host)

    def test_03_probe_clock_and_reset_clock_are_rejected(self):
        w=World()
        for field,value in (('deadline',108.0),('invocation_started',101.0),('deadline',float('inf'))):
            with self.subTest(field=field,value=value):
                data=dict(w.context); data[field]=value
                with self.assertRaises(ValueError):w.m.context_data(w.m.canonical(data))

    def test_04_missing_inputs_or_changed_caller_are_rejected(self):
        w=World()
        for kind in ('input','caller','source'):
            data=copy.deepcopy(w.context)
            if kind=='input':data['input_files'].pop(next(iter(data['input_files'])))
            elif kind=='source':data['source_pins'].pop(next(iter(data['source_pins'])))
            else:data['caller_sha']='0'*64
            with self.assertRaises(ValueError):w.m.context_data(w.m.canonical(data))

    def test_05_full_context_cannot_grant_authority(self):
        w=World()
        for name in w.m.GATES:
            data=dict(w.context);data[name]=True
            with self.assertRaises(ValueError):w.m.context_data(w.m.canonical(data))

    def test_06_offer_and_ack_tamper_reject_before_effects(self):
        w=World();raw=w.m.offer(w.host); data=w.m.decode(raw);data['deadline']=108.0
        with self.assertRaises(ValueError):w.m.ack_bytes(w.request_raw,w.context_raw,w.m.canonical(data))
        with self.assertRaises(w.m.HostUnresolved):w.m.acknowledge(w.host,b'{}')
        self.assertEqual(w.events,['context_1']);self.assertFalse(w.files)

    def test_07_forward_hash_dag_and_actual_quoted_argv(self):
        w=World();binding=w.m.decode(w.bound()); built=w.root()['built'][0]
        manifest=w.m.decode(built['manifest']);desc=binding['descriptor']
        self.assertNotIn('manifest_sha',manifest['pre_manifest_binding']); self.assertNotIn('owner_pid',manifest)
        self.assertEqual(desc['manifest_sha'],w.m.pin(built['manifest'])['sha256'])
        self.assertEqual(desc['ack_sha'],w.m.pin(w.root()['ack'][0])['sha256'])
        self.assertEqual(built['utf16_units'],len(built['command'].encode('utf-16-le'))//2+1)
        self.assertEqual(built['argv'][17:],[100.0.hex(),280.0.hex()]);w.m.close(w.host)

    def test_08_utf16_capacity_counts_quotes_and_nul(self):
        w=World();offer=w.m.offer_bytes(w.request_raw,w.context_raw);ack=w.m.ack_bytes(w.request_raw,w.context_raw,offer)
        raw=('"\\'*15000).encode();template=dict(w.template);template['bootstrap_pin']=w.m.pin(raw)
        with self.assertRaisesRegex(ValueError,'command line'):
            w.m.artifacts(w.request_raw,w.context_raw,offer,ack,w.m.canonical(template),raw,w.payload)

    def test_09_independent_header_framing_oracle(self):
        w=World();w.bound();header=w.image[:4096];length=int.from_bytes(header[:4],'little')
        raw=header[4:4+length];parsed=json.loads(raw)
        self.assertEqual(header[4+length:-40],bytes(4052-length));self.assertEqual(header[-8:],b'FEPv1OK!')
        import hashlib
        self.assertEqual(header[-40:-8],hashlib.sha256(raw).digest())
        self.assertEqual(parsed['owner_pid'],os.getpid());self.assertEqual(w.image[4096:],bytes(65536));w.m.close(w.host)

    def test_10_unchanged_core51_consumes_host_header(self):
        w=World();w.bound();ep=load(EP_PATH,'_host_core_fixture');core=ep.load_core();k=ep.Kernel(core)
        k.descriptor=w.root()['built'][0]['descriptor'];k.header=w.m.decode(w.image[4:4+int.from_bytes(w.image[:4],'little')])
        k.write_header();core.time=SimpleNamespace(monotonic=lambda:100.0)
        core.sys=SimpleNamespace(orig_argv=w.root()['built'][0]['argv'])
        lease=k.acquire();core.bookend_pre_manifest_endpoint(lease);k.close();w.m.close(w.host)

    def test_11_success_order_and_single_release(self):
        w=World();w.active();w.m.close(w.host)
        for left,right in (('publish_after','before_mapping'),('after_view','create_before'),('create_after','commit_before'),
                           ('commit_after','accept_binding'),('accept_binding','resume'),('terminate','quiet'),('quiet','close_thread'),('close_job','close_view')):
            self.assertLess(w.events.index(left),w.events.index(right))
        self.assertEqual(w.events.count('resume'),1);self.assertEqual(len(w.closed),6)

    def test_12_no_ack_cannot_create_or_release(self):
        w=World();w.m.offer(w.host)
        with self.assertRaises(ValueError):w.m.prepare(w.host)
        with self.assertRaises(ValueError):w.m.release(w.host,b'{}')
        self.assertEqual(w.events,['context_1']);w.m.close(w.host)

    def test_13_external_host_rejection_cleans_suspended_child(self):
        w=World();binding=w.bound();w.accepted=False
        with self.assertRaises(w.m.HostUnresolved):w.m.release(w.host,w.m.release_ack_bytes(binding))
        self.assertNotIn('resume',w.events);self.assertEqual(len(w.closed),6)

    def test_14_original_deadline_expiry_never_reopens_clock(self):
        w=World();binding=w.bound();w.now=281.0
        with self.assertRaises(w.m.HostUnresolved) as caught:w.m.release(w.host,w.m.release_ack_bytes(binding))
        self.assertNotIn('resume',w.events);self.assertIn('terminate',w.events);self.assertNotIn('quiet',w.events)
        self.assertFalse(w.closed);self.assertEqual(w.root()['deadline'],280.0)
        self.assertIn('quiet',[name for name,_ in caught.exception.secondary])

    def test_15_full_source_bookend_failure_before_release(self):
        w=World();binding=w.bound();w.fail='context_3'
        with self.assertRaises(w.m.HostUnresolved) as caught:w.m.release(w.host,w.m.release_ack_bytes(binding))
        self.assertIs(caught.exception.primary,w.error);self.assertNotIn('resume',w.events);self.assertEqual(len(w.closed),6)

    def test_16_partial_endpoint_acquisitions_are_retained(self):
        for name,count in (('mapping',1),('mutex',2),('view',3)):
            w=World();w.acked();w.fail='after_'+name;FAULT_CASES.append(w.fail)
            with self.assertRaises(w.m.HostUnresolved) as caught:w.m.prepare(w.host)
            self.assertIs(caught.exception.primary,w.error);self.assertEqual(len(w.closed),count)
            self.assertNotIn('create_before',w.events)

    def test_17_partial_child_acquisitions_cleanup_before_endpoint(self):
        for name,count in (('job',4),('process',5),('thread',6)):
            w=World();w.acked();w.fail='after_'+name;FAULT_CASES.append(w.fail)
            with self.assertRaises(w.m.HostUnresolved):w.m.prepare(w.host)
            self.assertEqual(len(w.closed),count);self.assertLess(w.events.index('quiet'),w.events.index('close_view'))

    def test_18_prepare_commit_failure_matrix(self):
        for effect in ('context_2','check_manifest','publish_before','publish_after','before_mapping','create_before',
                       'create_after','child_identity','commit_before','commit_after','endpoint_read'):
            w=World();w.acked();w.fail=effect;FAULT_CASES.append(effect)
            with self.assertRaises(w.m.HostUnresolved) as caught:w.m.prepare(w.host)
            self.assertIs(caught.exception.primary,w.error);self.assertNotIn('resume',w.events)
            self.assertEqual(len(w.closed),0 if effect=='child_identity' else len(w.root()['acquisitions']))
            if effect=='publish_after':self.assertEqual(len(w.files),1)

    def test_19_resume_uncertainty_is_issued_once_then_quiet(self):
        w=World();binding=w.bound();w.fail='resume'
        with self.assertRaises(w.m.HostUnresolved) as caught:w.m.release(w.host,w.m.release_ack_bytes(binding))
        self.assertIs(caught.exception.primary,w.error);self.assertEqual(w.root()['release'],['UNCERTAIN',1])
        before=list(w.events)
        with self.assertRaises(w.m.HostUnresolved) as again:w.m.close(w.host)
        self.assertIs(caught.exception,again.exception);self.assertEqual(before,w.events)

    def test_20_wrong_suspend_count_is_uncertain(self):
        for value in (0,2,0xffffffff):
            w=World();binding=w.bound();w.resume_value=value
            with self.assertRaises(w.m.HostUnresolved):w.m.release(w.host,w.m.release_ack_bytes(binding))
            self.assertEqual(w.root()['release'],['UNCERTAIN',1]);self.assertEqual(len(w.closed),6)

    def test_21_second_release_cannot_repeat_native_effect(self):
        w=World();binding=w.active();before=list(w.events)
        with self.assertRaises(ValueError):w.m.release(w.host,w.m.release_ack_bytes(binding))
        self.assertEqual(before,w.events);w.m.close(w.host)

    def test_22_termination_uncertain_still_observes_quiet(self):
        w=World();w.bound();w.fail='terminate'
        with self.assertRaises(w.m.HostUnresolved) as caught:w.m.close(w.host)
        self.assertEqual(w.root()['termination'],['UNCERTAIN',1]);self.assertEqual(len(w.closed),6)
        self.assertIs(caught.exception.secondary[0][1],w.error)

    def test_23_unproven_quiet_retains_all_resources(self):
        w=World();w.bound();w.quiet_ok=False
        with self.assertRaises(w.m.HostUnresolved):w.m.close(w.host)
        self.assertFalse(w.closed);self.assertEqual(len(w.root()['acquisitions']),6)

    def test_24_quiet_deadline_clamped_to_original(self):
        w=World();w.bound();w.now=279.0;w.m.close(w.host)
        self.assertEqual(w.quiet_deadline,280.0)

    def test_25_each_close_failure_continues_other_resources(self):
        for name in ('thread','process','job','view','mutex','mapping'):
            w=World();w.bound();w.fail='close_'+name;FAULT_CASES.append(w.fail)
            with self.assertRaises(w.m.HostUnresolved):w.m.close(w.host)
            self.assertEqual(w.root()['close_states'][name],['UNCERTAIN',1]);self.assertEqual(len(w.closed),5)
            before=list(w.events)
            with self.assertRaises(w.m.HostUnresolved):w.m.close(w.host)
            self.assertEqual(before,w.events)

    def test_26_close_witness_failure_never_retries(self):
        w=World();w.bound();w.fail='witness_process'
        with self.assertRaises(w.m.HostUnresolved):w.m.close(w.host)
        self.assertEqual(len(w.closed),6);self.assertEqual(w.root()['close_states']['process'],['UNCERTAIN',1])

    def test_27_host_cannot_be_copied_serialized_or_rebound(self):
        import pickle
        w=World()
        for call in (lambda:copy.copy(w.host),lambda:copy.deepcopy(w.host),lambda:pickle.dumps(w.host),lambda:setattr(w.host,'_anchor',()),lambda:delattr(w.host,'_anchor')):
            with self.assertRaises(TypeError):call()
        w.m.close(w.host)

    def test_28_resource_drift_preserves_original_cleanup_roots(self):
        w=World();binding=w.bound();w.root()['escrow']['process']=999
        with self.assertRaises(w.m.HostUnresolved):w.m.release(w.host,w.m.release_ack_bytes(binding))
        self.assertIn(('process',202),w.closed);self.assertNotIn(('process',999),w.closed);self.assertNotIn('resume',w.events)

    def test_29_swallowed_reentrant_close_still_poisoned(self):
        w=World();w.bound();seen=[]
        def callback(name):
            if name=='close_thread':
                try:w.m.close(w.host)
                except ValueError as error:seen.append(error)
        w.callback=callback
        with self.assertRaises(w.m.HostUnresolved) as caught:w.m.close(w.host)
        self.assertEqual(len(seen),1);self.assertIn(('reentry',seen[0]),caught.exception.secondary);self.assertEqual(len(w.closed),6)

    def test_30_terminal_drift_fails_without_reclosing(self):
        w=World();w.bound();w.m.close(w.host);before=list(w.events);w.root()['escrow']['view']=999
        with self.assertRaises(w.m.HostUnresolved):w.m.close(w.host)
        self.assertEqual(before,w.events)

    def test_31_failed_prepare_preserves_manifest_and_cannot_retry(self):
        w=World();w.acked();w.fail='create_after'
        with self.assertRaises(w.m.HostUnresolved):w.m.prepare(w.host)
        before=list(w.events);self.assertEqual(len(w.files),1)
        with self.assertRaises(w.m.HostUnresolved):w.m.prepare(w.host)
        self.assertEqual(before,w.events)

    def test_32_changed_endpoint_or_child_blocks_release(self):
        for which in ('header','identity'):
            w=World();binding=w.bound()
            if which=='header':w.image=w.image[:-1]+b'x'
            else:w.child['creation_filetime']+=1
            with self.assertRaises(w.m.HostUnresolved):w.m.release(w.host,w.m.release_ack_bytes(binding))
            self.assertNotIn('resume',w.events);self.assertEqual(len(w.closed),6 if which=='header' else 0)

    def test_33_swallowed_effect_reentry_cannot_revive_state(self):
        for effect in ('context_1','check_manifest','publish_after','commit_after','accept_binding','resume'):
            w=World();seen=[]
            def callback(name):
                if name==effect:
                    try:w.m.close(w.host)
                    except ValueError as error:seen.append(error)
            w.callback=callback
            with self.assertRaises(w.m.HostUnresolved):w.active()
            self.assertEqual(len(seen),1);self.assertEqual(w.root()['state'][0],'UNRESOLVED')
            self.assertNotEqual(w.root()['release'][0],'DONE')

    def test_34_clock_regression_cannot_extend_original_window(self):
        w=World();binding=w.bound();w.now=99.0
        with self.assertRaises(w.m.HostUnresolved):w.m.release(w.host,w.m.release_ack_bytes(binding))
        self.assertNotIn('resume',w.events);self.assertFalse(w.closed)

    def test_35_original_prepare_and_failure_reservations(self):
        w=World();binding=w.bound();w.now=110.0
        with self.assertRaises(w.m.HostUnresolved):w.m.release(w.host,w.m.release_ack_bytes(binding))
        self.assertNotIn('resume',w.events);self.assertEqual(len(w.closed),6)
        self.assertEqual(w.root()['cleanup_deadline'][0],125.0)

    def test_36_missing_job_never_accepts_quiet_or_closes(self):
        w=World();w.acked()
        def create(escrow,*args):escrow['process']=202;raise w.error
        effects=list(w.root()['effects']);effects[w.m.EFFECTS.index('create_suspended')]=create
        anchor=dict(w.host._anchor);anchor['effects']=tuple(effects);object.__setattr__(w.host,'_anchor',tuple(anchor.items()))
        with self.assertRaises(w.m.HostUnresolved):w.m.prepare(w.host)
        self.assertNotIn('quiet',w.events);self.assertFalse(w.closed)

    def test_37_quiet_must_bind_original_child_and_job(self):
        for mode in ('member','job','member_cap'):
            w=World();w.bound();original=w.quiet
            def quiet(escrow,deadline):
                row=original(escrow,deadline)
                if mode=='member':row['member_identities'][0]['creation_filetime']+=1
                elif mode=='job':row['job_handle']+=1
                else:
                    row['member_identities']=[dict(w.child)]+[dict(pid=500+n,creation_filetime=100+n) for n in range(1024)]
                    row['observed_count']=row['observed_total']=1025
                return row
            effects=list(w.root()['effects']);effects[w.m.EFFECTS.index('quiet')]=quiet
            anchor=dict(w.host._anchor);anchor['effects']=tuple(effects);object.__setattr__(w.host,'_anchor',tuple(anchor.items()))
            with self.assertRaises(w.m.HostUnresolved):w.m.close(w.host)
            self.assertFalse(w.closed)

    def test_38_publication_drift_rejected_before_host_acceptance(self):
        w=World();binding=w.bound();path=next(iter(w.files));w.files[path]+=b' '
        with self.assertRaises(w.m.HostUnresolved):w.m.release(w.host,w.m.release_ack_bytes(binding))
        self.assertNotIn('accept_binding',w.events);self.assertNotIn('resume',w.events);self.assertEqual(len(w.files),1)

    def test_39_transport_equivalence_effect_required_before_publication(self):
        w=World();w.acked();w.fail='check_transport'
        with self.assertRaises(w.m.HostUnresolved):w.m.prepare(w.host)
        self.assertFalse(w.files);self.assertFalse(w.closed)

    def test_40_nested_launch_cannot_reuse_outer_prepare_reservation(self):
        w=World();request=dict(w.request);request['role']='fresh'
        with self.assertRaises(w.m.FullHostUnavailable):w.m.open_full_role_host(w.m.canonical(request))
        with self.assertRaisesRegex(ValueError,'outer prepare'):
            w.m._mechanical_host(w.m.canonical(request),w.context_raw,w.template_raw,w.transport,w.payload,tuple(getattr(w,n) for n in w.m.EFFECTS))

    def test_41_duplicate_kernel_handles_do_not_close_twice(self):
        w=World();w.acked()
        def callback(name):
            if name=='after_mutex':w.root()['escrow']['mutex']=101
        w.callback=callback
        with self.assertRaises(w.m.HostUnresolved):w.m.prepare(w.host)
        self.assertEqual(w.closed,[('view',103),('mapping',101)])
        other=World();other.acked()
        def collide(name):
            if name=='after_view':other.root()['escrow']['view']=101
        other.callback=collide;other.m.prepare(other.host);other.m.close(other.host)
        self.assertIn(('view',101),other.closed);self.assertIn(('mapping',101),other.closed);self.assertEqual(len(other.closed),6)

    def test_42_artifact_drift_between_calls_cleans_original_resources(self):
        w=World();binding=w.bound();w.root()['built'][0]['argv'][0]='changed'
        with self.assertRaises(w.m.HostUnresolved):w.m.release(w.host,w.m.release_ack_bytes(binding))
        self.assertNotIn('accept_binding',w.events);self.assertEqual(len(w.closed),6)

    def test_43_nonce_and_native_identity_widths(self):
        w=World();offer=w.m.offer_bytes(w.request_raw,w.context_raw);ack=w.m.ack_bytes(w.request_raw,w.context_raw,offer)
        template=dict(w.template);template['nonce']='4'*32
        with self.assertRaises(ValueError):w.m.artifacts(w.request_raw,w.context_raw,offer,ack,w.m.canonical(template),w.transport,w.payload)
        for child in (dict(pid=2**32,creation_filetime=1),dict(pid=1,creation_filetime=2**64)):
            with self.assertRaises(ValueError):w.m.identity(child)

    def test_44_accepted_binding_expiry_retains_responsibility_without_resume(self):
        w=World();binding=w.bound()
        def callback(name):
            if name=='accept_binding':w.now=111.0
        w.callback=callback
        with self.assertRaises(w.m.HostUnresolved):w.m.release(w.host,w.m.release_ack_bytes(binding))
        self.assertEqual(w.root()['acceptance'],['DONE',1]);self.assertNotIn('resume',w.events);self.assertEqual(len(w.closed),6)

    def test_45_publication_readback_failure_is_uncertain_and_preserved(self):
        for fail in ('publish_after','published_read','invalid_receipt'):
            w=World();w.acked()
            if fail=='invalid_receipt':
                def publish(path,raw):
                    receipt=w.publish(path,raw);receipt['create_only']=False;return receipt
                effects=list(w.root()['effects']);effects[w.m.EFFECTS.index('publish')]=publish
                anchor=dict(w.host._anchor);anchor['effects']=tuple(effects);object.__setattr__(w.host,'_anchor',tuple(anchor.items()))
            else:w.fail=fail
            with self.assertRaises(w.m.HostUnresolved):w.m.prepare(w.host)
            self.assertEqual(w.root()['publication_state'][0],'UNCERTAIN');self.assertEqual(len(w.files),1)
            self.assertNotIn('before_mapping',w.events)

    def test_46_acquisition_secondary_cannot_replace_primary(self):
        w=World();w.acked();w.fail='after_view'
        def callback(name):
            if name=='after_mutex':w.root()['escrow']['mutex']=101
        w.callback=callback
        with self.assertRaises(w.m.HostUnresolved) as caught:w.m.prepare(w.host)
        self.assertIs(caught.exception.primary,w.error);self.assertEqual(w.closed,[('view',103),('mapping',101)])


def contract():
    assert len(FAULT_CASES)==23 and len(set(FAULT_CASES))==23
    return dict(schema='staged_saved_F_host_preentry_synthetic_contract_v1',synthetic_only=True,
        private_gate_removed=['_mechanical_host'],fault_cases=sorted(FAULT_CASES),
        physical_host_provider_implemented=False,full_context_bytes_synthetic=True,
        source_authenticated_host_issuer=False,native_return_to_publication_window_verified=False,new_startup_profile_verified=False,
        native_authorized=False,public_P2_execution_enabled=False,
        real_broker_cancel_ack_verified=False,real_transport_payload_equivalence_verified=False,
        core51_full_manifest_validated=False,core51_header_only_interop=True,
        source49_pin_map_from_saved_record=True,source49_modules_executed=0,P1_reads=0,
        project_native_calls=0,target_child_processes=0,validation_child_processes=0,
        actual_entry_authenticated=False,full_role_entry_connected=False,native_equivalence_verified=False,
        run_authority=False,actual_F=False,formal_result=False)
