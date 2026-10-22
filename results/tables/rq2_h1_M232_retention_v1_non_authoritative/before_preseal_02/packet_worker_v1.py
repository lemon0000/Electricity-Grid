"""One real-source M232 origin packet, without a Reader, model or solve."""
from dataclasses import fields
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import time
import traceback

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
sys.path.insert(0,str(REPO))


def pin(path):return sha256(Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(Path(path).read_bytes())


def main():
    out=Path(sys.argv[1]).resolve()
    if out.parent!=HERE or not out.is_dir():raise ValueError('exclusive registered output required')
    started=time.perf_counter();times={};report={};error=None
    opened={};audit_errors=[];auditing=[False]
    protected=(REPO/'data',REPO/'configs')
    def in_repo_input(value):
        if not isinstance(value,(str,bytes,os.PathLike)):return None
        path=Path(os.path.abspath(os.fsdecode(value)))
        return path if any(path.is_relative_to(root) for root in protected) else None
    def audit(event,values):
        if auditing[0]:return
        auditing[0]=True
        try:
            if event=='open':
                name,mode,flags=values
                if not isinstance(name,(str,bytes,os.PathLike)):return
                path=Path(os.path.abspath(os.fsdecode(name)))
                writing=(isinstance(mode,str) and any(c in mode for c in 'wax+')) or (
                    isinstance(flags,int) and bool(flags&(os.O_WRONLY|os.O_RDWR|os.O_APPEND|os.O_CREAT|os.O_TRUNC)))
                if writing and not path.is_relative_to(out):raise RuntimeError('diagnostic write outside owned output denied')
                source=in_repo_input(name)
                if not writing and source is not None and source.is_file() and str(source) not in opened:
                    if len(opened)>=512:raise RuntimeError('input audit distinct-file cap')
                    opened[str(source)]=pin(source)
            elif event in ('os.mkdir','os.remove','os.rmdir','os.chmod','os.utime','os.truncate'):
                if not Path(os.path.abspath(os.fsdecode(values[0]))).is_relative_to(out):
                    raise RuntimeError('diagnostic input mutation denied')
            elif event in ('os.rename','os.link','os.symlink'):
                if any(not Path(os.path.abspath(os.fsdecode(value))).is_relative_to(out) for value in values[:2]):
                    raise RuntimeError('diagnostic input mutation denied')
        except BaseException as caught:
            audit_errors.append(type(caught).__name__+': '+str(caught)[:512]);raise
        finally:auditing[0]=False
    sys.addaudithook(audit)
    def progress(phase):
        (out/'activity.json').write_text(json.dumps(dict(phase=phase,elapsed_seconds=time.perf_counter()-started)),encoding='utf-8')
    try:
        progress('import')
        from src.rq2_joint_deliverability_boundary_v1 import normal_h1_resource_shape as shape
        request=load(HERE.parent/'rq2_normal_h1_shape_v1_non_authoritative/request.json')
        declaration=shape.binding.H1SourceDeclaration(**request['declaration'])
        assert pin(request['config_path'])==declaration.config_sha256
        assert Path(request['upstream_root']).is_relative_to(REPO/'data')
        slots=((type(shape.SolverFactory),'__call__'),(shape.current,'solve_current'),
            (shape.current.native,'run_h1_chain'),(shape.current.native.capture,'solve_once'),
            (shape.current.native.capture.provenance.adapter,'create_solver'))
        original_slots=tuple(getattr(owner,name) for owner,name in slots)
        with shape.solver_calls_forbidden() as denied:
            # Capture the diagnostic's active deny adapter in v3's finite guard;
            # no source prepare/replay or authority-bearing object is created.
            from experiments import h1_phase_historical_batch_development_v3 as source_v3
            progress('load_pinned_origin')
            tick=time.perf_counter()
            receipt=shape.binding.load_pinned_current(declaration,request['upstream_root'],config_path=request['config_path'])
            times['load_pinned_current']=time.perf_counter()-tick
            assert type(receipt) is shape.binding.H1PinnedObservation and receipt.declaration==declaration
            assert receipt.identity==request['expected_source_identity']
            assert receipt.network.identity==request['expected_network_identity']
            progress('assemble_origin')
            tick=time.perf_counter()
            packet=shape.current.source.assemble_current_normal(receipt.network,receipt.row,receipt.raw_workload,
                relative_hour=0,dc_bus=request['dc_bus'],source_time_basis=receipt.source_time_basis)
            times['assemble_current_normal']=time.perf_counter()-tick
            order=shape.model_api.stage_order(packet.inputs)
            assert len(order)==request['expected_stage_count']==232 and packet.relative_hour==0
            progress('remember_and_validate')
            packets={};tick=time.perf_counter()
            size=source_v3._remember_packet(packets,packet,1)
            times['remember_one_actual_packet']=time.perf_counter()-tick
            tick=time.perf_counter();source_v3._validate_all_packets(packets,1)
            times['validate_one_actual_packet']=time.perf_counter()-tick
            component={}
            tick=time.perf_counter()
            for field in fields(packet):component[field.name]=source_v3.retained_size(getattr(packet,field.name))
            times['nine_field_size_diagnostics']=time.perf_counter()-tick
            assert tuple(packets)==(0,) and packets[0][0] is packet
            assert size==source_v3.retained_size(packets[0])
            container_size=source_v3.retained_size(packets)
            assert container_size>=size
            stored_pin=packets[0][1]
            assert stored_pin[:2]==(packet.input_identity,packet.audit_identity)
            progress('source_revalidation')
            tick=time.perf_counter()
            rebuilt=shape.binding.validate_pinned_current(receipt,request['upstream_root'],
                expected_identity=request['expected_source_identity'],config_path=request['config_path'])
            times['source_revalidation']=time.perf_counter()-tick
            assert rebuilt.identity==receipt.identity and denied==[]
            source_audit=json.loads(receipt.audit_payload)
            assert source_audit['source_authenticated'] is False and source_audit['formal_result'] is False
            report=dict(stage_count=len(order),relative_hour=0,source_identity=receipt.identity,
                network_identity=receipt.network.identity,input_identity=packet.input_identity,
                audit_identity=packet.audit_identity,full_nine_field_packet_digest=stored_pin[2],
                source_declaration=request['declaration'],v3_packet_accounting_bytes=size,
                all_packets_container_recursive_bytes=container_size,
                accounting_is_recursive_sys_getsizeof_not_serialized_or_RSS=True,
                accounting_unit_excludes_all_packets_dict_and_key_overhead=True,
                component_sizes_individually_deduplicated=component,
                component_sizes_are_not_additive_unique_footprint=True,
                conditional_equal_footprint_products={str(h):h*size for h in (168,170,192)},
                products_are_H192_upper_bounds=False,products_are_predictions_or_lower_bounds=False,
                other_hours_proved_no_larger_than_origin=False,
                per_Reader_combined_packet_and_selected_frame_cap_bytes=source_v3.MAX_RETAINED_BYTES,
                source_correspondence_rechecked=True,source_authenticated=False,
                accepted_normal_carry=None,selected_frame_or_ChildInspection_created=False,
                timed_child_retention_structure='ChildInspection holds scalar status/head/archive/stored_reports and final Projection bytes, not232 raw reports',
                after_boundary_or_future_carry_created=False,two_Reader_source_executed=False,
                complete_H192_retention_or_all_source_rows_covered=False,
                model_builds=0,Reader_invocations=0,new_normal_jobs=0,selector_calls=0,real_native_solver_calls=0)
        report['solver_deny_hooks_restored']=all(getattr(owner,name) is value for (owner,name),value in zip(slots,original_slots,strict=True))
        assert report['solver_deny_hooks_restored']
    except BaseException:error=traceback.format_exc()[-16000:]
    progress('hash_after')
    changes=[name for name,value in opened.items() if pin(name)!=value]
    accepted=error is None and changes==[] and audit_errors==[]
    report.update(status='DRAFT_NONAUTHORITATIVE',exit_code=0 if accepted else 1,error=error,
        stage_seconds=times,elapsed_seconds=time.perf_counter()-started,
        opened_input_pins_before=opened,opened_input_pins_changed=changes,
        Python_audited_input_files=len(opened),audit_errors=audit_errors,
        audit_is_not_complete_native_or_hostile_FS_protection=True,
        source_successor_adopted=False,resource_admission=False,formal_execution_ready=False,
        full_192_hour_execution_verified=False,formal_result=False)
    with (out/'worker_terminal.json').open('x',encoding='utf-8') as stream:
        json.dump(report,stream,indent=2);stream.write('\n')
    print(json.dumps({name:report.get(name) for name in ('exit_code','elapsed_seconds',
        'v3_packet_accounting_bytes','conditional_equal_footprint_products','error')}),flush=True)
    return report['exit_code']


if __name__=='__main__':raise SystemExit(main())
