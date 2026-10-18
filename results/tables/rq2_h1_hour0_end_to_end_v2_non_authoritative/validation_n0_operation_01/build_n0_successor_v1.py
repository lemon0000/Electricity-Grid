"""Mechanical N0 successor routing plus explicit four-build proof lifetime."""
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
E=HERE.parent


def change(text,old,new):
    if text.count(old)!=1:raise ValueError('non-unique source anchor: '+old)
    return text.replace(old,new)


def source(name):return (REPO/'experiments'/name).read_text(encoding='utf-8')


original={name:source(name) for name in ('h1_operation_historical_witness_development_v1.py',
    'h1_bootstrap_integration_development_v2.py','h1_owned_bootstrap_controller_development_v2.py')}
before={str(REPO/'experiments'/name):sha256((REPO/'experiments'/name).read_bytes()).hexdigest() for name in original}
old_pins=json.loads((E/'chain_07/request.json').read_bytes())['before']
assert all(sha256(Path(name).read_bytes()).hexdigest()==pin for name,pin in old_pins.items())

v=original['h1_operation_historical_witness_development_v1.py']
v=v.replace('h1_operation_historical_witness_development_v1','h1_historical_n0_verifier_development_v2')
v=v.replace('OperationHistoricalWitness','N0ValidationOperation').replace('DiagnosticVerifiedHistoricalEnvelope','VerifiedHistoricalEnvelope')
v=change(v,'"""Single-arm, two-prepare diagnostic proof reuse; no live Handoff credential.\n\nThe unchanged predecessor context is observed before and after every old site.\nThis development prototype must not be installed under a predecessor module name.\n"""',
    '"""Four-build N0 historical proof reuse with explicit bootstrap registration scope.\n\nScientific projections remain in the predecessor schema. Execution receipts name\nthis verifier and every actual observation; no formal run authority is issued.\n"""')
v=change(v,"_ENVELOPE_TOKEN=object()","_ENVELOPE_TOKEN=object()\nBUILD_SITES=('explicit_primary','explicit_after_local','registry_before','registry_after')")
v=change(v,"            completed_hours=1,reuse_numerical_proof=True):", "            completed_hours=1,reuse_numerical_proof=True,_bootstrap_owner=None,diagnostic_only=False):")
v=change(v,"        self._exact_root=str(root)",'''        if type(diagnostic_only) is not bool:raise TypeError('explicit diagnostic scope required')
        self._bootstrap_owner=_bootstrap_owner
        self._bootstrap_binding=None
        if _bootstrap_owner is not None:
            from experiments import h1_bootstrap_integration_development_v3 as bootstrap
            owner=_bootstrap_owner
            if (diagnostic_only or not reuse_numerical_proof or type(owner) is not bootstrap.BootstrapOwner
                    or owner.closed or owner.poisoned or owner._operation is not owner._original_operation
                    or not owner._operation.locked() or owner._operation_nonce is None
                    or str(root)!=owner.roots['controller'] or arm_id!=owner._slot['slot_id']):
                raise ValueError('live exact bootstrap N0 registration owner required')
            self._bootstrap_binding=(owner,owner._operation,owner._operation_nonce,owner.declaration)
        elif reuse_numerical_proof and not diagnostic_only:
            raise ValueError('unbound proof reuse requires explicit diagnostic-only scope')
        self._max_prepares=4 if reuse_numerical_proof else 1
        self._diagnostic_only=diagnostic_only
        self._exact_root=str(root)''')
v=change(v,'completed_hours,reuse_numerical_proof)','completed_hours,reuse_numerical_proof,self._max_prepares,diagnostic_only)')
v=change(v,"        self._context_function=_CONTEXT;self._context_code=_CONTEXT.__code__",'''        self._context_function=_CONTEXT;self._context_code=_CONTEXT.__code__
        self._candidate_proof=None;self._build_ticket=None;self._awaiting_build=None
        self._confirmed_builds=[];self._body_bytes=None''')
v=change(v,"        _runtime_check()\n        if (self._failure", "        _runtime_check()\n        self._check_bootstrap_binding()\n        if (self._failure")
v=change(v,"                or self._declaration!=self._fixed_declaration",'''                or self._max_prepares!=self._fixed_declaration[6]
                or self._diagnostic_only!=self._fixed_declaration[7]
                or self._declaration!=self._fixed_declaration''')
