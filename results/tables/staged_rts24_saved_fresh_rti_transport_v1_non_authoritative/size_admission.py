"""One finite, static codec admission; no unit or cold child is started."""
import ast
import base64
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
import time
import zlib

OUT=Path(__file__).absolute().parent;ROOT=OUT.parents[2]
OLD=ROOT/'results/tables/staged_rts24_saved_fresh_rti_v1_non_authoritative'
NGT=ROOT/'results/tables/staged_rts24_saved_fresh_ngt_v1_non_authoritative'
PARENT=ROOT/'experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v9.py'
SCOPE=ROOT/'docs/plan/staged_deliverability_c_saved_fresh_runtime_transport_size_scope_v1.md'
EXE='D:/Miniconda3/envs/compute/python.exe'

def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def read(path):return json.loads(path.read_bytes())
def write(path,raw):
    with path.open('xb') as stream:stream.write(raw)
def units(code):
    command=[EXE,'-P','-B','-s','-S','-c',code.decode(),'--pre-entry-lease',str(OLD/'probe_import_discovery.plan.json'),'0'*64]
    return len(subprocess.list2cmdline(command).encode('utf-16-le'))//2

def main():
    started=time.perf_counter();assert not (OUT/'size_report.json').exists()
    failure=read(OLD/'registration_failure.json');assert failure['accepted'] is False
    old_files={p.name:pin(p.read_bytes()) for p in OLD.iterdir() if p.is_file()};assert len(old_files)==4
    snapshots=read(OLD/'helper_snapshots.json')
    for path,encoded in snapshots.items():assert Path(path).read_bytes()==base64.b64decode(encoded)
    spec=importlib.util.spec_from_file_location('_rti_size_parent',PARENT);parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
    sources=parent.source();source_epoch=pin(canonical(sources))['sha256'];assert source_epoch==parent.SOURCE_SHA
    original=parent.transport();tree=ast.parse(original)
    calls=[node for node in ast.walk(tree) if type(node) is ast.Call and type(node.func) is ast.Attribute and node.func.attr=='b85decode']
    assert len(calls)==1 and type(calls[0].args[0]) is ast.Constant
    old_packed=calls[0].args[0].value;assert type(old_packed) is bytes
    unpacker=zlib.decompressobj();payload=unpacker.decompress(base64.b85decode(old_packed),131073)
    assert len(payload)<=131072 and unpacker.eof and not unpacker.unconsumed_tail and not unpacker.unused_data
    marker=b'\nimport os as _bootstrap_os\n';assert original.count(marker)==1
    prefix=original.partition(marker)[0]
    old_decoder=b'_unpacker=_transport_zlib.decompressobj()'
    new_decoder=b"_unpacker=_transport_zlib.decompressobj(zdict=sys.orig_argv[6].partition('\\nimport os as _bootstrap_os\\n')[0].encode('utf-8'))"
    assert original.count(old_decoder)==1 and original.count(repr(old_packed).encode())==1
    candidates=[];codes=[]
    parameters=[(memory,strategy,None) for memory in (7,8,9) for strategy in (zlib.Z_DEFAULT_STRATEGY,zlib.Z_FILTERED)]
    parameters.extend((memory,zlib.Z_DEFAULT_STRATEGY,prefix) for memory in (7,8))
    for memory,strategy,dictionary in parameters:
        options={} if dictionary is None else dict(zdict=dictionary)
        compressor=zlib.compressobj(9,zlib.DEFLATED,zlib.MAX_WBITS,memory,strategy,**options)
        compressed=compressor.compress(payload)+compressor.flush();packed=base64.b85encode(compressed)
        decoder=zlib.decompressobj(**options);restored=decoder.decompress(base64.b85decode(packed),131073)
        assert restored==payload and decoder.eof and not decoder.unconsumed_tail and not decoder.unused_data
        code=original.replace(repr(old_packed).encode(),repr(packed).encode())
        if dictionary is not None:code=code.replace(old_decoder,new_decoder)
        assert code.partition(marker)[0]==prefix
        ast.parse(code);codes.append(code)
        candidates.append(dict(memory=memory,strategy='default' if strategy==zlib.Z_DEFAULT_STRATEGY else 'filtered',
            dictionary='none' if dictionary is None else 'original_prefix',dictionary_pin=None if dictionary is None else pin(dictionary),
            transport_pin=pin(code),command_utf16_units=units(code),roundtrip=True,payload_byte_identical=True))
    chosen_index=min(range(len(candidates)),key=lambda index:candidates[index]['command_utf16_units'])
    chosen=candidates[chosen_index];chosen_code=codes[chosen_index]
    write(OUT/'original_transport.snapshot',original);write(OUT/'payload.snapshot',payload);write(OUT/'chosen_transport.snapshot',chosen_code)
    for path,encoded in snapshots.items():assert Path(path).read_bytes()==base64.b64decode(encoded)
    assert {p.name:pin(p.read_bytes()) for p in OLD.iterdir() if p.is_file()}==old_files
    assert parent.source()==sources
    previous=read(NGT/'checkpoint.json')['all_cumulative_charged_seconds'];charge=time.perf_counter()-started
    cumulative={**previous,'static':previous['static']+failure['charged_seconds']+charge}
    report=dict(analysis_complete=True,accepted=charge<=2,authority='DRAFT_NONAUTHORITATIVE',kind='static',charged_seconds=charge,cap_seconds=2,
        original_command_utf16_units=units(original),candidates=candidates,chosen=chosen,candidate_within_command_cap=chosen['command_utf16_units']<=30000,
        predecessor_failure_charge=failure['charged_seconds'],prior_not_accepted_count=22,all_cumulative_charged_seconds=cumulative,
        source_pins=sources,source_epoch=source_epoch,input_pins={str(p):pin(p.read_bytes()) for p in (PARENT,SCOPE,Path(__file__).absolute(),NGT/'checkpoint.json')},
        predecessor_root_map=old_files,artifact_pins={p.name:pin(p.read_bytes()) for p in OUT.iterdir() if p.is_file()},
        cold_children_launched=0,unit_children_launched=0,actual_F=False,run_authority=False,formal_result=False,resource_admission=False)
    raw=canonical(report);files=[p for p in OUT.iterdir() if p.is_file()];assert len(files)+1<=6 and sum(p.stat().st_size for p in files)+len(raw)<=1024**2
    write(OUT/'size_report.json',raw)
    print(canonical(dict(accepted=report['accepted'],charge=charge,original_units=report['original_command_utf16_units'],chosen=chosen)).decode())
    if not report['accepted']:raise SystemExit(1)

if __name__=='__main__':main()
