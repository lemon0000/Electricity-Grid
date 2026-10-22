"""Detached source-batch v2 data audit; never an owner or live receipt."""
from fractions import Fraction as Q
import json
from experiments import h1_phase_exact_source_batch_development_v2 as batch_source
from experiments import h1_phase_obligation_controller_development_v1 as normal

def validate_detached_batch(result,binding,terminals,selected,source_identity):
    """Validate the successor data contract before scientific replay/effects."""
    encoded=batch_source.io.encode
    if (type(result) is not batch_source.CurrentBatch or type(result.currents) is not dict
            or set(result.currents)!=set(selected)):
        raise ValueError('exact batch current keyset/type required')
    if type(result.observations) is not tuple or len(result.observations)!=2:
        raise ValueError('two independent batch observations required')
    tokens=[]
    for metric in result.observations:
        if (type(metric) is not dict or metric.get('completed_hours')!=max(terminals)+1
                or metric.get('selected_hours')!=list(selected)
                or type(metric.get('parent_inspect_traversals')) is not int
                or metric['parent_inspect_traversals']!=1
                or metric.get('constructor_inspection_reused') is not True
                or metric.get('normal_model_dependency_bookends_verified') is not True
                or type(metric.get('observation_token')) is not str or len(metric['observation_token'])!=32):
            raise ValueError('batch observation shape differs')
        tokens.append(metric['observation_token'])
    if tokens[0]==tokens[1]:raise ValueError('distinct batch observations required')
    prior=batch_source.prior
    false_flags=('policy_visible','shared_observed_clock','accepted_real_RTS_root_integration_verified',
        'detached_consumer_authenticated','persistent_lane_owner_implemented','common_publication_verified',
        'full_192_hour_execution_verified','resource_admission','formal_execution_ready','formal_result',
        'native_execution_authorized')
    verified=('current_source_correspondence_checked','registry_action_and_cap_lookup_checked',
        'exact_source_projection_checked')
    historical_true=('historical_parent_prefix_verified','historical_obligation_prefix_verified',
        'historical_job_clock_prefix_verified')
    historical_false=('suffix_chain_verified','current_latest_parent_verified','current_latest_obligation_verified',
        'live_release_authenticated','live_handoff_authenticated','writer_lock_authenticated',
        'persistent_lane_owner_implemented','detached_consumer_authenticated','common_prefix_publication_verified',
        'reference_or_actual_ready',*batch_source.historical.old.FLAGS)
    for hour,current in result.currents.items():
        if type(hour) is not int or type(current) is not prior.ExactSourceCurrent:
            raise ValueError('exact successor current type required')
        prepared=current.prepared_current
        if (type(prepared) is not prior.origin_join.PreparedCurrent
                or type(current.source_projection_audit_payload) is not bytes
                or len(current.source_projection_audit_payload)>prior.historical.binding.CAP
                or type(current.exogenous_scientific_payload) is not bytes
                or type(current.workload_exact) is not Q or type(current.source_cfe_at_alpha_one_exact) is not Q):
            raise ValueError('exact successor current fields required')
        audit=json.loads(current.source_projection_audit_payload)
        if (type(audit) is not dict or encoded(audit)!=current.source_projection_audit_payload
                or prepared.audit_payload!=current.source_projection_audit_payload
                or audit.get('schema')!=batch_source.SCHEMA or audit.get('replay_contract')!=batch_source.SCHEMA
                or audit.get('implementation_identity')!=source_identity
                or type(audit.get('completed_hours')) is not int or audit['completed_hours']!=hour+1
                or audit.get('controller_binding_sha256')!=binding.binding_sha256
                or audit.get('controller_terminal_sha256')!=terminals[hour]
                or audit.get('registry_identity')!=binding.registry_identity
                or any(audit.get(k) is not False for k in false_flags)
                or any(audit.get(k) is not True for k in verified)):
            raise ValueError('successor source audit identity/pins differ')
        proof=audit.get('historical_controller')
        if (type(proof) is not dict or proof.get('replay_contract')!=batch_source.historical.SCHEMA
                or type(proof.get('completed_hours')) is not int or proof['completed_hours']!=hour+1
                or any(proof.get(k) is not True for k in historical_true)
                or any(proof.get(k) is not False for k in historical_false)):
            raise ValueError('successor historical replay contract differs')
        normal_audit=audit.get('normal_audit_payload');registry_audit=audit.get('registry_audit_payload')
        if (type(normal_audit) is not dict or normal_audit.get('schema')!=prior.SCHEMA
                or normal_audit.get('historical_controller')!=proof
                or audit.get('normal_audit_identity')!=normal.io.digest(encoded(normal_audit))
                or type(registry_audit) is not dict or registry_audit.get('registry_identity')!=binding.registry_identity
                or audit.get('registry_audit_identity')!=normal.io.digest(encoded(registry_audit))
                or prepared.frame.info.relative_hour!=hour
                or audit.get('decision_identity')!=prepared.decision.decision_identity
                or normal_audit.get('decision_identity')!=prepared.decision.normal.decision_identity
                or audit.get('source_observation_identity')!=current.source_observation_identity
                or audit.get('exogenous_scientific_identity')!=current.exogenous_scientific_identity
                or audit.get('source_action_audit_identity')!=prior.physical._digest(prepared.source_action)
                or audit.get('source_cfe_at_alpha_one_exact')!=prior._ratio(current.source_cfe_at_alpha_one_exact)):
            raise ValueError('successor current projection correspondence differs')
        scientific=json.loads(current.exogenous_scientific_payload)
        if (encoded(scientific)!=current.exogenous_scientific_payload
                or scientific.get('schema')!=prior.SCHEMA or type(scientific.get('relative_hour')) is not int
                or scientific['relative_hour']!=hour or scientific.get('current_decision_identity')!=prepared.decision.decision_identity
                or scientific.get('workload_exact')!=prior._ratio(current.workload_exact)
                or scientific.get('source_cfe_at_alpha_one_exact')!=prior._ratio(current.source_cfe_at_alpha_one_exact)):
            raise ValueError('successor scientific quantity correspondence differs')
