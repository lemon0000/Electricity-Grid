"""Closed-issuer single-file publication body; ordinary filesystem evidence only."""
from hashlib import sha256
import json
import math
import os
from pathlib import PureWindowsPath
import stat
from threading import current_thread, get_ident

AUTHORITY='DRAFT_NONAUTHORITATIVE'
SCOPE='saved_P1_actual_21_and_journal_5h'
IO_NAMES=('open','write','fsync','lseek','read','fstat','lstat','get_inheritable','close')
MAX_BYTES=131072
MAX_PARENTS=32
MAX_TRANSFERS=8
MAX_IO=15*MAX_PARENTS+58


class PublicationUnavailable(RuntimeError):pass


class PublicationUnresolved(RuntimeError):
    def __init__(self,capsule,primary,secondary):
        self.capsule,self.primary,self.secondary=capsule,primary,tuple(secondary)
        super().__init__('file publication responsibility unresolved')
    def __reduce__(self):raise TypeError('live publication responsibility is not serializable')


class BoundPublication:
    __slots__=('_anchor',)
    def __new__(cls,*args,**kwargs):raise PublicationUnavailable('source-authenticated file issuer is closed')
    def __setattr__(self,*args):raise TypeError('opaque publication capsule')
    def __delattr__(self,*args):raise TypeError('opaque publication capsule')
    def __reduce__(self):raise TypeError('publication capsule cannot be serialized')


def open_publication(*args,**kwargs):
    raise PublicationUnavailable('source-authenticated file issuer is closed')


def require(value,message):
    if not value:raise ValueError(message)


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def creator():return os.getpid(),get_ident()


def decode(raw):
    require(type(raw) is bytes and 0<len(raw)<=32768,'bounded publication binding')
    def unique(items):
        result={}
        for key,value in items:require(key not in result,'duplicate binding key');result[key]=value
        return result
    value=json.loads(raw,object_pairs_hook=unique)
    require(canonical(value)==raw,'canonical binding required');return value


def check_pin(value):
    require(type(value) is dict and set(value)=={'bytes','sha256'},'closed pin')
    require(type(value['bytes']) is int and 0<value['bytes']<=MAX_BYTES,'manifest/source pin bound')
    h=value['sha256'];require(type(h) is str and len(h)==64 and all(c in '0123456789abcdef' for c in h),'SHA domain')


