"""Draft guard-v3 outer protocol; original kernel and inner Job semantics retained."""
import json
from src import staged_rts24_p2_package_check_v1 as old
from src import staged_rts24_p2_outer_observation_v2 as parent
from src import staged_rts24_p2_outer_v1 as outer

codec, require, CAPS = old.codec, old.require, old.CAPS
completion, keys, same = old.completion, old.keys, old.same
journal_references, point_references = old.journal_references, old.point_references
contract_references, events_check = old.contract_references, old.events_check
process_ok, query_identity = old.process_ok, old.query_identity
EXCLUDED, PACKET_PINS, ACTUAL = old.EXCLUDED, old.PACKET_PINS, old.ACTUAL
PurePosixPath = old.PurePosixPath
FRESH_LIMITS, digest = old.FRESH_LIMITS, old.digest

def protocol(snapshot,context,reg,packet,process_record,numeric,terminal_rejection=False):
    raw,pins=snapshot['raw'],snapshot['pins'];completion_pin=completion(raw,pins)
    require(not any(n.endswith('.pending') or n.rsplit('/',1)[-1].endswith('_failure.json') and not (numeric and n=='numeric_failure.json')
        or n=='journal/failure.json' for n in raw),'failure/pending cannot close protocol')
    report=codec.parse(raw['report.json']);keys(report,'authority package_complete failure point_attempts_reserved points_imported native_run_invoked_observed native_run_returned_observed fresh_launches metrics contracts full_139_executed actual_accepted_slots resource_admission overall_performance_review_complete fx_temporal_backing formal_result')
    require(report['authority']=='DRAFT_NONAUTHORITATIVE' and all(report[n] is False for n in ('resource_admission','overall_performance_review_complete','fx_temporal_backing','formal_result')),'worker report authority differs')
    count,imported=report['point_attempts_reserved'],report['points_imported']
    require(type(count) is type(imported) is int and 1<=count<=319 and imported==count-int(numeric),'point counts differ')
    complete=not (numeric or terminal_rejection)
    require(report['package_complete'] is complete and report['full_139_executed'] is complete,'worker completion claims differ')
    require(type(report['fresh_launches']) is int and report['fresh_launches']==1,'fresh launch count differs')
    if numeric:
        keys(report['failure'],'stage type message')
        require(type(report['failure']['type']) is type(report['failure']['message']) is str
            and report['failure']['stage'] in ('reference_numeric','actual_numeric','contract_numeric'),'numeric failure stage differs')
        require('numeric_failure.json' in raw,'numeric failure record missing')
        failure=codec.parse(raw['numeric_failure.json']);keys(failure,'stage type message infeasibility_inferred');require(failure['infeasibility_inferred'] is False
            and same({k:v for k,v in failure.items() if k!='infeasibility_inferred'},report['failure']),'numeric failure report differs')
        role=packet['schedule'][count-1];stage='contract_numeric' if role['section']=='contract' else 'actual_numeric' if role['role']=='actual_P' else 'reference_numeric'
        require(report['failure']['stage']==stage,'numeric failure slot differs')
    elif terminal_rejection:require(count==imported<=41 and report['failure'] is None and 'numeric_failure.json' not in raw,'terminal rejection counts differ')
    else:require(count==imported==319 and report['failure'] is None,'success point count differs')
    launcher=codec.parse(raw['launcher_start.json']);require(same(launcher,dict(limits=CAPS,package='staged_rts24_P2_v1',registration_sha=context['registration']['pin']['sha256'])),'launcher start differs')
    require(same(codec.parse(raw['launcher.json']),process_record),'saved outer supervisor record differs')
    start=codec.parse(raw['start.json']);keys(start,'authority pins preserved packet_pin max_point_attempts registration_sha native_user_authority')
    require(start['authority']=='DRAFT_NONAUTHORITATIVE' and same(start['pins'],reg['pins']) and same(start['preserved'],reg['preserved'])
        and start['packet_pin']==PACKET_PINS['packet.json'] and type(start['max_point_attempts']) is int and start['max_point_attempts']==319
        and start['registration_sha']==context['registration']['pin']['sha256']
        and start['native_user_authority']=='external_explicit_user_instruction_not_inferred_from_files','worker start differs')
    states,state,hour_events,committed=journal_references(raw,packet['schedule'],report,reg,packet,terminal_rejection)
    members={(m['pid'],m['creation_filetime']) for m in process_record['quiescence_witness']['member_identities']}
    points,inner_members,invoked,returned=point_references(raw,pins,packet['schedule'],count,imported,reg,context['registration']['pin']['sha256'],states,members)
    require(type(report['native_run_invoked_observed']) is type(report['native_run_returned_observed']) is int
        and report['native_run_invoked_observed']==invoked and report['native_run_returned_observed']==returned,'observed native run counts differ')
    prepared_rows=[row['prepared'] for row in state['records']]
    if report['failure'] and report['failure']['stage']=='actual_numeric':prepared_rows.append(report['metrics']['unaccepted_attempt']['prepared'])
    for prepared in prepared_rows:
        hour=prepared['observation']['hour'];slots=[r for r in packet['schedule'] if r['section']=='actual' and r['hour']==hour]
        actual_slot=slots[-1];by_role={r['role']:points[r['ordinal']]['evidence'] for r in slots[:-1]}
        require(same(prepared['evidence'],dict(reference=by_role['reference_base_P0'],raw=by_role.get('reference_raw_need'),
            lower=by_role['recovery_min_meter'],upper=by_role['recovery_max_meter']))
            and same(prepared['actual_outage'],actual_slot['outage']),'prepared reference point graph differs')
    for i,row in enumerate(state['records']):
        if row['actual'] is None:require(terminal_rejection and count==ACTUAL[i]-1,'missing committed actual point')
        else:require(ACTUAL[i] in points and same(row['actual'],points[ACTUAL[i]]['evidence']),'committed state actual point differs')
    rows=codec.parse(raw['contract_rows.json']);require(same(rows,report['contracts']),'saved contract/report differ');contract_references(rows,packet['schedule'],points,imported)
    require(not complete or len(states)==10 and len(rows)==138,'success state/contract counts differ')
    fresh_members=process_ok(codec.parse(raw['fresh_process.json']),FRESH_LIMITS,members)
    require(inner_members.isdisjoint(fresh_members),'fresh and point Job identities overlap');inner_members|=fresh_members
    require((process_record['owner_pid'],process_record['owner_creation_filetime']) not in inner_members,'outer owner appears in internal Job')
    residual=members-inner_members
    require((process_record['owner_pid'],process_record['owner_creation_filetime']) in residual
        and len(members)==len(inner_members)+len(residual),'outer Job history partition differs')
    fresh=codec.parse(raw['fresh.json']);keys(fresh,'metrics solver_calls');require(type(fresh['solver_calls']) is int and fresh['solver_calls']==0 and same(fresh['metrics'],report['metrics']),'fresh metrics differ')
    for name in ('worker_observations.json','fresh_observations.json'):require(codec.parse(raw[name])['allow_native'] is False,'worker/fresh observations mode differs')
    events_check(raw['events.jsonl'],packet['schedule'],count,imported,len(states),len(rows),complete,hour_events)
    root_files=EXCLUDED|{'outer_context.json','outer_startup.json','launcher_start.json','start.json','report.json','events.jsonl','contract_rows.json','trusted_binding.json',
        'fresh.json','fresh_process.json','fresh_observations.json','fresh.stdout.log','fresh.stderr.log','worker_observations.json'}
    if numeric:root_files.add('numeric_failure.json')
    require({n for n in raw if '/' not in n}==root_files,'unknown or missing root file')
    require(all('/' not in n or n.startswith(('points/','journal/','trusted_prefixes/')) for n in raw),'unknown top-level tree')
    require({n for n in raw if n.startswith('journal/') and not n.startswith('journal/objects/')}=={'journal/genesis.json',*{f'journal/entry_{i:06d}.json' for i in range(1,committed+2)}},'unknown journal file')
    wanted_dirs={'.'}
    for n in raw:
        wanted_dirs.update(p.as_posix() for p in PurePosixPath(n).parents if p.as_posix()!='.')
    require(set(snapshot['directories'])==wanted_dirs,'unknown empty directory')
    require(len(pins)==process_record['terminal_files']+1
        and sum(v['bytes'] for v in pins.values())==process_record['terminal_bytes']+len(raw['launcher.json']),'outer terminal inventory accounting differs')
    return dict(completion_core_pin=completion_pin,report_pin=pins['report.json'],point_reference_count=count,
        points_imported=imported,contract_row_reference_count=len(rows),actual_state_reference_count=len(states),committed_hour_entries=committed,
        outer_job_history_partition_verified=True,outer_member_count=len(members),known_inner_member_count=len(inner_members),
        outer_residual_member_count=len(residual),outer_residual_member_identities=[dict(pid=p,creation_filetime=t) for p,t in sorted(residual)],
        unverified_worker_claims=dict(package_complete=report['package_complete'],full_139_executed=report['full_139_executed']))