v=change(v,"    def _poison(self,error):",'''    def _check_bootstrap_binding(self):
        binding=self._bootstrap_binding
        if binding is None:
            if self._bootstrap_owner is not None:raise ValueError('bootstrap owner binding changed')
            return
        owner,guard,nonce,declaration=binding
        if (self._bootstrap_owner is not owner or owner.closed or owner.poisoned
                or owner._operation is not guard or owner._original_operation is not guard
                or not guard.locked() or owner._operation_nonce is not nonce or nonce is None
                or owner.declaration is not declaration or owner.roots['controller']!=self._exact_root
                or owner._slot['slot_id']!=self._fixed_declaration[1]):
            raise ValueError('bootstrap registration guard or nonce changed')

    def begin_build(self,owner,site):
        self._check()
        if (not self._fixed_declaration[5] or self._state!='active' or self._build_ticket is not None
                or self._awaiting_build is not None or len(self._confirmed_builds)!=self._attempts
                or self._attempts>=4 or site!=BUILD_SITES[self._attempts]
                or owner is not self._bootstrap_owner):
            raise ValueError('exact N0 build ordinal and owner required')
        token=object();self._build_ticket=(token,site,self._attempts+1)
        return token

    def confirm_build(self,ticket,body):
        self._check()
        envelope=self._awaiting_build
        if (self._build_ticket is None or ticket is not self._build_ticket[0]
                or type(envelope) is not VerifiedHistoricalEnvelope or type(body) is not dict
                or self._build_ticket[2]!=self._attempts or len(self._confirmed_builds)+1!=self._attempts):
            raise ValueError('complete N0 build required before confirmation')
        raw=io.encode(body);row=self._rows[-1]
        if (body.get('controller_root')!=self._exact_root
                or body.get('historical_verifier_schema')!=VERIFIER_SCHEMA
                or body.get('historical_validation_contract')!=VERIFIER_SCHEMA
                or body.get('historical_verifier_identity')!=envelope.verifier_identity
                or body.get('audit_payload_sha256')!=io.digest(envelope.audit_payload)
                or io.digest(envelope.execution_receipt)!=row['execution_receipt_sha256']
                or envelope.envelope_identity!=row['envelope_identity']
                or (self._body_bytes is not None and raw!=self._body_bytes)):
            raise ValueError('N0 build body/science/execution binding differs')
        if self._attempts==1:
            if self._proof is not None or self._candidate_proof is None:
                raise ValueError('first complete build proof required')
            for index,proof in enumerate(self._candidate_proof):
                context,frozen,value,key,nonce,ordinal,declaration=proof
                if (_freeze(value)!=frozen or _context_key(context)!=key or nonce is not self._nonce
                        or ordinal!=index or declaration!=self._fixed_declaration):
                    raise ValueError('candidate numerical proof changed before build confirmation')
            self._proof=self._candidate_proof;self._candidate_proof=None
            self._body_bytes=raw
        elif self._proof is None:raise ValueError('confirmed first build proof required')
        previous=self._confirmed_builds[-1]['receipt_sha256'] if self._confirmed_builds else None
        record=dict(site=self._build_ticket[1],prepare=self._attempts,body_sha256=io.digest(raw),
            execution_receipt_sha256=row['execution_receipt_sha256'],envelope_identity=envelope.envelope_identity,
            proof_basis_identity=row['proof_basis_identity'],previous_receipt_sha256=previous)
        record['receipt_sha256']=io.digest(io.encode(record))
        self._confirmed_builds.append(record)
        self._build_ticket=self._awaiting_build=None
        return record['receipt_sha256']

    def _poison(self,error):''')
v=change(v,"        self._proof=None;self._pending.clear();self._state='failed'", "        self._proof=self._candidate_proof=None;self._build_ticket=self._awaiting_build=None\n        self._pending.clear();self._state='failed'")
v=change(v,"        if self._state!='active' or self._attempts>=2:raise ValueError('two nonreentrant diagnostic prepares required')",'''        if self._state!='active' or self._attempts>=self._max_prepares:
            raise ValueError('bounded nonreentrant N0 prepares required')
        if self._fixed_declaration[5] and (self._build_ticket is None or self._awaiting_build is not None):
            raise ValueError('confirmed previous build and current build ticket required')''')
