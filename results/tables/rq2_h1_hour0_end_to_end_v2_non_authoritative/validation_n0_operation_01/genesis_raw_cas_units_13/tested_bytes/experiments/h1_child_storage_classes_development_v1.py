"""Conditional retained-child storage envelopes for the exact saved parent.

Pure arithmetic only. No filesystem admission, execution gate or native route.
The bound relies on the parent's stop-on-first-error path and fixed raw guard.
"""
from experiments import h1_attested_source_parent_development_v1 as parent

SCHEMA = 'h1_child_storage_classes_development_v1'


def envelope(hours, stages, *, allocation_quantum=None):
    if type(hours) is not int or not 1 <= hours <= 192:
        raise ValueError('exact bounded hour count required')
    original = parent.child_storage_bound(stages)
    if allocation_quantum is not None and (
            type(allocation_quantum) is not int or allocation_quantum < 1
            or allocation_quantum > 65536 or allocation_quantum & (allocation_quantum-1)):
        raise ValueError('explicit power-of-two allocation quantum up to 65536 required')
    io = parent.io
    hour = parent.hour_api
    grammar = hour.guard.grammar
    accepted_raw = grammar.prior.bound(grammar.grammar())
    retained_raw = io.RAW_CAP
    if not 0 < accepted_raw <= retained_raw:
        raise ValueError('accepted raw bound exceeds ingress envelope')
    # Distinct regular files: S raw, S mappings, one projection, all others metadata.
    metadata_files = original['files'] - 2*stages - 1
    nonraw = metadata_files*io.META_CAP + stages*hour.MAPPING_CAP + hour.PROJECTION_CAP
    if nonraw + stages*retained_raw != original['logical_bytes']:
        raise ValueError('legacy child storage topology changed')
    slots = hours*stages
    successful = hours*nonraw + slots*accepted_raw
    # Even if only the final attempted raw is large, all preceding files remain.
    any_stop = successful + retained_raw - accepted_raw
    result = dict(schema=SCHEMA, hours=hours, stages_per_hour=stages, stage_slots=slots,
        accepted_raw_cap=accepted_raw, retained_raw_cap=retained_raw,
        nonraw_bytes_per_child=nonraw, metadata_files_per_child=metadata_files,
        complete_success_logical_bytes=successful, first_stop_logical_bytes=any_stop,
        retained_children_logical_bytes=max(successful, any_stop),
        original_all_raw_caps_logical_bytes=hours*original['logical_bytes'],
        files=hours*original['files'], directories=hours*original['directories'],
        allocation_quantum=allocation_quantum, file_content_allocation_bytes=None,
        conditional_on_exact_saved_parent=True, parent_storage_included=False,
        job_storage_included=False, filesystem_metadata_included=False,
        filesystem_allocation_bound_proven=False, resource_admission=False,
        formal_execution_ready=False, formal_result=False)
    if allocation_quantum is not None:
        def rounded(size):
            return ((size+allocation_quantum-1)//allocation_quantum)*allocation_quantum
        overhead = hours*(metadata_files*rounded(io.META_CAP)
            + stages*rounded(hour.MAPPING_CAP)+rounded(hour.PROJECTION_CAP))
        result['file_content_allocation_bytes'] = (
            overhead+(slots-1)*rounded(accepted_raw)+rounded(retained_raw))
    return result
