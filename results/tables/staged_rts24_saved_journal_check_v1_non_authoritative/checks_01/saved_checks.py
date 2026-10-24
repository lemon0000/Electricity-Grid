"""Stdlib preservation and final ordinary-check audit, no scientific imports."""
from hashlib import sha256, sha1
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
PRIOR=ROOT/'results/tables/staged_rts24_saved_contract_replay_v1_non_authoritative/checks_01'
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
    assert len(summary['component_source_pins'])==45 and summary['component_source_group']=='selected_only'
    assert json.loads((OUT/'component_source_pins.json').read_bytes())==summary['component_source_pins']
    assert {n:g['passed'] for n,g in summary['groups'].items()}=={'chain_04':1,'bindings_02':15,'related_02a':12,'related_02b':12}
    for label,group in summary['groups'].items():
        record=json.loads((OUT/(label+'.exit.json')).read_bytes())
        assert record['exit_code']==0 and record['timed_out'] is False and record['source_pins_unchanged'] is True
        assert record['timeout_seconds']==90 and record['wall_seconds']<90 and record['source_pins']==summary['source_pins']
        assert pin((OUT/(label+'.exit.json')).read_bytes())==group['exit']
        assert pin((OUT/(label+'.stdout.log')).read_bytes())==group['stdout']
        assert (str(group['passed'])+' passed').encode() in (OUT/(label+'.stdout.log')).read_bytes()
        assert (OUT/(label+'.stderr.log')).read_bytes()==b''
    old=json.loads((OUT/'chain_01.exit.json').read_bytes());assert old['exit_code']==1 and old['timed_out'] is False
    old=json.loads((OUT/'related_01.exit.json').read_bytes());assert old['exit_code']==0 and 89<old['wall_seconds']<90
    exceptions=json.loads((OUT/'raw_log_whitespace_exceptions.json').read_bytes())
    allowed={str((OUT/n).relative_to(ROOT).as_posix()) for n in
        ('chain_01.stdout.log','related_02a.launcher.stdout.log','related_02b.launcher.stdout.log')}
    assert set(exceptions['pins'])==allowed and exceptions['raw_bytes_preserved'] is True
    assert all(pin((ROOT/n).read_bytes())==v for n,v in exceptions['pins'].items())
    collection=json.loads((OUT/'collection_01.exit.json').read_bytes())
    assert collection['exit_code']==0 and collection['source_pins']==summary['source_pins']
    nodes=[n for n in (OUT/'collection_01.stdout.log').read_text().splitlines() if n.startswith('tests/') and '::' in n]
    assert len(nodes)==len(set(nodes))==collection['node_count']==40
    assert collection['new_distinct']==16 and collection['related_distinct']==24
    assert pin((OUT/'collection_01.stdout.log').read_bytes())==collection['stdout']
    flat=[n for group in collection['group_nodes'].values() for n in group]
    assert set(flat)==set(nodes) and len(flat)==len(set(flat))==40
    assert {k:len(v) for k,v in collection['group_nodes'].items()}=={n:g['passed'] for n,g in summary['groups'].items()}
    split=json.loads((OUT/'related_split_nodes.json').read_bytes())
    assert all(collection['group_nodes'][n]==v for n,v in split.items())
    review=json.loads((OUT/'preseal_review.json').read_bytes())
    assert review['remaining_findings']==[] and review['source_pins']==summary['source_pins']
    assert review['official_verdict'] is review['receipt'] is review['seal'] is None
    assert len(review['closed_findings'])==4
    docs=json.loads((OUT/'document_checks.json').read_bytes())
    assert all(pin((ROOT/n).read_bytes())==v for n,v in docs['document_pins'].items())
    printed=[json.loads(line) for line in (OUT/'chain_04.stdout.log').read_text().splitlines() if line.startswith('{')]
    assert len(printed)==1 and printed[0]==json.loads((OUT/'saved_journal_observation.json').read_bytes())
    result=printed[0]
    assert result['P1_683_files_unchanged'] is True and result['new_native_calls']==0
    assert result['saved_P1_journal_reopened'] is True and result['simulated_hours']==5 and result['reconstructed_points']==21
    assert result['final_entries']==6 and result['saved_objects']==130 and result['accepted_hours']==5
    assert result['compile']=={'B':42} and result['snapshot']==result['import_snapshot']=={'B':21}
    assert result['prepare']==result['propose']=={'B':10,'E':10}
    assert result['execution_audit']=={'B':16,'E':17} and result['historical_rows']=={'B':40,'E':45}
    assert result['typed_pack']=={'B':105,'E':27,'join':23}
    assert result['io']=={'source_before:source':45,'inventory_before:P1':683,'B:source':1912,'B:P1':2152,
        'E:source':78,'E:P1':801,'inventory_after:P1':683,'source_after:source':45,'anchor_after:source':1}
    assert result['source_pins']==summary['component_source_pins']
    assert result['scientific_outcome']=='missing_input' and result['publication_outcome']=='committed' and result['state_certainty']=='known'
    assert result['summary']['coverage_complete'] is False
    assert result['summary']['method_conditions_satisfied'] is result['summary']['full_replay_conditions_satisfied'] is None
    for name in ('journal_replayed','scientific_evidence_adopted','full_fx_contract_verified','independent_139_verified',
            'resource_admission','formal_result'):assert result[name] is False
    p1=ROOT/'results/tables/staged_rts24_native_v1_non_authoritative/p1_01'
    anchor=p1.parent/'p1_execution_review_01/postcheck_03.stdout.json';anchor_raw=anchor.read_bytes()
    assert sha256(anchor_raw).hexdigest()=='c6a25cd96c8a4a2cf293d41fe51bc7905db63fbc35253076f97e9239a4f22473'
    p1_files=json.loads(anchor_raw)['p1_files'];assert len(p1_files)==683
    assert all(pin((p1/name).read_bytes())==value for name,value in p1_files.items())
    assert len(result['evidence_refs'])==21
    for n,row in enumerate(result['evidence_refs'],1):
        saved=json.loads((p1/f'points/point_{n:04d}/result.json').read_bytes())
        request=json.loads((p1/f'points/point_{n:04d}/request.json').read_bytes())
        assert row['ordinal']==n and row['evidence_ref']==saved['evidence_ref'] and row['query_sha']==request['query_sha']
    binding=json.loads((p1/'trusted_binding.json').read_bytes())
    assert result['state_sha']==binding['known_state_sha']
    prior=subprocess.run([sys.executable,'-B',str(PRIOR/'saved_checks.py')],cwd=ROOT,capture_output=True,timeout=30)
    assert prior.returncode==0 and prior.stderr==b'' and prior.stdout==(OUT/'prior_01.stdout.json').read_bytes()
    native=ROOT/'results/tables/staged_rts24_p2_native_v1_non_authoritative'
    assert not (native/'p2_01').exists() and not (native/'registration_v1.json').exists()
    return dict(authority='DRAFT_NONAUTHORITATIVE',targeted_distinct_passed=16,related_distinct_passed=24,
        preserved_paths_unchanged=len(preserved),navigation_bodies_preserved=len(tails),prior_stdout_exact=True,
        saved_P1_reconstructed_points=21,saved_P1_journal_reopened=True,P1_683_files_unchanged=True,
        source_scope='selected_only',component_sources=45,preseal_findings_remaining=0,
        public_P2_registered=False,public_P2_executed=False,new_native_calls=0,scientific_evidence_adopted=False,
        expected_query_provenance_independently_verified=False,full_fx_contract_verified=False,independent_139_verified=False,
        journal_replayed=False,actual_OS_commandline_independently_verified=False,full_runtime_closure_verified=False,
        resource_admission=False,formal_result=False,full_outer_time_budget_closed=False)


if __name__=='__main__':
    if sys.argv[1:]==['bootstrap']:bootstrap()
    else:print(json.dumps(verify(),sort_keys=True,indent=2))
