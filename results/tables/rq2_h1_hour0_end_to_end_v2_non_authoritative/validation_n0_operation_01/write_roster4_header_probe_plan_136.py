"""Revalidate the public header after the audited thread and opt-in changes."""
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
D=HERE/'whole_workflow_optimization_01_non_authoritative'
prior=D/'roster4_header_probe_plan_131.json';value=json.loads(prior.read_text())
paths={Path(p) for p in value['files_sha256']};paths.add(Path(__file__))
paths.update((ROOT/'tests').glob('*h1*.py'));paths.update((ROOT/'experiments').glob('h1_*.py'))
base=Path('D:/h1_roster4_header_136_non_authoritative');label='workflow_roster4_header_136'
assert not base.exists() and not (HERE/label).exists()
value.update(schema='h1_roster4_header_probe_plan_136',at_utc=datetime.now(timezone.utc).isoformat(),
    predecessor_plan_sha256=sha256(prior.read_bytes()).hexdigest(),
    current_pre_seal_input_sha256=sha256((D/'public_phase_fix_input_135.json').read_bytes()).hexdigest(),
    question='Does current source preserve the complete zero-N0 public header lifecycle after creator-thread isolation and explicit opt-in bool validation?',
    command=[sys.executable,'-B',str(HERE/'run_unit_bounded_v17.py'),label,'120','1024','128','--',
        str(HERE/'run_unit_entry_v4.py'),'-s','-p','no:faulthandler','--basetemp',str(base),
        'tests/test_h1_roster4_live_header_development_v1.py'],
    files_sha256={str(p):sha256(p.read_bytes()).hexdigest() for p in sorted(paths,key=str)},
    independent_public_pre_seal_review_pending=False,
    scoped_pre_seal_findings_135_closed=True,current_source_header_verified=False,
    reason_for_new_diagnostic='131 passed earlier source. Subsequent per-thread memo map and development opt-in change require current-source lifecycle evidence; no cap extension or unchanged retry.')
value['optimization']['new_evidence'].append('134 current116 cases and independent scoped135 findings closure, including two legal creator threads and raw entry exception.')
out=D/'roster4_header_probe_plan_136.json'
with out.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(path=str(out),sha256=sha256(out.read_bytes()).hexdigest(),pins=len(paths))))
