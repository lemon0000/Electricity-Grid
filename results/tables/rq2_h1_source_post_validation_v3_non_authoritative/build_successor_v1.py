"""Mechanical versioned successor construction; fail rather than overwrite."""
from pathlib import Path
from hashlib import sha256
import json

REPO = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def replace(text, old, new):
    if text.count(old) != 1:
        raise ValueError('expected one source fragment: ' + old[:100])
    return text.replace(old, new)


def build():
    source = REPO/'experiments/h1_phase_historical_batch_development_v2.py'
    text = source.read_text(encoding='utf-8')
    text = text.replace('h1_phase_historical_batch_development_v2', 'h1_phase_historical_batch_development_v3')
    text = replace(text, 'from uuid import uuid4',
        'from uuid import uuid4\n\nfrom experiments import h1_constructor_rejection_support_development_v1 as support\n'
        'from experiments import h1_constructor_runtime_guard_development_v1 as runtime\n'
        'from src.rq2_joint_deliverability_boundary_v1 import normal_h1_source as packet_source')
    begin = text.index('# Keep a private copy of the original close program')
    end = text.index('\n\ndef implementation_identity()', begin)
    text = text[:begin] + '''# A private closure retains an independent copy even after an exported helper
# alias, code, defaults, closure cell, or its private function graph changes.
_SAFE_CLOSE = runtime.frozen_teardown(support.close_replay)
_RUNTIME = runtime.NamedRuntimeSnapshot(runtime.runtime_roots(model, packet_source, support))


def _make_close_replay(safe_close):
    def close_replay(reader, leases, captured, completed, primary):
        return safe_close(reader, leases, captured, completed, primary)
    return close_replay


_close_replay = _make_close_replay(_SAFE_CLOSE)
''' + text[end:]
    text = replace(text, "io.digest(Path(__file__).read_bytes()), io.digest(Path(capture.__file__).read_bytes())]))",
        "io.digest(Path(__file__).read_bytes()), io.digest(Path(capture.__file__).read_bytes()),\n"
        "        io.digest(Path(support.__file__).read_bytes()), io.digest(Path(runtime.__file__).read_bytes())]))")
    text = replace(text, 'def _check_dependencies():\n',
        'def _check_dependencies():\n    _RUNTIME.check()\n')
    text = text.replace("'_CONSTRUCTOR_CLOSE', '_close_replay'", "'_SAFE_CLOSE', '_close_replay'")
    text = text.replace("'_CONSTRUCTOR_CLOSE', 'model'", "'_SAFE_CLOSE', 'model'")
    text = replace(text, "'prior', 'capture', 'io',", "'prior', 'capture', 'support', 'runtime', 'packet_source', '_RUNTIME', 'io',")
    text = replace(text, "'normal_model_dependency_bookends_verified", "'normal_model_dependency_bookends_verified") if False else text
    text = replace(text, "obligation_names=observed.setdefault('obligation_names',{});identities=observed.setdefault('identities',{})",
        "obligation_names=observed.setdefault('obligation_names',{});identities=observed.setdefault('identities',{})\n"
        "    parent_names=observed.setdefault('parent_names',{})")
    text = replace(text, 'captured={};evidence={};seen_hours=[];retained_bytes=0',
        'captured={};evidence={};seen_hours=[];retained_bytes=0;packet_bytes=0;all_packets={}')
    text = replace(text, 'nonlocal retained_bytes\n', 'nonlocal retained_bytes,packet_bytes\n')
    text = replace(text, '                seen_hours.append(hour)\n',
        '''                if type(packet) is not packet_source.H1CurrentNormal or hour in all_packets:
                    raise ValueError('one exact all-hour packet per chronological N hour required')
                packet_pin=(packet.inputs.input_identity,packet.audit_identity,packet_source._digest(packet))
                packet_bytes+=retained_size((packet,packet_pin))
                if packet_bytes+retained_bytes>MAX_RETAINED_BYTES:
                    raise ValueError('combined batch retained data byte cap exceeded')
                all_packets[hour]=(packet,packet_pin)
                seen_hours.append(hour)
''')
    text = replace(text, 'if retained_bytes>MAX_RETAINED_BYTES:raise ValueError(\'batch retained data byte cap exceeded\')',
        "if packet_bytes+retained_bytes>MAX_RETAINED_BYTES:raise ValueError('combined batch retained data byte cap exceeded')")
    text = replace(text, '            _observe_prefix(identities,root,completed_hours,stages)\n            model_before=',
        '''            _observe_prefix(identities,root,completed_hours,stages)
            support.observe_parent_names(Path(declaration['root']),completed_hours=completed_hours,
                declared_hours=declaration['hours'],retained=parent_names)
            _check_dependencies()
            model_before=''' )
    text = replace(text, '                    or set(captured)!=set(selected_hours)):',
        '                    or set(captured)!=set(selected_hours) or tuple(all_packets)!=tuple(range(completed_hours))):')
    text = replace(text, '            _model_dependencies_unchanged(model_before)\n            proofs={}',
        '''            _model_dependencies_unchanged(model_before)
            support.observe_parent_names(Path(declaration['root']),completed_hours=completed_hours,
                declared_hours=declaration['hours'],retained=parent_names)
            _check_dependencies()
            for hour,(packet,packet_pin) in all_packets.items():
                packet_source.validate_current(packet)
                if ((packet.inputs.input_identity,packet.audit_identity,packet_source._digest(packet))!=packet_pin
                        or packet.relative_hour!=hour):
                    raise ValueError('all-hour packet identity changed during historical replay')
            _check_dependencies()
            # The long all-H loop has its own final filesystem/namespace and
            # runtime bookends. None of the success flags precedes these.
            base.entry.unchanged(views);inventory()
            _observe_prefix(identities,root,completed_hours,stages)
            _observe_sources(identities,declaration)
            support.observe_parent_names(Path(declaration['root']),completed_hours=completed_hours,
                declared_hours=declaration['hours'],retained=parent_names)
            if implementation_identity()!=own:raise ValueError('historical controller implementation drift')
            _model_dependencies_unchanged(model_before)
            _check_dependencies()
            proofs={}''')
    text = replace(text, '                selected_frame_bytes=retained_bytes,seconds=',
        '''                all_hour_packet_revalidation_verified=True,all_hour_packet_count=len(all_packets),
                all_hour_packet_bytes=packet_bytes,combined_retained_bytes=packet_bytes+retained_bytes,
                retained_cap_bytes=MAX_RETAINED_BYTES,parent_namespace_bookends_verified=True,
                parent_namespace_observations=3,final_post_revalidation_bookends_verified=True,
                named_runtime_bookends_verified=True,named_runtime_inventory=dict(_RUNTIME.summary),
                complete_dynamic_input_closure_proved=False,unobserved_between_bookends_ABA_covered=False,
                selected_frame_bytes=retained_bytes,seconds=''' )
    text = replace(text, '        _close_replay(reader,leases,captured,completed,sys.exception())',
        '''        try:
            close_reader(reader,leases,captured,completed,sys.exception())
        finally:
            all_packets.clear()
            records.clear() if 'records' in locals() else None
            seen_hours.clear()''')
    # A call-local copy cannot be redirected by later module alias rebinding.
    text = replace(text, '    _check_dependencies()\n    old.additional_content_bound(completed_hours)',
        '    close_reader=_close_replay\n    _check_dependencies()\n    old.additional_content_bound(completed_hours)')
    target = REPO/'experiments/h1_phase_historical_batch_development_v3.py'
    with target.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(text)
    records = [dict(source=str(source),source_sha256=sha256(source.read_bytes()).hexdigest(),
                    target=str(target),target_sha256=sha256(target.read_bytes()).hexdigest())]
    pairs = (
        ('experiments/h1_phase_exact_source_batch_development_v2.py','experiments/h1_phase_exact_source_batch_development_v3.py'),
        ('experiments/h1_constructor_source_batch_validation_development_v1.py','experiments/h1_constructor_source_batch_validation_development_v2.py'),
    )
    for old, new in pairs:
        source, target = REPO/old, REPO/new
        text = source.read_text(encoding='utf-8')
        text = text.replace('h1_phase_historical_batch_development_v2','h1_phase_historical_batch_development_v3')
        text = text.replace('h1_phase_exact_source_batch_development_v2','h1_phase_exact_source_batch_development_v3')
        text = text.replace('source-batch v2','source-batch v3')
        with target.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(text)
        records.append(dict(source=str(source),source_sha256=sha256(source.read_bytes()).hexdigest(),
                            target=str(target),target_sha256=sha256(target.read_bytes()).hexdigest()))
    (HERE/'generation_record_v1.json').write_text(json.dumps(dict(status='DRAFT_NONAUTHORITATIVE',
        mechanical_base_only=True,records=records),indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':
    build()