def path_chain(path,parent,nonce,role):
    require(type(path) is type(parent) is str and len(path)>3 and path[0] in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
        and path[1:3]==':\\' and '/' not in path and len(path.encode('utf-16-le'))//2<32767,'ordinary absolute drive path')
    parts=path[3:].split('\\')
    require(1<len(parts)<=MAX_PARENTS and all(parts),'bounded direct child path')
    reserved={'CON','PRN','AUX','NUL','CONIN$','CONOUT$',*[f'COM{i}' for i in range(1,10)],*[f'LPT{i}' for i in range(1,10)],
        *[stem+suffix for stem in ('COM','LPT') for suffix in ('\u00b9','\u00b2','\u00b3')]}
    for part in parts:
        require(part not in ('.','..') and not part.endswith((' ','.')) and not any(ord(c)<32 or c in '<>:"|?*' for c in part)
            and part.split('.')[0].rstrip(' .').upper() not in reserved,'ordinary Windows component')
    require(str(PureWindowsPath(path))==path and str(PureWindowsPath(path).parent)==parent,'exact direct parent')
    require(parts[-1]==role+'.plan.json' and parts[-2]==nonce and len(parts)>=3 and parts[-3]=='transport','bound nonce/role path')
    parents=[path[:3]]
    for part in parts[:-1]:parents.append(parents[-1].rstrip('\\')+'\\'+part)
    require(parents[-1]==parent,'complete parent chain');return tuple(parents)


def binding_data(raw):
    value=decode(raw)
    require(type(value) is dict and set(value)==set('schema authority scope role path parent nonce manifest_pin source_binding_pin invocation_started deadline'.split()),'closed publication binding fields')
    require(value['schema']=='staged_saved_F_host_publication_binding_v1' and value['authority']==AUTHORITY
        and value['scope']==SCOPE and value['role']=='controller','publication binding scope')
    nonce=value['nonce'];require(type(nonce) is str and len(nonce)==64 and all(c in '0123456789abcdef' for c in nonce),'nonce')
    check_pin(value['manifest_pin']);check_pin(value['source_binding_pin'])
    start,end=value['invocation_started'],value['deadline']
    require(type(start) is type(end) is float and math.isfinite(start) and math.isfinite(end) and start>0 and end==start+180.0,'original absolute clock')
    return value,path_chain(value['path'],value['parent'],nonce,value['role'])


def metadata(fn):
    base=getattr(fn,'__func__',fn)
    defaults=getattr(base,'__defaults__',None);kw=getattr(base,'__kwdefaults__',None)
    return (id(fn),id(getattr(fn,'__self__',None)),id(base),getattr(base,'__code__',None),
        id(defaults),None if defaults is None else tuple(id(v) for v in defaults),
        id(kw),None if kw is None else tuple(sorted((k,id(v)) for k,v in kw.items())))


def _mechanical_publication(owner,binding_raw,clock,io=None):
    raise PublicationUnavailable('no authenticated source/owner file issuer')
    binding,parents=binding_data(binding_raw)
    require(owner is not None and callable(clock),'held owner and clock')
    functions=tuple(getattr(os,name) for name in IO_NAMES) if io is None else io
    require(type(functions) is tuple and len(functions)==len(IO_NAMES) and all(callable(f) for f in functions),'fixed file operation table')
    cap=object.__new__(BoundPublication)
    root=dict(cap=cap,owner=owner,creator=creator(),thread=current_thread(),binding_raw=binding_raw,binding=binding,parents=parents,
        clock=clock,io=functions,metadata=tuple(metadata(f) for f in (clock,*functions)),
        state=['NEW'],operation=['IDLE'],reentry=[0],last_clock=[binding['invocation_started']],
        fd=[None],captured=[None],opening=['IDLE'],closing=['IDLE'],cleanup=['IDLE',None],terminal=[None],primary=[None],errors=[],
        raw=[None],file_identity=[None],parent_identity=[None],write_offsets=[],reads=[0],io_count=[0],
        reservation=[None],journal=[],immutable=[None])
    root['immutable'][0]=_immutable(root)
    object.__setattr__(cap,'_anchor',tuple(root.items()))
    _time(root,min(binding['invocation_started']+10.0,binding['deadline']-15.0));return cap


def _immutable(root):
    return (id(root['cap']),id(root['owner']),root['creator'],id(root['thread']),root['binding_raw'],canonical(root['binding']),
        root['parents'],tuple(id(f) for f in (root['clock'],*root['io'])),id(root['fd']),id(root['captured']),id(root['opening']),id(root['closing']))


def _root(cap,cleanup=False):
    require(type(cap) is BoundPublication,'exact publication capsule')
    root=dict(object.__getattribute__(cap,'_anchor'))
    require(root['cap'] is cap and root['creator']==creator() and root['thread'] is current_thread(),'creating publication owner')
    try:
        require(_immutable(root)==root['immutable'][0],'publication anchor changed')
        if root['captured'][0] is not None:
            require(type(root['captured'][0]) is int and root['captured'][0]>=0 and type(root['fd'][0]) is int
                and root['fd'][0]==root['captured'][0],'captured descriptor mirror changed')
    except BaseException as error:
        if not cleanup:raise
        root['errors'].append(('cleanup_anchor',error))
    return root


def _image(root,capture=False):
    return (root['state'][0],root['operation'][0],root['opening'][0],root['closing'][0],tuple(root['cleanup'][:1]),
        root['raw'][0],canonical(root['file_identity'][0]),root['parent_identity'][0],tuple(root['write_offsets']),
        root['reads'][0],root['io_count'][0],root['reservation'][0],tuple(root['journal']),
        None if capture else (root['fd'][0],root['captured'][0]))


def _leaf(root,index,*args,capture=False):
    fn=root['clock'] if index is None else root['io'][index]
    expected=root['metadata'][0 if index is None else index+1]
    require(metadata(fn)==expected,'held filesystem callable changed')
    anchor=object.__getattribute__(root['cap'],'_anchor');before=_image(root,capture);entry=root['reentry'][0];primary=None
    try:
        if capture:
            root['fd'][0]=fn(*args)
            if type(root['fd'][0]) is int and root['fd'][0]>=0:root['captured'][0]=root['fd'][0]
            return root['fd'][0]
        return fn(*args)
    except BaseException as error:primary=error;raise
    finally:
        try:
            require(object.__getattribute__(root['cap'],'_anchor') is anchor and _immutable(root)==root['immutable'][0]
                and _image(root,capture)==before and metadata(fn)==expected and root['reentry'][0]==entry,'filesystem effect changed anchor or reentered')
        except BaseException as error:
            root['errors'].append(('effect_bookend',error))
            if primary is None:raise


def _time(root,limit):
    now=_leaf(root,None)
    require(type(now) is float and math.isfinite(now) and root['last_clock'][0]<=now,'monotonic publication clock')
    root['last_clock'][0]=now
    require(now<=limit<=root['binding']['deadline'],'original publication reservation expired')
    return now


def _limit(root):return min(root['binding']['invocation_started']+10.0,root['binding']['deadline']-15.0)


def _io(root,name,*args,capture=False):
    limit=_limit(root);_time(root,limit)
    require(root['io_count'][0]<MAX_IO,'file operation bound')
    root['io_count'][0]+=1;root['journal'].append((name,'ISSUED'));primary=None
    try:
        result=_leaf(root,IO_NAMES.index(name),*args,capture=capture)
        root['journal'].append((name,'RETURNED'));return result
    except BaseException as error:primary=error;raise
    finally:
        try:_time(root,limit)
        except BaseException as error:
            root['errors'].append(('io_deadline',error))
            if primary is None:raise


def _begin(cap,name,states,cleanup=False):
    root=_root(cap,cleanup=cleanup)
    if root['operation'][0]!='IDLE':
        error=ValueError('reentrant publication operation');root['reentry'][0]+=1;root['errors'].append(('reentry',error));raise error
    if not cleanup:
        if root['primary'][0] is not None:raise root['primary'][0]
        require(root['cleanup'][0]=='IDLE' and root['reentry'][0]==0 and not root['errors'],'closed or failed publication')
        require(root['state'][0] in states,'publication lifecycle')
    root['operation'][0]=name;return root


def _fail(root,error):
    if root['primary'][0] is None:root['primary'][0]=error
    root['state'][0]='FAILED'


def _identity(info,directory=False):
    values={name:getattr(info,'st_'+name) for name in ('dev','ino','mode','nlink','size','mtime_ns')}
    values['file_attributes']=getattr(info,'st_file_attributes',0)
    require(all(type(v) is int and v>=0 for v in values.values()) and values['ino']>0,'ordinary stat identity')
    require(not values['file_attributes']&0x400 and not stat.S_ISLNK(values['mode']),'non-reparse path')
    require(stat.S_ISDIR(values['mode']) if directory else stat.S_ISREG(values['mode']) and values['nlink']==1,'ordinary directory or single-link file')
    return values


def _parents(root):
    rows=[]
    for path in root['parents']:
        value=_identity(_io(root,'lstat',path),directory=True)
        rows.append((path,value['dev'],value['ino'],value['mode'],value['file_attributes']))
    result=tuple(rows)
    if root['parent_identity'][0] is None:root['parent_identity'][0]=result
    require(result==root['parent_identity'][0],'parent identity changed');return result


def _observe(root,exact=False):
    _parents(root)
    fd=root['fd'][0];require(type(fd) is int and fd>=0,'captured descriptor required')
    require(_io(root,'get_inheritable',fd) is False,'noninheritable descriptor required')
    opened=_identity(_io(root,'fstat',fd));named=_identity(_io(root,'lstat',root['binding']['path']))
    require(opened==named,'pathname/descriptor identity changed')
    if exact:require(opened==root['file_identity'][0],'retained file identity changed')
    _parents(root);return opened


def check_binding(cap,raw,clock):
    root=_begin(cap,'check_binding',('NEW',))
    try:
        binding_data(raw);require(raw==root['binding_raw'] and clock is root['clock'],'exact publication binding and Host clock callable')
        _time(root,_limit(root));return cap
    except BaseException as error:_fail(root,error);raise
    finally:root['operation'][0]='IDLE'


def _read(root):
    require(_io(root,'lseek',root['fd'][0],0,os.SEEK_SET)==0,'seek result')
    chunks=[];remaining=len(root['raw'][0]);calls=0
    while True:
        require(calls<MAX_TRANSFERS,'bounded read/EOF calls');calls+=1
        block=_io(root,'read',root['fd'][0],min(65536,remaining+1))
        require(type(block) is bytes and len(block)<=min(65536,remaining+1),'bounded immutable read result')
        if not block:
            require(remaining==0,'short read');break
        require(len(block)<=remaining,'unexpected trailing file byte')
        chunks.append(block);remaining-=len(block)
    raw=b''.join(chunks);require(raw==root['raw'][0],'retained bytes changed');return raw


def _receipt(root):
    value=root['binding']
    return dict(schema='staged_saved_F_host_manifest_receipt_v1',authority=AUTHORITY,path=value['path'],parent=value['parent'],
        nonce=value['nonce'],role=value['role'],content_pin=pin(root['raw'][0]),source_binding_pin=value['source_binding_pin'],
        creator=dict(pid=root['creator'][0],tid=root['creator'][1]),file_identity=dict(root['file_identity'][0]),
        create_only=True,noninheritable=True,role_authority=False,physical_immutability_verified=False,power_loss_durability_verified=False)


def publish(cap,path,raw):
    root=_begin(cap,'publish',('NEW',))
    try:
        require(type(raw) is bytes and 0<len(raw)<=MAX_BYTES and pin(raw)==root['binding']['manifest_pin']
            and path==root['binding']['path'],'bound publication bytes and path')
        root['raw'][0]=raw;root['reservation'][0]=(path,1,len(raw));root['state'][0]='PUBLISH_ISSUED'
        _parents(root)
        root['opening'][0]='OPEN_ISSUED'
        flags=os.O_CREAT|os.O_EXCL|os.O_RDWR|os.O_BINARY|os.O_NOINHERIT
        try:_io(root,'open',path,flags,0o600,capture=True)
        finally:
            root['opening'][0]='OPEN_CAPTURED' if type(root['fd'][0]) is int and root['fd'][0]>=0 else 'OPEN_UNCERTAIN'
        require(root['opening'][0]=='OPEN_CAPTURED','open returned no descriptor')
        opened=_observe(root);require(opened['size']==0,'new file must be empty')
        root['state'][0]='WRITE_ISSUED';offset=0;calls=0
        while offset<len(raw):
            require(calls<MAX_TRANSFERS,'bounded positive write calls');calls+=1
            chunk=raw[offset:offset+65536];count=_io(root,'write',root['fd'][0],chunk)
            require(type(count) is int and 0<count<=len(chunk),'positive bounded write progress')
            offset+=count;root['write_offsets'].append(offset)
        root['state'][0]='FSYNC_ISSUED';require(_io(root,'fsync',root['fd'][0]) is None,'fsync return')
        root['file_identity'][0]=_observe(root)
        require(root['file_identity'][0]['size']==len(raw),'published file size')
        _read(root);_observe(root,exact=True)
        root['state'][0]='RETAINED';return _receipt(root)
    except BaseException as error:_fail(root,error);raise
    finally:root['operation'][0]='IDLE'


def published_read(cap,path):
    root=_begin(cap,'published_read',('RETAINED',))
    try:
        require(path==root['binding']['path'] and root['reads'][0]<2,'two fixed Host publication bookends')
        root['reads'][0]+=1
        _observe(root,exact=True);raw=_read(root);_observe(root,exact=True)
        return raw,_receipt(root)
    except BaseException as error:_fail(root,error);raise
    finally:root['operation'][0]='IDLE'


def snapshot(cap):
    """Passive responsibility image; published_read performs physical bookends."""
    root=_root(cap)
    if root['operation'][0]!='IDLE':
        error=ValueError('snapshot during publication operation');root['reentry'][0]+=1;root['errors'].append(('reentry',error));raise error
    return (cap,root['binding_raw'],root['opening'][0],root['fd'][0],root['closing'][0],root['cleanup'][0],root['reservation'][0],
        tuple(root['write_offsets']),root['reads'][0],root['io_count'][0],root['reentry'][0])


def close(cap,deadline):
    root=_begin(cap,'close',(),cleanup=True)
    try:
        if root['cleanup'][0] in ('CLOSED','UNRESOLVED'):
            if root['cleanup'][1] is not None:raise root['cleanup'][1]
            try:
                require(root['closing'][0] in ('CLOSED','NEVER_OPENED') and root['opening'][0]!='OPEN_UNCERTAIN'
                    and _terminal(root)==root['terminal'][0] and not root['errors'],'terminal publication ledger changed')
            except BaseException as error:
                root['errors'].append(('terminal_drift',error));failure=PublicationUnresolved(cap,root['primary'][0],root['errors'])
                root['cleanup'][:]=['UNRESOLVED',failure];raise failure from error
            return True
        require(root['cleanup'][0]=='IDLE','one file cleanup attempt')
        root['cleanup'][0]='ISSUED';errors=root['errors']
        limit=root['binding']['deadline']
        try:
            require(type(deadline) is float and math.isfinite(deadline) and deadline<=limit,'original cleanup deadline')
            now=_time(root,limit);limit=min(limit,deadline,now+15.0)
        except BaseException as error:errors.append(('cleanup_clock',error))
        fd=root['captured'][0] if root['captured'][0] is not None else root['fd'][0]
        if type(fd) is int and fd>=0:
            try:
                require(root['closing'][0]=='IDLE','descriptor close already issued')
                root['closing'][0]='CLOSE_ISSUED'
                root['journal'].append(('close','ISSUED'));root['io_count'][0]+=1
                try:_time(root,limit)
                except BaseException as error:errors.append(('close_clock_before',error))
                require(_leaf(root,IO_NAMES.index('close'),fd) is None,'close return')
                root['journal'].append(('close','RETURNED'))
                root['closing'][0]='CLOSED'
            except BaseException as error:
                root['closing'][0]='CLOSE_UNCERTAIN';errors.append(('close',error))
            try:_time(root,limit)
            except BaseException as error:errors.append(('close_clock_after',error))
        elif root['opening'][0]=='IDLE':root['closing'][0]='NEVER_OPENED'
        else:errors.append(('open_capture',ValueError('open ownership capture unresolved')))
        if root['opening'][0]=='OPEN_UNCERTAIN':errors.append(('open_uncertain',ValueError('unknown file descriptor may remain live')))
        failure=PublicationUnresolved(cap,root['primary'][0],errors) if errors else None
        root['cleanup'][:]=['UNRESOLVED' if failure else 'CLOSED',failure]
        root['terminal'][0]=_terminal(root)
        if failure:raise failure from root['primary'][0]
        return True
    finally:root['operation'][0]='IDLE'


def closed_witness(cap):
    root=_root(cap)
    if root['operation'][0]!='IDLE':
        error=ValueError('close witness during publication operation');root['reentry'][0]+=1;root['errors'].append(('reentry',error));raise error
    require(root['operation'][0]=='IDLE' and root['cleanup'][0]=='CLOSED' and root['cleanup'][1] is None
        and root['closing'][0] in ('CLOSED','NEVER_OPENED') and root['opening'][0] in ('IDLE','OPEN_CAPTURED')
        and not root['errors'] and _terminal(root)==root['terminal'][0],'completed local close call and no pending capture required')
    return True


def _terminal(root):
    return (_immutable(root),root['fd'][0],root['captured'][0],root['opening'][0],root['closing'][0],root['reservation'][0],
        tuple(root['write_offsets']),root['reads'][0],root['io_count'][0],tuple(root['journal']),root['state'][0],root['raw'][0],
        canonical(root['file_identity'][0]),root['parent_identity'][0],id(root['primary'][0]),
        tuple(metadata(f) for f in (root['clock'],*root['io'])))
