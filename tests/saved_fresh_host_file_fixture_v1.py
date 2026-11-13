"""Ordinary private-body file fixtures; project Native leaves stay synthetic."""
import ast
import ctypes
import importlib.util
import os
from pathlib import Path
import stat
from types import ModuleType,SimpleNamespace

ROOT=Path(__file__).absolute().parents[1]
PUBLICATION=ROOT/'experiments/staged_rts24_saved_fresh_host_file_publication_v1.py'
HOST=ROOT/'experiments/staged_rts24_saved_fresh_full_role_host_preentry_v3.py'
WINDOWS_FIXTURE=ROOT/'tests/saved_fresh_host_windows_fixture_v1.py'


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def clone(path,name,gate):
    tree=ast.parse(path.read_bytes());changed=[]
    for node in tree.body:
        if type(node) is ast.FunctionDef and node.name==gate:
            assert type(node.body[0]) is ast.Raise;del node.body[0];changed.append(gate)
    assert changed==[gate]
    module=ModuleType(name);module.__file__=str(path)
    exec(compile(tree,str(path),'exec',dont_inherit=True,optimize=0),vars(module));return module


WINDOWS=load(WINDOWS_FIXTURE,'_file_previous_windows_fixture')


class Files:
    def __init__(self,module,binding):
        self.m=module;self.binding=binding;self.path=binding['path'];self.parents={};self.data={};self.meta={};self.fds={}
        self.next_fd=0;self.events=[];self.closed=[];self.fail=None;self.callback=None;self.inherit=False;self.write_limit=None
        self.write_return=None;self.read_empty=False;self.read_extra=False;self.read_limit=None;self.path_ino_delta=0
        self.error=OSError('synthetic file leaf failure')
        for i,p in enumerate(module.path_chain(self.path,binding['parent'],binding['nonce'],binding['role'])):
            self.parents[p]=dict(st_dev=1,st_ino=10+i,st_mode=stat.S_IFDIR|0o700,st_nlink=1,st_size=0,st_mtime_ns=1,st_file_attributes=16)
    def ops(self):return tuple(getattr(self,n) for n in self.m.IO_NAMES)
    def hit(self,name):
        self.events.append(name)
        if self.callback:self.callback(name)
        if self.fail==name:raise self.error
    def info(self,path):
        if path in self.parents:return SimpleNamespace(**self.parents[path])
        if path not in self.data:raise FileNotFoundError(path)
        values=dict(self.meta[path]);values['st_size']=len(self.data[path]);return SimpleNamespace(**values)
    def preexisting(self,raw=b'foreign'):
        self.data[self.path]=bytearray(raw);self.meta[self.path]=dict(st_dev=1,st_ino=100,st_mode=stat.S_IFREG|0o600,st_nlink=1,st_mtime_ns=5,st_file_attributes=32)
    def open(self,path,flags,mode):
        self.hit('open.before');assert path==self.path and flags==os.O_CREAT|os.O_EXCL|os.O_RDWR|os.O_BINARY|os.O_NOINHERIT and mode==0o600
        if path in self.data:raise FileExistsError(path)
        self.preexisting(b'');fd=self.next_fd;self.next_fd+=1;self.fds[fd]=[path,0];self.hit('open.after');return fd
    def write(self,fd,raw):
        self.hit('write.before');path,offset=self.fds[fd]
        count=min(len(raw),self.write_limit) if self.write_limit is not None else len(raw)
        self.data[path][offset:offset+count]=raw[:count];self.fds[fd][1]+=count;self.meta[path]['st_mtime_ns']+=1
        self.hit('write.after');return count if self.write_return is None else self.write_return
    def fsync(self,fd):self.hit('fsync.before');assert fd in self.fds;self.hit('fsync.after')
    def lseek(self,fd,offset,whence):
        self.hit('seek.before');assert offset==0 and whence==os.SEEK_SET;self.fds[fd][1]=0;self.hit('seek.after');return 0
    def read(self,fd,count):
        self.hit('read.before');path,offset=self.fds[fd];raw=bytes(self.data[path])+(b'!' if self.read_extra else b'')
        actual=min(count,self.read_limit) if self.read_limit is not None else count
        result=b'' if self.read_empty else raw[offset:offset+actual];self.fds[fd][1]+=len(result);self.hit('read.after');return result
    def fstat(self,fd):self.hit('fstat.before');value=self.info(self.fds[fd][0]);self.hit('fstat.after');return value
    def lstat(self,path):
        self.hit('lstat.before');value=self.info(path)
        if path in self.data:value.st_ino+=self.path_ino_delta
        self.hit('lstat.after');return value
    def get_inheritable(self,fd):self.hit('inherit.before');assert fd in self.fds;self.hit('inherit.after');return self.inherit
    def close(self,fd):self.hit('close.before');assert fd in self.fds;self.closed.append(fd);del self.fds[fd];self.hit('close.after')