v=v.replace('self._declaration[-1]','self._declaration[5]').replace('self._fixed_declaration[-1]','self._fixed_declaration[5]')
v=change(v,'root,arm,binding_pin,terminal_pin,hours,reuse=self._fixed_declaration','root,arm,binding_pin,terminal_pin,hours,reuse,maximum,diagnostic=self._fixed_declaration')
v=change(v,'reuse and ordinal==2','reuse and ordinal>1')
v=change(v,'[own,self._exact_root,arm,binding_pin,terminal_pin,reuse]','[own,self._exact_root,arm,binding_pin,terminal_pin,reuse,maximum,diagnostic]')
v=change(v,"            session_identity=self._public_session,prepare=ordinal,mode=", "            bootstrap_operation_bound=self._bootstrap_binding is not None,diagnostic_only=diagnostic,\n            maximum_prepares=maximum,build_site=None if self._build_ticket is None else self._build_ticket[1],\n            session_identity=self._public_session,prepare=ordinal,mode=")
v=change(v,"            self._proof=tuple((_copy_context", "            self._candidate_proof=tuple((_copy_context")
v=change(v,"        if self._proof is None:\n            if (full,fresh)!=(4,4)", "        if self._attempts==0:\n            if (full,fresh)!=(4,4)")
v=change(v,"            full,fresh=self._finish(ticket,decision,audit,envelope=envelope)\n            return envelope", "            full,fresh=self._finish(ticket,decision,audit,envelope=envelope)\n            if self._fixed_declaration[5]:self._awaiting_build=envelope\n            return envelope")
v=change(v,'ticket=self._start();root,arm,binding_pin,terminal_pin,hours,reuse=self._declaration',
    'ticket=self._start();root,arm,binding_pin,terminal_pin,hours,reuse,maximum,diagnostic=self._declaration')
v=change(v,"        self._proof=self._science_basis=None;self._pending.clear();self._ticket=None", "        self._proof=self._candidate_proof=self._science_basis=None;self._pending.clear();self._ticket=None\n        self._build_ticket=self._awaiting_build=None;self._body_bytes=None")
v=v.replace('self._attempts==2 and self._failure is None','self._attempts==self._max_prepares and self._failure is None')
v=change(v,"        closed=closed and self._ticket is None and not self._original_guard.locked()", "        closed=closed and self._candidate_proof is None and self._build_ticket is None and self._awaiting_build is None\n        closed=closed and self._ticket is None and not self._original_guard.locked()\n        public_complete=public_complete and (not self._fixed_declaration[5] or len(self._confirmed_builds)==4)")
v=change(v,"            completed_prepares=self._attempts,prepares=deepcopy(self._rows),context_observations=self._contexts,", "            completed_prepares=self._attempts,prepares=deepcopy(self._rows),context_observations=self._contexts,\n            maximum_prepares=self._max_prepares,confirmed_builds=deepcopy(self._confirmed_builds),\n            bootstrap_operation_bound=self._bootstrap_binding is not None,diagnostic_only=self._diagnostic_only,")
v=change(v,"('full_numerical_hour_replays',full),('fresh_byte_context_revalidations',fresh),", "('predecessor_schema',SCHEMA),('full_numerical_hour_replays',full),('fresh_byte_context_revalidations',fresh),")
v=change(v,"    for name in ('__enter__','prepare','_finish'):", "    for name in ('__enter__','prepare','_finish','begin_build','confirm_build'):")
extra='''

def prepare(root,*,expected_binding_sha256,expected_terminal_sha256,completed_hours,n0_operation=None):
    if n0_operation is not None:
        if type(n0_operation) is not N0ValidationOperation:raise TypeError('exact N0 validation operation required')
        n0_operation._check()
        expected=(str(Path(root)),expected_binding_sha256,expected_terminal_sha256,completed_hours)
        actual=(n0_operation._exact_root,*n0_operation._fixed_declaration[2:5])
        if expected!=actual:
            error=ValueError('N0 operation root or pins differ');n0_operation._poison(error);raise error
        return n0_operation.prepare()
    with N0ValidationOperation(root,arm_id='full_fallback',expected_binding_sha256=expected_binding_sha256,
            expected_terminal_sha256=expected_terminal_sha256,completed_hours=completed_hours,
            reuse_numerical_proof=False) as operation:
        return operation.prepare()


'''
v=change(v,'def _install_runtime_checks():',extra+'def _install_runtime_checks():')

