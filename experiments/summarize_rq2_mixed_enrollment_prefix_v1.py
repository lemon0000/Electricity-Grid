"""Pure mechanism diagnostics of an owned paired cursor, not archive validation."""
from fractions import Fraction as Q
from hashlib import sha256
from pathlib import Path

from experiments import export_rq2_continuous_capacity_diagnostics_v1 as business_diagnostics
from src.rq2_joint_deliverability_boundary_v1 import scale_hourly_zero_face_transaction as tx
from src.rq2_joint_deliverability_boundary_v1 import debt_cohorts
from src.rq2_joint_deliverability_boundary_v1 import capacity_policy


def implementation_identity():
    root = Path(__file__).resolve().parents[1]
    dependencies = set(business_diagnostics.DEPENDENCIES) | {
        Path(debt_cohorts.__file__).resolve().relative_to(root).as_posix(),
        Path(__file__).resolve().relative_to(root).as_posix()}
    return tx.legacy._identity(tx._implementation(), tuple(
        (name, sha256((root/name).read_bytes()).hexdigest()) for name in sorted(dependencies)))


def summarize_cursor(cursor, declared_source_hours, *, enrollment_source_hours, expected_cursor_identity):
    """Project only committed business history; an attempted candidate is not input.

    The caller supplies the planned window and cursor pin. These declarations
    do not authenticate a source, historical dispatch archives or a risk support.
    """
    if type(cursor) is not tx.ArmCursor:
        raise ValueError('owned paired ArmCursor required, not a business candidate')
    if (type(expected_cursor_identity) is not str or len(expected_cursor_identity) != 64
            or any(c not in '0123456789abcdef' for c in expected_cursor_identity)):
        raise ValueError('external lowercase SHA256 cursor identity required')
    implementation = implementation_identity()
    if cursor.identity != expected_cursor_identity or cursor.implementation != tx._implementation():
        raise ValueError('paired cursor identity or implementation mismatch')
    hours = declared_source_hours
    if (type(hours) is not tuple or not hours
            or any(type(h) is not int or h < 0 for h in hours)
            or any(b != a+1 for a, b in zip(hours, hours[1:]))):
        raise ValueError('explicit nonempty contiguous source hours required')
    enrolled = enrollment_source_hours
    if (type(enrolled) is not tuple or not enrolled
            or any(type(h) is not int for h in enrolled)
            or enrolled != hours[:len(enrolled)]):
        raise ValueError('enrollment must be an explicit nonempty prefix of the declared window')
    business = cursor.business
    if (type(business) is not capacity_policy.CapacityPolicyCursor
            or type(business.spec) is not capacity_policy.CapacityPolicy or business.spec.arm_id not in tx.ARMS):
        raise ValueError('exact canonical business cursor required')
    business.__post_init__()
    if cursor.business_policy_identity != business.policy_id:
        raise ValueError('paired business policy identity differs')
    records = business.records
    for record in records:
        if type(record) is not capacity_policy.CapacityPolicyRecord:
            raise ValueError('exact capacity policy record required')
        capacity_policy.CapacityPolicyRecord.__post_init__(record)
        if not record.committed:
            raise ValueError('paired cursor contains an uncommitted business record')
    initial = business.initial.tracks[0][1].physical.anchor.power_source_hour
    committed_hours = tuple(r.current.observation.hour.power_source_hour for r in records)
    if (hours[0] != initial+1 or len(records) > len(hours)
            or committed_hours != hours[:len(records)]):
        raise ValueError('committed history differs from declared source-hour prefix')
    endpoint = business.execution.tracks[0][1].physical.anchor.power_source_hour
    physical = tx.scale.actual._physical(cursor.grid)
    if (physical.source_hour != endpoint or endpoint != (committed_hours[-1] if records else initial)
            or (cursor.last_publication_identity is None) != (len(records) == 0)):
        raise ValueError('paired business/grid endpoint or publication differs')
    # Existing exact-energy and cohort accounting is reused unchanged. Because
    # all supplied records belong to the paired cursor, no candidate is counted.
    summary = business_diagnostics.summarize(business, len(hours))
    grid_applicable, cfe_applicable = business.spec.arm_id != tx.CFE, business.spec.arm_id != tx.NETWORK
    report = dict(schema='rq2_mixed_enrollment_prefix_diagnostic_v1', cursor_identity=cursor.identity,
        implementation_identity=implementation,
        policy_id=business.policy_id, arm_id=business.spec.arm_id,
        declared_source_hours=hours, committed_source_hours=committed_hours,
        uncommitted_source_hours=hours[len(records):],
        committed_hours=len(records), uncommitted_hours=len(hours)-len(records), halted=cursor.halted,
        grid_service_applicable=grid_applicable, cfe_service_applicable=cfe_applicable,
        committed_grid_shortfall_energy=summary['committed_grid_shortfall_energy'],
        committed_cfe_shortfall_energy=summary['committed_cfe_shortfall_energy'],
        committed_grid_failure_hours=(sum(r.response.grid_service_failure is True for r in records)
                                      if grid_applicable else None),
        committed_cfe_failure_hours=(sum(r.response.cfe_service_failure is True for r in records)
                                     if cfe_applicable else None),
        remaining_debt=business.execution.tracks[0][1].ledger.debt,
        cohort_assessment=business_diagnostics.assess_debt_cohorts(business.execution.tracks[0][1].ledger),
        evidence_class='derived_mechanism_committed_prefix',
        scope='caller_declared_window_and_owned_cursor_only',
        historical_grid_archives_replayed=False, grid_history_verified=False, empirical_risk_support_verified=False,
        complete_service_result=None, risk_probability=None, training_capacity_certificate=None,
        formal_result=False, security_certified=False)
    enrollment_records = [r for r in records if r.current.observation.hour.power_source_hour in enrolled]
    followup_records = [r for r in records if r.current.observation.hour.power_source_hour not in enrolled]
    ledger = business.execution.tracks[0][1].ledger
    classifications = dict(debt_cohorts.assess_debt_cohorts(ledger))
    cohorts = tuple(dict(birth=c.created_hour, due=c.due_hour, incurred=c.incurred,
        remaining=c.remaining, missed_at_deadline=c.missed_at_deadline,
        status=classifications[c.created_hour],
        scope='enrolled' if c.created_hour in enrolled else 'followup') for c in ledger.cohorts)
    dt = Q(str(dict(business.initial.tracks[0][1].physical.envelope)['time_step_hours']))
    def energy(rows, field, applicable):
        return sum((getattr(r.response, field)*dt for r in rows
                    if getattr(r.response, field) is not None), Q(0)) if applicable else None
    def part(rows):
        return dict(committed_source_hours=tuple(r.current.observation.hour.power_source_hour for r in rows),
            grid_shortfall_energy=energy(rows, 'grid_shortfall', grid_applicable),
            cfe_shortfall_energy=energy(rows, 'cfe_shortfall', cfe_applicable))
    report.update(enrollment_source_hours=enrolled,
        enrollment_uncommitted_source_hours=tuple(h for h in enrolled if h not in committed_hours),
        enrollment=part(enrollment_records), followup=part(followup_records), cohorts=cohorts,
        enrolled_remaining_debt=sum((c.remaining for c in ledger.cohorts if c.created_hour in enrolled), Q(0)),
        followup_remaining_debt=sum((c.remaining for c in ledger.cohorts if c.created_hour not in enrolled), Q(0)),
        enrollment_service_result=None, enrollment_declaration_registered=False,
        scope='caller_declared_enrollment_partition_of_owned_paired_prefix')
    if cursor.identity != expected_cursor_identity or implementation_identity() != implementation:
        raise ValueError('cursor or diagnostic implementation changed during summary')
    return report
