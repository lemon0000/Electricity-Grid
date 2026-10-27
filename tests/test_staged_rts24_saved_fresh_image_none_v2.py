"""Method-only value oracle and finite native-audit dispatch comparison."""
import ast
import builtins
import importlib.util
import json
from pathlib import Path
import statistics
import sys
import time
from types import SimpleNamespace
import unittest

ROOT=Path(__file__).absolute().parents[1]
OUT=ROOT/'results/tables/staged_rts24_saved_fresh_image_none_v2_non_authoritative'
OLD=ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_import_census512_parts_v1.py'
NEW=ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_import_image_none_v1.py'
PROBE=ROOT/'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v25.py'
TRANSFORM=ROOT/'experiments/staged_rts24_saved_fresh_image_none_transform_v1.py'


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


fixtures=load(ROOT/'tests/test_staged_rts24_saved_fresh_image_pin_v1.py','_none_image_fixtures')
fixtures.OLD=OLD;fixtures.NEW=NEW;fixtures.PROBE=PROBE
_GATE=dict(installed=False,active=False,events=[],calls=0,none_calls=0,none_id=id(None),
    fail_at=None,fail_none_at=None,primary=None,dispatch=None,guard=None,record=False)


def install_hook():
    if _GATE['installed']:return
    def hook(event,args):
        if event!='builtins.id' or not _GATE['active']:return
        _GATE['calls']+=1
        if args[0]==_GATE['none_id']:_GATE['none_calls']+=1
        if _GATE['record']:_GATE['events'].append(args[0])
        if (_GATE['fail_at'] is not None and _GATE['calls']==_GATE['fail_at']) or (_GATE['fail_none_at'] is not None and args[0]==_GATE['none_id'] and _GATE['none_calls']==_GATE['fail_none_at']):raise _GATE['primary']
        if _GATE['dispatch'] is not None:_GATE['dispatch'](_GATE['guard'],event,args,None,())
    sys.addaudithook(hook);_GATE['installed']=True


def begin(*,record=False,dispatch=None,guard=None,fail_at=None,fail_none_at=None,primary=None):
    install_hook();assert not _GATE['active']
    _GATE.update(events=[],calls=0,none_calls=0,record=record,dispatch=dispatch,guard=guard,fail_at=fail_at,fail_none_at=fail_none_at,primary=primary)
    _GATE['active']=True


def end():
    _GATE['active']=False
    _GATE['dispatch']=None;_GATE['guard']=None;_GATE['primary']=None


def fewer_none(values):
    result=[];seen=False
    for value in values:
        if value==_GATE['none_id']:
            if seen:continue
            seen=True
        result.append(value)
    return result