b=original['h1_bootstrap_integration_development_v2.py']
b=b.replace('h1_bootstrap_integration_development_v2','h1_bootstrap_integration_development_v3')
b=b.replace('h1_owned_bootstrap_controller_development_v2','h1_owned_bootstrap_controller_development_v3')
b=b.replace('h1_historical_n0_verifier_development_v1','h1_historical_n0_verifier_development_v2')
b=change(b,"        full_numerical_hour_replays=4,fresh_byte_context_revalidations=4,\n        recomputed_on_revalidation=False,",'''        historical_validation_contract=historical_verifier.VERIFIER_SCHEMA,
        legacy_compatibility_execution_metadata=dict(full_numerical_hour_replays=4,
            fresh_byte_context_revalidations=4,recomputed_on_revalidation=False,
            scope='predecessor_scientific_projection_only'),''')
b=change(b,'def verify(root,*,expected_binding_sha256,expected_terminal_sha256,completed_hours):',
    'def verify(root,*,expected_binding_sha256,expected_terminal_sha256,completed_hours,n0_operation=None):')
b=change(b,'expected_terminal_sha256=expected_terminal_sha256,completed_hours=completed_hours)\n        if (type(value)',
    'expected_terminal_sha256=expected_terminal_sha256,completed_hours=completed_hours,n0_operation=n0_operation)\n        if (type(value)')
b=change(b,"                or value.full_numerical_hour_replays!=4 or value.fresh_byte_context_revalidations!=4\n                or value.recomputed_on_revalidation is not False):",'''                or (value.full_numerical_hour_replays,value.fresh_byte_context_revalidations) not in ((4,4),(0,8))
                or type(value.execution_receipt) is not bytes
                or json.loads(value.execution_receipt)['predecessor_audit_sha256']!=sha256(value.audit_payload).hexdigest()):''')
b=change(b,"        value=operation(*args,**kwargs)\n        if _prepare_N0 is not route:raise ValueError('N0 verifier route changed')\n        return value",'''        scope=kwargs.get('n0_operation');ticket=None
        if scope is not None:
            scope._check_bootstrap_binding()
            if scope._bootstrap_owner is not args[0]:raise ValueError('foreign N0 operation owner')
            ticket=scope.begin_build(args[0],kwargs.get('n0_site'))
        try:
            value=operation(*args,**kwargs)
            if _prepare_N0 is not route:raise ValueError('N0 verifier route changed')
            if scope is not None:scope.confirm_build(ticket,value)
            return value
        except BaseException as error:
            if scope is not None:scope._poison(error)
            raise''')
b=change(b,'    def _registry(self):','    def _registry(self,*,n0_operation=None,n0_site=None):')
b=change(b,'                        observed,self._check)','                        observed,self._check,n0_operation=n0_operation if slot==self._slot[\'slot_id\'] else None,n0_site=n0_site)')
b=change(b,'    def _build_N0_terminal(self,claim_head,claim,release_head,ready_row,local_release_head,observed,check_binding):',
    '    def _build_N0_terminal(self,claim_head,claim,release_head,ready_row,local_release_head,observed,check_binding,*,n0_operation=None,n0_site=None):')
b=change(b,'            expected_terminal_sha256=terminal_pin,completed_hours=1)','            expected_terminal_sha256=terminal_pin,completed_hours=1,n0_operation=n0_operation)')
b=change(b,'    def _replay(self):\n        self._check();rows=self._bootstrap.rows();registry=self._registry()',
    "    def _replay(self,*,n0_operation=None):\n        self._check();rows=self._bootstrap.rows();registry=self._registry(n0_operation=n0_operation,n0_site='registry_before')")
