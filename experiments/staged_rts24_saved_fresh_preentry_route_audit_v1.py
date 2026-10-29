"""Source-derived pre-entry route and transport preparation; no target execution."""
import ast
import base64
from hashlib import sha256
import importlib.util
import io
import json
import lzma
from pathlib import Path
import subprocess
import tokenize
from types import CodeType, FunctionType

ROOT = Path(__file__).absolute().parents[1]
FILES = {
    'core44': 'experiments/staged_rts24_saved_fresh_pre_entry_lease_v44.py',
    'core50': 'experiments/staged_rts24_saved_fresh_pre_entry_lease_v50.py',
    'probe42': 'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v42.py',
    'parent39': 'experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v39.py',
    'parent40': 'experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v40.py',
    'transport': 'experiments/staged_rts24_saved_fresh_utf16_transport_v1.py',
    'adoption': 'experiments/staged_rts24_saved_fresh_adoption_v1.py',
    'native_owner': 'src/rq2_joint_deliverability_boundary_v1/normal_process.py',
    'permission': 'experiments/staged_rts24_saved_fresh_p1_permission_v1.py',
    'namespace': 'experiments/staged_rts24_saved_fresh_entry_namespace_consumer_v4.py',
    'loader': 'experiments/staged_rts24_saved_fresh_project_bootstrap_loader_v5.py',
    'actor': 'experiments/staged_rts24_saved_fresh_bootstrap_actor_v2.py',
    'boundary': 'experiments/staged_rts24_saved_fresh_bootstrap_post_return_v4.py',
    'role': 'experiments/staged_rts24_saved_fresh_full_context_role_runtime_v6.py',
}
SOURCE_EPOCH = 'acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('ascii')


def pin(raw):
    return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def node_at(tree, qualname):
    nodes = tree.body
    for name in qualname.split('.'):
        matches = [node for node in nodes if type(node) in (ast.FunctionDef, ast.ClassDef) and node.name == name]
        if len(matches) != 1:
            raise ValueError('unique direct source node required: ' + qualname)
        found = matches[0]
        nodes = found.body
    return found


def witness(raw, qualname, excerpts):
    node = node_at(ast.parse(raw), qualname)
    text = ast.get_source_segment(raw.decode('utf-8'), node)
    for excerpt in excerpts:
        if excerpt not in text:
            raise ValueError('source contract differs: ' + qualname + ': ' + excerpt)
    return dict(qualname=qualname, line=node.lineno, end_line=node.end_lineno,
        source_fragment_pin=pin(text.encode('utf-8')), required_excerpts=list(excerpts))


def ordered_calls(raw, qualname, selectors):
    parent = node_at(ast.parse(raw), qualname)
    result = []
    for function, literal_arg in selectors:
        found = []
        for node in ast.walk(parent):
            if type(node) is not ast.Call or ast.unparse(node.func) != function:
                continue
            if literal_arg is not None:
                if literal_arg.startswith('@first_name:'):
                    if not node.args or type(node.args[0]) is not ast.Name or node.args[0].id != literal_arg.split(':', 1)[1]:
                        continue
                elif not any(type(arg) is ast.Constant and arg.value == literal_arg for arg in node.args):
                    continue
            found.append(node)
        assert len(found) == 1, (qualname, function, literal_arg)
        node = found[0]
        result.append(dict(function=function, literal_arg=literal_arg, line=node.lineno,
            column=node.col_offset, end_line=node.end_lineno, end_column=node.end_col_offset))
    positions = [(row['line'], row['column']) for row in result]
    assert len(set(positions)) == len(positions) and positions == sorted(positions)
    assert all((left['end_line'], left['end_column']) <= (right['line'], right['column'])
        for left, right in zip(result, result[1:])), 'overlapping or nested source calls'
    return dict(qualname=qualname, ordered_calls=result, property='strict_source_span_order',
        actual_execution_observed=False)


