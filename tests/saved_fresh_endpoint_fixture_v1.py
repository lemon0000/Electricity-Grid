"""Synthetic kernel leaves for the exact Core51 endpoint control flow."""
import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import tempfile
from types import ModuleType

ROOT=Path(__file__).absolute().parents[1]
SOURCE=ROOT/'experiments/staged_rts24_saved_fresh_pre_entry_lease_v51.py'


def load_core(main=False,probe=False):
    raw=SOURCE.read_bytes().replace(b'\r\n',b'\n');prefix,tail=raw.split(b'\nimport builtins\n',1)
    payload=b'import builtins\n'+tail
    if probe:payload+=b'\n'+(ROOT/'experiments/staged_rts24_saved_fresh_pre_manifest_entry_probe_v1.py').read_bytes()
    core=ModuleType('_endpoint_core_fixture');core.__file__=str(SOURCE)
    exec(compile(prefix,'<test_nonmain_prefix>','exec',dont_inherit=True,optimize=0),vars(core))
    if main:
        assert not probe
        core.__name__='__main__'
    exec(compile(payload,'<pre_entry_payload>','exec',dont_inherit=True,optimize=0),vars(core))
    core._TEST_PAYLOAD=payload
    return core


class Kernel:
    def __init__(self,core,fail=None,wait=0,inherit=(),close_fail=(),witness_unknown=()):
        self.core=core;self.fail=fail;self.wait=wait;self.inherit=inherit
        self.close_fail=close_fail;self.witness_unknown=witness_unknown
        self.calls=[];self.closed=set();self.creation=1234567890;self.hook=None
        started=time.monotonic()
        self.descriptor=dict(schema='staged_saved_F_pre_manifest_descriptor_v1',authority='DRAFT_NONAUTHORITATIVE',
            scope='saved_P1_actual_21_and_journal_5h',role='parent',
            manifest_path=str(ROOT/'synthetic-manifest-never-read.json'),manifest_sha='1'*64,
            channel_name='Local\\saved_F_pre_entry_v1_'+'3'*64,channel_nonce='3'*64,
            request_sha='4'*64,offer_sha='5'*64,context_sha='6'*64,ack_sha='7'*64,
            source_epoch=core.SOURCE_SHA,transport_pin=core.pin(b'synthetic-transport'),
            payload_pin=core.pin(core._TEST_PAYLOAD),invocation_started=started,deadline=started+180)
        self.header=dict(schema='staged_saved_F_pre_manifest_header_v1',nonce='3'*64,descriptor=self.descriptor,
            owner_pid=os.getpid(),owner_creation_filetime=self.creation,slots=16,slot_bytes=4096)
        self.buffer=ctypes.create_string_buffer(69632);self.view=ctypes.addressof(self.buffer)
        self.write_header()
        outer=self
        class Leaf:
            def __init__(self,name):self.name=name;self.argtypes=();self.restype=int
            def __call__(self,*args):return outer.call(self.name,args)
        names=('OpenFileMappingW','OpenMutexW','MapViewOfFile','UnmapViewOfFile','WaitForSingleObject',
            'ReleaseMutex','CloseHandle','GetHandleInformation','GetCurrentProcess','GetCurrentProcessId',
            'GetProcessTimes','GetCommandLineW')
        self.leaves={name:Leaf(name) for name in names}
        self.rows=tuple((name,fn,(),int) for name,fn in self.leaves.items())
        core.endpoint_kernel=lambda:(self,self.rows)

    def write_header(self):
        raw=self.core.canonical(self.header)
        assert 0<len(raw)<=4052
        header=len(raw).to_bytes(4,'little')+raw+b'\0'*(4052-len(raw))+self.core.sha256(raw).digest()+b'FEPv1OK!'
        assert len(header)==4096
        ctypes.memmove(self.view,header,4096)

    def call(self,name,args):
        self.calls.append((name,args))
        if self.hook is not None:self.hook(name,args)
        if self.fail==name:
            ctypes.set_last_error(5)
            return 0
        if name=='OpenFileMappingW':return 201
        if name=='OpenMutexW':return 202
        if name=='MapViewOfFile':return self.view
        if name=='WaitForSingleObject':return self.wait
        if name=='ReleaseMutex':return 1
        if name in ('UnmapViewOfFile','CloseHandle'):
            if args[0] in self.close_fail:ctypes.set_last_error(5);return 0
            self.closed.add(args[0]);return 1
        if name=='GetHandleInformation':
            handle,flags=args
            if handle in self.closed:
                ctypes.set_last_error(5 if handle in self.witness_unknown else 6);return 0
            flags._obj.value=1 if handle in self.inherit else 0
            return 1
        if name=='GetCurrentProcess':return -1
        if name=='GetCurrentProcessId':return os.getpid()
        if name=='GetProcessTimes':
            args[1]._obj.dwLowDateTime=self.creation&0xffffffff
            args[1]._obj.dwHighDateTime=self.creation>>32
            return 1
        if name=='GetCommandLineW':return subprocess.list2cmdline(self.core.sys.orig_argv)
        raise AssertionError(name)

    def acquire(self):
        self.owner=object.__new__(self.core.LocalPreEntryLease)
        self.capsule=self.core.capture_pre_manifest_endpoint(self.owner,self.core.canonical(self.descriptor))
        self.anchor=self.owner._endpoint_anchor
        return self.owner

    def close(self,owner=None):
        return self.core.close_pre_manifest_endpoint(self.anchor,self.owner if owner is None else owner)

    def effects(self):
        return [(name,args[0]) for name,args in self.calls if name in ('CloseHandle','UnmapViewOfFile','ReleaseMutex')]