b=change(b,'            if self._registry()!=registry or self._bootstrap.rows()!=rows:',
    "            if self._registry(n0_operation=n0_operation,n0_site='registry_after')!=registry or self._bootstrap.rows()!=rows:")
start=b.index('        def prepare():\n',b.index('    def _finish_N0_terminal('))
end=b.index('\n    def reconcile_N0_terminal',start)
tail=b[start:end]
tail=change(tail,'        def prepare():','        def prepare(site):')
tail=change(tail,'                observed,check_binding)','                observed,check_binding,n0_operation=n0_operation,n0_site=site)')
tail=change(tail,'body=prepare()',"body=prepare('explicit_primary')")
tail=change(tail,'encode(prepare())',"encode(prepare('explicit_after_local'))")
tail=change(tail,"self._replay()!='pending_post_N'","self._replay(n0_operation=n0_operation)!='pending_post_N'")
wrapped='        def execute(n0_operation):\n            nonlocal local_rows,global_rows\n'+''.join('    '+line if line.strip() else line for line in tail.splitlines(keepends=True))
wrapped+='''
        if not create_local:return execute(None)
        binding_pin=ready_row[1]['files_sha256']['obligation_non_authoritative/binding.json']
        terminal_view=historical.history._read_single(root/'obligation_non_authoritative/000.terminal.json',phase.CAP)
        terminal_pin=sha256(terminal_view[0]).hexdigest()
        operation=historical_verifier.N0ValidationOperation(root,arm_id=self._slot['slot_id'],
            expected_binding_sha256=binding_pin,expected_terminal_sha256=terminal_pin,
            _bootstrap_owner=self)
        with operation:
            result=execute(operation)
        receipt=operation.receipt()
        if (not receipt['complete'] or receipt['context_observations']!=64
                or [r['site'] for r in receipt['confirmed_builds']]!=list(historical_verifier.BUILD_SITES)
                or [(r['full_numerical_hour_replays'],r['fresh_byte_context_revalidations'])
                    for r in receipt['prepares']]!=[(4,4),(0,8),(0,8),(0,8)]):
            raise ValueError('complete four-build N0 operation receipt required')
        result['N0_validation_execution_receipt']=historical.io.encode(receipt)
        return result
'''
b=b[:start]+wrapped+b[end:]

owned=original['h1_owned_bootstrap_controller_development_v2.py'].replace(
    'h1_bootstrap_integration_development_v2','h1_bootstrap_integration_development_v3')
outputs={'h1_historical_n0_verifier_development_v2.py':v,'h1_bootstrap_integration_development_v3.py':b,
    'h1_owned_bootstrap_controller_development_v3.py':owned}
for name,text in outputs.items():
    assert not (REPO/'experiments'/name).exists(),name
    compile(text,str(REPO/'experiments'/name),'exec')
for name,text in outputs.items():
    with (REPO/'experiments'/name).open('x',encoding='utf-8',newline='\n') as stream:stream.write(text)
assert all(sha256(Path(name).read_bytes()).hexdigest()==pin for name,pin in before.items())
assert all(sha256(Path(name).read_bytes()).hexdigest()==pin for name,pin in old_pins.items())
result=dict(status='DRAFT_NONAUTHORITATIVE',predecessor_sources_sha256=before,
    successor_sources_sha256={str(REPO/'experiments'/name):sha256((REPO/'experiments'/name).read_bytes()).hexdigest() for name in outputs},
    entry='BootstrapOwner.bootstrap -> owned v3 -> _finish_N0_terminal(create_local=True)',
    sites=['explicit_primary','explicit_after_local','registry_before','registry_after'],
    expected_counts=[[4,4],[0,8],[0,8],[0,8]],context_evaluations=64,
    scientific_oracle='legacy historical verifier on exact same saved controller/pins',
    old_chain_inputs_unchanged=len(old_pins),full_hour0_chain_passed=False,
    formal_execution_ready=False,formal_result=False,resource_admission=False,native_execution_authorized=False)
with (HERE/'draft_sources_01.json').open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
print(json.dumps(dict(sources=list(outputs),status=result['status'])),flush=True)
