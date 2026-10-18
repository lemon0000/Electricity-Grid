"""Build the next draft with a bounded per-root registry validation lifetime."""
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;REPO=HERE.parents[3]
def change(text,old,new):
    if text.count(old)!=1:raise ValueError('nonunique source anchor: '+old)
    return text.replace(old,new)
paths=[REPO/'experiments'/name for name in ('h1_historical_n0_verifier_development_v2.py',
    'h1_bootstrap_integration_development_v2.py','h1_owned_bootstrap_controller_development_v3.py')]
before={str(p):sha256(p.read_bytes()).hexdigest() for p in paths}
v=paths[0].read_text(encoding='utf-8').replace('h1_historical_n0_verifier_development_v2','h1_historical_n0_verifier_development_v3')
v=v.replace('h1_bootstrap_integration_development_v3','h1_bootstrap_integration_development_v4')
v=change(v,"BUILD_SITES=('explicit_primary','explicit_after_local','registry_before','registry_after')",
    "MAX_REGISTRY_ROOTS=3\nMAX_REGISTRY_PREPARES=64")
v=change(v,'completed_hours=1,reuse_numerical_proof=True,_bootstrap_owner=None,diagnostic_only=False):',
    'completed_hours=1,reuse_numerical_proof=True,_bootstrap_owner=None,diagnostic_only=False,\n            _registry_scope=None,maximum_prepares=MAX_REGISTRY_PREPARES):')
v=change(v,'        self._bootstrap_owner=_bootstrap_owner','''        if type(maximum_prepares) is not int or not 1<=maximum_prepares<=MAX_REGISTRY_PREPARES:
            raise ValueError('bounded explicit registry prepare count required')
        self._registry_scope=_registry_scope
        self._bootstrap_owner=_bootstrap_owner''')
v=change(v,"                    or str(root)!=owner.roots['controller'] or arm_id!=owner._slot['slot_id']):",
    "                    or type(_registry_scope) is not RegistryValidationScope):")
v=change(v,'            self._bootstrap_binding=(owner,owner._operation,owner._operation_nonce,owner.declaration)',
    '''            _registry_declare_operation(_registry_scope,owner,root,arm_id,expected_binding_sha256,expected_terminal_sha256)
            self._bootstrap_binding=(owner,owner._operation,owner._operation_nonce,owner.declaration,_registry_scope)''')
v=change(v,'        self._max_prepares=4 if reuse_numerical_proof else 1','        self._max_prepares=maximum_prepares if reuse_numerical_proof else 1')
v=change(v,'        owner,guard,nonce,declaration=binding','        owner,guard,nonce,declaration,scope=binding')
v=change(v,"                or owner.declaration is not declaration or owner.roots['controller']!=self._exact_root\n                or owner._slot['slot_id']!=self._fixed_declaration[1]):",
    "                or owner.declaration is not declaration or self._registry_scope is not scope):")
v=change(v,"            raise ValueError('bootstrap registration guard or nonce changed')",
    "            raise ValueError('bootstrap registration guard or nonce changed')\n        _registry_check_operation(scope,self)")
v=change(v,"                or self._attempts>=4 or site!=BUILD_SITES[self._attempts]",
    "                or self._attempts>=self._max_prepares or site!='build_'+str(self._attempts+1).zfill(3)")
v=change(v,'            build_sites=list(BUILD_SITES),','            maximum_registry_roots=MAX_REGISTRY_ROOTS,')
v=v.replace('self._attempts==self._max_prepares and self._failure is None',
    '0<self._attempts<=self._max_prepares and self._failure is None')
v=change(v,'len(self._confirmed_builds)==4','len(self._confirmed_builds)==self._attempts')
v=change(v,'def prepare(root,*,expected_binding_sha256,expected_terminal_sha256,completed_hours,n0_operation=None):',
    '''def prepare(root,*,expected_binding_sha256,expected_terminal_sha256,completed_hours,n0_operation=None,registry_scope=None):
    if registry_scope is not None:
        if n0_operation is not None or type(registry_scope) is not RegistryValidationScope:
            raise TypeError('one exact registry validation route required')
        return registry_scope.prepare(root,expected_binding_sha256=expected_binding_sha256,
            expected_terminal_sha256=expected_terminal_sha256,completed_hours=completed_hours)''')
