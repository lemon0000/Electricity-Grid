"""Versioned consumer parent/validation construction from frozen NFC10 source."""
import ast
from pathlib import Path

ROOT=Path(__file__).absolute().parents[1]


def replace(source,pairs):
    for before,after,count in pairs:
        assert source.count(before)==count,(before,source.count(before));source=source.replace(before,after)
    return source


def parent(source):
    source=replace(source,[('nfc_v10_non_authoritative','nfc_v11_non_authoritative',1),('lease_v37.py','lease_v38.py',1),
        ('probe_v35.py','probe_v36.py',1),('staged_rts24_saved_fresh_entry_namespace_post_return_v1.py','staged_rts24_saved_fresh_entry_namespace_consumer_v2.py',2),
        ('staged_rts24_saved_fresh_live_profile_validation_v1.py','staged_rts24_saved_fresh_consumer_binding_validation_v2.py',1)])
    node=next(node for node in ast.parse(source).body if type(node) is ast.FunctionDef and node.name=='transport')
    lines=source.splitlines(keepends=True);lines[node.lineno-1:node.end_lineno]=['def transport():return TRANSPORT.build(CORE,PROBE,minify_prefix)\n']
    source=''.join(lines)+"\nTRANSPORT=load(ROOT/'experiments/staged_rts24_saved_fresh_xz_transport_v1.py','_registered_xz_transport')\n"
    return source.encode()


def validator(source):
    source=replace(source,[("record['source_bookends']==5","record['source_bookends']==7",1),('source_bookends=5','source_bookends=7',1),
        ("('finder_check',10),('adapter_check',8)","('finder_check',14),('adapter_check',12)",1),
        ("record['graph_calls']==30","record['graph_calls']==38",1),('dict(namespace=21,adapter=9)','dict(namespace=25,adapter=13)',1),
        ("len(parsed['graph_frames'])==60","len(parsed['graph_frames'])==76",1),
        ("'before_boundary_close':[a,a],'before_profile':[a]","'before_boundary_close':[a,a],'after_boundary_close':[n,a,n,a],'before_profile':[a]",1),
        ("'before_final_runtime_close':[n,a,n]","'after_finish_import':[n,a,n,a,n,a,n]",1),
        ("{'runtime_phase_before_close','post_metrics','graph_calls'}","{'runtime_phase_before_close','post_metrics','graph_calls','consumer_result','consumer_state'}",1),
        ("    profile_shape(record['import_profile'])","    profile_shape(record['import_profile'])\n    assert record['consumer_state']=='CONSUMED'\n    validate_consumer_result(record['consumer_result'],parent)",1),
        ("terminal_mode='post_return_live_closed'","terminal_mode='live_binding_consumed_closed'",1),
        ("live_before_close=True,boundary_completed=True","live_before_close=True,binding_consumer_completed=True,boundary_completed=True",1)])
    source+='''

def validate_consumer_result(value,parent):
    flags=set(parent.FALSE_FIELDS)|{'producer_capability_verified'}
    assert type(value) is dict and set(value)==flags|{'schema','authority','consumer','binding_members','same_live_owner','consumer_return_is_adapter'}
    assert all(value[key] is False for key in flags)
    assert value['schema']=='staged_saved_F_consumer_binding_result_v1' and value['authority']=='DRAFT_NONAUTHORITATIVE'
    assert value['consumer']=='expectation_binding' and type(value['binding_members']) is int and value['binding_members']==10
    assert value['same_live_owner'] is True and value['consumer_return_is_adapter'] is True
    return value
'''
    return source.encode()


def create():
    for before,after,fn in (
            ('experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v34.py','experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v35.py',parent),
            ('experiments/staged_rts24_saved_fresh_live_profile_validation_v1.py','experiments/staged_rts24_saved_fresh_consumer_binding_validation_v2.py',validator)):
        raw=fn((ROOT/before).read_text(encoding='utf8'));compile(raw,after,'exec',dont_inherit=True,optimize=0)
        path=ROOT/after
        if path.exists():assert path.read_bytes()==raw
        else:path.write_bytes(raw)


if __name__=='__main__':create()