def attach_inputs(core,source,resource):
    """Explicit synthetic first transfer; the runtime transfer under test is unchanged."""
    kernel=Kernel(core);initial=kernel.acquire()
    previous=resource.owner;assert previous is source
    initial._resource=resource
    resource.owner=initial;core.bind_endpoint_resource_once(initial,resource)
    source._endpoint=initial._endpoint;source._endpoint_anchor=initial._endpoint_anchor
    core.endpoint_transfer_record(initial,source,resource);resource.owner=source
    kernel.owner=source
    return kernel


class Factory:
    """Synthetic startup/filesystem/profile leaves around the unchanged Core factory."""
    def __init__(self,fail=None):
        from types import SimpleNamespace
        self.core=core=load_core(True);self.kernel=k=Kernel(core);self.events=[];self.fail=fail
        self.temporary=tempfile.TemporaryDirectory(prefix='saved_F_endpoint_unit_')
        self.manifest=Path(self.temporary.name)/'plan.json';self.manifest.write_bytes(b'{}')
        k.descriptor['manifest_path']=str(self.manifest);k.write_header()
        core._EARLY=dict(active=True,endpoint_ready=False,sources_allowed=False,blocked=[])
        core.sys=SimpleNamespace(**vars(sys));core.sys.orig_argv=['synthetic','-P','-B','-s','-S','-c','synthetic']
        core.sys.modules={name:module for name,module in sys.modules.items()
            if not any(name==p or name.startswith(p+'.') for p in ('src','experiments','tests','numpy','scipy','pyomo','highspy','site','sitecustomize','usercustomize'))}
        core.sys.audit=lambda *args:None
        self.projection={key:value for key,value in k.descriptor.items() if key!='manifest_sha'}
        self.plan=dict(pre_manifest_binding=self.projection,nonce=k.descriptor['channel_nonce'][:32],
            environment=dict(os.environ),cwd=os.getcwd(),initial_paths=list(sys.path),
            bootstrap_pin=core.pin(b'synthetic'),source_pins={f'synthetic_{i}':core.pin(b'source') for i in range(49)},
            executable_pin=core.pin(b'exe'),selected_runtime_file_observations={},startup_absent=[])
        self.raw=core.canonical(self.plan)
        core._PAYLOAD_RAW=core._TEST_PAYLOAD
        core.full_role_entry_binding=lambda:core.canonical(k.descriptor)
        core.check_compiled_namespace=lambda raw:None
        core.check_plan=lambda raw:self.plan
        core.verify_startup_profile=lambda plan:None
        core.install_guard=lambda plan:dict(active=True,self_live=False,events=[],faults=[],runtime_attempted=False)
        def reader(path,pin,**kwargs):
            label='manifest' if str(path)==str(self.manifest) else 'exe' if Path(path)==core.EXE else 'source'
            self.events.append(label)
            assert core._EARLY['endpoint_ready']
            if label=='source':assert core._EARLY['sources_allowed']
            if self.fail==label:raise ValueError('synthetic '+label+' failure')
            return self.raw if label=='manifest' else b'exe' if label=='exe' else b'source'
        core.read_file=reader
        self.closed=set();self.native_calls=[]
        outer=self
        class Leaf:
            def __init__(self,name):self.name=name;self.argtypes=();self.restype=int
            def __call__(self,*args):
                outer.native_calls.append((self.name,args))
                if self.name==outer.fail:ctypes.set_last_error(5);return 0
                if self.name=='GetCurrentProcessId':return os.getpid()
                if self.name=='GetCurrentThreadId':return 7
                if self.name=='OpenProcess':return 101
                if self.name=='OpenThread':return 102
                if self.name=='CloseHandle':outer.closed.add(args[0]);return 1
                if self.name=='GetHandleInformation':ctypes.set_last_error(6);return 0
                raise AssertionError(self.name)
        held={name:(Leaf(name),(),int) for name in ('GetCurrentProcessId','GetCurrentThreadId','OpenProcess','OpenThread','CloseHandle','GetHandleInformation')}
        core.kernel_api=lambda:(object(),held)
        core._Resource.snapshot=lambda resource:dict(image_path=str(core.EXE),command_line_sha=core.pin(subprocess.list2cmdline(core.sys.orig_argv).encode()))

    def open(self):return self.core.open_bound_local_pre_entry_lease()
    def finish(self):self.temporary.cleanup()
