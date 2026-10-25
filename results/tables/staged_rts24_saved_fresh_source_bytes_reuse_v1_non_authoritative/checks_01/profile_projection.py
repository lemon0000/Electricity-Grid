"""One data-only full-capture/projection observation; never replay or launch F."""
import json
import os
from pathlib import Path
import sys
import time
import tracemalloc
from unittest.mock import patch
from capture_checks import ROOT,OUT,entry,save
from src import staged_rts24_saved_fresh_adoption_v1 as adapter
import highspy
import pyomo.environ as pyo

source=entry.source_pins();selected={(ROOT/name).absolute() for name in source}
anchor=adapter.ANCHOR.absolute();catalog=entry.INHERITED.absolute()
effects=[]
def denied(*args,**kwargs): effects.append(True);raise RuntimeError('data preparation requested a forbidden scientific effect')
for module,name in ((pyo,'SolverFactory'),(highspy,'Highs'),(adapter.prefix.point.backend,'make_model'),
        (adapter.prefix.point.backend,'call_highs'),(adapter.prefix.point.backend,'snapshot_from_raw'),
        (adapter.prefix.point.numeric,'compile_problem'),(adapter.prefix.point.numeric,'import_snapshot'),
        (adapter.prefix,'replay_prefix'),(adapter,'replay'),(adapter.journal,'reopen'),
        (adapter.codec.EvidenceStore,'put'),(adapter.codec,'publish'),(adapter.journal,'publish')):
    setattr(module,name,denied)
for name in ('create_session','begin_step','commit_step','finish'):setattr(adapter.journal,name,denied)


def observe(label,operation):
    original_open=Path.open;original_lstat=os.lstat;original_stat=os.stat;original_fstat=os.fstat;original_scandir=os.scandir
    reads={};source_file_reads={};metadata=dict(lstat=0,stat=0,fstat=0,scandir=0)
    def category(path):
        path=Path(path).absolute()
        if path.is_relative_to(entry.P1):return 'P1'
        if path in selected:return 'selected_source'
        if path==anchor:return 'external_anchor'
        if path==catalog:return 'source_catalog'
        return 'other'
    class Stream:
        def __init__(self,stream,kind,path):self.stream,self.kind,self.path=stream,kind,path
        def __enter__(self):return self
        def __exit__(self,*args):return self.stream.__exit__(*args)
        def __getattr__(self,name):return getattr(self.stream,name)
        def read(self,*args,**kwargs):
            value=self.stream.read(*args,**kwargs);row=reads.setdefault(self.kind,dict(read_calls=0,binary_bytes=0,text_characters=0))
            row['read_calls']+=1
            if self.kind=='selected_source':
                name=self.path.relative_to(ROOT).as_posix();source_file_reads[name]=source_file_reads.get(name,0)+1
            if type(value) is bytes:row['binary_bytes']+=len(value)
            else:row['text_characters']+=len(value)
            return value
    def opened(path,*args,**kwargs):return Stream(original_open(path,*args,**kwargs),category(path),Path(path).absolute())
    def lstat(*a,**k):metadata['lstat']+=1;return original_lstat(*a,**k)
    def stat(*a,**k):metadata['stat']+=1;return original_stat(*a,**k)
    def fstat(*a,**k):metadata['fstat']+=1;return original_fstat(*a,**k)
    def scandir(*a,**k):metadata['scandir']+=1;return original_scandir(*a,**k)
    with patch.object(Path,'open',opened),patch.object(os,'lstat',lstat),patch.object(os,'stat',stat),\
            patch.object(os,'fstat',fstat),patch.object(os,'scandir',scandir):
        tracemalloc.start(1)
        try:
            traced_before=tracemalloc.get_traced_memory()[0];tracemalloc.reset_peak()
            started=time.perf_counter();cpu=time.process_time();value=operation()
            wall=time.perf_counter()-started;cpu_seconds=time.process_time()-cpu
            traced_after,traced_peak=tracemalloc.get_traced_memory()
        finally:tracemalloc.stop()
    return value,dict(label=label,wall_seconds=wall,cpu_seconds=cpu_seconds,content_reads=reads,source_file_reads=source_file_reads,metadata_calls=metadata,
        python_traced_bytes=dict(before=traced_before,after=traced_after,peak=traced_peak,
            includes_probe_allocations=True,native_allocations_covered=False,RSS_measured=False),
        scope='one data-preparation operation with tracemalloc, excludes imports/setup, not total OS IO')


gold,left=observe('full_capture',lambda:adapter.capture(source))
loaded=[name for name in source if name.startswith('src/') and name.endswith('.py')
    and sys.modules.get(name[:-3].replace('/','.').removesuffix('.__init__')) is not None]
expectation,right=observe('expectation_projection',lambda:entry.capture_saved_expectation(source))
fixture_paths={'configs/staged_deliverability_rts24_v1.DRAFT.yaml','configs/staged_deliverability_small_case_v1.DRAFT.yaml',
    'configs/staged_deliverability_network_v1.DRAFT.yaml','src/staged_rts24_development_v1.py'}
value=dict(authority='DRAFT_NONAUTHORITATIVE',order=['full_capture','expectation_projection'],source_pins=source,
    source_raw_bytes=sum(p['bytes'] for p in source.values()),source_raw_cap_bytes=entry.EXPECTATION_SOURCE_RAW_CAP,
    loaded_selected_sources=loaded,fixture_source_paths=sorted(fixture_paths),initial_source_reads=49,duplicate_code_reads_avoided=10,
    observations=[left,right],image_sha=entry.pin(expectation.image),same_caller_image_bytes=True,
    forbidden_scientific_effect_calls=len(effects),actual_saved_F_execution=False,F_launch_admitted=False,
    full_workflow_cost_measured=False,resource_admission=False,formal_result=False)
save('projection_profile.json',value)
assert gold.image==expectation.image and left['content_reads']['P1']['read_calls']==683
assert right['content_reads']['P1']['read_calls']==53 and not effects
assert set(loaded)<=set(source) and fixture_paths<=set(source)
assert right['source_file_reads']=={name:3+2*int(name in loaded)+int(name in fixture_paths) for name in source}
assert left['source_file_reads']=={name:2+2*int(name in loaded)+int(name in fixture_paths) for name in source}
assert source==entry.source_pins() and not entry.OUTPUT.parent.exists()
print(json.dumps(dict(observations=value['observations'],same_caller_image_bytes=True,actual_saved_F_execution=False)))