def native_failure_matrix():
    rows = (
        ('ACK', ['missing', 'wrong', 'late'], ['zero_transport_manifest', 'zero_channel', 'zero_child', 'retain_context_offer_cleanup']),
        ('manifest_transport_descriptor', ['construction', 'binding', 'publication'], ['zero_child', 'create_only_residue_accounted']),
        ('channel_create', ['partial', 'collision', 'mutex'], ['zero_resume', 'close_all_acquired_channel_roots']),
        ('Native_constructor', ['Job', 'attribute_list', 'CreateProcess_partial'],
            ['recover_actual_handles', 'retain_partial_owner', 'zero_resume', 'terminate_any_created_child_Job', 'quiesce', 'close']),
        ('suspended_bind_header', ['before_bind', 'header_commit'], ['zero_resume', 'terminate_Job', 'quiesce', 'close_owner', 'close_channel']),
        ('bound_before_publish', ['failure'], ['zero_resume', 'terminate_Job', 'inner_and_outer_quiet']),
        ('resume', ['count_not_one'], ['no_retry', 'terminate_Job', 'retain_unresolved']),
        ('child_arguments', ['name', 'nonce', 'context', 'ACK', 'role', 'deadline', 'source_epoch', 'descriptor'],
            ['zero_manifest_read', 'zero_Core_Resource', 'zero_Source49_read']),
        ('child_endpoint', ['mapping_open', 'mutex_open', 'header_torn', 'header_uncommitted', 'mutex_abandoned', 'PID', 'creation'],
            ['zero_manifest_read', 'zero_Core_Resource', 'zero_Source49_read', 'capsule_partial_cleanup']),
        ('manifest_after_endpoint', ['open', 'pin', 'schema', 'correlation'], ['endpoint_close', 'zero_Core_Resource', 'zero_Source49_read']),
        ('Core_Resource', ['partial_process_open', 'partial_thread_open'],
            ['endpoint_cleanup_attempted', 'Native_partial_cleanup_attempted', 'zero_Source49_read']),
        ('lease_inputs_transfer', ['precommit', 'postcommit'], ['actual_resource_owner_decides_commit', 'original_capsule_cleanup']),
        ('runtime_transfer', ['PREPARING', 'anchor', 'precommit', 'postcommit'], ['capsule_already_in_anchor', 'Native_finally_attempted']),
        ('role_admission', ['Guard2_install', 'handoff', 'profile', 'claim'], ['revoke', 'abort', 'quiet', 'terminal_or_unresolved']),
        ('execution_stop', ['normal', 'error', 'deadline_180', 'root_exit_with_descendants', 'terminal_hang', 'resource', 'channel_corruption'],
            ['original_absolute_deadline', 'no_clock_renewal', 'inner_and_outer_quiet']),
        ('retirement', ['endpoint_close', 'Job_close', 'registry_retire', 'repeated_close', 'reentry'],
            ['sticky_primary_and_secondary', 'no_repeated_physical_close', 'retain_uncertain_terminal']),
    )
    return [dict(window=window, variants=variants, required_outcomes=outcomes, status='OPEN',
        executed_cases=0, native_execution_authorized=False) for window, variants, outcomes in rows]


