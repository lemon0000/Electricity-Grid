"""Bounded read-only reconstruction of two frozen metadata import orders."""
import sys
_PROGRESS=[]

def collect(mode):
    driver_path='D:/CUHKSZ/Research Project/electricity-grid/results/tables/staged_rts24_saved_fresh_aoc_v6_non_authoritative/driver.py'
    context=dict(__name__='_origin_frozen_driver',__file__=driver_path)
    with open(driver_path,'rb') as source:raw=source.read()
    exec(compile(raw,driver_path,'exec'),context)
    if mode=='size':exec('import io,tokenize,subprocess,zlib',context)
    context['previous']()
    if mode=='size':context['migration']()
    parent=context['load'](context['PARENT']);parent.source()
    if mode=='register':
        context['read'](context['OUT']/'size_admission.json');context['migration']()
        helpers=[context[n] for n in ('CORE','HELPER','PROBE','PARENT')]+[context['Path'](driver_path)]
        context['canonical']({str(p):context['base64'].b64encode(p.read_bytes()).decode() for p in helpers})
    code=parent.transport()
    if mode=='register':
        argv=[context['EXE'],'-P','-B','-s','-S','-c',code.decode(),'--pre-entry-lease',str(context['OUT']/'probe_import_discovery.plan.json'),'0'*64]
        len(sys.modules['subprocess'].list2cmdline(argv).encode('utf-16-le'))//2
        context['reuse_evidence']()
    origins,_=context['runtime_leaves']()
    expected=context['read'](context['OUT']/'size_admission.json')['conditional_runtime_origins']
    result=dict(mode=mode,origins=origins,matches_saved_size=origins==expected,
        added=sorted(set(origins)-set(expected)),removed=sorted(set(expected)-set(origins)),
        changed={n:dict(before=expected[n],after=origins[n]) for n in set(origins)&set(expected) if origins[n]!=expected[n]})
    sys.stdout.buffer.write(context['canonical'](result))

