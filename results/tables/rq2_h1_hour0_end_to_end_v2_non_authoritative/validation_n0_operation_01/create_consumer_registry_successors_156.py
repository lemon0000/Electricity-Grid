"""Create non-authoritative read-scope successors, preserving every old byte."""
import ast
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];EX=ROOT/'experiments'
mapping={
    'h1_bootstrap_integration_development_v5':'h1_bootstrap_integration_development_v6',
    'h1_owned_bootstrap_controller_development_v5':'h1_owned_bootstrap_controller_development_v6',
    'h1_historical_n0_verifier_development_v4':'h1_historical_n0_verifier_development_v5',
}
sources={name:(EX/(name+'.py')).read_bytes() for name in mapping}
for target in mapping.values():assert not (EX/(target+'.py')).exists()

def renamed(raw):
    value=raw.decode('utf-8').replace('\r\n','\n')
    for old,new in mapping.items():value=value.replace(old,new)
    return value.replace('Bootstrap5','Bootstrap6').replace('Owned5','Owned6')

bootstrap=renamed(sources['h1_bootstrap_integration_development_v5'])
bootstrap=bootstrap.replace('    return run\n', '''    records={}
    owner_type=BootstrapOwner

    def record(owner):
        _PHASE_RUNTIME()
        if type(owner) is not owner_type or (owner._pid,owner._thread)!=(os.getpid(),get_ident()):
            raise ValueError('original creator-thread Bootstrap6 read owner required')
        key=id(owner);saved=records.get(key)
        if saved is not None and saved[0]() is not owner:
            raise ValueError('original consumer read identity required')
        if saved is None:
            token=object()
            def expired(reference):
                value=records.get(key)
                if value is not None and value[0] is reference and value[1] is token:
                    del records[key]
            saved=(ref(owner,expired),token,[]);records[key]=saved
        return saved[2]

    def read(owner,mode):
        history=record(owner)
        if type(mode) is not str or mode not in ('constructor','inspect') or len(history)>=128:
            raise ValueError('bounded original consumer read route required')
        if owner.declaration.phase_archive is not None:_phase_current(owner)
        guard=owner._original_operation
        if owner._operation is not guard or owner._operation_nonce is not None or not guard.acquire(False):
            raise ValueError('unborrowed original consumer operation guard required')
        scope=None
        try:
            owner._operation_nonce=object()
            scope=open_scope(owner);error=None
            try:
                scope.__enter__()
                # Only these original source-defined bodies can execute here.
                # No caller-supplied callable or producer route is accepted.
                result=owner._replay() if mode=='constructor' else owner._inspect_read_body()
                _check_N0_contract(owner)
            except BaseException as failure:error=failure;poison(scope,failure);raise
            finally:close(scope,error)
            proof=receipt(scope)
            if (not proof['closed'] or proof['first_failure'] is not None
                    or (proof['root_receipts'] and not proof['complete'])
                    or (not proof['root_receipts'] and (proof['builds'] or proof['confirmed_builds']))):
                raise ValueError('complete original consumer registry read required')
            observation=historical.io.encode(dict(purpose='consumer_read',mode=mode,
                registry_execution=proof,metadata_read_complete=True,
                numerical_roots=len(proof['root_receipts']),producer_nonce_borrowed=False,
                proof_lifetime='one original synchronous public method',
                detached_consumer_credential=False,**FLAGS))
            history.append(observation)
            return result
        except BaseException:
            owner.poisoned=True
            raise
        finally:
            try:owner._operation_nonce=None
            finally:guard.release()

    def read_receipts(owner):
        history=record(owner)
        return dict(schema=SCHEMA,scope='consumer_registry_read_observations',
            reads=[json.loads(raw) for raw in history],successful_reads=len(history),
            cached_numerical_proofs_retained=False,detached_consumer_credential=False,**FLAGS)

    return run,read,read_receipts




''',1)
assert 'return run,read,read_receipts' in bootstrap
bootstrap=bootstrap.replace('            self._original_bootstrap=self._bootstrap\n            self._replay()',
    "            self._original_bootstrap=self._bootstrap\n            _run_registry_read(self,'constructor')",1)
tree=ast.parse(bootstrap)
cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='BootstrapOwner')
method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='inspect')
assert isinstance(method.body[1],ast.Try)
body=method.body[1].body
assert isinstance(body[0],ast.Assign) and isinstance(body[1],ast.Return)
replacement=ast.FunctionDef(name='_inspect_read_body',args=method.args,body=body,decorator_list=[])
ast.fix_missing_locations(replacement)
rendered='\n'.join('    '+line if line else '' for line in ast.unparse(replacement).splitlines())
rendered+='''

    def inspect(self):
        return _run_registry_read(self,'inspect')

    def registry_read_validation_receipt(self):
        """Detached observations; no producer or consumer execution credential."""
        return _read_registry_receipts(self)
'''
lines=bootstrap.splitlines(keepends=True)
bootstrap=''.join(lines[:method.lineno-1])+rendered+'\n'+''.join(lines[method.end_lineno:])
bootstrap=bootstrap.replace("'_continue_registered_development','reconcile_N0_terminal')",
    "'_continue_registered_development','reconcile_N0_terminal','_inspect_read_body','registry_read_validation_receipt')",1)
bootstrap=bootstrap.replace("'_global_N0_body','_run_registry_operation','_check_N0_contract'):",
    "'_global_N0_body','_run_registry_operation','_run_registry_read','_read_registry_receipts','_check_N0_contract'):",1)
bootstrap=bootstrap.replace('_run_registry_operation=_bind_registry_run()',
    '_run_registry_operation,_run_registry_read,_read_registry_receipts=_bind_registry_run()')
drafts={mapping[name]:bootstrap if name=='h1_bootstrap_integration_development_v5' else renamed(raw)
        for name,raw in sources.items()}
for name,source in drafts.items():
    path=EX/(name+'.py');compile(source,str(path),'exec')
    with path.open('x',encoding='utf-8',newline='\n') as stream:stream.write(source)
for name,raw in sources.items():assert (EX/(name+'.py')).read_bytes()==raw
value=dict(schema='h1_consumer_registry_successors_draft_origin_156',status='DRAFT_NONAUTHORITATIVE',
    source_sha256={name:sha256(raw).hexdigest() for name,raw in sources.items()},
    successor_sha256={name:sha256((EX/(name+'.py')).read_bytes()).hexdigest() for name in drafts},
    original_bytes_unchanged=True,read_scope_validation_pending=True,
    science_algorithm_changed=False,production_seal=False,official_review=False,
    formal_result=False,resource_admission=False,native_execution_authorized=False)
out=HERE/'whole_workflow_optimization_01_non_authoritative/consumer_registry_successors_draft_origin_156.json'
with out.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(value))
