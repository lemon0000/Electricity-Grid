"""Stdlib preservation and final ordinary-check audit, no scientific imports."""
from hashlib import sha256, sha1
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
PRIOR=ROOT/'results/tables/staged_rts24_saved_prefix_replay_v1_non_authoritative/checks_01'
NAV=tuple(json.loads((PRIOR/'navigation_tail_inventory.json').read_bytes()))


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
    assert prior.returncode==0 and prior.stderr==b'' and prior.stdout==(PRIOR/'verify_01.stdout.json').read_bytes()
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
    for group in ('source_pins','component_source_pins','support_pins'):
        for name,value in summary[group].items():assert pin((ROOT/name).read_bytes())==value,(group,name)
    assert len(summary['component_source_pins'])==26 and summary['component_source_group']=='selected_only'
    assert json.loads((OUT/'component_source_pins.json').read_bytes())==summary['component_source_pins']
    assert {n:g['passed'] for n,g in summary['groups'].items()}=={'units_03':40,'saved_02':1,'related_02':192}
    for label,group in summary['groups'].items():
        record=json.loads((OUT/(label+'.exit.json')).read_bytes())
        assert record['exit_code']==0 and record['timed_out'] is False and record['source_pins_unchanged'] is True
        assert record['source_pins']==summary['source_pins']
        assert pin((OUT/(label+'.exit.json')).read_bytes())==group['exit']
        assert pin((OUT/(label+'.stdout.log')).read_bytes())==group['stdout']
        assert (str(group['passed'])+' passed').encode() in (OUT/(label+'.stdout.log')).read_bytes()
        assert (OUT/(label+'.stderr.log')).read_bytes()==b''
    for label in ('units_01','units_02','saved_01','related_01'):
        record=json.loads((OUT/(label+'.exit.json')).read_bytes())
        assert record['exit_code']==0 and record['timed_out'] is False
    collection=json.loads((OUT/'collection_01.exit.json').read_bytes())
    assert collection['exit_code']==0 and collection['source_pins']==summary['source_pins']
    nodes=[n for n in (OUT/'collection_01.stdout.log').read_text().splitlines() if n.startswith('tests/') and '::' in n]
    assert len(nodes)==len(set(nodes))==collection['node_count']==233
    assert collection['new_distinct']==41 and collection['related_distinct']==192
    assert pin((OUT/'collection_01.stdout.log').read_bytes())==collection['stdout']
    review=json.loads((OUT/'preseal_review.json').read_bytes())
    assert review['remaining_findings']==[] and review['source_pins']==summary['source_pins']
    assert review['official_verdict'] is review['receipt'] is review['seal'] is None
    assert len(review['closed_findings'])==4
    docs=json.loads((OUT/'document_checks.json').read_bytes())
    assert all(pin((ROOT/n).read_bytes())==v for n,v in docs['document_pins'].items())
    printed=[json.loads(line) for line in (OUT/'saved_02.stdout.log').read_text().splitlines() if line.startswith('{')]
    assert len(printed)==1 and printed[0]==json.loads((OUT/'saved_contract_observation.json').read_bytes())
    result=printed[0]
    assert result['P1_683_files_unchanged'] is True and result['new_native_calls']==0 and result['replayed_points']==10
    assert result['calls']==dict(compile=20,snapshot=10,import_snapshot=10,hour_requests=2,legal_x=4,
        explicit_firm_audit=4,source_reads=954,point_reads=1024,row_reads=2,typed_pack=50)
    assert result['cas_objects']==88 and len(result['rows'])==4 and len(result['queries'])==10
    for name in ('scientific_evidence_adopted','full_fx_contract_verified','independent_139_verified',
            'journal_replayed','resource_admission','formal_result'):assert result[name] is False
    p1=ROOT/'results/tables/staged_rts24_native_v1_non_authoritative/p1_01'
    anchor=p1.parent/'p1_execution_review_01/postcheck_03.stdout.json';anchor_raw=anchor.read_bytes()
    assert sha256(anchor_raw).hexdigest()=='c6a25cd96c8a4a2cf293d41fe51bc7905db63fbc35253076f97e9239a4f22473'
    p1_files=json.loads(anchor_raw)['p1_files'];assert len(p1_files)==683
    assert all(pin((p1/name).read_bytes())==value for name,value in p1_files.items())
    assert json.dumps(result['rows'],ensure_ascii=True,sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii')==(p1/'contract_rows.json').read_bytes()
    for ordinal,row in zip(range(22,32),result['queries']):
        saved=json.loads((p1/f'points/point_{ordinal:04d}/result.json').read_bytes())
        request=json.loads((p1/f'points/point_{ordinal:04d}/request.json').read_bytes())
        assert row['ordinal']==ordinal and row['query_sha']==request['query_sha']
        assert row['evidence_ref']==saved['evidence_ref']
    assert [r['evidence_family'] for r in result['queries']]==['economic_kkt','primal_point','child_lp_kkt','primal_point','child_lp_kkt']*2
    for row in result['rows']:
        assert row['raw_curtailment_mw']==0 and row['firm_audit']['point_constraints_satisfied'] is True
        assert row['legal_X']==dict(point_legal_under_X=True,minimum_established=False,
            independent_firm_point_still_required=True,temporal_backing='not_established')
    prior=subprocess.run([sys.executable,'-B',str(PRIOR/'saved_checks.py')],cwd=ROOT,capture_output=True,timeout=30)
    assert prior.returncode==0 and prior.stderr==b'' and prior.stdout==(OUT/'prior_01.stdout.json').read_bytes()
    native=ROOT/'results/tables/staged_rts24_p2_native_v1_non_authoritative'
    assert not (native/'p2_01').exists() and not (native/'registration_v1.json').exists()
    return dict(authority='DRAFT_NONAUTHORITATIVE',targeted_distinct_passed=41,related_distinct_passed=192,
        preserved_paths_unchanged=len(preserved),navigation_bodies_preserved=len(tails),prior_stdout_exact=True,
        saved_P1_replayed_points=10,saved_P1_representative_rows_matched=4,P1_683_files_unchanged=True,
        source_scope='selected_only',component_sources=26,preseal_findings_remaining=0,
        public_P2_registered=False,public_P2_executed=False,new_native_calls=0,scientific_evidence_adopted=False,
        expected_query_provenance_independently_verified=False,full_fx_contract_verified=False,independent_139_verified=False,
        journal_replayed=False,actual_OS_commandline_independently_verified=False,full_runtime_closure_verified=False,
        resource_admission=False,formal_result=False,full_outer_time_budget_closed=False)


if __name__=='__main__':
    if sys.argv[1:]==['bootstrap']:bootstrap()
    else:print(json.dumps(verify(),sort_keys=True,indent=2))