def interface_witnesses(raws):
    specs = (
        ('adoption', '_held_context_offer', ('ROLE_PROBE_SCHEMA', 'deadline=started+8.', 'canonical(context) == canonical(expected)')),
        ('adoption', '_ordinary_invocation_broker', ('make_role_probe_context', 'write_packet(\'context\'', 'read_packet(\'ack\'')),
        ('adoption', 'StageChannel', ('progress/corruption detection, never authority', 'OpenFileMappingW', 'OpenMutexW', 'owner_creation_filetime')),
        ('adoption', '_construct_stage_owner', ('ordinary_owner_probe', 'channel.bind_owner(owner)')),
        ('adoption', '_watch_stage', ('_watch_owned_stage',)),
        ('adoption', '_watch_owned_stage', ('if invocation is None: owner.release()',)),
        ('adoption', 'SavedFileBootstrap', ('_direct_main_shape(list(self.argv))',)),
        ('adoption', '_direct_main_shape', ("main.__name__ == '__main__'",)),
        ('parent39', 'one_case', ('subprocess.Popen', 'SAVED_PRE_ENTRY_V1:', 'process.stdin.close()')),
        ('native_owner', 'DevelopmentNormalChild.__init__', ('0x2000D', 'CreateProcessW(argv[0], command, None, None, False', '0x08000000 | 0x00080000 | 0x4 | 0x400')),
        ('native_owner', 'DevelopmentNormalChild.release', ('ResumeThread', 'previous != 1')),
        ('core50', 'open_local_pre_entry_lease', ('_RELEASED', 'plan=check_plan(plan_raw)', 'resource=_Resource(owner,guard)', "if resource is not None:")),
        ('core50', 'LocalPreEntryLease.transfer', ('resource.owner=target',)),
        ('core50', 'LocalPreEntryInputs.transfer_runtime', ('seal_runtime_cleanup(target)', "object.__setattr__(resource,'owner',target)")),
        ('core50', 'LocalRuntimeInputs.own_pending_boundary', ("self._phase=='ADOPTED'", "'_phase','IMPORTING'")),
        ('core50', 'LocalRuntimeInputs.consume_once', ('close(self,primary)',)),
        ('permission', 'bind_owner', ("owner._phase=='ADOPTED'",)),
        ('permission', 'install_guard', ("owner._phase=='IMPORTING'", 'ACTIVE_B3', 'sys.addaudithook')),
        ('namespace', 'build_consumer_plan', ("owner._phase=='IMPORTING'", 'expectation_binding')),
        ('loader', 'prepare_project_bridge', ('bind_owner', 'new_actor', 'permission_program')),
        ('actor', 'dispatch', ("operation=='install_guard'", "_phase='IMPORTING'")),
        ('probe42', '_probe_main', ('open_local_pre_entry_lease(raw,guard)', 'prepare_project_bridge', "actor_call('install_guard'")),
        ('role', 'bind_full_role', ('raise FullRoleUnavailable',)),
    )
    result = []
    for source, qualname, excerpts in specs:
        result.append(dict(source=source, path=str(ROOT / FILES[source]), pin=pin(raws[source]),
            **witness(raws[source], qualname, excerpts)))
    prefix = raws['core50'].split(b'\nimport builtins\n')[0]
    assert prefix.count(b'sys.stdin.buffer.read') == 2 and b'SAVED_PRE_ENTRY_V1:' in prefix
    assert prefix.index(b'sys.stdin.buffer.read') < prefix.index(b'sys.addaudithook')
    assert b'launcher_present=False' in raws['parent40']
    parent_refs = next(node for node in ast.parse(raws['parent40']).body if type(node) is ast.Assign
        and len(node.targets) == 1 and type(node.targets[0]) is ast.Name and node.targets[0].id == 'SOURCE_REFS')
    refs = ast.literal_eval(parent_refs.value)
    assert refs['core'][0] == FILES['core44'] and refs['probe'][0] == FILES['probe42']
    orders = [dict(source=source, path=str(ROOT / FILES[source]), pin=pin(raws[source]),
        **ordered_calls(raws[source], qualname, selectors)) for source, qualname, selectors in (
        ('adoption', '_ordinary_invocation_broker', (
            ('mailbox.read_packet', 'ack'), ('require', 'host exact context ACK missing or differs'),
            ('StageChannel.create', None), ('_construct_stage_owner', None),
            ('mailbox.write_packet', 'binding'), ('_watch_stage', None))),
        ('adoption', '_construct_stage_owner', (('factory.__init__', None), ('channel.bind_owner', None), ('OwnedStage', None))),
        ('probe42', '_probe_main', (('read_file', '@first_name:path'), ('install_guard', None), ('open_local_pre_entry_lease', None))),
    )]
    watch = witness(raws['adoption'], '_watch_stage', ('_watch_owned_stage',))
    release = witness(raws['adoption'], '_watch_owned_stage', ('if invocation is None: owner.release()',))
    return dict(nodes=result, node_count=len(result), stdin_before_payload_and_early_audit=True,
        parent40_bound_core=refs['core'], parent40_bound_probe=refs['probe'],
        parent40_launcher_present=False, core50_parent40_source_join_implemented=False,
        source_order_relations=orders, watch_release_source_chain=[watch, release],
        source_order_relation_count=3, source_order_actual_execution_verified=False)


