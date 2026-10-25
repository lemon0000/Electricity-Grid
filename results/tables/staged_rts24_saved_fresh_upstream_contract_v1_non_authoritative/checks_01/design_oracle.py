"""Independent structural oracle. It does not validate or authorize live actors."""
import copy
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
ROLES = ('controller', 'parent', 'fresh')
PRODUCERS = dict(controller='broker', parent='controller', fresh='parent')

def raw(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('ascii')

def pin(value):
    return dict(bytes=len(value), sha256=sha256(value).hexdigest())

def pairs(items):
    value = {}
    for key, item in items:
        assert key not in value, 'duplicate key'
        value[key] = item
    return value

def read(path):
    data = path.read_bytes()
    value = json.loads(data, object_pairs_hook=pairs, parse_constant=lambda _: (_ for _ in ()).throw(AssertionError('nonfinite')))
    assert raw(value) == data, 'noncanonical design JSON'
    return value

def acyclic(order, edges):
    assert len(set(order)) == len(order)
    positions = {n: i for i, n in enumerate(order)}
    for a, b in edges:
        assert a in positions and b in positions and positions[a] < positions[b], (a, b)

def object_bound(f, types):
    values = [len(raw(t['literal'])) if type(t) is dict else types[t]['encoded_max'] for t in f.values()]
    return 2 + max(0, len(f)-1) + sum(len(raw(k))+1+n for (k, _), n in zip(f.items(), values))

def structure(registry, dag, templates, macro):
    expected = {'ACK'} | {r+'_'+k for r in ROLES for k in ('permit_binding', 'entry_packet', 'stage_descriptor')}
    schemas = registry['schemas']
    assert set(schemas) == expected and registry['schema_count'] == 10
    assert registry['implemented'] is False and registry['production_data_validator_implemented'] is False
    assert registry['cross_field_obligations_implemented'] is False and len(registry['open_domains']) == 4
    assert len({s['schema_literal'] for s in schemas.values()}) == 10
    forbidden = {'packet_sha', 'argv_sha', 'descriptor_sha', 'stage_descriptor_sha', 'entry_header_sha',
                 'owner_pid', 'owner_creation_filetime', 'child_identity', 'role', 'run_authority'}
    bounds = {}
    for name, domain in schemas.items():
        assert domain['implemented'] is False and domain['edge_kind'] == 'binding_data'
        assert all(domain[key] is False for key in ('role_bootstrap', 'run_authority', 'resource_admission', 'scientific_evidence_adopted', 'formal_result'))
        assert domain['fields']['schema'] == {'literal': domain['schema_literal']}
        assert domain['fields']['data_only'] == 'true'
        assert domain['producer'] == ('host' if name == 'ACK' else PRODUCERS[domain['role_literal']])
        assert domain['consumer'] == ('broker' if name == 'ACK' else domain['role_literal'])
        edge = [domain['emit_node'], domain['consume_node']]
        assert edge in dag['data_order_edges'], edge
        assert dag['node_roles'][edge[0]] == domain['producer'] and dag['node_roles'][edge[1]] == domain['consumer']
        assert domain['emission_capability_required']['producer_role'] == domain['producer']
        assert domain['emission_capability_required']['exact_type'].startswith('_')
        assert domain['consumer_receives_capability'] is False
        equalities = {}
        for field, artifact in (('runtime_binding_contract_sha','runtime_binding_contract_v2.json'), ('deadline_profile_sha','deadline_contract_v2.json'),
                                ('descriptor_template_sha','fixed_templates.json'), ('entry_transport_contract_sha','fixed_templates.json')):
            if field in domain['fields']:
                item = registry['template_pin'] if artifact == 'fixed_templates.json' else registry['fixed_inputs'][artifact]
                equalities[field] = {'artifact': artifact, 'literal': item['sha256']}
        assert domain['field_equalities'] == equalities
        if name != 'ACK' and not name.endswith('stage_descriptor'):
            f = domain['fields']
            if domain['role_literal'] == 'controller':
                assert not any(k.startswith('reservation_') for k in f)
                assert {'controller_attempt_nonce','attempt_commit_sha','attempt_started','attempt_deadline'} <= set(f)
            else:
                assert {'reservation_nonce','reservation_commit_sha','reservation_started','reservation_deadline'} <= set(f)
                assert not any(k.startswith('attempt_') or k.startswith('controller_attempt_') for k in f)
        if name.endswith('entry_packet'):
            assert not forbidden.intersection(domain['fields'])
            assert {'descriptor_template_sha', 'entry_transport_contract_sha', 'permit_binding_sha', 'context_receipt'} <= set(domain['fields'])
            assert domain['encoded_value_cap'] == 32768
        if name.endswith('permit_binding'):
            assert not forbidden.intersection(domain['fields']) and domain['encoded_value_cap'] == 4096
            assert {'producer_identity', 'active_deadline', 'closed_deadline'} <= set(domain['fields'])
        if name.endswith('stage_descriptor'):
            assert domain['encoded_value_cap'] == 3072
            base = templates['production_descriptor_values'][domain['role_literal']]
            assert set(domain['fields']) == set(base) | {'schema','data_only','packet_sha','permit_binding_sha','deadline_profile_sha'}
            for key, value in base.items(): assert raw(domain['fields'][key]) == raw({'literal':value})
        bound = object_bound(domain['fields'], registry['types'])
        assert bound <= domain['encoded_value_cap'], (name, bound)
        bounds[name] = bound
    assert schemas['ACK']['encoded_value_cap'] == 3072 and bounds['ACK']+363 <= 4096
    transport = templates['entry_transport']
    assert transport['frame_extra_bound'] == 363 and transport['physical_extra'] == 44
    assert (transport['binding_value_cap'],transport['binding_raw_cap'],transport['binding_physical_cap']) == (4096,4608,4652)
    assert (transport['packet_value_cap'],transport['packet_raw_cap'],transport['packet_physical_cap']) == (32768,36864,36908)
    for role in ROLES:
        for suffix, slot in (('permit_binding','binding'),('entry_packet','packet')):
            name = role+'_'+suffix
            assert bounds[name] <= schemas[name]['encoded_value_cap'] == transport[slot+'_value_cap']
            assert schemas[name]['encoded_value_cap']+363 <= transport[slot+'_raw_cap']
            assert transport[slot+'_raw_cap']+44 == transport[slot+'_physical_cap']
    for role, upstream, other in (('parent', 'controller_G0_projection_sha', 'parent_hold_projection_sha'),
                                  ('fresh', 'parent_hold_projection_sha', 'controller_G0_projection_sha')):
        for suffix in ('permit_binding', 'entry_packet'):
            f = schemas[role+'_'+suffix]['fields']
            assert upstream in f and other not in f
    assert 'ACK_sha' in schemas['controller_entry_packet']['fields']
    assert not any(n.startswith('fresh_issuer') for n in dag['node_roles'])
    assert templates['entry_transport']['retry_with_new_nonce'] is False
    assert templates['entry_transport']['single_constructor_attempt_consumed_before_first_allocation'] is True
    assert templates['entry_transport']['kernel_producer_authentication'] is False
    assert templates['entry_transport']['instance_header_schema'] == 'OPEN_NOT_IMPLEMENTED'
    assert templates['hash_inputs'] == {}  # Fixed template never reverse-pins the registry.
    phase_names = dict(fresh=['fresh'], parent=['parent','fresh','inner_quiesce','inner_terminal','parent_compare'],
        controller=['prepare','parent','fresh','inner_quiesce','inner_terminal','parent_compare','outer_quiesce','outer_terminal','final_check','final_publish'])
    phase_caps = dict(prepare=10,parent=45,fresh=40,inner_quiesce=5,inner_terminal=5,parent_compare=15,outer_quiesce=5,outer_terminal=10,final_check=15,final_publish=15)
    for role in ROLES:
        total, quiet, terminal = dict(fresh=(50.,5.,5.),parent=(125.,5.,10.),controller=(180.,5.,5.))[role]
        expected_base = dict(authority='DRAFT_NONAUTHORITATIVE',mode='production_descriptor_only',role=role,preset=None,
            phases=phase_names[role],phase_seconds=[float(phase_caps[p]) for p in phase_names[role]],total_seconds=total,
            quiesce_seconds=quiet,terminal_seconds=terminal,rss_bytes=1024**3,process_commit_bytes=1024**3,
            job_commit_bytes=2*1024**3,member_handles=1024)
        assert raw(templates['production_descriptor_values'][role]) == raw(expected_base)
    assert templates['deadlines'] == {'controller': [155, 165], 'parent': [110, 125], 'fresh': [80, 90]}
    assert dag['implemented'] is False and dag['channel_allocation_consumes_original_attempt'] is True
    assert dag['producer_kernel_authentication_by_child'] is False
    order = dag['topological_order']
    assert len(order) == 59 and set(macro['topological_order']) <= set(order)
    assert {n: dag['node_roles'][n] for n in macro['node_roles']} == macro['node_roles']
    edges = dag['data_order_edges']
    acyclic(order, edges + dag['same_process_capability_edges'])
    assert all(dag['node_roles'][a] == dag['node_roles'][b] for a, b in dag['same_process_capability_edges'])
    assert all(edge in dag['same_process_capability_edges'] for edge in macro['same_process_capability_edges'])
    for role in ROLES:
        expansion = [role+'_'+s for s in ('permit', 'permit_binding', 'packet', 'descriptor', 'argv',
                                        'allocation_attempt', 'owner_constructed', 'header_bound', 'release', 'bootstrap')]
        assert dag['entry_expansions'][role] == expansion
        assert all([a, b] in edges for a, b in zip(expansion, expansion[1:]))
        assert [role+'_permit', role+'_owner_constructed'] not in edges
        assert [role+'_owner_constructed', role+'_bootstrap'] not in edges
        grammar = registry['argv_grammars'][role]; tokens = grammar['tokens']
        assert tokens[:5] == ['EXE', '-B', '-s', 'ENTRY', '--saved-successor-'+role]
        assert len(tokens) == grammar['exact_count'] == (25 if role == 'controller' else 19)
        assert '--role' not in tokens and grammar['implemented'] is False
        assert tokens[5:19:2] == ['--entry-name', '--entry-nonce', '--packet-sha', '--context-sha', '--stage-name', '--stage-nonce', '--descriptor-sha']
        assert ('--mailbox-name' in tokens) == (role == 'controller')
    acyclic(dag['static_hash_order'], dag['static_hash_edges'])
    # Old StageChannel header shape: descriptor maximum plus exact outer keys/scalars.
    header = dict(schema='staged_saved_F_memory_header_v1', context_sha='f'*64, nonce='f'*64,
                  descriptor=None, owner_pid=2**32-1, owner_creation_filetime=2**64-1, slots=16, slot_bytes=4096)
    header_bound = len(raw(header))-4+3072
    assert header_bound+44 <= 4096
    return bounds, header_bound

def verify():
    registry = read(HERE/'protocol_domains.json'); dag = read(HERE/'protocol_dag.json')
    templates = read(HERE/'fixed_templates.json'); matrix = read(HERE/'verification_matrix.json')
    baseline = read(HERE/'baseline.json')
    prior = ROOT/'results/tables/staged_rts24_saved_fresh_runtime_binding_v1_non_authoritative/checks_01'
    for name, expected in registry['fixed_inputs'].items():
        assert pin((prior/name).read_bytes()) == expected == baseline['inputs'][(prior/name).relative_to(ROOT).as_posix()]
    macro = json.loads((prior/'capability_edges_v3.json').read_bytes())
    assert pin((HERE/'fixed_templates.json').read_bytes()) == registry['template_pin']
    assert pin((HERE/'protocol_domains.json').read_bytes()) == dag['registry_pin'] == matrix['registry_pin']
    assert pin((HERE/'protocol_dag.json').read_bytes()) == matrix['dag_pin']
    assert dag['macro_pin'] == registry['fixed_inputs']['capability_edges_v3.json']
    bounds, header_bound = structure(registry, dag, templates, macro)
    # Mutate architecture data in RAM. These are design checks, never runtime fault evidence.
    mutations = []
    def reject(label, change):
        r, d, t = copy.deepcopy(registry), copy.deepcopy(dag), copy.deepcopy(templates)
        change(r, d, t)
        try: structure(r, d, t, macro)
        except (AssertionError, KeyError): mutations.append(label)
        else: raise AssertionError('design mutation accepted: '+label)
    reject('packet contains argv SHA', lambda r,d,t: r['schemas']['fresh_entry_packet']['fields'].update(argv_sha='sha256'))
    reject('packet contains descriptor instance SHA', lambda r,d,t: r['schemas']['parent_entry_packet']['fields'].update(stage_descriptor_sha='sha256'))
    reject('packet contains entry header instance SHA', lambda r,d,t: r['schemas']['controller_entry_packet']['fields'].update(entry_header_sha='sha256'))
    reject('permit contains future child identity', lambda r,d,t: r['schemas']['fresh_permit_binding']['fields'].update(owner_pid='identity'))
    reject('fresh receives G0 in place of hold', lambda r,d,t: r['schemas']['fresh_entry_packet']['fields'].update(controller_G0_projection_sha=r['schemas']['fresh_entry_packet']['fields'].pop('parent_hold_projection_sha')))
    reject('role schema collision', lambda r,d,t: r['schemas']['parent_entry_packet'].update(schema_literal=r['schemas']['fresh_entry_packet']['schema_literal']))
    reject('authority true', lambda r,d,t: r['schemas']['fresh_entry_packet'].update(run_authority=True))
    reject('late owner feeds packet cycle', lambda r,d,t: d['data_order_edges'].append(['fresh_owner_constructed','fresh_packet']))
    reject('cross process capability', lambda r,d,t: d['same_process_capability_edges'].append(['fresh_permit','fresh_bootstrap']))
    reject('static registry/template hash cycle', lambda r,d,t: d['static_hash_edges'].append(['protocol_domains.json','fixed_templates.json']))
    reject('template reverse pins registry', lambda r,d,t: t.update(hash_inputs={'protocol_domains.json': 'f'*64}))
    reject('capacity exceeded by legal path maximum', lambda r,d,t: r['types']['path'].update(encoded_max=32768))
    reject('generic role argv', lambda r,d,t: r['argv_grammars']['parent']['tokens'].__setitem__(4,'--role'))
    reject('nonce retry permitted', lambda r,d,t: t['entry_transport'].update(retry_with_new_nonce=True))
    reject('child independently authenticates producer', lambda r,d,t: d.update(producer_kernel_authentication_by_child=True))
    reject('controller has nonexistent RoleStore reservation', lambda r,d,t: r['schemas']['controller_entry_packet']['fields'].update(reservation_nonce='sha256'))
    reject('descriptor loses phase resource semantics', lambda r,d,t: r['schemas']['parent_stage_descriptor']['fields'].pop('phase_seconds'))
    reject('fixed contract SHA not equal to pinned artifact', lambda r,d,t: r['schemas']['fresh_entry_packet']['field_equalities']['runtime_binding_contract_sha'].update(literal='0'*64))
    reject('child receives producer permit capability', lambda r,d,t: r['schemas']['parent_entry_packet'].update(consumer_receives_capability=True))
    reject('binding raw transport cap shrunk', lambda r,d,t: t['entry_transport'].update(binding_raw_cap=1024))
    reject('packet physical transport cap shrunk', lambda r,d,t: t['entry_transport'].update(packet_physical_cap=32768))
    assert len(matrix['runtime_fault_matrix']) == 26 and all(row['status'] == 'UNRUN' for row in matrix['runtime_fault_matrix'])
    assert all(matrix[key] is False for key in ('implemented','actual_F','scientific_evidence_adopted','resource_admission','formal_result'))
    return dict(authority='DRAFT_NONAUTHORITATIVE', exact_data_schemas=10, expanded_nodes=59,
                design_mutations_rejected=len(mutations), mutation_names=mutations, encoded_upper_bounds=bounds,
                stage_header_encoded_upper_bound=header_bound, canonical_upper_bounds_proved=True,
                transport_composition_conditional_on_proposed_frame_bound=True,
                runtime_faults_unrun=26, production_data_validator_implemented=False,
                runtime_bootstrap_implemented=False, runtime_cross_field_verification=False,
                producer_kernel_authentication_by_child=False, actual_F=False,
                scientific_evidence_adopted=False, resource_admission=False, formal_result=False,
                scientific_ENTRY_imported=False)

def guard(event, args):
    if event in ('subprocess.Popen','os.system','os.posix_spawn','os.spawn'):
        raise AssertionError('static target cannot launch another process')
    if event == 'import' and args and str(args[0]).split('.')[0] in ('experiments','src','numpy','scipy','pyomo','highspy'):
        raise AssertionError('static target cannot import project/science')

if __name__ == '__main__':
    sys.addaudithook(guard)
    result = verify()
    if sys.argv[1:] == ['--finalize']:
        baseline = read(HERE/'baseline.json')
        document_pins, links = {}, []
        paths = [ROOT/n for n in baseline['navigation_before']] + [ROOT/n for n in baseline['new_documents']]
        for path in paths:
            text = path.read_text(encoding='utf-8'); document_pins[path.relative_to(ROOT).as_posix()] = pin(path.read_bytes())
            if path.relative_to(ROOT).as_posix() in baseline['navigation_before']:
                before = baseline['navigation_before'][path.relative_to(ROOT).as_posix()]
                data = path.read_bytes(); count = before['bytes']
                assert pin(data[-count:]) == before, 'historical navigation bytes changed'
                link_text = data[:-count].decode('utf-8')
            else:
                link_text = text
            for target in re.findall(r'\]\(([^)]+)\)', link_text):
                if '://' in target or target.startswith('#'): continue
                target = target.split('#')[0]
                assert (path.parent/target).resolve().exists(), (path, target)
                links.append(target)
        with (HERE/'document_checks.json').open('xb') as stream:
            stream.write(raw(dict(document_pins=document_pins, links_resolve=True, checked_links=len(links))))
    else:
        assert not sys.argv[1:]
    print(json.dumps(result, sort_keys=True))
