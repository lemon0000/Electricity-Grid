"""Synthetic DLL around prepared Win32 source and the actual host protocol body."""
import ast
import ctypes
import importlib.util
import os
from pathlib import Path
from types import ModuleType,SimpleNamespace

ROOT=Path(__file__).absolute().parents[1]
HOST=ROOT/'experiments/staged_rts24_saved_fresh_full_role_host_preentry_v2.py'
PROVIDER=ROOT/'experiments/staged_rts24_saved_fresh_host_windows_resources_v1.py'
PRIOR=ROOT/'tests/test_staged_rts24_saved_fresh_full_role_host_preentry_v1.py'


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module);return module


def clone(path,name,gate):
    tree=ast.parse(path.read_bytes());changed=[]
    for node in tree.body:
        if type(node) is ast.FunctionDef and node.name==gate:
            assert type(node.body[0]) is ast.Raise;del node.body[0];changed.append(gate)
    assert changed==[gate]
    module=ModuleType(name);module.__file__=str(path)
    exec(compile(tree,str(path),'exec',dont_inherit=True,optimize=0),vars(module));return module


OLD=load(PRIOR,'_windows_prior_fixture')


class Kernel:
    def __init__(self,module):
        self.m=module;self.calls=[];self.closed=set();self.unmapped=False;self.inherit=set()
        self.fail=None;self.after=None;self.hook=None;self.wait=0;self.exists=None;self.unknown_witness=None
        self.error=RuntimeError('synthetic Native return interruption')
        self.buffer=ctypes.create_string_buffer(69632);self.view=ctypes.addressof(self.buffer)
        self.rootpid=os.getpid();self.tid=45678;self.creation=1234567890
        self.processes={};self.active=[];self.total=0;self.terminated=False;self.image=module.EXE
        self.extra=[];self.open_handles={};self.next_handle=301;self.resume_value=1
        self.member_unknown=False;self.accounting_extra=0;self.attribute_deleted=0
        self.info_written=False;self.startup=None;self.leaves={}
        outer=self
        class Leaf:
            def __init__(self,name):self.name=name;self.argtypes=();self.restype=int
            def __call__(self,*args):return outer.call(self.name,args)
        class Library:
            def __getattr__(self,name):
                if name not in outer.leaves:outer.leaves[name]=Leaf(name)
                return outer.leaves[name]
        self.library=Library()

    def label(self,name,args):
        if name=='InitializeProcThreadAttributeList':return 'InitQuery' if args[0] is None else 'InitAttributes'
        if name in ('CloseHandle','GetHandleInformation','WaitForSingleObject','GetProcessTimes'):return name+':'+str(args[0])
        return name

    def call(self,name,args):
        label=self.label(name,args);self.calls.append((name,args))
        if self.hook:self.hook(name,args)
        if self.fail in (name,label):
            ctypes.set_last_error(5);return 0xffffffff if name=='WaitForSingleObject' else 0
        result=self.perform(name,args)
        if self.after in (name,label):raise self.error
        return result

    def perform(self,name,a):
        m=self.m
        if name=='CreateFileMappingW':
            assert a[0].value==ctypes.c_void_p(-1).value and a[1:5]==(None,4,0,69632)
            ctypes.set_last_error(183 if self.exists=='mapping' else 0);return 101
        if name=='CreateMutexW':
            assert a[:2]==(None,False);ctypes.set_last_error(183 if self.exists=='mutex' else 0);return 102
        if name=='MapViewOfFile':assert a==(101,6,0,0,69632);return self.view
        if name=='GetHandleInformation':
            if a[0] in self.closed:
                ctypes.set_last_error(5 if self.unknown_witness==a[0] else 6);return 0
            a[1]._obj.value=int(a[0] in self.inherit);return 1
        if name=='WaitForSingleObject':
            if a[0]==102:return self.wait
            return 0 if self.terminated else 258
        if name=='ReleaseMutex':return 1
        if name=='CreateJobObjectW':assert a==(None,None);return 201
        if name=='SetInformationJobObject':
            assert a[0:2]==(201,9);limit=a[2]._obj
            assert limit.basic.flags==0x2300 and limit.process_memory==1024**3 and limit.job_memory==2*1024**3
            return 1
        if name=='InitializeProcThreadAttributeList':
            assert a[1:3]==(1,0)
            if a[0] is None:a[3]._obj.value=256;ctypes.set_last_error(122);return 0
            return 1
        if name=='UpdateProcThreadAttribute':
            assert a[1:3]==(0,0x2000D) and list(a[3])==[201] and a[4]==ctypes.sizeof(ctypes.c_void_p) and a[5:]==(None,None)
            return 1
        if name=='DeleteProcThreadAttributeList':self.attribute_deleted+=1;return None
        if name=='CreateProcessW':
            assert a[0]==m.EXE and a[2:5]==(None,None,False) and a[5]==0x08080404 and a[7]==str(ROOT)
            startup=a[8]._obj;assert startup.startup.cb==112 and startup.attributes
            self.startup=(a[1].value,ctypes.wstring_at(a[6]),a[5]);info=a[9]._obj
            info.process=202;info.thread=203;info.pid=self.rootpid;info.tid=self.tid;self.info_written=True
            self.processes[202]=(self.rootpid,self.creation);self.active=[self.rootpid];self.total=1;return 1
        if name=='IsProcessInJob':a[2]._obj.value=(a[1]==201 and a[0] in self.processes);return 1
        if name=='GetProcessId':return self.processes[a[0]][0]
        if name=='GetThreadId':assert a[0]==203;return self.tid
        if name=='GetProcessIdOfThread':assert a[0]==203;return self.rootpid
        if name=='GetProcessTimes':
            creation=self.processes[a[0]][1];a[1]._obj.dwLowDateTime=creation&0xffffffff;a[1]._obj.dwHighDateTime=creation>>32;return 1
        if name=='QueryFullProcessImageNameW':a[2].value=self.image;a[3]._obj.value=len(self.image);return 1
        if name=='ResumeThread':assert a[0]==203;return self.resume_value
        if name=='TerminateJobObject':assert a==(201,0xE002);self.terminated=True;self.active=[];return 1
        if name=='QueryInformationJobObject':
            assert a[0]==201
            if a[1]==3:
                count=len(self.active);m.DWORD.from_buffer(a[2],0).value=count;m.DWORD.from_buffer(a[2],4).value=count
                data=(m.SIZE_T*count).from_buffer(a[2],8)
                for i,pid in enumerate(self.active):data[i]=pid
            elif a[1]==1:
                a[2]._obj.total=self.total+self.accounting_extra;a[2]._obj.active=len(self.active)
            else:raise AssertionError(a[1])
            return 1
        if name=='OpenProcess':
            assert a[:2]==(0x101000,False);pid=a[2]
            if self.member_unknown:ctypes.set_last_error(87);return 0
            handle=self.next_handle;self.next_handle+=1;self.closed.discard(handle)
            creation=next(c for p,c in self.extra if p==pid);self.processes[handle]=(pid,creation);self.open_handles[handle]=(pid,creation)
            return handle
        if name=='CloseHandle':self.closed.add(a[0]);return 1
        if name=='UnmapViewOfFile':assert a[0]==self.view;self.unmapped=True;return 1
        if name=='VirtualQuery':a[1]._obj.state=0x10000 if self.unmapped else 0x1000;return ctypes.sizeof(m._MemoryInfo)
        raise AssertionError(name)

    def add_member(self,pid=9001,creation=90001):
        self.extra.append((pid,creation));self.active.append(pid);self.total+=1

    def count(self,name):return sum(n==name for n,_ in self.calls)