v=change(v,"'SCHEMA','VERIFIER_SCHEMA','BUILD_SITES'","'SCHEMA','VERIFIER_SCHEMA','MAX_REGISTRY_ROOTS','MAX_REGISTRY_PREPARES'")
v=change(v,'            ChildReference,prior_witness._HourScope):','            ChildReference,prior_witness._HourScope,RegistryValidationScope):')
scope=(HERE/'registry_scope_body_v1.py.txt').read_text(encoding='utf-8')
v=change(v,'def _install_runtime_checks():',scope+'\n\ndef _install_runtime_checks():')

b=paths[1].read_text(encoding='utf-8').replace('h1_bootstrap_integration_development_v2','h1_bootstrap_integration_development_v4')
b=b.replace('h1_owned_bootstrap_controller_development_v2','h1_owned_bootstrap_controller_development_v4')
b=b.replace('h1_historical_n0_verifier_development_v1','h1_historical_n0_verifier_development_v3')
b=change(b,'import stat','import stat\nimport types')
b=change(b,'        full_numerical_hour_replays=4,fresh_byte_context_revalidations=4,\n        recomputed_on_revalidation=False,',
    '''        historical_validation_contract=historical_verifier.VERIFIER_SCHEMA,
        legacy_compatibility_execution_metadata=dict(full_numerical_hour_replays=4,
            fresh_byte_context_revalidations=4,recomputed_on_revalidation=False,
            scope='predecessor_scientific_projection_only'),''')
b=change(b,'def verify(root,*,expected_binding_sha256,expected_terminal_sha256,completed_hours):',
    'def verify(root,*,expected_binding_sha256,expected_terminal_sha256,completed_hours,registry_scope=None):')
b=change(b,'expected_terminal_sha256=expected_terminal_sha256,completed_hours=completed_hours)\n        if (type(value)',
    'expected_terminal_sha256=expected_terminal_sha256,completed_hours=completed_hours,registry_scope=registry_scope)\n        if (type(value)')
b=change(b,'                or value.full_numerical_hour_replays!=4 or value.fresh_byte_context_revalidations!=4\n                or value.recomputed_on_revalidation is not False):',
    '''                or (value.full_numerical_hour_replays,value.fresh_byte_context_revalidations) not in ((4,4),(0,8))
                or type(value.execution_receipt) is not bytes
                or json.loads(value.execution_receipt)['predecessor_audit_sha256']!=sha256(value.audit_payload).hexdigest()):''')
start=b.index('def _guard_N0_route(operation):');end=b.index('\n\ndef _journal_header',start)
b=b[:start]+'''def _snapshot(fn):
    result=types.FunctionType(fn.__code__,fn.__globals__,fn.__name__,fn.__defaults__,fn.__closure__)
    result.__kwdefaults__=dict(fn.__kwdefaults__ or {});return result


def _guard_N0_route(operation):
    route=_prepare_N0;current=_snapshot(historical_verifier.registry_validation_scope)
    poison=_snapshot(historical_verifier._poison_registry_scope)
    def guarded(*args,**kwargs):
        owner=args[0];scope=current(owner)
        try:
            _check_N0_contract(owner)
            if _prepare_N0 is not route or 'registry_scope' in kwargs:raise ValueError('N0 verifier route changed')
            site=kwargs.pop('_n0_site','N0_build')
            if scope is not None:
                claim=args[2];scope.begin_build(owner,claim['proposal']['roots']['controller'],claim['slot_id'],site)
            value=operation(*args,**kwargs,registry_scope=scope)
            _check_N0_contract(owner)
            if scope is not None:scope.confirm_build(value)
            return value
        except BaseException as error:
            if scope is not None:poison(scope,error)
            raise
    return guarded


def _bind_registry_run():
    scope_type=historical_verifier.RegistryValidationScope
    close=_snapshot(historical_verifier._close_registry_scope)
    poison=_snapshot(historical_verifier._poison_registry_scope)
    receipt=_snapshot(historical_verifier._registry_scope_receipt)
    def run(owner,execute):
        scope=scope_type(owner);error=None
        try:
            scope.__enter__();result=execute();_check_N0_contract(owner)
        except BaseException as failure:error=failure;poison(scope,failure);raise
        finally:close(scope,error)
        try:
            proof=receipt(scope)
            if type(result) is not dict or result.get('state')!='pending_post_N' or not proof['complete']:
                raise ValueError('complete bootstrap registry execution receipt required')
            result['N0_validation_execution_receipt']=historical.io.encode(proof)
            _check_N0_contract(owner);return result
        except BaseException as failure:poison(scope,failure);raise
    return run


_run_registry_operation=_bind_registry_run()
'''+b[end:]
b=change(b,'    def _build_N0_terminal(self,claim_head,claim,release_head,ready_row,local_release_head,observed,check_binding):',
    '    def _build_N0_terminal(self,claim_head,claim,release_head,ready_row,local_release_head,observed,check_binding,*,registry_scope=None):')
