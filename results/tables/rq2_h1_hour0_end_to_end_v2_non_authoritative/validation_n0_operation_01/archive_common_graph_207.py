"""Check the mechanical typed graph and preserve its bounded import regression."""
import ast
from hashlib import sha256
import json
from pathlib import Path
import re

H=Path(__file__).resolve().parent;R=H.parents[3];D=H/'whole_workflow_optimization_01_non_authoritative'
origin=D/'common_typed_graph_origin_205.json';plan=json.loads(origin.read_bytes());checked=[]
for row in plan['files']:
    current=R/row['target'];assert sha256(current.read_bytes()).hexdigest()==row['after_sha256']
    old=R/row['source']
    if row['original_path_modified']:old=D/'roster_scoped_source_202_non_authoritative'/old.name
    assert sha256(old.read_bytes()).hexdigest()==row['before_sha256']
    changes=row['namespace_schema_substitutions']
    pattern=re.compile('|'.join(re.escape(key) for key in sorted(changes,key=len,reverse=True)))
    expected=ast.parse(pattern.sub(lambda match:changes[match[0]],old.read_text(encoding='utf-8')))
    actual=ast.parse(current.read_bytes())
    if row['additional_literal_route_pin_refresh']:
        assignment='ROUTES' if 'genesis_validation_routes' in current.name else '_PINNED_ROUTES'
        a=next(node for node in actual.body if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id==assignment for t in node.targets))
        b=next(node for node in expected.body if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id==assignment for t in node.targets))
        pins=ast.literal_eval(a.value)
        for item in pins:
            name=item[0].split('.')[-1];pin=item[-1]
            assert sha256((R/'experiments'/(name+'.py')).read_bytes()).hexdigest()==pin
        b.value=a.value
    assert ast.dump(expected,include_attributes=False)==ast.dump(actual,include_attributes=False)
    compile(current.read_bytes(),str(current),'exec',dont_inherit=True)
    checked.append(dict(path=row['target'],sha256=row['after_sha256'],normalized_AST_equal=True))
label=H/'common_typed_graph_units_206';terminal=json.loads((label/'terminal.json').read_bytes())
assert terminal['exit_code']==0 and terminal['source_unchanged'] and terminal['observed_owned_processes_absent']
assert not terminal['cleanup_errors'] and not terminal['storage_read_errors']
closed_path=Path('D:/h1_common_typed_graph_206_non_authoritative/unit_code_read_lease_closed.json')
closed=json.loads(closed_path.read_bytes());assert closed['all_code_handles_closed'] and closed['original_read_alias_restored']
stdout=(label/'stdout.log').read_text(encoding='utf-8');match=re.search(r'(\d+) passed in ([\d.]+)s',stdout);assert match and int(match[1])==1
archive=D/'common_graph_207_preserved_non_authoritative';archive.mkdir(exist_ok=False);saved=[]
for source in [label/name for name in ('request.json','started.json','terminal.json','stdout.log')]+[closed_path]:
    raw=source.read_bytes();target=archive/source.name
    with target.open('xb') as stream:stream.write(raw)
    assert target.read_bytes()==raw
    saved.append(dict(source=str(source),saved=str(target.relative_to(R)),sha256=sha256(raw).hexdigest()))
v=dict(schema='h1_common_typed_graph_evidence_207',status='VERIFIED_MECHANICAL_DRAFT_GRAPH',
    origin_sha256=sha256(origin.read_bytes()).hexdigest(),sources=checked,
    terminal=terminal,pytest_cases=1,pytest_seconds=float(match[2]),archive_files=saved,
    checks=['20 complete ASTs equal under explicit namespace/schema substitutions and refreshed literal route pins',
        'all predecessor source bytes unchanged; two previously provisional drafts bound to202 before bytes',
        'real canonical successor graph imports with exact shared type identities',
        'unbound Common rejects canonical Genesis loader and rolls back all three new route aliases'],
    common_authorized=False,positive_loader_activation_verified=False,numerical_Roster_verified=False,
    new_N0_Jobs=0,real_native_calls=0,production_seal=False,official_review=False,
    full_optimized_workflow_accepted=False,whole_workflow_performance_review_complete=False,
    formal_execution_ready=False,formal_run_authority=False,formal_result=False,resource_admission=False)
out=D/'common_typed_graph_evidence_207.json'
with out.open('x',encoding='utf-8',newline='\n') as stream:json.dump(v,stream,indent=2);stream.write('\n')
print(json.dumps(dict(path=str(out),sha256=sha256(out.read_bytes()).hexdigest(),files=len(checked),pytest_seconds=float(match[2]),outer_seconds=terminal['elapsed_seconds'])))