def inspect():
    import base64
    from hashlib import sha256
    import importlib.util
    import json
    from pathlib import Path
    import time
    started=time.perf_counter();out=Path(__file__).absolute().parent;root=out.parents[2]
    old=root/'results/tables/staged_rts24_saved_fresh_aoc_v6_non_authoritative'
    target=out/'inspection.json';assert {p.name for p in out.iterdir()}=={'origin_probe.py'}
    def read(p):return json.loads(p.read_bytes())
    def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
    prior_path=out.parent/'staged_rts24_saved_fresh_origin_order_v1_non_authoritative/inspection.json'
    prior=read(prior_path);assert prior['accepted'] and prior['all_cumulative_total_seconds']==671.9810072000212 and prior['prior_not_accepted_count']==26
    for p,v in prior['input_pins'].items():assert pin(Path(p).read_bytes())==v,p
    cp=read(old/'checkpoint.json');assert cp['accepted'] and cp['diagnostic_accepted'] is False and cp['prior_not_accepted_count']==26
    assert cp['all_cumulative_total_seconds']==670.4226138000188
    assert {p.name for p in old.iterdir()}==set(cp['root_map_before_checkpoint'])|{'checkpoint.json'}
    inputs={**read(old/'size_admission.json')['input_pins'],**{str(old/n):v for n,v in cp['root_map_before_checkpoint'].items()},str(old/'checkpoint.json'):pin((old/'checkpoint.json').read_bytes())}
    inputs.update(prior['input_pins']);inputs[str(prior_path)]=pin(prior_path.read_bytes())
    scope=root/'docs/plan/staged_deliverability_c_saved_fresh_origin_order_scope_v2.md'
    capture=root/'results/tables/staged_rts24_saved_fresh_machinery_transition_v1_non_authoritative/checks_01/capture.py'
    for p in (Path(__file__).absolute(),scope,capture):inputs[str(p)]=pin(p.read_bytes())
    for p,v in inputs.items():assert pin(Path(p).read_bytes())==v,p
    spec=importlib.util.spec_from_file_location('_origin_capture',capture);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    observations=[];accepted=True
    for mode in ('size','register'):
        rc,stdout,stderr,error,obs=module.bounded(['D:/Miniconda3/envs/compute/python.exe','-B','-s',str(Path(__file__).absolute()),mode],min(2,5.5-(time.perf_counter()-started)))
        drain=obs['bounded_drain'];ok=rc==0 and error is None and obs['handle_closed'] and not obs['cleanup'] and drain['pipes_closed'] and drain['reader_threads_terminal'] and not drain['cleanup'] and not drain['reader_errors'] and not drain['killed'] and not drain['stdout_truncated'] and not drain['stderr_truncated']
        observations.append(dict(mode=mode,accepted=ok,returncode=rc,error=error,observation=obs,stdout_pin=pin(stdout),stderr_pin=pin(stderr),stdout_raw_base64=base64.b64encode(stdout).decode(),stderr_raw_base64=base64.b64encode(stderr).decode(),result=json.loads(stdout) if ok else None))
        _PROGRESS[:]=observations
        accepted=accepted and ok
        if not ok:break
    for p,v in inputs.items():assert pin(Path(p).read_bytes())==v,p
    charge=time.perf_counter()-started;accepted=accepted and charge<=6
    cumulative={**prior['all_cumulative_charged_seconds'],'static':prior['all_cumulative_charged_seconds']['static']+charge}
    record=dict(accepted=accepted,authority='DRAFT_NONAUTHORITATIVE',kind='static',charged_seconds=charge,cap_seconds=6,input_pins=inputs,observations=observations,
        all_cumulative_charged_seconds=cumulative,all_cumulative_total_seconds=sum(cumulative.values()),prior_not_accepted_count=26+(not accepted),
        metadata_only=True,cold_children=0,entry_exec=0,actual_F=False,run_authority=False,formal_result=False,resource_admission=False)
    raw=json.dumps(record,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('ascii');assert len(raw)+Path(__file__).stat().st_size<=1024**2
    with target.open('xb') as stream:stream.write(raw)
    print(json.dumps(dict(accepted=accepted,charge=charge,total=sum(cumulative.values()),summaries=[dict(mode=o['mode'],matches_saved_size=o['result']['matches_saved_size'],added=o['result']['added'],removed=o['result']['removed'],changed=list(o['result']['changed'])) for o in observations if o['result'] is not None])))
    if not accepted:raise SystemExit(1)

if __name__=='__main__':
    if sys.argv[1:] in (['size'],['register']):collect(sys.argv[1])
    elif sys.argv[1:]==['inspect']:
        import time
        failure_started=time.perf_counter()
        try:inspect()
        except BaseException as error:
            import json
            from pathlib import Path
            out=Path(__file__).absolute().parent
            if not (out/'inspection.json').exists():
                cp=json.loads((out.parent/'staged_rts24_saved_fresh_origin_order_v1_non_authoritative/inspection.json').read_bytes())
                charge=time.perf_counter()-failure_started;cumulative={**cp['all_cumulative_charged_seconds'],'static':cp['all_cumulative_charged_seconds']['static']+charge}
                record=dict(accepted=False,kind='static',charged_seconds=charge,cap_seconds=6,error=type(error).__name__+':'+str(error)[:500],observations=_PROGRESS,
                    all_cumulative_charged_seconds=cumulative,all_cumulative_total_seconds=sum(cumulative.values()),prior_not_accepted_count=27,
                    authority='DRAFT_NONAUTHORITATIVE',actual_F=False,run_authority=False,formal_result=False,resource_admission=False)
                with (out/'inspection_failure.json').open('xb') as f:f.write(json.dumps(record,sort_keys=True,separators=(',',':')).encode('ascii'))
            raise
    else:raise SystemExit('metadata order inspection only')