def inspect_package(held_context,expected_context_sha,process_record,held_startup,hook=None):
    require(type(held_context) is bytes and old.pin(held_context)['sha256']==expected_context_sha,'held package context SHA differs')
    context=codec.parse(held_context);require(outer.validate_context(context)==held_context,'outer package context differs')
    base=context['kernel_context'];startup_record=base['startup']
    assessment=parent.assess_process(process_record,CAPS);record=assessment['process_snapshot']
    result=dict(authority='DRAFT_NONAUTHORITATIVE',context_sha=expected_context_sha,inspection_status='inspection_prohibited',
        process_snapshot=record,parent_supplied_startup_record=json.loads(codec.canonical(startup_record)),
        mechanical_package_integrity=False,outer_process_verified=assessment['inspection_permitted'],inner_process_records_verified=False,
        completion_core_verified=False,full_inventory_verified=False,journal_reference_chain_verified=False,fresh_worker_protocol_closed=False,
        inventory=None,inventory_directories=None,inventory_sha=None,inventory_files=None,inventory_bytes=None,protocol_error=None,
        completion_core_pin=None,report_pin=None,point_reference_count=None,points_imported=None,contract_row_reference_count=None,
        actual_state_reference_count=None,committed_hour_entries=None,unverified_worker_claims=None,source_freshness_selected_only=False,
        outer_job_history_partition_verified=False,outer_member_count=None,known_inner_member_count=None,outer_residual_member_count=None,
        outer_residual_member_identities=None,process_tree_attribution_independently_verified=False,
        actual_spawn_argv_verified=False,full_runtime_closure_verified=False,typed_values_validated=False,startup_record_schema_verified=False,actual_os_commandline_independently_verified=False,
        scientific_audit_replayed=False,scientific_evidence_adopted=False,full_139_independently_verified=False,
        fx_temporal_backing=False,resource_admission=False,formal_result=False,official_verdict=None,receipt=None,seal=None)
    if assessment['ownership_status']!='quiet_verified':return result
    inputs,reg,packet=outer.read_inputs(context)
    outer.check_startup(held_startup,context,expected_context_sha,record)
    result['startup_record_schema_verified']=True
    worker=codec.directory_chain(old.absolute(base['worker_root']));par=codec.directory_chain(old.absolute(base['parent_root']))
    require(not worker.resolve().is_relative_to(par.resolve()) and not par.resolve().is_relative_to(worker.resolve()),'physical parent and worker overlap')
    try:before=old.inventory(worker)
    except old.InventoryLimit as exc:result['protocol_error']=dict(type=type(exc).__name__,message=str(exc));return result
    require(before['raw'].get('outer_context.json')==held_context and before['raw'].get('outer_startup.json')==held_startup,'held outer/startup bytes differ')
    details=None;diagnostic=(record['exit_code']==2 and record['stop_reason']=='child_exit_nonzero' and record['monitor_error'] is record['cleanup_error'] is None and assessment['proposal_caps_satisfied'])
    terminal_rejection=False
    if assessment['inspection_permitted'] or diagnostic:
        try:
            saved_report=codec.parse(before['raw']['report.json']);terminal_rejection=diagnostic and saved_report['failure'] is None
            require(before['raw'].get('outer_context.json')==held_context and before['raw'].get('outer_startup.json')==held_startup,'held outer/startup bytes differ')
            details=protocol(before,base,reg,packet,record,diagnostic and not terminal_rejection,terminal_rejection)
        except (ValueError,KeyError,TypeError,IndexError,RecursionError) as exc:result['protocol_error']=dict(type=type(exc).__name__,message=str(exc)[:256])
    if hook is not None:hook('before_bookend',worker)
    after=old.inventory(worker);require(before==after,'worker inventory bookend differs')
    again,_,_=outer.read_inputs(context);require(inputs==again,'package input bookend differs')
    result.update(full_inventory_verified=True,inventory=before['pins'],inventory_directories=before['directories'],inventory_sha=digest(before['pins']),inventory_files=len(before['pins']),
        inventory_bytes=sum(v['bytes'] for v in before['pins'].values()),source_freshness_selected_only=True,inspection_status='failure_inventory_captured')
    if details is not None:
        result.update(details,inspection_status='terminal_diagnostic_closed' if terminal_rejection else 'numeric_diagnostic_closed' if diagnostic else 'success_protocol_closed',
            mechanical_package_integrity=True,inner_process_records_verified=True,completion_core_verified=True,
            journal_reference_chain_verified=True,fresh_worker_protocol_closed=True)
    return result