b=change(b,'            expected_terminal_sha256=terminal_pin,completed_hours=1)',
    '            expected_terminal_sha256=terminal_pin,completed_hours=1,registry_scope=registry_scope)')
b=change(b,'                        observed,self._check)',"                        observed,self._check,_n0_site='registry')")
start=b.index('    def bootstrap(self):');try_start=b.index('        try:\n',start);catch=b.index('        except BaseException:\n',try_start)
body=b[try_start+len('        try:\n'):catch]
wrapped='        try:\n            def execute():\n'+''.join('    '+line if line.strip() else line for line in body.splitlines(keepends=True))
wrapped+='            return _run_registry_operation(self,execute)\n'
b=b[:try_start]+wrapped+b[catch:]
contract=(REPO/'experiments/h1_bootstrap_integration_development_v3.py').read_text(encoding='utf-8')
contract=contract[contract.index('def _install_N0_contract():'):]
contract=contract.replace("'_run_N0_operation'","'_run_registry_operation'")
contract=contract.replace("'N0ValidationOperation','VerifiedHistoricalEnvelope','prepare','BUILD_SITES',\n            '_close_operation','_poison_operation'",
    "'N0ValidationOperation','VerifiedHistoricalEnvelope','prepare','RegistryValidationScope',\n            'registry_validation_scope','_close_registry_scope','_poison_registry_scope','_registry_scope_receipt'")
b=change(b,'    def _check(self):\n        if (self.closed or self.poisoned',
    '    def _check(self):\n        _check_N0_contract(self)\n        if (self.closed or self.poisoned')
b+='\n\n'+contract
owned=paths[2].read_text(encoding='utf-8').replace('h1_bootstrap_integration_development_v3','h1_bootstrap_integration_development_v4')
outputs={'h1_historical_n0_verifier_development_v3.py':v,'h1_bootstrap_integration_development_v4.py':b,
    'h1_owned_bootstrap_controller_development_v4.py':owned}
for name,text in outputs.items():
    target=REPO/'experiments'/name;assert not target.exists();compile(text,str(target),'exec')
for name,text in outputs.items():
    with (REPO/'experiments'/name).open('x',encoding='utf-8',newline='\n') as stream:stream.write(text)
assert all(sha256(Path(p).read_bytes()).hexdigest()==h for p,h in before.items())
value=dict(status='DRAFT_NONAUTHORITATIVE',predecessors_sha256=before,
    successors_sha256={str(REPO/'experiments'/n):sha256((REPO/'experiments'/n).read_bytes()).hexdigest() for n in outputs},
    max_roots=3,max_prepares_per_root=64,scope='one bootstrap lock/nonce; all original root observations retained',
    formal_execution_ready=False,formal_result=False,resource_admission=False,native_execution_authorized=False)
with (HERE/'registry_draft_sources_01.json').open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
print(json.dumps(dict(status=value['status'],sources=list(outputs))),flush=True)
