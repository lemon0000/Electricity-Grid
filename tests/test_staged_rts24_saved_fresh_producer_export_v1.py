"""Private connected data/cleanup fixtures. No actual outer, P1 or Native."""
import ast
import base64
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
from types import FunctionType,ModuleType,SimpleNamespace
import time
import unittest
from unittest.mock import patch
import zlib

ROOT=Path(__file__).absolute().parents[1]


def load(name,relative):
    path=ROOT/relative;spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


codec=load('_export_codec','experiments/staged_rts24_saved_fresh_producer_packet_v1.py')
coordinator=load('_export_coordinator','experiments/staged_rts24_saved_fresh_complete_producer_v1.py')
parent=load('_export_parent','experiments/staged_rts24_saved_fresh_producer_parent_reopen_v1.py')
deferred=load('_export_deferred','experiments/staged_rts24_saved_fresh_producer_bootstrap_v6.py')
transform=load('_export_transform','experiments/staged_rts24_saved_fresh_producer_export_transform_v1.py')
deferred_transform=load('_export_deferred_transform','experiments/staged_rts24_saved_fresh_deferred_bundle_transform_v1.py')

# Adapt only the private fixture text; the frozen 48-test source is untouched.
path=ROOT/'tests/test_staged_rts24_saved_fresh_p1_permission_v2.py'
source=path.read_text(encoding='utf8').replace('staged_rts24_saved_fresh_retained_producer_v4.py',
    'staged_rts24_saved_fresh_retained_producer_v5.py')
needle='legacy_raw=legacy_path.read_text(encoding=\'utf8\')'
assert source.count(needle)==1
source=source.replace(needle,needle+"\nlegacy_raw=legacy_raw.replace('_pending_reentry=None)', '_pending_reentry=None,_packet=None,_stage_clocks=[])')")
base=ModuleType('_export_permission_fixture');base.__file__=str(path)
exec(compile(source,str(path)+'::export_fixture','exec',dont_inherit=True,optimize=0),vars(base),vars(base))
permission=base.permission;legacy=base.legacy
before="return STATE['canonical'](dict(source_pins=held.source_pins,input_files=held.files))"
after="return STATE['canonical'](dict(source=held.source_pins,files=held.files,inventory=dict(pins=held.files,files=held.metadata,directories=held.folders),**held.core_extra))"
assert legacy.ADAPTER_RAW.count(before.encode())==1;legacy.ADAPTER_RAW=legacy.ADAPTER_RAW.replace(before.encode(),after.encode())
before=b'        self.close_calls+=1'
after=b'        self._cleanup_started=True;self.close_calls+=1'
assert legacy.CORE_RAW.count(before)==1;legacy.CORE_RAW=legacy.CORE_RAW.replace(before,after)
before=b"        self._cleanup_started=True;self._failure=primary"
after=b"        self._cleanup_started=True;self._failure=primary;self._resource.close_calls=[value+1 for value in self._resource.close_calls]"
assert legacy.CORE_RAW.count(before)==1;legacy.CORE_RAW=legacy.CORE_RAW.replace(before,after)


def private_permission_dispatch(held,operation,args):
    state=held[2]
    if operation=='retire':
        if 'retire_fault' in globals():retire_observed.append(state.guard_phase);raise retire_fault
        return permission.retire(state,*args)
    if operation=='close_guard':return permission.close_guard(state)
    if operation=='report':return permission.observation(state)
    raise ValueError('private mechanical permission operation')


def private_bundle_dispatch(state,producer,operation,args,kwargs):
    if fixture.outer_fault==operation:
        if fixture.cleanup_error is not None:fixture.state['check_error']=fixture.cleanup_error
        raise fixture.outer_error
    if producer is None:
        if fixture.prepare_error is not None:raise fixture.prepare_error
        if operation!='prepare' or args!=(fixture.owner,fixture.token):raise ValueError('private prepare seam')
        return fixture.context['claim_runtime_slot'](fixture.producer)
    result=fixture.call(fixture.dispatch_spec[2],producer,operation,args,kwargs)
    if operation=='close' and fixture.report_fault is not None:
        result['injected']='x'*262144 if fixture.report_fault=='cap' else object()
    return result