class World(OLD.World):
    def __init__(self):
        module=clone(HOST,'_host_v2_private','_mechanical_host')
        self.provider=None;super().__init__(module)
        self.p=clone(PROVIDER,'_windows_resources_private','_mechanical_resources');self.k=Kernel(self.p)
        self.p.C=SimpleNamespace(**vars(ctypes));self.p.C.WinDLL=lambda name,**kw:self.k.library
        self.provider=self.p._mechanical_resources(self.host,100.0,280.0,self.clock)
    def provider_root(self):return dict(object.__getattribute__(self.provider,'_root'))
    def resource_snapshot(self):return self.p.resource_snapshot(self.provider)
    def endpoint_create(self,*args):return self.p.endpoint_create(self.provider,*args)
    def create_suspended(self,*args):return self.p.create_suspended(self.provider,*args)
    def child_identity(self,*args):return self.p.child_identity(self.provider,*args)
    def endpoint_commit(self,*args):return self.p.endpoint_commit(self.provider,*args)
    def endpoint_read(self,*args):return self.p.endpoint_read(self.provider,*args)
    def resume(self,*args):return self.p.resume(self.provider,*args)
    def terminate(self,*args):return self.p.terminate(self.provider,*args)
    def quiet(self,*args):return self.p.quiet(self.provider,*args)
    def close(self,*args):return self.p.close(self.provider,*args)
    def closed_witness(self,*args):return self.p.closed_witness(self.provider,*args)
