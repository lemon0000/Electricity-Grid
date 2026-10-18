"""One fixed-order reader comparison over one completed owned synthetic archive."""
import ast
from hashlib import sha256
import json
import os
from pathlib import Path

import psutil

HERE=Path(__file__).resolve().parent;REPO=HERE.parents[3]
prior=json.loads((HERE/'fresh_owned_source_cost_plan_03.json').read_bytes())
completed=json.loads((HERE/'fresh_owned_source_cost_monitor_03/terminal.json').read_bytes())
assert completed['exit_code']==0 and completed['observed_owned_processes_absent']
assert completed['owned_lock_inventory_matches'] and len(completed['saved_locks_reacquired_and_released'])==10
for row in completed['observed_owned_processes']:
    try:assert psutil.Process(row['pid']).create_time()!=row['creation_time']
    except psutil.NoSuchProcess:pass
base=Path(prior['basetemp'])
reports=list(base.rglob('n0_source_cost_report.json'));assert len(reports)==1
report=reports[0];cost=json.loads(report.read_bytes())
assert cost['owner_closed_before_source'] and cost['synthetic_jobs']==1 and cost['real_native_calls']==0
saved={str(p):sha256(p.read_bytes()).hexdigest() for p in base.rglob('*') if p.is_file() and p.name!='execution.lock'}
saved[str(HERE/'fresh_owned_source_cost_monitor_03/terminal.json')]=sha256((HERE/'fresh_owned_source_cost_monitor_03/terminal.json').read_bytes()).hexdigest()
sources={name:sha256(Path(name).read_bytes()).hexdigest() for name in prior['source_sha256']}
code={Path(name):sha256(Path(name).read_bytes()).hexdigest() for name in prior['code_lease_sha256']}
members=(Path(__file__),HERE/'measure_fresh_source_reader_v1.py',HERE/'run_fresh_source_reader_bounded_v1.py',
    HERE/'bounded_stable_read_entry_v2.py',HERE/'bounded_stable_read_entry_v3.py',
    REPO/'tests/test_h1_bounded_stable_read_entry_development_v3.py',HERE/'run_unit_bounded_v7.py')
for path in members:
    raw=path.read_bytes();ast.parse(raw,filename=str(path));sources[str(path)]=sha256(raw).hexdigest()
for path in members[3:5]:code[path]=sources[str(path)]
for path,pin in code.items():assert {Path(k):v for k,v in sources.items()}[path]==pin
for name,pin in prior['old_chain_sha256'].items():assert sha256(Path(name).read_bytes()).hexdigest()==pin
for mode,reader in (('baseline','bounded_stable_read_entry_v2.py'),('candidate','bounded_stable_read_entry_v3.py')):
    value=dict(status='DRAFT_NONAUTHORITATIVE',mode=mode,attempts=1,reader_entry=reader,
        question='Does open/exit full self-validation reduce source time with original scientific I/O intact?',
        original_source_prepares=1,synthetic_jobs=0,real_native_calls=0,new_owners=0,new_Parents=0,
        source_sha256=sources,code_lease_sha256={str(p):pin for p,pin in code.items()},
        old_chain_sha256=prior['old_chain_sha256'],saved_sha256=saved,
        saved_source_cost_report=str(report),completed_input_owned_processes=completed['observed_owned_processes'],
        expected_decision_sha256=cost['N0_terminal']['decision_identity'],
        expected_audit_sha256=cost['source_audit_sha256'],
        expected_complete_projection_sha256=cost['source_complete_fields_sha256'],
        fixture_base=f'D:/h1_source_reader_01_{mode}_non_authoritative',
        path_roots=[str(REPO),str(base)],
        inner_output=str(HERE/f'fresh_source_reader_01_{mode}_non_authoritative'),
        outer_output=str(HERE/f'fresh_source_reader_monitor_01_{mode}'),
        limits=dict(wall_seconds=120,sampled_rss_bytes=768*1024**2,storage_bytes=128*1024**2),
        fixed_order=['baseline','candidate'],source_data_cached=False,numerical_results_cached=False,
        performance_threshold=dict(minimum_source_wall_reduction_fraction=.05,
            decision='adopt only if all fields, original scientific IO and cleanup pass and reduction reaches threshold',
            statistics='one fixed-order pair; not independent repeated statistics or complete-chain speedup'),
        scientific_contract='rawv1 stat/open/fstat/actual read/fstat/close/stat unchanged; only read size bounded',
        validation_contract='v3 self-dispatch checks open+terminal; extra guard chronology differs from v2',
        dag=['verify completed owned process identities absent and pinned archive/source bytes',
            'fresh isolated interpreter and same code/metadata/full-path coverage',
            'strict synthetic fixture import window and pure code identity bookends',
            'one original source over same completed N0; compare decision/audit/all source fields',
            'close/restore all leases, write-open code without writes, verify saved/source/old36 bytes and owned PID absence'],
        stop_conditions=['120s hard wall, sampled RSS768MiB,128MiB new artifacts',
            'stop first source/fields/process/cleanup error; no retry with unchanged package',
            'if reduction below5percent stop branch; do not route complete chain through this reader'],
        formal_result=False,resource_admission=False,whole_workflow_performance_review_complete=False,
        full_hour0_chain_passed=False,native_execution_authorized=False)
    # The source decision identity hashes canonical decision bytes.
    projection=json.loads((report.parent/'source_complete_fields.json').read_bytes())
    assert sha256(json.dumps(projection,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()==value['expected_complete_projection_sha256']
    for key in ('fixture_base','inner_output','outer_output'):
        if os.path.lexists(value[key]):raise ValueError('unused comparison roots required')
    path=HERE/f'fresh_source_reader_plan_01_{mode}.json'
    with path.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
    print(json.dumps(dict(mode=mode,plan_sha256=sha256(path.read_bytes()).hexdigest(),source_files=len(sources),saved_files=len(saved))))
