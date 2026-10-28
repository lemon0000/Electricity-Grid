"""Quiet-after-exit data replay. This module grants no parent P1 read permission."""
from hashlib import sha256
import json
from pathlib import Path
from types import ModuleType

ROOT=Path(__file__).absolute().parents[1]
CODEC_PIN=(15478, 'aa2309c1e6b815c9d6d688bdf8ba3e314bb696ed7cb63b474f96a3bf176d9723')


def parent_require(value,message):
    if not value:raise ValueError(message)


def parent_codec():
    # The calling parent must bind this source and codec bytes in its scope.
    path=ROOT/'experiments/staged_rts24_saved_fresh_producer_packet_v2.py'
    raw=path.read_bytes()
    parent_require(CODEC_PIN is not None and (len(raw),sha256(raw).hexdigest())==CODEC_PIN,'fixed parent producer codec source required')
    module=ModuleType('_parent_producer_packet');module.__file__=str(path)
    exec(compile(raw,str(path),'exec',dont_inherit=True,optimize=0),vars(module),vars(module));return module


def audit_producer_data(raw,quiet,expected_sources):
    """Validate detached relationships only after the parent's terminal facts.

    quiet is an observation from the retained parent actor, not transferable
    object-graph authority. Physical parent P1 verification is separate.
    """
    keys={'child_exit','process_handle_closed','pipes_closed','reader_threads_terminal','writer_thread_terminal',
        'killed','stdout_truncated','stderr_truncated','reader_errors','cleanup'}
    parent_require(type(quiet) is dict and set(quiet)==keys and type(quiet['child_exit']) is int and quiet['child_exit']==0,
        'closed parent quiet observation required')
    parent_require(all(quiet[key] is True for key in ('process_handle_closed','pipes_closed','reader_threads_terminal','writer_thread_terminal'))
        and all(quiet[key] is False for key in ('killed','stdout_truncated','stderr_truncated'))
        and quiet['reader_errors']==quiet['cleanup']==[],'parent must be quiet before producer replay')
    codec=parent_codec();value=codec.packet_decode(raw,262144)
    false=('parent_independent_P1_verified','external_permission_verified','scientific_evidence_adopted',
        'resource_admission','formal_result','run_authority','actual_F')
    parent_require(set(value)=={'schema','authority','producer','permission','terminal',*false}
        and value['schema']=='staged_saved_F_complete_producer_data_v2' and value['authority']=='DRAFT_NONAUTHORITATIVE'
        and all(value[key] is False for key in false),'closed complete producer data required')
    report=value['producer'];expected_false=('producer_capability_verified','initial_project_state_authenticated',
        'full_runtime_binding_verified','full_P1_content_verified','role_bootstrap','permit_issued','run_authority',
        'resource_admission','scientific_evidence_adopted','formal_result','actual_F')
    parent_require(type(report) is dict and set(report)=={'schema','authority','stages','closed','packet',*expected_false}
        and report['schema']=='staged_saved_F_retained_producer_observation_v3' and report['authority']=='DRAFT_NONAUTHORITATIVE'
        and report['closed'] is True and all(report[key] is False for key in expected_false),'closed detached producer report required')
    packet_raw=codec.packet_unwire(report['packet']);restored=codec.packet_restore(packet_raw)
    packet=restored['packet']
    parent_require(packet['sources']==expected_sources and report['stages']==packet['stages'],'independent source/stage binding differs')
    terminal=value['terminal'];parent_require(type(terminal) is dict and set(terminal)=={'runtime_phase','resource_phase','consumer_state',
        'close_calls','pending','namespace_phase','cleanup_started'} and terminal['runtime_phase']==terminal['resource_phase']=='CLOSED'
        and terminal['consumer_state']=='CONSUMED' and terminal['namespace_phase']=='CONSUMED' and terminal['close_calls']==[1,1]
        and all(type(item) is int for item in terminal['close_calls']) and terminal['pending']==[False,False]
        and all(type(item) is bool for item in terminal['pending']) and terminal['cleanup_started'] is True,'exact producer terminal required')
    permission=value['permission'];permission_false=('external_permission_verified','full_P1_content_verified','independent_root_verified','role_bootstrap',
        'permit_issued','run_authority','F_launch_admitted','actual_F','resource_admission','scientific_evidence_adopted','formal_result')
    parent_require(type(permission) is dict and set(permission)=={'schema','authority','issuer_phase','guard_phase','installed','counters','faults','admission_present',*permission_false}
        and permission['schema']=='staged_saved_F_P1_permission_observation_v1' and permission['authority']=='DRAFT_NONAUTHORITATIVE'
        and all(permission[key] is False for key in permission_false) and permission['admission_present'] is False
        and permission['installed'] is True and permission['issuer_phase']=='RETIRED'
        and permission['guard_phase']=='CLOSED' and permission['faults']==[], 'retired permission observation required')
    counts=permission['counters'];parent_require(type(counts) is dict and set(counts)=={'selected','protected','allowed','writes','processes','mutations','construction_reads','runtime_reads','outside_reads'}
        and all(type(number) is int and 0<=number<=16384 for number in counts.values())
        and all(counts[key]==0 for key in ('writes','processes','mutations','outside_reads')),'clean bounded producer guard counters required')
    # No P1 file is opened here. Map equality never becomes a content claim.
    return dict(schema='staged_saved_F_producer_data_replay_v2',authority='DRAFT_NONAUTHORITATIVE',
        data_relationships_replayed=True,packet_pin=codec.packet_pin(packet_raw),source_files=49,P1_files=683,P1_bytes=2950863,
        physical_parent_P1_reads=0,parent_independent_P1_verified=False,parent_python_graph_attested=False,
        scientific_evidence_adopted=False,resource_admission=False,formal_result=False,run_authority=False,actual_F=False)
