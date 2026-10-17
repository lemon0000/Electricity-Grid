"""Current-byte saved-arm comparison, with an explicit code-read lease receipt."""
from contextlib import ExitStack
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
from time import perf_counter
import traceback

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
mode,label=sys.argv[1:3];assert mode in ('plain','leased','views','parse')
target=sys.argv[3] if len(sys.argv)>3 else 'arm'
assert target in ('arm','phase')
out=ROOT/'performance'/label;out.mkdir(exist_ok=False)
prefix=out/'empty_pycache';prefix.mkdir();sys.pycache_prefix=str(prefix)
from performance.code_read_lease import CodeReadLease
from performance.metadata_parse_lease import MetadataParseLease
REPO=Path('D:/CUHKSZ/Research Project/electricity-grid')
sys.path[:0]=[str(REPO),str(REPO/'tests')]

def save(name,value):
    with (out/name).open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)

allowlist=ROOT/'performance/code_allowlist_v2.json'
assert sha256(allowlist.read_bytes()).hexdigest()=='06ea1daacdef6a1b575b404b9f8c1025eae6febccff2a6d2f75cc9d5ba203c19'
expected={Path(name):pin for name,pin in json.loads(allowlist.read_bytes())['files_sha256'].items()}
code_pins={str(p):sha256(p.read_bytes()).hexdigest() for p in (
    Path(__file__),ROOT/'performance/code_read_lease.py',ROOT/'performance/metadata_parse_lease.py',allowlist)}
metadata_allowlist=ROOT/'performance/metadata_allowlist_v1.json'
assert sha256(metadata_allowlist.read_bytes()).hexdigest()=='90fc679a8e71971e1f0bdb97575ed83d9a620826c7670ce5a308566b7b710302'
code_pins[str(metadata_allowlist)]=sha256(metadata_allowlist.read_bytes()).hexdigest()
save('request.json',dict(mode=mode,candidate_sha256=code_pins,pycache_prefix=str(prefix),
    pycache_prefix_initially_empty=not any(prefix.iterdir()),dont_write_bytecode=sys.dont_write_bytecode,
    formal_result=False))
start=perf_counter();result=dict(mode=mode,formal_result=False,full_chain_passed=False)
try:
    with ExitStack() as stack:
        lease=stack.enter_context(CodeReadLease(expected,root=REPO,code_views=mode in ('views','parse'))) if mode!='plain' else None
        parse=None
        E=REPO/'results/tables/rq2_h1_hour0_end_to_end_v2_non_authoritative'
        spec=importlib.util.spec_from_file_location('pair_fixture',E/'replay_saved_with_fixture_v1.py')
        fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
        from experiments import h1_selector_input_snapshot_development_v2 as snapshot
        if mode in ('views','parse'):
            from experiments import h1_phase_dependency_verifier_development_v1 as bounded
            from experiments import h1_raw_ingress_development_v1 as raw_ingress
            lease.bind_readers((bounded.read_stable,raw_ingress.read_stable))
        common=snapshot.common.common
        saved=Path('D:/h1_chain_06_non_authoritative')
        header=json.loads(next(saved.glob('nt_non_authoritative/common_owners_non_authoritative/*/header.json')).read_bytes())['declaration']
        base=saved/'test_complete_independent_N0_r0'
        packet=json.loads((base/'parent_non_authoritative/worker_non_authoritative/selector_snapshot.json').read_bytes())
        d=packet['declaration'];manifest,binding,configuration=snapshot._declarations(d['manifest'],d['source_binding'],d['run_configuration'])
        report=header['initial_report'];arm=report['canonical_arm']
        before={str(p):sha256(p.read_bytes()).hexdigest() for p in saved.rglob('*') if p.is_file()}
        patch=fixture.complete_fixture(fixture.saved.synthetic_source)(base)
        try:
            if mode=='parse':parse=stack.enter_context(MetadataParseLease(json.loads(metadata_allowlist.read_bytes())['files_sha256']))
            begin=perf_counter()
            if target=='phase':
                fingerprint=common.bootstrap._phase_input_fingerprint(configuration)
                result['phase_seconds']=perf_counter()-begin;save('scientific.json',fingerprint)
            else:
                produced=common._arm(report['arm_audits'][arm]['reference'],binding.registry_identity,manifest)
                result['arm_seconds']=perf_counter()-begin
                assert common.encode(produced[1])==common.encode(report['common_scientific_payload'])
                audit=json.loads(common.encode(produced[2]));prior=json.loads(common.encode(report['arm_audits'][arm]))
                audit.pop('verification_execution',None)
                audit['exact_current_audit'].pop('implementation_identity')
                prior['exact_current_audit'].pop('implementation_identity')
                assert common.encode(audit)==common.encode(prior)
                save('scientific.json',produced[1]);save('audit.json',produced[2])
        finally:patch.undo()
        after={str(p):sha256(p.read_bytes()).hexdigest() for p in saved.rglob('*') if p.is_file()}
        assert before==after
        result.update(saved_files_unchanged=True,saved_file_count=len(before),
            numerical_contract='4 full numerical hour replays and 4 fresh revalidations',
            source_cache=False,real_native_calls=0)
        if lease:save('lease_receipt.json',lease.receipt())
        if parse:save('metadata_receipt.json',parse.receipt())
    result['exit_code']=0
except BaseException:
    result.update(exit_code=1,error=traceback.format_exc())
finally:
    if any(sha256(Path(p).read_bytes()).hexdigest()!=pin for p,pin in code_pins.items()):
        result.update(exit_code=1,error='candidate code changed during measurement')
    result['elapsed_seconds']=perf_counter()-start
    save('terminal.json',result);print(json.dumps(result),flush=True)
sys.exit(result['exit_code'])
