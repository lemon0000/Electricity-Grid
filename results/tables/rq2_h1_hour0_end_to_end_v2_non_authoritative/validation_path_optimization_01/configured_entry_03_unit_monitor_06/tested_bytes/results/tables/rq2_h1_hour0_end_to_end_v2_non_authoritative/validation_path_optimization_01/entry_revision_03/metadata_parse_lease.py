"""Cache only immutable METADATA parsing; native distribution discovery stays live."""
import email
import email.feedparser
import email.message
import email.parser
from hashlib import sha256
import importlib.metadata as metadata
from pathlib import Path
import sys
from threading import RLock
from types import FunctionType

from performance.code_read_lease import CodeReadLease,_bytes,_identity,_kernel,_key


def _binding(value):
    function=value.fget if isinstance(value,property) else value
    return (value,getattr(function,'__code__',None),repr(getattr(function,'__defaults__',None)),
        repr(getattr(function,'__kwdefaults__',None)))


class MetadataParseLease:
    def __init__(self,expected):
        self._expected={Path(k):v for k,v in expected.items()}
        if (not self._expected or len(self._expected)>16
                or any(_key(p) is None or p.name!='METADATA' or len(pin)!=64
                    or any(c not in '0123456789abcdef' for c in pin)
                    for p,pin in self._expected.items())):
            raise ValueError('small exact METADATA allowlist required')
        self._handles=[];self._identities={};self._files={};self._raw={};self._values={}
        self._lock=RLock();self._state='new';self.hits=0;self.misses=0;self.windows=0
        self._original=metadata.Distribution.version
        self._open=CodeReadLease._open.__get__(self,MetadataParseLease)

    def _check(self):
        binding=self._binding_function
        if (_binding is not binding or binding.__code__ is not self._binding_code
                or binding.__defaults__!=self._binding_defaults
                or binding.__kwdefaults__!=self._binding_keywords
                or _key is not self._key_function
                or binding(_key)!=self._key_pin
                or binding(MetadataParseLease._check)!=self._check_pin
                or metadata.Distribution.version is not self._property
                or binding(self._property)!=self._property_pin
                or any(binding(getattr(owner,name,None))!=pin for owner,name,pin in self._bindings)):
            raise ValueError('metadata parser or dispatch changed')

    def __enter__(self):
        if self._state!='new':raise ValueError('metadata parse lease is single-use')
        try:
            directories={p for file in self._expected for p in file.parents}
            for path in sorted(directories,key=lambda p:(len(p.parts),str(p))):self._open(path,True)
            for path,pin in self._expected.items():
                handle=self._open(path,False);raw=_bytes(handle,8*1024**2)
                if sha256(raw).hexdigest()!=pin:raise ValueError('METADATA bytes differ')
                self._raw[_key(path)]=raw
            targets=[(metadata,'version'),(metadata,'distribution'),(metadata,'PathDistribution'),
                (metadata.Distribution,'metadata'),(metadata.PathDistribution,'read_text'),
                (metadata._adapters,'Message'),(email,'message_from_string'),
                (email.message.Message,'__getitem__'),(email.message.Message,'get'),
                (email.parser,'Parser'),(email.parser.Parser,'parsestr'),(email.parser.Parser,'parse'),
                (email.feedparser.FeedParser,'feed'),(email.feedparser.FeedParser,'close'),
                (email.feedparser.FeedParser,'_parsegen')]
            for cls in (metadata._adapters.Message,email.message.Message,email.parser.Parser,
                    email.feedparser.FeedParser,email.feedparser.BufferedSubFile):
                targets.extend((cls,name) for name,value in vars(cls).items()
                    if isinstance(value,(FunctionType,property)))
            self._binding_function=_binding;self._binding_code=_binding.__code__
            self._binding_defaults=_binding.__defaults__;self._binding_keywords=_binding.__kwdefaults__
            self._key_function=_key;self._key_pin=_binding(_key)
            self._check_pin=_binding(MetadataParseLease._check)
            self._bindings=tuple((o,n,_binding(getattr(o,n))) for o,n in targets)
            self._paths=tuple(sys.path);self._finders=tuple(sys.meta_path)
            original=self._original;exact_type=metadata.PathDistribution;owner=self
            key_function=self._key_function;check=self._check
            def get(distribution):
                with owner._lock:
                    check()
                    path=getattr(distribution,'_path',None)
                    key=key_function(path/'METADATA') if type(distribution) is exact_type and isinstance(path,Path) else None
                    if (tuple(sys.path)!=owner._paths or tuple(sys.meta_path)!=owner._finders
                            or key not in owner._raw or not owner._raw[key]
                            or 'read_text' in vars(distribution)):
                        owner.misses+=1
                    else:
                        file=path/'METADATA';stat=file.stat(follow_symlinks=False)
                        if (stat.st_dev,stat.st_ino)!=owner._identities[file]:
                            raise ValueError('selected METADATA path identity changed')
                        if key not in owner._values:
                            expected=owner._raw[key].decode('utf-8').replace('\r\n','\n').replace('\r','\n')
                            if distribution.read_text('METADATA')!=expected:
                                raise ValueError('selected METADATA read differs from held bytes')
                            owner._values[key]=original.fget(distribution)
                        owner.hits+=1;return owner._values[key]
                return original.fget(distribution)
            self._property=property(get);self._property_pin=_binding(self._property)
            if metadata.Distribution.version is not original:raise ValueError('metadata getter changed during acquisition')
            metadata.Distribution.version=self._property;self._state='active'
            return self
        except BaseException:
            self._release();raise

    def receipt(self):
        self._check()
        return dict(schema='synthetic_metadata_parse_lease_v1',hits=self.hits,misses=self.misses,
            discovery_windows=self.windows,
            files_sha256={str(p):v for p,v in self._expected.items()},
            selected_locked_metadata_version_value_cached=True,
            native_version_function_unchanged=True,distribution_discovery_cached=False,
            sys_path_changes_fall_back=True,custom_distribution_falls_back=True,formal_result=False)

    def begin_discovery_window(self):
        """Keep one getter identity; reset parsed values after fixture setup."""
        with self._lock:
            if self._state!='active':raise ValueError('live metadata lease required')
            self._check();self._values.clear()
            self._paths=tuple(sys.path);self._finders=tuple(sys.meta_path);self.windows+=1

    def _release(self):
        errors=[]
        for handle in reversed(self._handles):
            if not _kernel.CloseHandle(handle):errors.append('CloseHandle failed')
        self._handles.clear();self._state='closed'
        if errors:raise OSError('; '.join(errors))

    def __exit__(self,kind,value,tb):
        try:
            self._check()
            for path,pin in self._expected.items():
                if _identity(self._files[path])!=self._identities[path] or sha256(_bytes(self._files[path],8*1024**2)).hexdigest()!=pin:
                    raise ValueError('held METADATA bytes changed')
                info=path.stat(follow_symlinks=False)
                if (info.st_dev,info.st_ino)!=self._identities[path]:raise ValueError('METADATA path changed')
        finally:
            metadata.Distribution.version=self._original;self._release()
