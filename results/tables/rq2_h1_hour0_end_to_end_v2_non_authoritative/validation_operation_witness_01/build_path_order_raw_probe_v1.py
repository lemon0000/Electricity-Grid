"""Mechanical successor of the checked raw-audit entry, only for path order."""
from hashlib import sha256
from pathlib import Path
import ast
import json

HERE=Path(__file__).resolve().parent
source=HERE.parent/'validation_selector_incremental_01/measure_configured_raw_audits_v2.py'
raw=source.read_bytes()
if sha256(raw).hexdigest()!='0fa4005a29ca457baffaa2c92b3f2a92bd0e721b3eafa2c9a2f3f0f6b0cfce0d':
    raise ValueError('raw-audit predecessor bytes differ')
text=raw.decode('utf-8')
edits=[
    ("if mode not in ('standard', 'configured') or bool(sys.flags.isolated) != (mode == 'configured'):",
        "if mode not in ('c_first', 'd_first') or not sys.flags.isolated:"),
    ("out = HERE / label", "out = HERE / label / 'attempt_non_authoritative'"),
    ("if mode == 'configured':", "if mode in ('c_first', 'd_first'):"),
    ("sys.path.insert(index,str(support))", "sys.path.insert(index+(mode=='d_first'),str(support))"),
    ("exact_path_deduplication=(mode=='configured')", "exact_path_deduplication=True"),
    ("metadata_discovery_fresh=True, both_lanes_match_saved=True", "stock_distribution_discovery_fresh=True, selected_locked_metadata_version_value_cached=True, metadata_parse_window='one invocation including both lane audits', both_lanes_match_saved=True"),
]
for old,new in edits:
    expected=2 if old=="if mode == 'configured':" else 1
    if text.count(old)!=expected:raise ValueError('mechanical predecessor anchor count differs: '+old)
    text=text.replace(old,new)
target=HERE/'measure_path_order_raw_audits_v3.py'
ast.parse(text,filename=str(target))
with target.open('x',encoding='utf-8') as stream:stream.write(text)
plan=dict(schema='h1_path_order_saved_raw_probe_plan_development_v1',
    predecessor_source_sha256=sha256(raw).hexdigest(),candidate_source_sha256=sha256(target.read_bytes()).hexdigest(),
    scope='original final saved Rref and Actual raw audits, unchanged mathematical bodies',
    modes=['c_first','d_first'],attempts_per_mode=1,wall_seconds_per_mode=60,sampled_rss_mib=512,new_artifact_mib=64,
    saved_input='D:/h1_incremental_helper_05_non_authoritative/selector_raw_v2_non_authoritative0',
    question='Does the no-cache path-order saving survive real raw audits with identical scientific bytes and module origins?',
    admission='fixed source/package/test/saved beforepins, empty pycache, original audit functions, solver-forbidden',
    acceptance=['both mode terminals exit0','all common module origins/file SHAs identical','science/records/bridge identity exact',
        'saved and common source closures unchanged','budgets observed; no unmodified repeat'],
    whole_workflow_performance_review_complete=False,long_chain_launch_admitted=False,
    full_chain_passed=False,formal_result=False,resource_admission=False,native_execution_authorized=False)
with (HERE/'path_order_raw_plan_01.json').open('x',encoding='utf-8') as stream:json.dump(plan,stream,indent=2)
print(json.dumps(dict(source_sha256=plan['candidate_source_sha256'],mechanical_replacements=len(edits))))
