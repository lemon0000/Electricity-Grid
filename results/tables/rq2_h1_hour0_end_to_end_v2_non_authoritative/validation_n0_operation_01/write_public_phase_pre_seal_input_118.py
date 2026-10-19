"""Current successor to117; adds definition-bound Roster4 and no gate authority."""
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
D=HERE/'whole_workflow_optimization_01_non_authoritative'
previous=D/'public_phase_pre_seal_input_117.json';value=json.loads(previous.read_text())
paths=[p for p in value['files_sha256'] if '/monitor_public_phase_units_117/' not in p]
for name in ('request.json','started.json','terminal.json','stdout.log'):
    paths.append((HERE/'public_phase_roster_route_units_118'/name).relative_to(ROOT).as_posix())
value.update(schema='h1_public_phase_pre_seal_input_118',predecessor_input_sha256=sha256(previous.read_bytes()).hexdigest(),
    files_sha256={p:sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
    terminal=json.loads((HERE/'public_phase_roster_route_units_118/terminal.json').read_text()),
    unit_bodies='20 passed in 6.52s',
    self_identified_route_fix=dict(problem='Roster4 had no own callable/class/module seal although its methods run inside held callback-free phase scopes.',
        change='New runtime2 seal covers own helpers/class methods, module metadata and original Bootstrap phase routes; instance method shadows refused.',
        negatives='view/replay/class helpers/Bootstrap private route/source descriptor/module registry drift refused before any phase handle'),
    tested_scope='Original coordinator AST + tiny actual-handle protocol and exact namespace fields. Six additional Roster route negatives and seven strict monitor tests. No genuine header or N0 executed.')
assert value['terminal']['exit_code']==0 and value['terminal']['source_unchanged'] and not value['terminal']['cleanup_errors']
out=D/'public_phase_pre_seal_input_118.json'
with out.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(path=str(out),sha256=sha256(out.read_bytes()).hexdigest())))
