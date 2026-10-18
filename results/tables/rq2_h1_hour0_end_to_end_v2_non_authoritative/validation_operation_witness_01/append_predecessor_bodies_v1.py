"""Root-only draft construction from exact predecessor function bodies."""
import ast
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
target=ROOT/'experiments/h1_operation_historical_witness_development_v1.py'
old_witness=(ROOT/'experiments/h1_historical_hour_witness_development_v1.py').read_text(encoding='utf-8')
old_verifier=(ROOT/'experiments/h1_historical_n0_verifier_development_v1.py').read_text(encoding='utf-8')


def function(source,name):
    node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name==name)
    return ast.get_source_segment(source,node)


def replace_once(source,left,right):
    if source.count(left)!=1:raise ValueError('nonunique mechanical predecessor edit: '+left)
    return source.replace(left,right)


tree=ast.parse(old_witness)
child=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='ChildReference')
inspect=next(n for n in child.body if isinstance(n,ast.FunctionDef) and n.name=='inspect')
body='\n'.join('    '+line for line in ast.get_source_segment(old_witness,inspect).splitlines())
# get_source_segment preserves the inner indentation after its first line.
import textwrap
lines=ast.get_source_segment(old_witness,inspect).splitlines()
body='    '+lines[0]+'\n'+textwrap.indent(textwrap.dedent('\n'.join(lines[1:])),'        ')
pieces=['witness=sys.modules[__name__]',
    'class ChildReference(prior_witness.ChildReference):\n'+body,
    function(old_witness,'after'),function(old_witness,'outcome')]
prefix=function(old_verifier,'_replay_prefix')
prefix=replace_once(prefix,'completed_hours,_observed=None):',
    'completed_hours,_observed=None,_operation,_ticket,_prefix_index):')
prefix=replace_once(prefix,'scope=witness._HourScope(root,leases,caller=sys.modules[__name__])',
    'scope=_OperationHourScope(root,leases,caller=sys.modules[__name__],_operation=_operation,_ticket=_ticket,_prefix_index=_prefix_index)')
prefix=replace_once(prefix,"if (scope.full_calls,scope.revalidation_calls)!=(2,2): raise ValueError('complete prefix verification count differs')",
    '_operation._record_prefix(_ticket,_prefix_index,scope)')
pieces.append(prefix)
projection=function(old_verifier,'_projection')
projection=replace_once(projection,'expected_terminal_sha256,completed_hours):',
    'expected_terminal_sha256,completed_hours,_operation,_ticket):')
projection=replace_once(projection,'first,captured,header=_replay_prefix(root,**args,_observed=observed)',
    'first,captured,header=_replay_prefix(root,**args,_observed=observed,_operation=_operation,_ticket=_ticket,_prefix_index=0)')
projection=replace_once(projection,'second,fresh,fresh_header=_replay_prefix(root,**args,_observed=observed)',
    'second,fresh,fresh_header=_replay_prefix(root,**args,_observed=observed,_operation=_operation,_ticket=_ticket,_prefix_index=1)')
pieces.append(projection)
raw=target.read_text(encoding='utf-8')
if '\ndef _replay_prefix(' in raw:raise ValueError('draft body already constructed')
raw+='\n\n'+'\n\n\n'.join(pieces)+'\n'
ast.parse(raw)
target.write_text(raw,encoding='utf-8',newline='\n')
print(str(target))
