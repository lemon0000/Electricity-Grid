"""Independent stdlib canonical-length bound, never import research code."""
import json

U32, U64, N = 2**32-1, 2**64-1, 1024


def image(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('ascii')


def encoding_bound(value):
    # A finite nonnegative binary64 repr needs at most 17 significant digits,
    # punctuation and a signed three-digit exponent; 32 is conservative.
    if type(value) is float: return 32
    if type(value) is bool: return 5
    if type(value) is list: return 2+max(0, len(value)-1)+sum(encoding_bound(v) for v in value)
    if type(value) is dict:
        return 2+max(0, len(value)-1)+sum(len(image(k))+1+encoding_bound(v) for k, v in value.items())
    return len(image(value))


def main():
    members = [dict(pid=U32, creation_filetime=U64-i) for i in range(N)]
    process = dict(exit_code=U32, stop_reason='\U0001f600'*514, monitor_error='\U0001f600'*514,
        cleanup_error='\U0001f600'*514, job_quiet_confirmed=True, outer_seconds=float.fromhex('0x1.fffffffffffffp+1023'),
        sampled_tree_peak_rss_bytes=U64, rss_observation_available=True, peak_job_commit_bytes=U64, samples=U64,
        terminal_bytes=U64, terminal_files=U64, terminal_reserved_bytes=131072, parent_reserved_bytes=131072,
        terminal_reserved_files=1, parent_reserved_files=1, member_handle_cap=N, owner_pid=U32, owner_creation_filetime=U64,
        quiescence_witness=dict(active_processes=U32, all_handles_signaled=True, complete_inventory=True,
            final_pids=[U32-i for i in range(N)], member_identities=members, observed_unique_member_handles=U32, total_processes=U32))
    claims = dict(inspection_scope='caller_supplied_mechanical', completion_core_sha='f'*64, inventory_sha='f'*64,
        report_sha='f'*64, point_references=319, contract_rows=138, mechanical_package_integrity=True,
        unverified_worker_claims=dict(full_139_executed=True, package_complete=True))
    error = dict(type='\U0001f600'*64, message='\U0001f600'*256)
    parent = dict(authority='DRAFT_NONAUTHORITATIVE', scope='bounded parent process and caller-supplied mechanical observation only',
        context_sha='f'*64, execution_status='failed_or_unknown', ownership_status='quiet_verified', proposal_caps_satisfied=False,
        inspection_permitted=False, process_snapshot=process, inspection_status='returned', inspection_error=error,
        accounting_error=error, worker_accounting_at_entry_verified=False, terminal_record_cap_bytes=131072, max_member_handles=N,
        caller_supplied_mechanical_claims=claims, worker_terminal_status='not_independently_replayed',
        source_freshness_independently_verified=False, scientific_audit_replayed=False, scientific_evidence_adopted=False,
        full_139_independently_verified=False, fx_temporal_backing=False, resource_admission=False, formal_result=False)
    pb, ob = encoding_bound(process), encoding_bound(parent)
    assert len(image(members)) == 61441
    assert len(image(process)) == 92020 and len(image(parent)) == 101064
    assert len(image(process)) <= pb < 131072 and len(image(parent)) <= ob < 131072
    return dict(authority='DRAFT_NONAUTHORITATIVE', oracle='independent_stdlib_finite_field_encoding_bound',
        max_historical_identities_including_owner=N, member_array_bytes=61441,
        maximal_process_example_bytes=len(image(process)), maximal_parent_example_bytes=len(image(parent)),
        process_encoding_upper_bound=pb, parent_encoding_upper_bound=ob,
        each_record_limit_bytes=131072, aggregate_reserve_bytes=262144, aggregate_reserved_files=2,
        real_P2_record_measured=False, full_resource_admission=False, native_calls=0)


if __name__ == '__main__': print(json.dumps(main(), indent=2, sort_keys=True))
