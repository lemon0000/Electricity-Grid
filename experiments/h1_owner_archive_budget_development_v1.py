"""Conditional logical-byte envelopes for the existing H1 owner and holder.

DRAFT_NONAUTHORITATIVE. These are arithmetic bounds on accepted serialized
content, not disk quotas, SQLite bounds, reservations or execution authority.
"""
from src.rq2_joint_deliverability_boundary_v1.prefix_handoff import _encoded

KINDS = ('attempt', 'intent', 'outcome', 'witness', 'episode_terminal')
PIN = 'f'*64


def _positive(value, name):
    if type(value) is not int or value < 1:
        raise ValueError(name+' must be a positive built-in integer')
    return value


def base64_bytes(raw_bytes):
    if type(raw_bytes) is not int or raw_bytes < 0:
        raise ValueError('nonnegative built-in byte count required')
    return 4*((raw_bytes+2)//3)


def packed_group_bound(*, max_stages, max_record_bytes, max_total_bytes):
    """One selector's list, with independently applied count/record/total caps."""
    for name, value in locals().copy().items():
        _positive(value, name)
    raw = min(max_total_bytes, max_stages*max_record_bytes)
    records = min(max_stages, raw)  # Every record is nonempty.
    encoded = 4*((raw+2*records)//3)
    return dict(max_records=records, raw_bytes=raw, base64_bytes=encoded,
        # Each string adds two quotes and all but one add a comma; brackets add 2.
        json_list_bytes=encoded+3*records+1, exact_tight_maximum_claimed=False)


def holder_metadata_bytes(sequence, kind):
    _positive(sequence, 'sequence')
    if sequence > 999999 or kind not in KINDS:
        raise ValueError('existing holder ordinal/kind domain required')
    return len(_encoded(dict(sequence=sequence, previous=PIN, ticket=dict(
        store_identity=PIN, sequence=sequence, before_heads=[PIN, PIN], kind=kind, body=''))))


def holder_logical_bound(*, max_tickets, max_ticket_bytes, max_total_ticket_bytes):
    """Use the holder's own header limits; owner limits need not be equal.

    The sum is file content only: ticket wrappers, a <=4096-byte accepted
    header, and the writer-created one-byte lock. External corruption and
    filesystem allocation are outside this conditional grammar bound.
    """
    _positive(max_tickets, 'max_tickets')
    _positive(max_ticket_bytes, 'max_ticket_bytes')
    _positive(max_total_ticket_bytes, 'max_total_ticket_bytes')
    if max_tickets > 999999:
        raise ValueError('existing six-digit holder ordinal domain required')
    raw = min(max_total_ticket_bytes, max_tickets*max_ticket_bytes)
    overhead = max(holder_metadata_bytes(max_tickets, kind) for kind in KINDS)
    # Metadata grows only at decimal digit boundaries; no earlier sequence has
    # more digits than max_tickets. Every other metadata value has fixed length.
    encoded = 4*((raw+2*max_tickets)//3)
    tickets = encoded+max_tickets*overhead
    return dict(holder_max_tickets=max_tickets, holder_max_ticket_bytes=max_ticket_bytes,
        holder_max_total_ticket_bytes=max_total_ticket_bytes, raw_body_bytes=raw,
        base64_body_bytes_bound=encoded, max_wrapper_overhead_bytes=overhead,
        ticket_file_bytes_bound=tickets, accepted_header_bytes_bound=4096,
        writer_created_lock_bytes=1, logical_content_bytes_bound=tickets+4097,
        includes_filesystem_allocation=False, includes_sqlite_or_journal=False,
        includes_external_checkpoint_or_head_retention=False, resource_admission=False)


def intent_logical_bound(*, lane_ids, source_audit_ascii_cap, max_stages,
                         max_record_bytes, max_total_bytes):
    """An intent envelope for exact JSON source audit and independently capped groups.

    The source audit must be canonical raw-ingress JSON (ensure_ascii=True,
    compact, no newline), with an object at the top level. For an owner-encodable
    JSON value, its UTF8 object representation is no longer than those source
    ASCII bytes. The owner then adds exactly one outer newline. This function
    does not prove input freshness, scientific validity, or that the maximum
    declared packing envelope is attainable by numerical solver reports.
    """
    if (type(lane_ids) is not tuple or not lane_ids
            or any(type(name) is not str or not name or len(name)>128 for name in lane_ids)
            or lane_ids != tuple(sorted(set(lane_ids)))):
        raise ValueError('existing sorted unique bounded lane identities required')
    _positive(source_audit_ascii_cap, 'source_audit_ascii_cap')
    if source_audit_ascii_cap < 2:
        raise ValueError('a source audit JSON object needs at least two bytes')
    group = packed_group_bound(max_stages=max_stages, max_record_bytes=max_record_bytes,
                               max_total_bytes=max_total_bytes)
    skeleton = dict(hour=191, terminal=PIN, key=PIN, source_audit={},
        records=dict(reference=[], actual={name: [] for name in lane_ids}),
        alternate=False, before_heads=[PIN, PIN])
    base = len(_encoded(skeleton))
    count = 1+len(lane_ids)
    bound = base+(source_audit_ascii_cap-2)+count*(group['json_list_bytes']-2)
    return dict(lane_ids=list(lane_ids), selector_groups=count,
        source_audit_ascii_cap=source_audit_ascii_cap,
        source_cap_proof_condition='exact accepted source cap and source-to-owner JSON encoding relation',
        empty_intent_bytes=base, per_selector_group=group, intent_body_bytes_bound=bound,
        all_relative_hours_0_through_191=True, includes_one_outer_newline=True,
        numerical_report_attainability_proved=False, resource_admission=False)


def successful_event_counts(hours, *, alternate_witnesses=0):
    if type(hours) is not int or not 1 <= hours <= 192:
        raise ValueError('successful business horizon must be 1..192')
    if type(alternate_witnesses) is not int or alternate_witnesses < 0:
        raise ValueError('nonnegative built-in alternate witness count required')
    return dict(hours=hours, alternate_witnesses=alternate_witnesses,
        bootstrap_intent_and_outcome=2, later_attempts=hours-1,
        later_intents_and_outcomes=2*(hours-1), alternate_events=2*alternate_witnesses,
        events_after_last_paired=3*hours-1+2*alternate_witnesses,
        additional_terminal_calls=1, additional_terminal_events=1,
        events_after_terminal=3*hours+2*alternate_witnesses,
        alternate_count_enforced_by_this_arithmetic=False)
