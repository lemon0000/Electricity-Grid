"""One fixed, read-only allocation diagnostic; no Job, solver or run authority."""
from hashlib import sha256
import json
from pathlib import Path
import sys
from time import perf_counter

HERE=Path(__file__).resolve().parent;REPO=HERE.parents[3]
sys.path.insert(0,str(REPO))
OUT=HERE/'bounded_read_probe_01_non_authoritative';OUT.mkdir(exist_ok=False)
source_names=('h1_raw_ingress_development_v1.py','h1_phase_dependency_verifier_development_v1.py')
sources={str(REPO/'experiments'/name):sha256((REPO/'experiments'/name).read_bytes()).hexdigest() for name in source_names}
def save(name,value):
    with (OUT/name).open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
save('request.json',dict(sources=sources,repetitions_per_reader=256,rounds=1,cap=32*1024**2,
    target='experiments/h1_registry_declaration_development_v1.py',formal_result=False))
from experiments import h1_raw_ingress_development_v1 as prior
from experiments import h1_phase_dependency_verifier_development_v1 as bounded
target=REPO/'experiments/h1_registry_declaration_development_v1.py';size=target.stat().st_size
rows=[];basis=None
for name,reader in (('predecessor',prior.read_stable),('bounded',bounded.read_stable)):
    start=perf_counter()
    for _ in range(256):
        value=reader(target,32*1024**2)
        if basis is None:basis=value
        assert value==basis
    rows.append(dict(reader=name,repetitions=256,seconds=perf_counter()-start,
        requested_bytes_per_read=32*1024**2+1 if name=='predecessor' else size+1))
unchanged=all(sha256(Path(p).read_bytes()).hexdigest()==pin for p,pin in sources.items())
result=dict(exit_code=0 if unchanged else 1,measurements=rows,source_unchanged=unchanged,
    target_bytes=size,target_sha256=sha256(basis[0]).hexdigest(),fresh_reads=512,
    all_raw_and_identity_tuples_equal=True,allocation_request_is_not_physical_IO=True,
    formal_result=False,resource_admission=False,full_hour0_chain_passed=False)
save('terminal.json',result);print(json.dumps(result),flush=True)
sys.exit(result['exit_code'])
