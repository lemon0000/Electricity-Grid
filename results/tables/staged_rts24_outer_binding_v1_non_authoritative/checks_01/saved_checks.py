"""Stdlib preservation and final ordinary-check audit, no scientific imports."""
from hashlib import sha256, sha1
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
PRIOR=ROOT/'results/tables/staged_rts24_terminal_budget_v1_non_authoritative/checks_01'
NAV=tuple(json.loads((PRIOR/'navigation_original_bytes.json').read_bytes()))


def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def save(name,value):
    (OUT/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n',encoding='utf-8')


def bootstrap():
    paths=set(json.loads((PRIOR/'preservation_inventory.json').read_bytes()))
    changed=subprocess.check_output(['git','diff-tree','--no-commit-id','--name-only','-r','-z','HEAD'],cwd=ROOT)
    paths.update(n.decode('utf-8') for n in changed.split(b'\0') if n)
    names=sorted(paths)
    objects=subprocess.run(['git','cat-file','--batch-check=%(objectname) %(objecttype) %(objectsize)'],
        input=b''.join(('HEAD:'+n+'\n').encode('utf-8') for n in names),capture_output=True,check=True,cwd=ROOT).stdout.splitlines()
    assert len(objects)==len(names)
    preserved={};tails={}
    for name,record in zip(names,objects):
        blob,kind,size=record.split();raw=(ROOT/name).read_bytes()
        assert kind==b'blob' and len(raw)==int(size) and sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==blob.decode()
        if name in NAV:
            header,sep,body=raw.partition(b'\n\n');assert sep
            tails[name]=dict(header=header.decode('utf-8'),body=pin(body))
        else:preserved[name]=pin(raw)
    save('preservation_inventory.json',preserved);save('navigation_tail_inventory.json',tails)
    prior=subprocess.run([sys.executable,'-B',str(PRIOR/'saved_checks.py')],cwd=ROOT,capture_output=True,timeout=30)
    assert prior.returncode==0 and prior.stderr==b'' and prior.stdout==(PRIOR/'verify_02.stdout.json').read_bytes()
    (OUT/'prior_01.stdout.json').write_bytes(prior.stdout);(OUT/'prior_01.stderr.log').write_bytes(prior.stderr)
    save('prior_01.exit.json',dict(exit_code=0,script=pin((PRIOR/'saved_checks.py').read_bytes()),
        stdout=pin(prior.stdout),exact_prior_stdout=True))
    print(json.dumps(dict(preserved_paths=len(preserved),navigation_bodies=len(tails),prior_stdout_exact=True)))


def verify():
    preserved=json.loads((OUT/'preservation_inventory.json').read_bytes())
    for name,value in preserved.items():assert pin((ROOT/name).read_bytes())==value,('old file drift',name)
    tails=json.loads((OUT/'navigation_tail_inventory.json').read_bytes())
    for name,value in tails.items():
        raw=(ROOT/name).read_bytes();assert raw.split(b'\n\n',1)[0].decode('utf-8')==value['header']
        assert pin(raw[-value['body']['bytes']:])==value['body'],('old navigation body drift',name)
    summary=json.loads((OUT/'ordinary_check_summary.json').read_bytes())
    for name,value in summary['source_pins'].items():assert pin((ROOT/name).read_bytes())==value
    for name,value in summary['support_pins'].items():assert pin((ROOT/name).read_bytes())==value
    for label,group in summary['groups'].items():
        record=json.loads((OUT/(label+'.exit.json')).read_bytes())
        assert record['exit_code']==0 and record['timed_out'] is False and record['source_pins_unchanged'] is True
        assert record['source_pins']==summary['source_pins']
        assert pin((OUT/(label+'.exit.json')).read_bytes())==group['exit']
        assert pin((OUT/(label+'.stdout.log')).read_bytes())==group['stdout']
        assert (str(group['passed'])+' passed').encode() in (OUT/(label+'.stdout.log')).read_bytes()
        assert (OUT/(label+'.stderr.log')).read_bytes()==b''
    collection=json.loads((OUT/'collection_01.exit.json').read_bytes())
    assert collection['exit_code']==0 and collection['source_pins']==summary['source_pins']
    nodes=(OUT/'collection_01.stdout.log').read_text().splitlines()
    nodes=[n for n in nodes if n.startswith('tests/') and '::' in n]
    assert len(nodes)==len(set(nodes))==collection['node_count']==261
    assert pin((OUT/'collection_01.stdout.log').read_bytes())==collection['stdout']
    assert json.loads((OUT/'units_01.exit.json').read_bytes())['exit_code']==1
    review=json.loads((OUT/'preseal_review.json').read_bytes())
    assert review['remaining_findings']==[] and review['source_pins']==summary['source_pins']
    assert review['official_verdict'] is review['receipt'] is review['seal'] is None
    docs=json.loads((OUT/'document_checks.json').read_bytes())
    assert all(pin((ROOT/n).read_bytes())==v for n,v in docs['document_pins'].items())
    prior=subprocess.run([sys.executable,'-B',str(PRIOR/'saved_checks.py')],cwd=ROOT,capture_output=True,timeout=30)
    assert prior.returncode==0 and prior.stderr==b'' and prior.stdout==(OUT/'prior_01.stdout.json').read_bytes()
    native=ROOT/'results/tables/staged_rts24_p2_native_v1_non_authoritative'
    assert not (native/'p2_01').exists() and not (native/'registration_v1.json').exists()
    return dict(authority='DRAFT_NONAUTHORITATIVE',targeted_distinct_passed=48,related_distinct_passed=213,
        preserved_paths_unchanged=len(preserved),navigation_bodies_preserved=len(tails),prior_stdout_exact=True,
        parent_startup_short_Python_only=True,full_319_synthetic_metadata_only=True,source_scope='selected_only',
        public_P2_registered=False,public_P2_executed=False,new_native_calls=0,scientific_evidence_adopted=False,
        actual_OS_commandline_independently_verified=False,full_runtime_closure_verified=False,
        resource_admission=False,formal_result=False,full_outer_time_budget_closed=False)


if __name__=='__main__':
    if sys.argv[1:]==['bootstrap']:bootstrap()
    else:print(json.dumps(verify(),sort_keys=True,indent=2))
