"""One data-only full-capture/projection observation; never replay or launch F."""
import json
import os
from pathlib import Path
import sys
import time
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
    reads={};metadata=dict(lstat=0,stat=0,fstat=0,scandir=0)
    def category(path):
        path=Path(path).absolute()
        if path.is_relative_to(entry.P1):return 'P1'
        if path in selected:return 'selected_source'
        if path==anchor:return 'external_anchor'
        if path==catalog:return 'source_catalog'
        return 'other'
    class Stream:
        def __init__(self,stream,kind):self.stream,self.kind=stream,kind
        def __enter__(self):return self
        def __exit__(self,*args):return self.stream.__exit__(*args)
        def __getattr__(self,name):return getattr(self.stream,name)
        def read(self,*args,**kwargs):
            value=self.stream.read(*args,**kwargs);row=reads.setdefault(self.kind,dict(read_calls=0,binary_bytes=0,text_characters=0))
            row['read_calls']+=1
            if type(value) is bytes:row['binary_bytes']+=len(value)
            else:row['text_characters']+=len(value)
            return value
    def opened(path,*args,**kwargs):return Stream(original_open(path,*args,**kwargs),category(path))
    def lstat(*a,**k):metadata['lstat']+=1;return original_lstat(*a,**k)
    def stat(*a,**k):metadata['stat']+=1;return original_stat(*a,**k)
    def fstat(*a,**k):metadata['fstat']+=1;return original_fstat(*a,**k)
    def scandir(*a,**k):metadata['scandir']+=1;return original_scandir(*a,**k)
    with patch.object(Path,'open',opened),patch.object(os,'lstat',lstat),patch.object(os,'stat',stat),\
            patch.object(os,'fstat',fstat),patch.object(os,'scandir',scandir):
        started=time.perf_counter();cpu=time.process_time();value=operation()
        wall=time.perf_counter()-started;cpu_seconds=time.process_time()-cpu
    return value,dict(label=label,wall_seconds=wall,cpu_seconds=cpu_seconds,content_reads=reads,metadata_calls=metadata,
        scope='one data-preparation operation, excludes imports/setup, not total OS IO')


gold,left=observe('full_capture',lambda:adapter.capture(source))
expectation,right=observe('expectation_projection',lambda:entry.capture_saved_expectation(source))
assert gold.image==expectation.image and left['content_reads']['P1']['read_calls']==683
assert right['content_reads']['P1']['read_calls']==53 and not effects
assert source==entry.source_pins() and not entry.OUTPUT.parent.exists()
value=dict(authority='DRAFT_NONAUTHORITATIVE',order=['full_capture','expectation_projection'],source_pins=source,
    observations=[left,right],image_sha=entry.pin(expectation.image),same_caller_image_bytes=True,
    forbidden_scientific_effect_calls=len(effects),actual_saved_F_execution=False,F_launch_admitted=False,
    full_workflow_cost_measured=False,resource_admission=False,formal_result=False)
save('projection_profile.json',value)
print(json.dumps(dict(observations=value['observations'],same_caller_image_bytes=True,actual_saved_F_execution=False)))