def independent_decode_transport(transport_raw, expected_raw):
    tree = ast.parse(transport_raw)
    matches = [node for node in ast.walk(tree) if type(node) is ast.Assign and len(node.targets) == 1
        and type(node.targets[0]) is ast.Name and node.targets[0].id == '_packed14']
    assert len(matches) == 1
    call = matches[0].value
    assert type(call) is ast.Call and type(call.func) is ast.Name and call.func.id == '_u14' and len(call.args) == 2
    encoded, size = (ast.literal_eval(node) for node in call.args)
    assert type(encoded) is str and type(size) is int and 0 < size <= 26214
    # Independent bit-string decoder: deliberately does not call unpack14/decode.
    assert all(0 <= ord(char) - 0x4e00 < 16384 for char in encoded)
    bits = ''.join(format(ord(char) - 0x4e00, '014b') for char in encoded)
    assert len(encoded) == (size * 8 + 13) // 14 and set(bits[size * 8:]) <= {'0'}
    packed = bytes(int(bits[index:index + 8], 2) for index in range(0, size * 8, 8))
    decoder = lzma.LZMADecompressor(format=lzma.FORMAT_XZ, memlimit=67108864)
    raw = decoder.decompress(packed, max_length=131073)
    assert raw == expected_raw and len(raw) <= 131072 and decoder.eof and not decoder.unused_data
    assert decoder.check == lzma.CHECK_CRC64
    assignments = {node.targets[0].id: node for node in ast.walk(tree) if type(node) is ast.Assign
        and len(node.targets) == 1 and type(node.targets[0]) is ast.Name and node.targets[0].id in ('_ux', '_PAYLOAD_RAW', '_PAYLOAD_CODE')}
    assert set(assignments) == {'_ux', '_PAYLOAD_RAW', '_PAYLOAD_CODE'}
    def expression(text):
        return ast.dump(ast.parse(text, mode='eval').body, include_attributes=False)
    assert ast.dump(assignments['_ux'].value, include_attributes=False) == expression('_xz.LZMADecompressor(format=_xz.FORMAT_XZ,memlimit=67108864)')
    assert ast.dump(assignments['_PAYLOAD_RAW'].value, include_attributes=False) == expression('_ux.decompress(_packed14,max_length=131073)')
    expected = (len(expected_raw), sha256(expected_raw).hexdigest())
    checks = (
        ('type(_PAYLOAD_RAW) is not bytes or len(_PAYLOAD_RAW)>131072 or _ux.eof is not True or _ux.unused_data or _ux.check!=_xz.CHECK_CRC64', 'cap'),
        ('(len(_PAYLOAD_RAW),_hs(_PAYLOAD_RAW).hexdigest())!=' + repr(expected), 'payload'),
    )
    guard_lines = []
    for test, message in checks:
        guards = [node for node in ast.walk(tree) if type(node) is ast.If and ast.dump(node.test, include_attributes=False) == expression(test)]
        assert len(guards) == 1 and len(guards[0].body) == 1 and not guards[0].orelse
        raised = guards[0].body[0]
        assert type(raised) is ast.Raise and ast.dump(raised.exc, include_attributes=False) == expression('RuntimeError(' + repr(message) + ')')
        assert assignments['_PAYLOAD_RAW'].lineno < guards[0].lineno < assignments['_PAYLOAD_CODE'].lineno
        guard_lines.append(guards[0].lineno)
    return dict(packed_pin=pin(packed), encoded_BMP_units=len(encoded), decoded_pin=pin(raw),
        zero_padding_bits=len(bits) - size * 8, independent_bit_string_decode=True, crc64=True,
        generated_loader_guards_AST_verified=True, generated_guard_lines=guard_lines, generated_loader_executed=False)


