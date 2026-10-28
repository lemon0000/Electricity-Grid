"""LC4 -> LC5: detach before cleanup, bind success data, release live objects."""
from hashlib import sha256
from pathlib import Path

ROOT=Path(__file__).absolute().parents[1]
BEFORE=ROOT/'experiments/staged_rts24_saved_fresh_retained_producer_v4.py'
AFTER=ROOT/'experiments/staged_rts24_saved_fresh_retained_producer_v5.py'
CODEC=ROOT/'experiments/staged_rts24_saved_fresh_producer_packet_v1.py'


def replace(source,before,after,count=1):
    assert source.count(before)==count,(before,source.count(before),count)
    return source.replace(before,after)


def derive():
    source=BEFORE.read_text(encoding='utf8')
    source=replace(source,'import sys\n','import sys\nimport time\n')
    source=replace(source,"'_pending_reentry','_permission_revoke')","'_pending_reentry','_permission_revoke','_packet','_stage_clocks')")
    source=replace(source,"id(producer._pending_reentry),id(producer._permission_revoke))",
        "id(producer._pending_reentry),id(producer._permission_revoke),None if producer._packet is None else pin(producer._packet),tuple(producer._stage_clocks))")
    source=replace(source,'_pending_reentry=None,_permission_revoke=permission_revoke_spec()).items():',
        '_pending_reentry=None,_permission_revoke=permission_revoke_spec(),_packet=None,_stage_clocks=[]).items():')
    source=replace(source,"    commit(producer,_phase='HELD',_busy=False)",
        "    producer._stage_clocks.append(time.monotonic())\n    commit(producer,_phase='HELD',_busy=False)")
    source=replace(source,"    commit(producer,_phase=stage,_busy=False)",
        "    producer._stage_clocks.append(time.monotonic())\n    commit(producer,_phase=stage,_busy=False)")
    source=replace(source,'    before=retained_data_witness(producer)\n    errors=cleanup(producer,None)',
        """    try:
        raw=detached_packet(producer)
        commit(producer,_packet=raw)
    except BaseException as primary:fail(producer,primary)
    before=retained_data_witness(producer)
    errors=cleanup(producer,None)""")
    source=replace(source,"    try:require(retained_data_witness(producer)==before,'retained data changed during close')",
        "    try:require(retained_data_witness(producer)==before and detached_packet(producer)==producer._packet,'retained data changed during close')")
    source=replace(source,"    try:_terminal_reset(producer)\n    except BaseException as error:fail(producer,error,(('close_terminal_reset',error),))",
        """    try:result=detached_report(producer)
    except BaseException as error:fail(producer,error,(('detached_report',error),))
    try:_terminal_reset(producer)
    except BaseException as error:fail(producer,error,(('close_terminal_reset',error),))""")
    source=replace(source,"_permission_revoke=None,_phase='CLOSED',_busy=False)\n    return report(producer)",
        "_permission_revoke=None,_phase='CLOSED',_busy=False)\n    return result")
    source=replace(source,"staged_saved_F_retained_producer_observation_v1","staged_saved_F_retained_producer_observation_v2")
    source=replace(source,"    result=dict(schema='staged_saved_F_retained_producer_observation_v2'",
        "    return detached_report(producer)\n\n\ndef detached_report(producer):\n    result=dict(schema='staged_saved_F_retained_producer_observation_v2'")
    source=replace(source,'        stages=producer._evidence,closed=True,**{name:False for name in FALSE_FIELDS})',
        '        stages=producer._evidence,closed=True,packet=packet_wire(producer._packet),**{name:False for name in FALSE_FIELDS})')
    source=replace(source,"    require(len(canonical(result))<=32768,'bounded producer data report required')",
        "    require(len(canonical(result))<=262144,'bounded producer data report required')")
    source+='''


def detached_packet(producer):
    """Pure retained data only: no entry, disk read or transferred file bytes."""
    require(type(producer._expectation.raw) is bytes and type(producer._context) is bytes
        and type(producer._held.image) is bytes and producer._held.image==producer._expectation.image,
        'exact retained producer bytes required')
    return packet_capture(producer._expectation.raw,producer._context,producer._expectation.image,
        producer._source,producer._held.files,producer._evidence,producer._stage_clocks)
'''
    # Codec is pure stdlib/data code. Appending keeps its functions within the
    # original lifecycle source witness, without an injected exporter callback.
    source+='\n\n'+CODEC.read_text(encoding='utf8')
    return source.encode('utf8')


def current():
    raw=derive();assert AFTER.read_bytes()==raw,'export lifecycle successor differs'
    compile(raw,str(AFTER),'exec',dont_inherit=True,optimize=0)
    return None,dict(schema='staged_saved_F_producer_export_successor_v1',authority='DRAFT_NONAUTHORITATIVE',
        source_pin=dict(bytes=len(raw),sha256=sha256(raw).hexdigest()),
        export='input_metadata_pins_and_53_file_derived_expectation_context',P1_raw_content_exported=False,
        actual_P1_read=False,parent_read_authorized=False,external_authorization_implemented=False,
        run_authority=False,resource_admission=False,formal_result=False,actual_F=False)


if __name__=='__main__':
    raw=derive();compile(raw,str(AFTER),'exec',dont_inherit=True,optimize=0)
    with AFTER.open('xb') as stream:stream.write(raw)
