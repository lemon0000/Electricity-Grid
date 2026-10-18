"""Two fixed split projections, fresh predecessor and bounded successor once."""
from hashlib import sha256
import json
from pathlib import Path
import sys
from time import perf_counter

HERE=Path(__file__).resolve().parent;REPO=HERE.parents[3]
sys.path.insert(0,str(REPO))
OUT=HERE/'registry_reads_01_non_authoritative';OUT.mkdir(exist_ok=False)
sources={str(REPO/'experiments'/name):sha256((REPO/'experiments'/name).read_bytes()).hexdigest()
    for name in ('h1_raw_ingress_development_v1.py','h1_phase_dependency_verifier_development_v1.py',
        'h1_registry_declaration_development_v1.py','h1_registry_declaration_development_v2.py')}
def save(name,value):
    with (OUT/name).open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
save('request.json',dict(source_sha256=sources,splits=['training','holdout'],rounds=1,
    old_builds=2,new_builds=2,source_and_result_cache=False,formal_result=False))
from experiments import h1_registry_declaration_development_v1 as prior
from experiments import h1_registry_declaration_development_v2 as candidate
rows=[]
for split in ('training','holdout'):
    start=perf_counter();old=prior.build(split);old_seconds=perf_counter()-start
    start=perf_counter();new=candidate.build(split);new_seconds=perf_counter()-start
    assert type(new) is candidate.VerifiedRegistryDeclaration and new.compatibility_raw==old
    assert new.value()==json.loads(old)
    proof=json.loads(new.verification_receipt)
    assert proof['compatibility_raw_sha256']==sha256(old).hexdigest()
    (OUT/(split+'_raw.json')).write_bytes(old)
    (OUT/(split+'_verification.json')).write_bytes(new.verification_receipt)
    rows.append(dict(split=split,predecessor_seconds=old_seconds,candidate_seconds=new_seconds,
        raw_sha256=sha256(old).hexdigest(),receipt_sha256=sha256(new.verification_receipt).hexdigest(),
        compatibility_raw_exact=True,execution=proof))
unchanged=all(sha256(Path(p).read_bytes()).hexdigest()==pin for p,pin in sources.items())
result=dict(exit_code=0 if unchanged else 1,measurements=rows,source_unchanged=unchanged,
    formal_result=False,resource_admission=False,full_hour0_chain_passed=False,
    real_native_calls=0,synthetic_jobs=0)
save('terminal.json',result);print(json.dumps(result),flush=True)
sys.exit(result['exit_code'])