class ImageNoneTests(fixtures.ImagePinTests):
    def test_01_only_image_ast_changes(self):
        super().test_01_only_image_ast_changes()
        transform=load(TRANSFORM,'_none_transform_test')
        self.assertEqual(transform.helper(OLD.read_text(encoding='utf-8')),NEW.read_bytes())
        original=ROOT/'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v24.py'
        self.assertEqual(transform.probe(original.read_text(encoding='utf-8')),PROBE.read_bytes())
        self.assertEqual(self.after.__defaults__,(builtins.id,))

    def test_07_pin_order_unique_failures_and_per_call_lifetime(self):
        sequences=[]
        for module,method in ((self.old,self.before),(self.new,self.after)):
            original=module.pin;seen=[]
            def counted(raw):seen.append(raw);return original(raw)
            module.pin=counted
            try:
                method(self.f);first=seen[:];method(self.f);self.assertEqual(seen,first+first)
                sequences.append(first)
            finally:module.pin=original
        self.assertEqual(*sequences)
        primary=OSError('first unique value')
        for module,method in ((self.old,self.before),(self.new,self.after)):
            original=module.pin
            def reject(raw):
                if raw==b'null':raise primary
                return original(raw)
            module.pin=reject
            try:
                with self.assertRaises(OSError) as caught:method(self.f)
                self.assertIs(caught.exception,primary)
            finally:module.pin=original

    def test_09_three_round_real_image_digest_cost(self):
        self.equal();process,prefixes,mutations=self.f._event_sets
        self.assertNotIn('builtins.id',process);self.assertNotIn('builtins.id',mutations)
        self.assertFalse('builtins.id'.startswith(prefixes))
        guard=SimpleNamespace(_state=self.f._state,_event_sets=self.f._event_sets,_busy=True)
        dispatch=self.old.BootstrapImportBoundary._audit
        def measure(name,scans,audited):
            module=getattr(self,name);method=self.before if name=='old' else self.after
            begin(dispatch=dispatch if audited else None,guard=guard)
            if not audited:_GATE['active']=False
            started=time.perf_counter()
            try:
                for _ in range(scans):module.digest(method(self.f))
                seconds=time.perf_counter()-started;calls=_GATE['calls'];none_calls=_GATE['none_calls']
            finally:end()
            return dict(variant=name,scans=scans,seconds=seconds,id_dispatch_calls=calls,none_dispatch_calls=none_calls)
        rounds=[]
        for index,order in enumerate((('old','new'),('new','old'),('old','new'))):
            rounds.append(dict(round=index+1,order=list(order),observations=[measure(name,48,True) for name in order]))
        plain=[measure(name,20,False) for name in ('old','new')]
        old=[r['seconds'] for pair in rounds for r in pair['observations'] if r['variant']=='old']
        new=[r['seconds'] for pair in rounds for r in pair['observations'] if r['variant']=='new']
        total=sum(new)/sum(old);median=statistics.median(new)/statistics.median(old);plain_ratio=plain[1]['seconds']/plain[0]['seconds']
        rows=[r for pair in rounds for r in pair['observations']]
        self.assertTrue(all(r['none_dispatch_calls']==48 for r in rows if r['variant']=='new'))
        self.assertGreater(rows[0]['id_dispatch_calls'],rows[1]['id_dispatch_calls'])
        met=total<=.95 and median<=.95 and plain_ratio<=1.20
        report=dict(authority='DRAFT_NONAUTHORITATIVE',method_fixture_only=True,synthetic_dispatch_only=True,
            rounds=rounds,without_dispatch=plain,total_ratio_new_over_old=total,median_ratio_new_over_old=median,
            without_dispatch_ratio_new_over_old=plain_ratio,dispatch_threshold=.95,without_dispatch_threshold=1.20,
            benchmark_threshold_met=met,hook_installed=_GATE['installed'],hook_deactivated=not _GATE['active'],hook_uninstalled=False,
            fixture_rows=dict(global_bindings=len(self.f._global_bindings),own_bindings=len(self.f._own_bindings),attribute_bindings=len(self.f._attribute_bindings)),
            candidate_adopted=False,production_helper_selected=False,cross_call_cache=False,all_unselected_events_verified=False,
            native_behavior_verified=False,full_runtime_binding_verified=False,full_P1_content_verified=False,independent_root_verified=False,
            role_bootstrap=False,permit_issued=False,F_launch_admitted=False,native_authorized=False,
            production_seal=False,scientific_evidence_adopted=False,
            cold_children_launched=0,adapter_imports=0,actual_F=False,run_authority=False,formal_result=False,resource_admission=False)
        raw=json.dumps(report,sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii');self.assertLessEqual(len(raw),65536)
        with (OUT/'metrics.json').open('xb') as stream:stream.write(raw)
        validator=load(OUT/'driver.py','_none_independent_metrics').validate_metrics
        self.assertIs(validator(report),met)
        changes=[lambda m:m.update(benchmark_threshold_met=not met),lambda m:m.update(hook_deactivated=False),
            lambda m:m.update(hook_uninstalled=True),lambda m:m.update(full_runtime_binding_verified=True),
            lambda m:m.update(production_helper_selected=True),lambda m:m.update(extra=0),
            lambda m:m.update(production_seal=True),lambda m:m.update(scientific_evidence_adopted=True),
            lambda m:m.pop('authority'),lambda m:m.update(dispatch_threshold=.96),
            lambda m:m.update(total_ratio_new_over_old=m['total_ratio_new_over_old']+.01),
            lambda m:m['rounds'][0].update(order=['new','old']),
            lambda m:m['rounds'][0]['observations'][0].update(scans=True),
            lambda m:m['rounds'][0]['observations'][1].update(none_dispatch_calls=47),
            lambda m:m['without_dispatch'][0].update(id_dispatch_calls=1)]
        changes.extend(lambda m,value=value:m['rounds'][0]['observations'][0].update(seconds=value) for value in (float('nan'),float('inf'),0.0,-1.0,1))
        for change in changes:
            bad=fixtures.copy.deepcopy(report);change(bad)
            with self.assertRaises(AssertionError):validator(bad)
        self.assertTrue(met,'predeclared dispatch benefit and inactive-hook overhead not established')

    def test_10_native_id_events_and_field_read_order(self):
        class Fields:
            def __init__(self,values):object.__setattr__(self,'values',values);object.__setattr__(self,'seen',[])
            def __getattribute__(self,name):
                if name in ('values','seen'):return object.__getattribute__(self,name)
                object.__getattribute__(self,'seen').append(name)
                return object.__getattribute__(self,'values')[name]
        for f in (self.f,fixtures.fixture(self.new,True)):
            images=[];traces=[];fields=[]
            for method in (self.before,self.after):
                proxy=Fields(vars(f));begin(record=True)
                try:images.append(method(proxy));traces.append(_GATE['events'][:])
                finally:end()
                fields.append(proxy.seen)
            self.assertEqual(images[0],images[1]);self.assertEqual(fields[0],fields[1])
            self.assertEqual(traces[1],fewer_none(traces[0]));self.assertEqual(traces[1].count(_GATE['none_id']),1)
            self.assertGreater(traces[0].count(_GATE['none_id']),1)

    def test_11_held_native_default_rejects_replacement(self):
        self.assertIs(self.after.__defaults__[0],builtins.id)
        fixtures.proof_for(self.new)
        saved=self.after.__defaults__
        try:
            for value in ((lambda v:0,),(),(None,)):
                self.after.__defaults__=value
                with self.assertRaisesRegex(ValueError,'B_S source defaults differ'):fixtures.proof_for(self.new)
        finally:self.after.__defaults__=saved
        fixtures.proof_for(self.new)

    def test_12_native_exception_primary_and_suppressed_none_event(self):
        vectors=[]
        for method in (self.before,self.after):
            begin(record=True)
            try:method(self.f);vectors.append(_GATE['events'][:])
            finally:end()
        for kind in ('first_none','later_non_none'):
            primary=OSError(kind)
            for method,values in zip((self.before,self.after),vectors):
                position=values.index(_GATE['none_id']) if kind=='first_none' else max(i for i,v in enumerate(values) if i>values.index(_GATE['none_id']) and v!=_GATE['none_id'])
                begin(fail_at=position+1,primary=primary)
                try:
                    with self.assertRaises(OSError) as caught:method(self.f)
                    self.assertIs(caught.exception,primary)
                finally:end()
        primary=OSError('second None audit is deliberately absent')
        begin(fail_none_at=2,primary=primary)
        try:
            with self.assertRaises(OSError) as caught:self.before(self.f)
            self.assertIs(caught.exception,primary)
        finally:end()
        begin(fail_none_at=2,primary=primary)
        try:self.after(self.f);self.assertEqual(_GATE['none_calls'],1)
        finally:end()


if __name__=='__main__':unittest.main()