def binding(module,path,raw=b'publication',nonce='4'*64):
    return dict(schema='staged_saved_F_host_publication_binding_v1',authority=module.AUTHORITY,scope=module.SCOPE,role='controller',
        path=path,parent=str(Path(path).parent),nonce=nonce,manifest_pin=module.pin(raw),source_binding_pin=module.pin(b'held full source relation'),
        invocation_started=100.0,deadline=280.0)


class Harness:
    def __init__(self,raw=b'publication',path=None):
        self.m=clone(PUBLICATION,'_file_publication_private','_mechanical_publication');self.raw=raw;self.now=100.0;self.clock_callback=None
        self.path=path or 'D:\\synthetic\\transport\\'+'4'*64+'\\controller.plan.json';self.binding=binding(self.m,self.path,raw)
        self.fs=Files(self.m,self.binding)
        self.cap=self.m._mechanical_publication(object(),self.m.canonical(self.binding),self.clock,self.fs.ops())
    def clock(self):
        if self.clock_callback:self.clock_callback()
        return self.now
    def root(self):return dict(object.__getattribute__(self.cap,'_anchor'))
    def publish(self):return self.m.publish(self.cap,self.path,self.raw)
    def close(self):return self.m.close(self.cap,min(280.0,self.now+15.0))


class World(WINDOWS.World):
    def __init__(self,constructor_failure=None):
        self.constructor_failure=constructor_failure;self.constructing=True;self.clock_calls=0;self.snapshot_failure=False;self.snapshot_mutation=None
        self.fm=clone(PUBLICATION,'_connected_file_publication','_mechanical_publication')
        host=clone(HOST,'_connected_host_v3','_mechanical_host');factory=host._mechanical_host
        def build(request,context,template,transport,payload,effects):
            raw=host.publication_binding(request,context,template,transport,payload);self.file_binding=self.fm.decode(raw)
            self.fs=Files(self.fm,self.file_binding);self.pub=self.fm._mechanical_publication(object(),raw,effects[host.EFFECTS.index('clock')],self.fs.ops())
            return factory(request,context,template,transport,payload,effects,self.pub)
        proxy=SimpleNamespace(**vars(host));proxy._mechanical_host=build
        self.provider=None;WINDOWS.OLD.World.__init__(self,proxy)
        self.p=clone(WINDOWS.PROVIDER,'_connected_windows_provider','_mechanical_resources');self.k=WINDOWS.Kernel(self.p)
        self.p.C=SimpleNamespace(**vars(ctypes));self.p.C.WinDLL=lambda name,**kw:self.k.library
        held_clock=self.root()['effects'][self.m.EFFECTS.index('clock')]
        self.provider=self.p._mechanical_resources(self.host,100.0,280.0,held_clock)
        self.constructing=False
    def clock(self):
        self.clock_calls+=1
        if self.constructing and self.constructor_failure=='clock' and self.clock_calls>=3:return 111.0
        return self.now
    def file_root(self):return dict(object.__getattribute__(self.pub,'_anchor'))
    def resource_snapshot(self):
        if self.provider is None:return tuple((name,None) for name in self.m.RESOURCES),()
        return self.p.resource_snapshot(self.provider)
    def publication_check(self,*args):
        if self.constructing and self.constructor_failure=='check':raise self.error
        return self.fm.check_binding(*args)
    def publication_snapshot(self,*args):
        if self.snapshot_failure or self.constructing and self.constructor_failure=='snapshot':raise self.error
        value=self.fm.snapshot(*args)
        return self.snapshot_mutation(value) if self.snapshot_mutation else value
    def publication_close(self,*args):return self.fm.close(*args)
    def publication_closed_witness(self,*args):return self.fm.closed_witness(*args)
    def publish(self,*args):return self.fm.publish(*args)
    def published_read(self,*args):return self.fm.published_read(*args)
