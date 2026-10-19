"""Updated bounded header question after the measured identity DAG repair."""
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path
import platform
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
D=HERE/'whole_workflow_optimization_01_non_authoritative'
prior=D/'roster4_header_probe_plan_119.json';value=json.loads(prior.read_text())
paths={Path(name) for name in json.loads((D/'public_implementation_identity_cost_plan_125.json').read_text())['files_sha256']}
paths.update((ROOT/'experiments').glob('h1_*.py'));paths.update((ROOT/'tests').glob('*h1*.py'))
paths.update((HERE/'run_unit_bounded_v17.py',HERE/'run_unit_entry_v4.py',
              HERE/'pinned_distribution_resolver_v1.py',Path(__file__)))
base=Path('D:/h1_roster4_header_131_non_authoritative');label='workflow_roster4_header_131'
assert not base.exists() and not (HERE/label).exists()
value.update(schema='h1_roster4_header_probe_plan_131',at_utc=datetime.now(timezone.utc).isoformat(),
    predecessor_plan_sha256=sha256(prior.read_bytes()).hexdigest(),
    current_pre_seal_input_sha256=sha256((D/'public_phase_pre_seal_input_130.json').read_bytes()).hexdigest(),
    command=[sys.executable,'-B',str(HERE/'run_unit_bounded_v17.py'),label,'120','1024','128','--',
        str(HERE/'run_unit_entry_v4.py'),'-s','-p','no:faulthandler','--basetemp',str(base),
        'tests/test_h1_roster4_live_header_development_v1.py'],
    question='Can the genuine header lifecycle complete within the same120s cap after segment-owned Bootstrap identity reuse and tested per-body metadata composition?',
    files_sha256={str(p):sha256(p.read_bytes()).hexdigest() for p in sorted(paths,key=str)},
    environment=dict(interpreter=sys.executable,interpreter_sha256=sha256(Path(sys.executable).read_bytes()).hexdigest(),
        version=sys.version,platform=platform.platform(),timezone='Asia/Shanghai'))
value['optimization'].update(
    reuse='Immutable phase science inside each private data segment; Bootstrap root implementation digest between full raw entry/exit bookends. Metadata parser and discovery paths inside original per-test entry4 resolver scope.',
    boundaries='Runtime checks remain fresh per call. Dynamic journals/registry/N0 uncached. Callback/Job gaps and outside/foreign-thread implementation calls use raw; no per-call source freshness or transient ABA claim.',
    new_evidence=['119 stopped120.281s after Bootstrap create; not a successful or matched baseline.',
        '124 original metadata composition: fast388/fallback0, all bookends/handles/aliases closed.',
        '125 public identity8calls2.165s; repeated dependency DAG is measured CPU attribution, not a whole-workflow runtime.',
        '128 owner identity99 cases;129 observation/failure composition110 cases;130 fresh exact source PRE_SEAL input.'],
    comparison='Changed implementation and diagnostic entry; successful131 would establish lifecycle closure only, not a matched percentage speedup over119.')
value['budget']['estimate']='Six complete one-seed science windows plus12 full Bootstrap identity observations. Each window remains capped256 projects/4096 checks;120s is a fixed diagnostic cap.'
value['budget']['uncertainty']='Remaining real public nested-check and metadata costs are not known; no full N0/Common/paired budget follows.'
value['acceptance'].append('Six segments each have exactly1 entry+1 exit raw implementation attempt, matching private baseline, memo hits>0; all memos cleared before return.')
value['whole_workflow_performance_review_complete']=False
out=D/'roster4_header_probe_plan_131.json'
with out.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(path=str(out),sha256=sha256(out.read_bytes()).hexdigest(),pins=len(paths))))
