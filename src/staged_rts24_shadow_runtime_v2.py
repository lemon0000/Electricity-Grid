"""Reuse v1 identity closure and explicitly bind the str/int-key successor."""
from pathlib import Path
import sys
import types

from src import staged_rts24_shadow_runtime_v1 as base
from src import staged_rts24_plain_v2 as candidate,staged_rts24_shadow_monitor_v2 as shadow

ROOT=base.ROOT
probe,support,core,journal=base.probe,base.support,base.core,base.journal
PACKAGES=base.PACKAGES
EXTRA=('src.staged_rts24_plain_v2','src.staged_rts24_shadow_monitor_v2','src.staged_rts24_shadow_runtime_v2')
APP_NAMES=[*base.APP_NAMES,*EXTRA]
require=base.require


def routes():return base.routes()


def snapshot():
    base.require(sys is base.sys and types is base.types and Path is base.Path
        and probe is base.probe and support is base.support and core is base.core and journal is base.journal
        and require is base.require and PACKAGES is base.PACKAGES
        and sys.modules.get('src.staged_rts24_shadow_runtime_v1') is base,'successor runtime dependency alias differs')
    require(EXTRA==('src.staged_rts24_plain_v2','src.staged_rts24_shadow_monitor_v2','src.staged_rts24_shadow_runtime_v2')
        and APP_NAMES==[*base.APP_NAMES,*EXTRA] and len(APP_NAMES)==38,'successor declared module set differs')
    pins,refs=base.snapshot()
    require(candidate._legacy_plain is core.plain and candidate._KNOWN_FIELDS==base.candidate._KNOWN_FIELDS
        and candidate.MAX_FAST_DEPTH==64,'successor registry or fallback differs')
    require(candidate.CLASSES is base.codec.CLASSES and candidate.Fraction is base.fractions.Fraction
        and candidate.fields is base.dataclasses.fields and candidate.json is base.json
        and candidate.sha256 is base.shadow.sha256,'successor serializer binding differs')
    require(shadow.base is base.shadow and shadow.candidate is candidate and shadow.legacy is core
        and shadow.ShadowMonitor.__bases__==(base.shadow.ShadowMonitor,)
        and shadow.ShadowMonitor.NAME=='electricity-grid-saved-digest-shadow-v2'
        and shadow.ShadowMonitor.TOOL==3 and shadow.sha256 is base.shadow.sha256
        and shadow.sys is base.shadow.sys is sys,'successor monitor parent differs')
    for name in EXTRA:
        module=sys.modules.get(name);spec=getattr(module,'__spec__',None)
        path=ROOT.joinpath(*name.split('.')).with_suffix('.py')
        require(type(module) is types.ModuleType and module.__name__==name and spec is not None
            and spec.name==name and Path(spec.origin).resolve()==path and Path(module.__file__).resolve()==path
            and spec.submodule_search_locations is None,'successor application module shadow: '+name)
        parent,member=name.rsplit('.',1)
        require(getattr(sys.modules.get(parent),member,None) is module,'successor parent binding differs: '+name)
        pins['application_modules'][name]=dict(path=str(path),pin=support.stamp(path))
        refs['application/'+name]=module
    require(sys.modules.get(candidate.__name__) is candidate and sys.modules.get(shadow.__name__) is shadow
        and sys.modules.get(base.__name__) is base,'captured successor module differs')
    functions=dict(successor_walk=candidate._walk,successor_plain=candidate.plain,
        successor_bytes=candidate.canonical_bytes,successor_digest=candidate.digest,successor_root_tag=shadow._root_tag,
        successor_routes=routes,successor_snapshot=snapshot,successor_unchanged=unchanged)
    functions.update({'successor_monitor/'+k:v for k,v in vars(shadow.ShadowMonitor).items() if type(v) is types.FunctionType})
    compiled={}
    for name,function in functions.items():
        pins['functions'][name]=base._function_pin(function,compiled,pins['application_modules'])
        refs['function/'+name]=function;refs['code/'+name]=function.__code__
    refs['successor/monitor_class']=shadow.ShadowMonitor
    pins['successor_domain']='exact_str_int_dict_keys_20_registered_classes_depth_64_stationary_same_thread'
    return pins,refs


def unchanged(before,refs):
    after,current=snapshot()
    require(after==before and set(current)==set(refs) and all(current[k] is v for k,v in refs.items()),
        'shadow successor runtime identity changed')
    return after
