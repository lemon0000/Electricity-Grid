"""Fixed ordinary node groups for the input-projection development contract."""
import json
from capture_checks import ROOT,OUT,entry,capture,save

target='tests/test_staged_rts24_saved_fresh_adoption_v1.py'
result=capture('collection_03','static',[str(entry.EXE),'-B','-m','pytest','--collect-only','-q',target,
    '-p','no:cacheprovider'],10)
nodes=[line for line in (OUT/'collection_03.stdout.log').read_text(encoding='utf-8').splitlines()
    if line.startswith('tests/') and '::test_' in line]
new=[n for n in nodes if '::test_saved_expectation_' in n]
smoke=[n for n in new if any(key in n for key in ('projection_has_equal_image','G0_G2_G3_and_H3'))]
remaining=[n for n in new if n not in smoke]
old=ROOT/'results/tables/staged_rts24_saved_fresh_owner_v1_non_authoritative/checks_01/group_admission_06.json'
related=json.loads(old.read_bytes())['groups']['binding_affected_01']
assert len(smoke)==2 and len(related)==18 and set(related)<=set(nodes)
groups=dict(expectation_smoke_04=smoke,expectation_rest_05=remaining[::2],
    expectation_rest_06=remaining[1::2],binding_regression_07=related)
caps=dict(expectation_smoke_04=25,expectation_rest_05=35,expectation_rest_06=35,binding_regression_07=40)
assert sum(caps.values())<=160
save('collected_nodes.json',nodes)
save('group_admission_01.json',dict(authority='DRAFT_NONAUTHORITATIVE',groups=groups,caps=caps,
    pytest_cap_seconds=160,static_cap_seconds=40,total_cap_seconds=200,actual_saved_F_execution=False,F_launch_admitted=False))
print(json.dumps({name:len(group) for name,group in groups.items()}))
