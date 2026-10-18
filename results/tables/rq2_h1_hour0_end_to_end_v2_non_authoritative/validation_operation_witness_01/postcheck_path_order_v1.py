"""Verify completed lookup/raw trials; never start another measurement."""
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]


def read(root,name):return json.loads((root/name).read_bytes())


def current(pins):
    if any(sha256(Path(name).read_bytes()).hexdigest()!=h for name,h in pins.items()):
        raise ValueError('current source/input pin differs')


def terminal(label,seconds):
    root=HERE/label;out=root/'attempt_non_authoritative'
    outer=read(root,'terminal.json');inner=read(out,'terminal.json');request=read(root,'request.json')
    if (outer['exit_code']!=0 or inner['exit_code']!=0 or outer['stop_reason'] is not None
            or not outer['source_unchanged'] or not inner['source_unchanged']
            or request['seconds']!=seconds or request['sampled_rss_cap_bytes']!=512*1024**2
            or request['storage_cap_bytes']!=64*1024**2
            or outer['peak_observed_process_tree_rss']>request['sampled_rss_cap_bytes']
            or sum(p.stat().st_size for p in root.rglob('*') if p.is_file())>request['storage_cap_bytes']):
        raise ValueError('bounded trial terminal/budget differs')
    current(request['source_sha256'])
    return out,inner,read(out,'request.json')


micro={};raw={};evidence={}
for mode in ('c_first','d_first'):
    out,t,r=terminal('metadata_'+mode+'_01',30)
    current(r['source_sha256']);current(r['metadata_sha256'])
    if not t['metadata_unchanged'] or not t['stock_version_and_distribution_functions_unchanged']:
        raise ValueError('stock lookup or metadata bytes changed')
    receipt=read(out,'metadata_receipt.json')
    if (receipt['hits']!=4016 or receipt['misses']!=0 or receipt['discovery_windows']!=1
            or receipt['distribution_discovery_cached']):raise ValueError('lookup parse/discovery scope differs')
    micro[mode]=dict(seconds=t['lookup_seconds'],selected=t['selected'],source=r['source_sha256'],metadata=r['metadata_sha256'])
    out,t,r=terminal('path_order_'+mode+'_01',60)
    current(r['source_sha256']);current(r['saved_sha256'])
    if not t['saved_unchanged'] or t['saved_files']!=140 or t['real_native_calls']!=0 or t['static_identity_shortcut']:
        raise ValueError('real raw audit scope differs')
    raw[mode]=dict(out=out,terminal=t,request=r,origins=read(out,'module_origins.json'),
        module_pins=read(out,'module_origin_sha256.json'),
        lanes={lane:read(out,lane+'_'+mode+'.json') for lane in ('Rref','A')})
    for p in (out/'request.json',out/'terminal.json',out/'module_origins.json',out/'module_origin_sha256.json',
            out/('Rref_'+mode+'.json'),out/('A_'+mode+'.json')):
        evidence[p.relative_to(REPO).as_posix()]=sha256(p.read_bytes()).hexdigest()
if any(micro['c_first'][key]!=micro['d_first'][key] for key in ('selected','source','metadata')):
    raise ValueError('lookup selected versions/paths or source pins differ')
left,right=raw['c_first'],raw['d_first']
for key in ('source_sha256','saved_sha256','route_identity','fixed_byte_and_metadata_parse_package_sha256'):
    if left['request'][key]!=right['request'][key]:raise ValueError('raw input/source closure differs')
if left['origins']!=right['origins'] or left['module_pins']!=right['module_pins']:
    raise ValueError('full loaded-module sets/origin/file hashes differ')
for path,h in left['module_pins'].items():
    actual=left['origins'][path]
    if sha256(Path(actual).read_bytes()).hexdigest()!=h:raise ValueError('loaded module file changed after terminal')
paths=[d['terminal']['effective_sys_path'] for d in (left,right)]
if paths[0][:-2]!=paths[1][:-2] or paths[0][-2:]!=list(reversed(paths[1][-2:])):
    raise ValueError('path difference exceeds the declared last-two-root swap')
metadata=json.loads((HERE.parent/'validation_io_optimization_01/metadata_allowlist_v1.json').read_bytes())['files_sha256']
current(metadata)
rows=[]
for lane in ('Rref','A'):
    a,b=left['lanes'][lane],right['lanes'][lane]
    if any(a[key]!=b[key] for key in ('projection','bridge_implementation_identity','capture_mode')):
        raise ValueError('scientific projection/record/bridge bytes differ')
    rows.append(dict(lane=lane,c_first_seconds=a['audit_seconds'],d_first_seconds=b['audit_seconds'],
        fraction_saved=1-b['audit_seconds']/a['audit_seconds'],scientific_projection_equal=True))
value=dict(schema='h1_stock_metadata_path_order_comparison_development_v1',
    micro_seconds={mode:micro[mode]['seconds'] for mode in micro},
    micro_fraction_saved=1-micro['d_first']['seconds']/micro['c_first']['seconds'],
    micro_scope='single sequential warm lookup pair; locked version parsing and stdlib internal path caches remain',
    no_added_selected_distribution_cache=True,stock_version_distribution_callables_unchanged=True,
    measurements=rows,raw_two_lane_fraction_saved=1-sum(r['d_first_seconds'] for r in rows)/sum(r['c_first_seconds'] for r in rows),
    loaded_module_sets_origins_file_hashes_exact_equal=True,loaded_module_count=len(left['origins']),
    source_files=len(left['request']['source_sha256']),saved_files=140,metadata_files=len(metadata),
    source_saved_metadata_current_pins_equal=True,scientific_outputs_and_selector_records_exact_equal=True,
    decision='use D-before-C in the next versioned entry; do not infer full-chain speed',
    configured_entry_changed=False,full_chain_passed=False,whole_workflow_performance_review_complete=False,
    long_chain_launch_admitted=False,formal_result=False,resource_admission=False,native_execution_authorized=False,
    evidence_sha256=evidence)
with (HERE/'path_order_comparison_01.json').open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
print(json.dumps({k:v for k,v in value.items() if k!='evidence_sha256'}))