def transport_baselines(raws):
    # These repository compiler/minifier implementations depend only on stdlib.
    # The built prefix/payload and all target modules are compiled, never executed.
    path = ROOT / FILES['transport']
    spec = importlib.util.spec_from_file_location('_static_F_transport', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    node = node_at(ast.parse(raws['parent40']), 'minify_prefix')
    unit = ast.Module(body=[node], type_ignores=[])
    code = compile(unit, str(ROOT / FILES['parent40']), 'exec', dont_inherit=True, optimize=0)
    held = next(item for item in code.co_consts if type(item) is CodeType and item.co_name == 'minify_prefix')
    minify = FunctionType(held, dict(__builtins__=__builtins__, ast=ast, io=io, tokenize=tokenize))
    manifest = str(ROOT / 'results/tables/staged_rts24_saved_fresh_full_role_entry_native_v1_non_authoritative/transport/controller/manifest.json')
    rows = []
    for key in ('core44', 'core50'):
        core, probe = ROOT / FILES[key], ROOT / FILES['probe42']
        before, payload = module.payload(core, probe)
        transport = module.build(core, probe, minify)
        compile(transport, '<string>', 'exec', dont_inherit=True, optimize=0)
        decoded = independent_decode_transport(transport, payload)
        baseline = ['D:\\Miniconda3\\envs\\compute\\python.exe', '-P', '-B', '-s', '-S', '-c',
            transport.decode('utf-8'), '--pre-entry-lease', manifest, '0' * 64]
        # Proposed fields are a width reservation, not a runnable manifest/argv.
        proposed = baseline[:7] + ['--full-role-pre-entry', manifest, '0' * 64, 'controller',
            'Local\\saved_F_full_role_' + '0' * 64, '0' * 64, '0' * 64, '0' * 64, '0' * 64,
            '0' * 32, SOURCE_EPOCH]
        widths = []
        for label, argv in (('current_shape', baseline), ('proposed_field_reservation', proposed)):
            command = subprocess.list2cmdline(argv)
            units = len(command.encode('utf-16-le')) // 2 + 1  # Includes terminating NUL.
            assert units <= 30000
            widths.append(dict(shape=label, utf16_units_including_nul=units, project_cap=30000,
                remaining_units=30000 - units, argv_count=len(argv), non_code_argv=argv[:6] + ['<transport>'] + argv[7:],
                runnable_invocation=False))
        rows.append(dict(core=key, core_pin=pin(raws[key]), probe_pin=pin(raws['probe42']),
            raw_prefix_pin=pin(before), minified_prefix_pin=pin(minify(before)), payload_pin=pin(payload),
            payload_cap=131072, payload_remaining_bytes=131072-len(payload), transport_pin=pin(transport),
            transport_raw_base64=base64.b64encode(transport).decode('ascii'),
            source_code_compiled=True, source_code_executed=False, parent40_closed_refs_match=key == 'core44',
            independent_decode=decoded, command_lines=widths, future_successor_admitted=False))
    return rows


def replay_saved(report):
    expected = route_contract()
    assert set(report) == set(expected) | {'source_pins', 'interface_evidence', 'transport_baselines'}
    assert all(canonical(report[key]) == canonical(value) for key, value in expected.items())
    assert len(report['native_diagnostic_failure_stop_matrix']) == 16
    assert all(row['status'] == 'OPEN' and type(row['executed_cases']) is int and row['executed_cases'] == 0
        and row['native_execution_authorized'] is False for row in report['native_diagnostic_failure_stop_matrix'])
    raws = {name: (ROOT / path).read_bytes() for name, path in FILES.items()}
    assert report['source_pins'] == {str(ROOT / FILES[name]): pin(raw) for name, raw in raws.items()}
    assert canonical(report['interface_evidence']) == canonical(interface_witnesses(raws))
    assert [row['core'] for row in report['transport_baselines']] == ['core44', 'core50']
    decoded_rows = []
    for row in report['transport_baselines']:
        raw = base64.b64decode(row['transport_raw_base64'], validate=True)
        assert pin(raw) == row['transport_pin'] and row['future_successor_admitted'] is False
        assert row['source_code_executed'] is False and row['source_code_compiled'] is True
        # Reconstruct expected payload from the pinned source with an independent
        # comment masker; locations and compilation must remain identical.
        original = raws[row['core']] + b'\n' + raws['probe42']
        prefix, tail = original.split(b'\nimport builtins\n')
        source = b'import builtins\n' + tail
        lines = source.decode('utf-8').splitlines(keepends=True)
        for token in tokenize.tokenize(io.BytesIO(source).readline):
            if token.type == tokenize.COMMENT:
                line, col = token.start
                lines[line-1] = lines[line-1][:col] + ' ' * (token.end[1]-col) + lines[line-1][token.end[1]:]
        payload = ''.join(lines).encode('utf-8')
        assert pin(prefix) == row['raw_prefix_pin'] and pin(payload) == row['payload_pin']
        assert compile(payload, '<pre_entry_payload>', 'exec', dont_inherit=True, optimize=0) == compile(source, '<pre_entry_payload>', 'exec', dont_inherit=True, optimize=0)
        decoded = independent_decode_transport(raw, payload)
        assert decoded == row['independent_decode']
        assert row['payload_cap'] == 131072 and row['payload_remaining_bytes'] == 131072-len(payload)
        for width in row['command_lines']:
            argv = list(width['non_code_argv'])
            assert argv[6] == '<transport>' and len(argv) == width['argv_count'] and width['runnable_invocation'] is False
            argv[6] = raw.decode('utf-8')
            units = len(subprocess.list2cmdline(argv).encode('utf-16-le')) // 2 + 1
            assert units == width['utf16_units_including_nul'] and width['remaining_units'] == 30000-units and units <= 30000
        decoded_rows.append(dict(core=row['core'], transport_pin=pin(raw), decoded_pin=pin(payload)))
    return dict(accepted=True, source_count=len(raws), source_node_count=report['interface_evidence']['node_count'],
        decoded_rows=decoded_rows, project_target_modules_executed=0, project_children_spawned=0,
        executed_control_modules=['driver', 'route_audit', 'contract_snapshot'],
        full_role_entry_connected=False, resource_admission=False, run_authority=False, actual_F=False)


def route_contract():
    return dict(schema='staged_saved_F_preentry_route_preparation_v1', authority='DRAFT_NONAUTHORITATIVE',
        source_epoch=SOURCE_EPOCH,
        selected_route='source_specific_suspended_channel_successor',
        required_order=['host_full_context_ACK', 'create_only_manifest_transport_descriptor_complete',
            'manifest_pin_bound_to_argv_and_header_descriptor', 'channel_create', 'suspended_owner_create', 'bind_actual_PID_creation',
            'publish_binding', 'resume_thread_once', 'child_open_only_endpoint', 'child_physical_header_and_identity_check',
            'endpoint_owned', 'manifest_read', 'self_resource_open', 'Source49', 'lease_inputs_transfer_record',
            'runtime_PREPARING_anchor', 'runtime_owner_commit', 'ADOPTED', 'pending_B_S',
            'IMPORTING_Guard2_install', 'audit_handoff', 'profile_matched_LIVE', 'one_shot_role_claim'],
        open_source_interfaces=['full_request_offer_ACK', 'broker_create_only_manifest_transport_descriptor_and_full_role_constructor', 'pre_manifest_endpoint_kernel',
            'thin_entry_Core_API', 'capsule_transfer_and_cleanup_domains', 'Namespace_full_role_lifetime',
            'Permission_external_root_Guard2', 'LIVE_source_role_factory', 'source_launcher_inner_outer_quiet',
            'new_startup_import_profile_and_whole_cost_admission'],
        native_diagnostic_failure_stop_matrix=native_failure_matrix(),
        native_diagnostic_crosscutting=['non_inheritable_handles_and_physical_close', 'OS_commandline_and_payload',
            'Job_members_and_two_quiet_boundaries', 'new_startup_import_profiles'],
        module_execution=dict(executed_control_modules=['driver', 'route_audit', 'contract_snapshot'],
            repository_transport_compiler_modules=1, isolated_parent_minifier_definitions=1,
            core=0, probe=0, parent_modules=0, Source49_modules=0, Native_target=0),
        P1_reads=0, validation_children_spawned=0, project_children_spawned=0,
        startup_profile_equivalence_verified=False, full_role_entry_connected=False,
        resource_admission=False, run_authority=False, actual_F=False, formal_result=False)


def snapshot():
    raws = {name: (ROOT / path).read_bytes() for name, path in FILES.items()}
    evidence = interface_witnesses(raws)
    baselines = transport_baselines(raws)
    for name, path in FILES.items():
        assert (ROOT / path).read_bytes() == raws[name], 'source changed during static audit'
    return dict(route_contract(), source_pins={str(ROOT / FILES[name]): pin(raw) for name, raw in raws.items()},
        interface_evidence=evidence, transport_baselines=baselines)


if __name__ == '__main__':
    print(canonical(snapshot()).decode('ascii'))
