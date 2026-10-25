"""Independent stdlib fixture oracle; does not import the validator or its helpers."""
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[4]
P1=ROOT/'results/tables/staged_rts24_native_v1_non_authoritative/p1_01'
OUTPUT=ROOT/'results/tables/staged_rts24_saved_fresh_adoption_v1_non_authoritative/draft_01'
FROZEN=ROOT/'results/tables/staged_rts24_saved_fresh_runtime_binding_v1_non_authoritative/checks_01'

def encode(value):return json.dumps(value,sort_keys=True,ensure_ascii=True,separators=(',',':'),allow_nan=False).encode('ascii')
def sha(raw):return sha256(raw).hexdigest()
def byte_pin(raw):return dict(bytes=len(raw),sha256=sha(raw))
def stamp(path):
    s=path.lstat();return [s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns]
def ancestors(path,synthetic=False):
    return [[str(p),1 if synthetic else p.lstat().st_dev,i+1 if synthetic else p.lstat().st_ino]
        for i,p in enumerate(reversed((path,*path.parents)))]


def build():
    spec_raw=(FROZEN/'successor_context_spec_v3.json').read_bytes()
    assert byte_pin(spec_raw)==dict(bytes=18167,sha256='b151876e286f24dca3571134e4506e55978f0fe1dee949b76005f3e3c24b2f90')
    spec=json.loads(spec_raw)
    contracts={key:(ROOT/spec[key]['path']).read_bytes() for key in ('runtime_binding_contract','deadline_contract','request_contract')}
    assert all(byte_pin(raw)==spec[key]['pin'] for key,raw in contracts.items())
    runtime=json.loads(contracts['runtime_binding_contract'])
    source={n:byte_pin((ROOT/n).read_bytes()) for n in runtime['source_names']}
    anchor=P1.parent/'p1_execution_review_01/postcheck_03.stdout.json';anchor_raw=anchor.read_bytes()
    assert sha(anchor_raw)=='c6a25cd96c8a4a2cf293d41fe51bc7905db63fbc35253076f97e9239a4f22473'
    pins=json.loads(anchor_raw)['p1_files']
    def saved(name):
        raw=(P1/name).read_bytes();assert byte_pin(raw)==pins[name];return json.loads(raw)
    start=saved('start.json');bindings=[saved(f'trusted_prefixes/prefix_{n:06d}.json') for n in range(6)]
    slots=saved('request_schedule.json')[:21]
    expected=dict(fixture_sha=saved('journal/genesis.json')['fixture_sha'],initial_state_sha=bindings[0]['known_state_sha'],
        after_state_shas=[b['known_state_sha'] for b in bindings[1:]],pins_sha=sha(encode(start['pins'])),
        registration_sha=start['registration_sha'],slots=slots,
        point_files={str(i):{n[len(f'points/point_{i:04d}/'):]:p for n,p in pins.items() if n.startswith(f'points/point_{i:04d}/')} for i in range(1,22)})
    refs=[dict(ordinal=i,role=slots[i-1]['role'],query_sha=saved(f'points/point_{i:04d}/request.json')['query_sha'],
        evidence_ref=saved(f'points/point_{i:04d}/result.json')['evidence_ref']) for i in range(1,22)]
    dirs={p.relative_to(P1).as_posix():[p.lstat().st_dev,p.lstat().st_ino] for p in (P1,*[p for p in P1.rglob('*') if p.is_dir()])}
    core=dict(files=pins,fixture_sha=expected['fixture_sha'],outer=saved('launcher.json'),trusted=saved('trusted_binding.json'),
        expectations=expected,bindings=bindings,source=source,anchor_path=str(anchor),anchor_pin=byte_pin(anchor_raw),
        anchor_identity=stamp(anchor),anchor_directories=ancestors(anchor.parent),root_directories=ancestors(P1),
        inventory=dict(pins=pins,files={n:stamp(P1/n) for n in pins},directories=dirs),
        historical_metrics=saved('fresh.json')['metrics'],expected_evidence_refs=refs)
    gates={n:False for n in ('native_authorized','resource_admission','formal_result','scientific_evidence_adopted','public_P2_execution_enabled')}
    readset=sorted(['launcher.json','trusted_binding.json','start.json','request_schedule.json','fresh.json']
        +[f'trusted_prefixes/prefix_{n:06d}.json' for n in range(6)]
        +[f'points/point_{i:04d}/{leaf}.json' for i in range(1,22) for leaf in ('request','result')])
    expectation=dict(schema='staged_saved_P1_caller_expectation_development_v1',authority='DRAFT_NONAUTHORITATIVE',
        scope=spec['scope'],caller_expectation_core=core,caller_expectation_sha=sha(encode(core)),
        source_sha=sha(encode(source)),input_pins_sha=sha(encode(pins)),content_read_files=readset,metadata_passes=2,
        full_P1_content_verified=False,F_launch_admitted=False,**gates)
    expectation_raw=encode(expectation)
    environment={k:v for k,v in os.environ.items() if k.upper() in spec['environment_allowed_keys']}
    environment.update(spec['environment_fixed_values'])
    exe=Path('D:/Miniconda3/envs/compute/python.exe')
    executable=dict(path=str(exe),pin=byte_pin(exe.read_bytes()),identity=stamp(exe),python=spec['field_rules']['executable']['constraint']['python'])
    basis=dict(source_pins=source,executable=executable,environment=environment,
        host_identity=dict(pid=1001,creation_filetime=2001),broker_identity=dict(pid=1002,creation_filetime=2002),
        output_parent_directories=ancestors(OUTPUT.parent,synthetic=True))
    request=dict(schema='staged_saved_F_successor_request_development_v1',authority='DRAFT_NONAUTHORITATIVE',scope=spec['scope'],
        nonce='a'*64,host_identity=basis['host_identity'],repo_root=str(ROOT),input_root=str(P1),output_root=str(OUTPUT),
        source_sha=sha(encode(source)),executable_pin=executable['pin'],environment_sha=sha(encode(environment)),
        input_pins_sha=sha(encode(pins)),caller_expectation_sha=sha(encode(core)),expectation_sha=sha(expectation_raw),
        anchor_sha=sha(anchor_raw),invocation_started=1000.0,deadline=1180.0,
        runtime_binding_contract_sha=spec['runtime_binding_contract']['pin']['sha256'],
        deadline_profile_sha=spec['deadline_contract']['pin']['sha256'],limits=spec['exact_limits'])
    context=dict(schema=spec['schema_literal'],authority='DRAFT_NONAUTHORITATIVE',scope=spec['scope'],
        repo_root=str(ROOT),input_root=str(P1),output_root=str(OUTPUT),output_mode=spec['output_mode'],
        output_parent_directories=basis['output_parent_directories'],source_pins=source,executable=executable,
        environment=environment,anchor_sha=sha(anchor_raw),input_files=pins,invocation_started=1000.0,deadline=1180.0,
        stage_seconds=spec['exact_stage_seconds'],limits=spec['exact_limits'],
        inherited_sources_pin=byte_pin((ROOT/'results/tables/staged_rts24_saved_journal_check_v1_non_authoritative/checks_01/component_source_pins.json').read_bytes()),
        caller_expectation_core=core,caller_expectation_sha=sha(encode(core)),expectation_sha=sha(expectation_raw),
        full_P1_content_verified=False,request_sha=sha(encode(request)),broker_identity=basis['broker_identity'],
        runtime_binding_contract_sha=request['runtime_binding_contract_sha'],deadline_profile_sha=request['deadline_profile_sha'],**gates)
    assert sorted(context)==spec['fields']
    return dict(context_raw=encode(context),request_raw=encode(request),expectation_raw=expectation_raw,
        host_basis_raw=encode(basis),anchor_raw=anchor_raw,runtime_contract_raw=contracts['runtime_binding_contract'],
        deadline_contract_raw=contracts['deadline_contract'],request_contract_raw=contracts['request_contract'],now=1000.25)