def private_bridge_dispatch(state,stage,owner,args):
    if owner is not fixture.owner or args:raise ValueError('private bridge owner')
    if stage=='bundle':
        if fixture.bundle_error is not None:raise fixture.bundle_error
        return state['bundle']
    if stage=='release':state['released']=True;return
    raise ValueError('private bridge operation')


class ExportLifecycleTests(base.PermissionLifecycleTests):
    def setUp(self):
        super().setUp()
        self.owner._resource.close_calls=[0,0]
        held=self.state['held']
        held.metadata={name:[0,index+1,row['bytes'],1] for index,(name,row) in enumerate(sorted(held.files.items()))}
        held.folders={'.':[0,1]}
        held.core_extra=dict(fixture_sha='0'*64,outer={},trusted={},expectations={},bindings=[{} for _ in range(6)],
            anchor_path='synthetic-anchor',anchor_pin=dict(bytes=1,sha256='0'*64),anchor_identity=[0,1,1,1],
            anchor_directories=[],root_directories=[],historical_metrics={},expected_evidence_refs=[{} for _ in range(21)])
        image=self.adapter.caller_image(held);held.image=image
        core=json.loads(image);expectation=self.state['expectation'];expectation.image=image
        gates={name:False for name in ('native_authorized','resource_admission','formal_result','scientific_evidence_adopted','public_P2_execution_enabled')}
        content=sorted(['launcher.json','trusted_binding.json','start.json','request_schedule.json','fresh.json']
            +['trusted_prefixes/prefix_%06d.json'%index for index in range(6)]
            +['points/point_%04d/%s.json'%(index,name) for index in range(1,22) for name in ('request','result')])
        expectation.raw=codec.packet_canonical(dict(schema='staged_saved_P1_caller_expectation_development_v1',
            authority='DRAFT_NONAUTHORITATIVE',scope='saved_P1_actual_21_and_journal_5h',caller_expectation_core=core,
            caller_expectation_sha=sha256(image).hexdigest(),source_sha=sha256(codec.packet_canonical(held.source_pins)).hexdigest(),
            input_pins_sha=sha256(codec.packet_canonical(held.files)).hexdigest(),content_read_files=content,metadata_passes=2,
            full_P1_content_verified=False,F_launch_admitted=False,**gates))
        start=time.monotonic()
        context=dict(schema='staged_saved_P1_expectation_context_development_v1',authority='DRAFT_NONAUTHORITATIVE',
            scope='saved_P1_actual_21_and_journal_5h',repo_root=str(ROOT),input_root='synthetic-input',output_root='synthetic-output',
            output_mode='ordinary_expectation_fixture',output_parent_directories=[],source_pins=held.source_pins,
            executable={},environment={},anchor_sha='0'*64,input_files=held.files,invocation_started=start,deadline=start+180.0,
            stage_seconds={},limits={},inherited_sources_pin=dict(bytes=0,sha256='0'*64),caller_expectation_core=core,
            caller_expectation_sha=sha256(image).hexdigest(),expectation_sha=sha256(expectation.raw).hexdigest(),
            full_P1_content_verified=False,**gates)
        self.state.update(expected_image=image,expectation_raw=expectation.raw,context=codec.packet_canonical(context))

    def finished(self):
        self.run_producer();self.invoke('G2');self.invoke('G3');return self.invoke('close')

    def detached(self):return json.loads(codec.packet_unwire(self.finished()['packet']))

    def setup_coordinator(self):
        self.bundle_error=None;self.prepare_error=None;self.outer_fault=None;self.outer_error=LookupError('outer graph fault');self.cleanup_error=None;self.report_fault=None
        self.permission_spec=(private_permission_dispatch.__code__,dict(permission=permission),
            (None,None,self.permission))
        self.context['_P1_PERMISSION_PROGRAM']=self.permission_spec
        # Capture the original close/revoke at the same pre-import phase as a
        # creating bootstrap. This fixture never instantiates a native owner.
        base.put(self.permission,phase='DISABLED',guard_phase='NEW',admission=None)
        self.owner._phase='ADOPTED'
        cleanup=coordinator.prepare_coordinator_cleanup(self.owner,self.permission_spec,base.RAW)
        self.owner._phase='LIVE';self.owner._consume_state='PREPARED';self.owner._seal=self.core.runtime_seal(self.owner)
        base.put(self.permission,phase='ISSUED',guard_phase='READ_WINDOW',admission=self.token,sentinel=1)
        base.put(self.producer,_claimed=False);self.context['commit'](self.producer)
        env=dict(fixture=self)
        bundle=(private_bundle_dispatch.__code__,env,(None,None,None,self.dispatch_spec,None,None,None))
        bridge_state=dict(bundle=bundle,released=False)
        bridge=(private_bridge_dispatch.__code__,env,bridge_state)
        self.cleanup_packet=cleanup;self.bridge=bridge;self.bridge_state=bridge_state
        return cleanup

    def complete(self):
        return coordinator.complete_producer(self.owner,self.bridge,self.permission_spec,self.cleanup_packet,
            ROOT/'results/tables/synthetic_not_written',time.monotonic())

    @staticmethod
    def quiet():
        # A synthetic parent observation. Real Parent must bind these facts to
        # its retained child/handle/drain receipt and exact stdout bytes.
        return dict(child_exit=0,process_handle_closed=True,pipes_closed=True,reader_threads_terminal=True,
            writer_thread_terminal=True,killed=False,stdout_truncated=False,stderr_truncated=False,reader_errors=[],cleanup=[])

    def test_49_detached_bytes_restore_after_all_live_refs_released(self):
        expected=(self.state['expectation_raw'],self.state['context'],self.state['expected_image'])
        report=self.finished();raw=codec.packet_unwire(report['packet']);restored=codec.packet_restore(raw)
        self.assertEqual(tuple(restored[key] for key in ('expectation_raw','context_raw','caller_image')),expected)
        self.assertEqual(self.producer._packet,raw);self.assertEqual(len(restored['packet']['files']),683)
        for field in ('_expectation','_context','_held','_owner','_snapshot','_permission_revoke'):
            self.assertIsNone(getattr(self.producer,field))
        self.assertNotIn('raw',restored['packet']['core_tail']['inventory'])
        self.assertEqual(report,self.invoke('close'));self.assertEqual(self.owner.close_calls,1)

    def test_50_each_envelope_and_internal_gate_is_closed(self):
        value=self.detached()
        for field in ('core_tail','expectation_tail','context_tail'):
            changed=json.loads(codec.packet_canonical(value));changed[field]['injected']=True
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'closed original producer'):
                codec.packet_restore(codec.packet_canonical(changed))
        for field in ('expectation_tail','context_tail'):
            changed=json.loads(codec.packet_canonical(value));changed[field]['formal_result']=True
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'authority fields'):
                codec.packet_restore(codec.packet_canonical(changed))

    def test_51_missing_full_map_identity_or_parent_rejected(self):
        value=self.detached()
        for mode in ('input','source','metadata','folder','alias'):
            changed=json.loads(codec.packet_canonical(value))
            if mode=='input':changed['files'].pop(next(iter(changed['files'])))
            elif mode=='source':changed['sources'].pop(next(iter(changed['sources'])))
            elif mode=='metadata':changed['core_tail']['inventory']['files'].pop(next(iter(changed['files'])))
            elif mode=='folder':changed['core_tail']['inventory']['directories']={}
            else:
                rows=list(changed['core_tail']['inventory']['files'].values());rows[1][:2]=rows[0][:2]
            with self.subTest(mode=mode),self.assertRaises(ValueError):codec.packet_restore(codec.packet_canonical(changed))

    def test_52_stage_pin_order_and_original_deadline_are_bound(self):
        value=self.detached()
        for mode in ('order','pin','clock','reset'):
            changed=json.loads(codec.packet_canonical(value))
            if mode=='order':changed['stages'].reverse()
            elif mode=='pin':changed['stages'][1]['context_pin']['sha256']='0'*64
            elif mode=='clock':changed['clocks'][-1]=changed['context_tail']['deadline']+1.0
            else:changed['context_tail']['deadline']+=1.0
            with self.subTest(mode=mode),self.assertRaises(ValueError):codec.packet_restore(codec.packet_canonical(changed))

    def test_53_duplicate_noncanonical_trailing_and_bomb_wire_rejected(self):
        raw=codec.packet_unwire(self.finished()['packet']);wire=codec.packet_wire(raw)
        for data in (b'{"schema":0,"schema":1}',raw+b'\n',b'{"value":NaN}'):
            with self.subTest(data=data[:32]),self.assertRaises(ValueError):codec.packet_restore(data)
        for packed in (zlib.compress(raw)+b'extra',zlib.compress(b'x'*(codec.PACKET_RAW_CAP+1))):
            changed=dict(wire,data=base64.b64encode(packed).decode('ascii'))
            with self.assertRaises(ValueError):codec.packet_unwire(changed)
        with self.assertRaises(ValueError):codec.packet_unwire(dict(wire,data='*'))

    def test_54_export_fault_retires_and_keeps_original_live_evidence(self):
        self.run_producer();self.invoke('G2');self.invoke('G3')
        self.producer._stage_clocks.pop();self.context['commit'](self.producer)
        failure=self.failure(lambda:self.invoke('close'))
        self.assertIn('stage clocks',str(failure.primary));self.assertEqual(self.permission.guard_phase,'DENY')
        self.assertIs(self.producer._held,self.state['held']);self.assertIsNone(self.producer._packet)

    def test_55_coordinator_full_private_chain_and_quiet_data_replay(self):
        self.setup_coordinator();value=self.complete()
        result=parent.audit_producer_data(codec.packet_canonical(value),self.quiet(),legacy.SOURCE_PINS)
        self.assertIs(result['data_relationships_replayed'],True);self.assertEqual(result['physical_parent_P1_reads'],0)
        self.assertIs(result['actual_F'],False);self.assertIs(self.bridge_state['released'],True)
        self.assertEqual(self.owner._resource.close_calls,[1,1]);self.assertEqual(self.owner._consume_state,'CONSUMED')

    def test_56_bundle_finalization_error_uses_preimport_cleanup(self):
        self.setup_coordinator();primary=LookupError('issue succeeded then finalization failed');self.bundle_error=primary
        with self.assertRaises(LookupError) as caught:self.complete()
        self.assertIs(caught.exception,primary);self.assertEqual(self.owner._consume_state,'PREPARED')
        self.assertEqual(self.owner.close_calls,1);self.assertEqual(self.permission.phase,'RETIRED')
        self.assertEqual(self.permission.guard_phase,'CLOSED');self.assertEqual(self.state['capture_calls'],0)

    def test_57_preproducer_prepare_error_consumes_zero_slot_and_closes_once(self):
        self.setup_coordinator();primary=ArithmeticError('prepare before producer return');self.prepare_error=primary
        with self.assertRaises(ArithmeticError) as caught:self.complete()
        self.assertIs(caught.exception,primary);self.assertEqual(self.owner._consume_state,'PREPARED')
        self.assertEqual(self.owner.close_calls,1);self.assertEqual(self.permission.guard_phase,'CLOSED')

    def test_58_outer_bookend_fault_preserves_sticky_LC_carrier(self):
        self.setup_coordinator();self.outer_fault='G2';primary=self.outer_error
        secondary=OSError('LC context final cleanup fault');self.cleanup_error=secondary
        with self.assertRaises(self.context['RetainedProducerFailure']) as caught:self.complete()
        self.assertIs(caught.exception,self.producer._failure);self.assertIs(caught.exception.primary,primary)
        self.assertIn(('context_final',secondary),caught.exception.secondary)
        self.assertIsNotNone(caught.exception.runtime_close);self.assertEqual(self.owner.close_calls,1)

    def test_59_parent_requires_quiet_and_closed_permission_envelope(self):
        self.setup_coordinator();value=self.complete();raw=codec.packet_canonical(value)
        for key,bad in (('child_exit',1),('pipes_closed',False),('reader_threads_terminal',False),('writer_thread_terminal',False),('killed',True)):
            quiet=self.quiet();quiet[key]=bad
            with self.subTest(key=key),self.assertRaises(ValueError):parent.audit_producer_data(raw,quiet,legacy.SOURCE_PINS)
        for mode in ('extra','claim','open','counter','wrong_source'):
            changed=json.loads(raw);sources=dict(legacy.SOURCE_PINS)
            if mode=='extra':changed['permission']['extra']=0
            elif mode=='claim':changed['formal_result']=True
            elif mode=='open':changed['permission']['guard_phase']='READ_WINDOW'
            elif mode=='counter':changed['permission']['counters']['outside_reads']=1
            else:sources.pop(next(iter(sources)))
            with self.subTest(mode=mode),self.assertRaises(ValueError):parent.audit_producer_data(codec.packet_canonical(changed),self.quiet(),sources)

    def test_60_parent_executes_only_the_raw_bytes_it_pin_checked(self):
        raw=(ROOT/'experiments/staged_rts24_saved_fresh_producer_packet_v1.py').read_bytes()
        with patch.object(Path,'read_bytes',return_value=raw) as reads:
            module=parent.parent_codec();self.assertEqual(module.PACKET_RAW_CAP,1048576)
        self.assertEqual(reads.call_count,1)

    def test_61_successor_derivation_and_original_Source49_envelope_contract(self):
        transform.current();deferred_transform.current()
        tree=ast.parse((ROOT/'experiments/staged_rts24_saved_fresh_adoption_v1.py').read_bytes())
        assignments={node.targets[0].id:node.value for node in tree.body if type(node) is ast.Assign
            and len(node.targets)==1 and type(node.targets[0]) is ast.Name}
        original_gates={key.arg:ast.literal_eval(key.value) for key in assignments['GATES'].keywords}
        self.assertEqual(set(original_gates),set(codec.PACKET_GATES));self.assertTrue(all(value is False for value in original_gates.values()))
        self.assertEqual(ast.literal_eval(assignments['EXPECTATION_SCHEMA']),'staged_saved_P1_caller_expectation_development_v1')
        self.assertEqual(len(codec.PACKET_CONTENT_FILES),53)
        with patch.object(deferred,'check',return_value=None):
            plan=SimpleNamespace(_phase='FINAL',_owner=SimpleNamespace(_phase='IMPORTING'))
            with self.assertRaisesRegex(ValueError,'prepared profile-matched LIVE'):
                deferred._make_bundle(plan,None,None,None,None,compile('pass','<fixture>','exec'),None)

    def test_62_deferred_import_return_never_builds_or_issues_early(self):
        runtime=SimpleNamespace(_phase='IMPORTING');state=dict(owner=runtime,creator=deferred.creator(),phase='COLLECTING',
            plan=object(),bundle=None,failure=None,graph=None,graph_raw=None,lifecycle=None,lifecycle_raw=None,capture_code=None,admission=None)
        state['seal']=deferred.pin(deferred.canonical(deferred.bridge_image(state)))
        with (patch.object(deferred,'check_program'),patch.object(deferred,'finalize_project_construction',return_value=state['plan']) as finalize,
                patch.object(deferred,'make_project_bootstrap_bundle',side_effect=AssertionError('early issuance')) as make):
            self.assertIsNone(deferred.import_bridge_event(state,'after_import',runtime,(object(),)))
        self.assertEqual(state['phase'],'READY');self.assertIsNone(state['bundle']);self.assertEqual(finalize.call_count,1);make.assert_not_called()

    def test_63_real_bridge_release_requires_all_terminals_then_clears_references(self):
        def state():
            value=dict(owner=self.owner,creator=deferred.creator(),phase='BUNDLED',plan=object(),bundle=object(),failure=None,
                graph=object(),graph_raw=b'graph',lifecycle=object(),lifecycle_raw=b'lc',capture_code=object(),admission=None)
            value['seal']=deferred.pin(deferred.canonical(deferred.bridge_image(value)));return value
        spec=(None,None,(None,None,self.permission))
        with patch.object(deferred,'check_program'),patch.object(deferred,'_P1_PERMISSION_PROGRAM',spec):
            active=state()
            with self.assertRaises(ValueError):deferred.import_bridge_event(active,'release',self.owner,())
            self.assertIs(active['owner'],self.owner);self.assertIsNotNone(active['graph'])
            self.finished();denied=state()
            with self.assertRaisesRegex(ValueError,'closed permission'):deferred.import_bridge_event(denied,'release',self.owner,())
            self.assertIs(denied['owner'],self.owner);self.assertIsNotNone(denied['bundle'])
            permission.close_guard(self.permission);closed=state()
            deferred.import_bridge_event(closed,'release',self.owner,())
        self.assertEqual(closed['phase'],'RELEASED')
        for key in ('owner','plan','bundle','graph','graph_raw','lifecycle','lifecycle_raw','capture_code','admission'):
            self.assertIsNone(closed[key])

    def test_64_retire_verifier_failure_observes_independent_deny_and_primary(self):
        self.setup_coordinator();primary=LookupError('bundle failure');secondary=OSError('retire verifier drift')
        self.bundle_error=primary;observed=[]
        with patch.dict(self.permission_spec[1],retire_fault=secondary,retire_observed=observed):
            with self.assertRaises(LookupError) as caught:self.complete()
        self.assertIs(caught.exception,primary);self.assertEqual(observed,['DENY'])
        self.assertIn(secondary,primary.__cause__.exceptions);self.assertEqual(self.owner.close_calls,1)
        self.assertEqual(self.permission.guard_phase,'CLOSED');self.assertEqual(self.owner._consume_state,'PREPARED')

    def test_65_cleanup_capture_rejects_noop_wrong_state_or_put_before_issuance(self):
        self.setup_coordinator();self.owner._phase='ADOPTED'
        base.put(self.permission,phase='DISABLED',guard_phase='NEW',admission=None)
        original=self.permission.revocation
        def noop(state,put):pass
        for packet in ((noop.__code__,original[1],original[2]),
                (original[0],original[1],(object(),object.__setattr__)),
                (original[0],original[1],(self.permission,lambda *args:None))):
            base.put(self.permission,revocation=packet)
            with self.assertRaisesRegex(ValueError,'same-state read revoke'):
                coordinator.prepare_coordinator_cleanup(self.owner,self.permission_spec,base.RAW)
        self.assertEqual(self.owner.close_calls,0);self.assertEqual(self.state['capture_calls'],0)

    def test_66_late_wire_cap_failure_preserves_original_refs_after_one_close(self):
        self.run_producer();self.invoke('G2');self.invoke('G3')
        self.context['PACKET_WIRE_CAP']=1
        failure=self.failure(lambda:self.invoke('close'))
        self.assertIn('wire cap',str(failure.primary));self.assertIn(('detached_report',failure.primary),failure.secondary)
        self.assertIs(self.producer._held,self.state['held']);self.assertIsNotNone(self.producer._packet)
        self.assertIs(self.producer._owner,self.owner);self.assertIsNotNone(self.producer._permission_revoke)
        self.assertEqual(self.owner.close_calls,1);self.assertEqual(self.owner._resource.phase,'CLOSED')

    def test_67_complete_cap_failure_keeps_bridge_evidence_after_physical_close(self):
        self.setup_coordinator();self.report_fault='cap'
        with self.assertRaisesRegex(ValueError,'complete producer data cap'):self.complete()
        self.assertIs(self.bridge_state['released'],False);self.assertEqual(self.producer._phase,'CLOSED')
        self.assertEqual(self.owner.close_calls,1);self.assertEqual(self.permission.guard_phase,'CLOSED')
        self.assertIsNotNone(self.producer._packet)

    def test_68_complete_serialization_failure_keeps_bridge_evidence(self):
        self.setup_coordinator();self.report_fault='json'
        with self.assertRaises(TypeError):self.complete()
        self.assertIs(self.bridge_state['released'],False);self.assertEqual(self.producer._phase,'CLOSED')
        self.assertEqual(self.owner.close_calls,1);self.assertEqual(self.permission.guard_phase,'CLOSED')

    def test_69_deferred_issuer_uses_fixed_disabled_code_and_rejects_callback(self):
        calls=[]
        spec=permission.source_program(base.RAW,type(self.owner),base.UTILITY_RAW)
        with patch.object(deferred,'_P1_PERMISSION_RAW',base.RAW),patch.object(deferred,'_P1_PERMISSION_PROGRAM',spec):
            with self.assertRaisesRegex(PermissionError,'no approved external'):
                deferred.permission_operation('issue',(self.owner,self.owner._consumer_plan,self.producer._snapshot,self.owner._boundary))
        def callback(*args):calls.append(args)
        with patch.object(deferred,'_P1_PERMISSION_RAW',base.RAW),patch.object(deferred,'_P1_PERMISSION_PROGRAM',(callback.__code__,{},spec[2])):
            with self.assertRaisesRegex(ValueError,'fixed permission dispatch code'):deferred.permission_operation('issue',())
        self.assertEqual(calls,[])


if __name__=='__main__':unittest.main()
