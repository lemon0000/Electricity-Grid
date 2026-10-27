"""Static successor binding obligations; never imports or executes audited sources."""
import ast
import builtins
import dis
import hashlib
import json
from pathlib import Path
import sys
from types import CodeType


ENTRY = 'experiments/staged_rts24_saved_fresh_adoption_v1.py'
ADAPTER = 'src/staged_rts24_saved_fresh_adoption_v1.py'
BASE = 'results/tables/staged_rts24_saved_fresh_machinery_transition_v1_non_authoritative/checks_01/'
LEGACY = 'results/tables/staged_rts24_saved_fresh_runtime_binding_v1_non_authoritative/checks_01/root_contracts_v2.json'
CAPABILITY = 'results/tables/staged_rts24_saved_fresh_runtime_binding_v1_non_authoritative/checks_01/capability_edges_v3.json'
CAPABILITY_PIN = dict(bytes=5677, sha256='b50111372ac810e86e3a5edebe654f3c0e15c2e94905399d4c4ba06a42285536')
MECHANICAL = 'results/tables/staged_rts24_saved_fresh_machinery_transition_archive_v1_non_authoritative/'
ENTRY_ROOTS = ('open_saved_self_anchor', 'SavedSelfProcessAnchor', '_saved_self_api',
    'capture_saved_direct_entry_observation', 'SavedDirectEntryObservation', '_direct_entry_main',
    '_ordinary_direct_entry_cli', 'source_names', 'source_pins', 'capture_saved_expectation',
    'context_from_saved_expectation',
    'open_saved_successor_import_boundary', 'load_saved_successor_dependencies', 'SavedSuccessorImportBoundary')
ADAPTER_ROOTS = ('hold', 'capture', 'bookend', 'caller_image', 'sources', 'validate_metrics',
    'replay', '_replay', 'bind_payload', 'validate_payload', 'compare_payloads', 'project_metrics')
EXTERNAL_MODULES = ('numpy.testing._private.utils', 'subprocess', 'pyomo.common.deprecation', 'pyomo.common.dependencies')
DYNAMIC = frozenset(('getattr', 'setattr', 'delattr', 'globals', 'locals', 'eval', 'exec', '__import__'))
FALSE_GATES = dict(independent_root_verified=False, full_runtime_binding_verified=False,
    expected_truth_external=False,
    baseline_root_authenticated=False, cold_main_self_anchor_verified=False, full_P1_content_verified=False,
    permit_issued=False, F_launch_admitted=False, native_authorized=False,
    finder_registry_contents_verified=False, finder_behavior_closure_verified=False,
    unobserved_RAM_ABA_verified=False, actual_filesystem_alias_verified=False, arbitrary_native_effects_verified=False,
    role_bootstrap=False, actual_F=False, run_authority=False, resource_admission=False,
    scientific_evidence_adopted=False, formal_result=False, production_seal=False)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('ascii')


def pin(raw):
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verified_bytes(path, expected):
    raw = Path(path).read_bytes()
    require(pin(raw) == expected, 'static input bytes changed: ' + str(path))
    return raw


def module_name(path):
    return path[:-3].replace('/', '.').removesuffix('.__init__')


def import_target(node, alias, module, package):
    if isinstance(node, ast.Import):
        return alias.name
    if node.level:
        parts = package.split('.')
        require(node.level <= len(parts), 'relative import escapes supplied package')
        base = '.'.join(parts[:len(parts) - node.level + 1])
        prefix = '.'.join(p for p in (base, node.module) if p)
    else:
        prefix = node.module or ''
    return '.'.join(p for p in (prefix, alias.name) if p)


def code_facts(code):
    names, writes, freevars, cellvars = set(), set(), set(), set()
    def walk(unit):
        freevars.update(unit.co_freevars); cellvars.update(unit.co_cellvars)
        for instruction in dis.get_instructions(unit):
            if instruction.opname in ('LOAD_GLOBAL', 'LOAD_NAME'):
                names.add(instruction.argval)
            elif instruction.opname in ('STORE_GLOBAL', 'DELETE_GLOBAL'):
                writes.add(instruction.argval)
        for child in unit.co_consts:
            if isinstance(child, CodeType):
                walk(child)
    walk(code)
    return names, writes, freevars, cellvars


class StaticModule:
    def __init__(self, name, path, raw):
        self.name, self.path, self.raw = name, path, raw
        self.package = name if path.replace('\\', '/').endswith('/__init__.py') else name.rpartition('.')[0]
        self.tree = ast.parse(raw, filename=path)
        unit = compile(raw, path, 'exec', dont_inherit=True, optimize=0)
        self.codes = {}
        def walk(code):
            self.codes.setdefault(code.co_qualname, []).append(code)
            for child in code.co_consts:
                if isinstance(child, CodeType):
                    walk(child)
        walk(unit)
        self.symbols = {}
        def add(name, node):
            self.symbols.setdefault(name, []).append(node)
        def statements(nodes, prefix=''):
            for node in nodes:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    name = prefix + node.name
                    add(name, node)
                    if isinstance(node, ast.ClassDef):
                        statements(node.body, name + '.')
                elif not prefix and isinstance(node, (ast.Import, ast.ImportFrom)):
                    for alias in node.names:
                        if alias.name != '*':
                            add(alias.asname or alias.name.split('.')[0], node)
                elif not prefix and isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                    for target in targets:
                        for child in ast.walk(target):
                            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
                                add(child.id, node)
                elif not prefix:
                    for field in ('body', 'orelse', 'finalbody'):
                        body = getattr(node, field, None)
                        if isinstance(body, list):
                            statements(body)
                    for handler in getattr(node, 'handlers', ()):
                        statements(handler.body)
        statements(self.tree.body)

    def imports(self, node):
        targets = []
        for item in ast.walk(node):
            if isinstance(item, (ast.Import, ast.ImportFrom)):
                for alias in item.names:
                    targets.append(import_target(item, alias, self.name, self.package))
        return sorted(set(targets))

    def facts(self, name):
        definitions = self.symbols[name]
        globals_, writes, attrs, dynamic, imported = set(), set(), set(), set(), set()
        definition_names = set()
        freevars, cellvars = set(), set()
        compiler_elided = False
        for node in definitions:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                codes = self.codes.get(name, ())
                if not codes:
                    # CPython may remove declarations after an unconditional raise/return.
                    # Keep their syntax as an open candidate; never execute it to obtain code.
                    compiler_elided = True
                    globals_.update(n.id for n in ast.walk(node) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load))
                for code in codes:
                    g, w, f, c = code_facts(code)
                    globals_.update(g); writes.update(w)
                    freevars.update(f); cellvars.update(c)
                expressions = list(node.decorator_list)
                if isinstance(node, ast.ClassDef):
                    expressions += list(node.bases) + [k.value for k in node.keywords]
                else:
                    expressions += list(node.args.defaults) + [v for v in node.args.kw_defaults if v is not None]
                    expressions += [a.annotation for a in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs) if a.annotation]
                    expressions += [v for v in (node.returns, getattr(node.args.vararg, 'annotation', None), getattr(node.args.kwarg, 'annotation', None)) if v]
                for expression in expressions:
                    definition_names.update(n.id for n in ast.walk(expression) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load))
            elif not isinstance(node, (ast.Import, ast.ImportFrom)):
                globals_.update(n.id for n in ast.walk(node) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load))
            imported.update(self.imports(node))
            for item in ast.walk(node):
                if isinstance(item, ast.Attribute):
                    attrs.add(ast.unparse(item))
                if isinstance(item, ast.Call) and isinstance(item.func, ast.Name) and item.func.id in DYNAMIC:
                    dynamic.add(item.func.id)
        globals_.update(definition_names)
        return dict(kind=type(definitions[0]).__name__, alternatives=len(definitions),
            declaration_ast_pins=[pin(ast.dump(n, include_attributes=False).encode()) for n in definitions],
            global_names=sorted(globals_), global_writes=sorted(writes),
            attribute_expressions=sorted(attrs), dynamic_name_operators=sorted(dynamic),
            imports=sorted(imported), definition_expression_names=sorted(definition_names),
            freevars=sorted(freevars), cellvars=sorted(cellvars), compiler_elided_definition=compiler_elided)


class ReferenceGraph:
    """Conservative declaration references with explicit runtime obligations."""
    def __init__(self, modules):
        require(len({name.casefold() for name in modules}) == len(modules), 'casefold module alias')
        require(len({m.path.replace('\\', '/').casefold() for m in modules.values()}) == len(modules), 'casefold source path alias')
        self.modules = modules

    def target(self, dotted):
        for name in sorted(self.modules, key=lambda v: (-len(v), v)):
            if dotted == name:
                return 'module:' + name
            if dotted.startswith(name + '.'):
                suffix = dotted[len(name) + 1:]
                if suffix in self.modules[name].symbols:
                    return name + '::' + suffix
                return 'unresolved:' + dotted
        return 'external:' + dotted

    def resolve(self, module, name):
        if name in module.symbols:
            return module.name + '::' + name
        if name in vars(builtins):
            return 'builtin_lookup:' + name
        if name in ('__name__', '__file__', '__package__', '__spec__', '__builtins__', '__annotations__'):
            return 'interpreter_binding:' + name
        return 'unresolved:' + module.name + '::' + name

    def build(self, roots):
        require(len(roots) == len(set(roots)), 'duplicate declared roots')
        for key in roots:
            if key.startswith('module:'):
                require(key[7:] in self.modules, 'missing module root')
                continue
            module, separator, name = key.partition('::')
            require(separator and module in self.modules and name in self.modules[module].symbols, 'missing declared root: ' + key)
            require(len(self.modules[module].symbols[name]) == 1, 'ambiguous declared root: ' + key)
        nodes, edges, pending = {}, set(), list(roots)
        while pending:
            key = pending.pop()
            if key in nodes:
                continue
            require(len(nodes) < 4096, 'static symbol cap')
            dependencies = set()
            if key.startswith('module:'):
                module = self.modules[key[7:]]
                # Module import executes every top-level declaration, including optional branches.
                dependencies.update(module.name + '::' + n for n in module.symbols)
                for target in module.imports(module.tree):
                    dependencies.add('dynamic_open:star_import:' + target if target.endswith('.*') else self.target(target))
                dependencies.add('dynamic_open:module_initialization:' + module.name)
                facts = dict(kind='module_initialization', runtime_verified=False,
                    obligation='top_level_execution_and_side_effects_require_import_policy_and_startup_TCB; declaration_edges_do_not_mean_function_calls')
            elif key.partition('::')[0] in self.modules:
                module_name_, name = key.split('::', 1)
                require(module_name_ in self.modules and name in self.modules[module_name_].symbols, 'missing declared root: ' + key)
                module = self.modules[module_name_]
                facts = module.facts(name)
                facts['source'] = module.path
                facts['runtime_verified'] = False
                facts['builtin_fallback_candidates'] = sorted(n for n in facts['global_names'] if n in vars(builtins))
                for global_ in facts['global_names']:
                    dependencies.add(self.resolve(module, global_))
                dependencies.update('builtin_lookup:' + n for n in facts['builtin_fallback_candidates'])
                for target in facts['imports']:
                    dependencies.add('dynamic_open:star_import:' + target if target.endswith('.*') else self.target(target))
                if facts['attribute_expressions']:
                    dependencies.add('dynamic_open:object_dispatch:' + key)
                if facts['dynamic_name_operators']:
                    dependencies.add('dynamic_open:name_lookup:' + key)
                if facts['global_writes']:
                    dependencies.add('runtime_state:global_writes:' + key)
                if facts['freevars'] or facts['cellvars']:
                    dependencies.add('runtime_state:closure_cells:' + key)
                if facts['alternatives'] != 1:
                    dependencies.add('runtime_state:ambiguous_binding:' + key)
                if facts['compiler_elided_definition']:
                    dependencies.add('dynamic_open:compiler_elided:' + key)
                if facts['kind'] == 'ClassDef':
                    dependencies.update(module.name + '::' + s for s in module.symbols if s.startswith(name + '.'))
                facts['obligation'] = 'loaded_binding_defaults_closure_class_registry_object_dispatch_unverified'
            else:
                facts = dict(kind=key.split(':', 1)[0], runtime_verified=False,
                    obligation='explicit_boundary_requires_future_verifier_or_declared_TCB')
            nodes[key] = facts
            for dependency in dependencies:
                edges.add((key, dependency))
                require(len(edges) <= 65536, 'static reference edge cap')
                if dependency not in nodes:
                    pending.append(dependency)
        edge_list = sorted([a, b, edge_disposition(b)] for a, b in edges)
        result = dict(nodes=dict(sorted(nodes.items())), edges=edge_list,
            recursive_components=strong_components(nodes, edges),
            complete_runtime_call_graph=False, runtime_closure_verified=False)
        result['edge_disposition_counts'] = {d: sum(e[2] == d for e in edge_list) for d in sorted({e[2] for e in edge_list})}
        validate_reference_graph(result)
        return result


def edge_disposition(target):
    if target.startswith('dynamic_open:'):
        return 'dynamic_open'
    if target.startswith('unresolved:'):
        return 'runtime_required'
    if target.startswith(('external:ctypes', 'external:_ctypes', 'external:_winapi', 'external:highspy', 'external:numpy')):
        return 'native_open'
    if target.startswith(('external:', 'interpreter_binding:')):
        return 'external_root_required'
    if target.startswith(('builtin_lookup:', 'runtime_state:')):
        return 'runtime_required'
    return 'static_candidate'


def validate_reference_graph(graph):
    require(graph['runtime_closure_verified'] is False and graph['complete_runtime_call_graph'] is False, 'static graph cannot verify runtime')
    nodes = graph['nodes']
    require(all(v['runtime_verified'] is False for v in nodes.values()), 'static nodes cannot verify runtime')
    for source, target, disposition in graph['edges']:
        require(source in nodes and target in nodes, 'unknown static reference endpoint')
        require(disposition == edge_disposition(target), 'reference disposition cannot promote open dependency')


def strong_components(nodes, edges):
    adjacency = {n: [] for n in nodes}
    reverse = {n: [] for n in nodes}
    for a, b in edges:
        adjacency[a].append(b); reverse[b].append(a)
    seen, order = set(), []
    for start in sorted(nodes):
        stack = [(start, False)]
        while stack:
            item, closing = stack.pop()
            if closing:
                order.append(item)
            elif item not in seen:
                seen.add(item); stack.append((item, True))
                stack.extend((n, False) for n in sorted(adjacency[item], reverse=True) if n not in seen)
    seen, result = set(), []
    for start in reversed(order):
        if start in seen:
            continue
        component, stack = [], [start]
        while stack:
            item = stack.pop()
            if item in seen:
                continue
            seen.add(item); component.append(item)
            stack.extend(reverse[item])
        if len(component) > 1 or (start, start) in edges:
            result.append(sorted(component))
    return sorted(result)


def validate_evidence_dag(nodes):
    require(type(nodes) is dict and bool(nodes), 'nonempty evidence DAG required')
    require(all(type(v) is dict and v.get('verified') is False for v in nodes.values()), 'static evidence cannot verify capabilities')
    require(all(v.get('produces_authority', False) is False for v in nodes.values()), 'static DAG cannot produce authority')
    require(all(v.get('status', 'UNIMPLEMENTED') == 'UNIMPLEMENTED'
        and v.get('evidence_ref') is None and v.get('runtime_witness') is None for v in nodes.values()), 'unimplemented DAG cannot claim evidence')
    require(all(v.get('artifact_pins', {}) == {} for v in nodes.values()), 'unimplemented DAG cannot claim artifact pins')
    order, remaining = [], set(nodes)
    while remaining:
        ready = []
        for name in sorted(remaining):
            dependencies = nodes[name]['requires']
            require(type(dependencies) is list and len(dependencies) == len(set(dependencies)), 'unique evidence dependencies required')
            require(set(dependencies) <= set(nodes), 'unknown evidence dependency')
            holds = nodes[name].get('same_process_holds', [])
            require(type(holds) is list and len(holds) == len(set(holds)) and set(holds) <= set(dependencies), 'held capabilities must be prerequisites')
            require(not holds or nodes[name].get('process_role') in ('host','broker','controller','parent','fresh'), 'held capabilities need a concrete process role')
            require(all(nodes[h].get('process_role') == nodes[name].get('process_role') for h in holds), 'cross-process capability hold')
            if not set(dependencies) & remaining:
                ready.append(name)
        require(bool(ready), 'cyclic evidence dependencies')
        order.extend(ready); remaining.difference_update(ready)
    return order


def evidence_dag():
    repo = Path(__file__).absolute().parents[1]
    legacy = json.loads(verified_bytes(repo/CAPABILITY, CAPABILITY_PIN))
    nodes = {}
    def add(name, role, kind, requires, obligation, holds=()):
        require(name not in nodes, 'duplicate evidence node')
        nodes[name] = dict(requires=list(requires), process_role=role, fact_kind=kind,
            future_verifier=obligation, open_obligations=obligation, same_process_holds=list(holds),
            status='UNIMPLEMENTED', verified=False, produces_authority=False, evidence_ref=None,
            artifact_pins={}, runtime_witness=None, external_authority_source='externally held manifest/owner or separately authorized decision; never child JSON',
            invalidators=['input_or_environment_drift', 'object_registry_or_creator_drift', 'expired_or_spent_nonce'],
            failure_terminal='reject; close only owned resources or retain unresolved with primary/secondary errors')
    add('host_expected', 'external', 'data', [], 'independently held Source49/EXE/profile/argv/environment manifest before project import')
    add('startup_TCB', 'external', 'trust_boundary', [], 'system site/pth/sitecustomize, Python/DLL/kernel/stdlib/native and initial machinery remain OPEN; -B -s does not disable system site')
    for name in ('scientific_protocol', 'whole_workflow_resource_review', 'explicit_F_run_authority'):
        add(name, 'external', 'decision', [], 'separate concrete evidence/authority required; static catalog grants none')
    add('F_external_decisions', 'external', 'decision', ['scientific_protocol', 'whole_workflow_resource_review', 'explicit_F_run_authority'],
        'bundle of three external pre-launch decisions; local bootstrap/runtime/owner conditions remain distinct')
    for name, role in legacy['node_roles'].items():
        same = [a for a, b in legacy['same_process_capability_edges'] if b == name]
        require(all(legacy['node_roles'][a] == role for a in same), 'legacy cross-process capability edge')
        kind = 'capability' if any(t in name for t in ('bootstrap', 'issuer', 'owner', 'permit', 'store', 'hold')) else 'observation'
        if name in ('request', 'context', 'offer', 'ACK', 'START', 'fresh_result', 'controller_return', 'broker_return'):
            kind = 'data'
        add(name, role, kind, [], 'exact original role contract plus successor runtime/owner bindings remain OPEN', same)
    for a, b in legacy['data_order_edges'] + legacy['same_process_capability_edges']:
        if a not in nodes[b]['requires']: nodes[b]['requires'].append(a)
    nodes['broker_owner_armed']['requires'].append('F_external_decisions')
    upstream = dict(host=None, broker='broker_owner_armed', controller='controller_owner_constructed',
        parent='parent_owner_constructed', fresh='fresh_owner_constructed')
    for role, launch in upstream.items():
        previous = ['host_expected', 'startup_TCB'] + ([launch] if launch else [])
        phases = (
            ('pre_ENTRY_bootstrap', 'observation', 'independently pinned stdlib bootstrap before ENTRY import; ENTRY cannot certify its own construction'),
            ('local_self', 'observation', 'retained actual self HANDLEs plus independent upstream process/thread identity'),
            ('cold_main', 'observation', 'exact external expected Source49/main/argv/environment and initial namespaces'),
            ('import_transition', 'observation', 'exact pinned B -> B+M -> D+B+M; historical 94/three cold cases do not verify registry contents or initial B'),
            ('live_lease', 'capability', 'full declared module/code/default/closure/global/class/builtin/registry/native binding; CLOSED import guard cannot substitute'),
            ('full_input', 'capability', 'actual independent full683 hold with external anchor; static catalog reads no P1'),
        )
        for phase, kind, obligation in phases:
            name = role + '_' + phase
            holds = previous if phase not in ('pre_ENTRY_bootstrap',) else []
            add(name, role, kind, previous, obligation, holds)
            previous = [name]
        target = {'host': 'host_expectation', 'broker': 'broker_ready'}.get(role, role + '_bootstrap')
        nodes[target]['requires'].extend(previous)
    add('workflow_closure', 'host', 'observation', ['host_final'], 'all quiet/G0/G1/G2/G3/H3/returns plus canonical reopen and failure costs verified')
    add('scientific_adoption', 'external', 'decision', ['workflow_closure', 'scientific_protocol'], 'independent scientific oracle and applicable formal protocol; separate from run authority')
    return dict(nodes=nodes, topological_order=validate_evidence_dag(nodes),
        original_capability_contract=dict(path=CAPABILITY, pin=CAPABILITY_PIN),
        original_data_edges=legacy['data_order_edges'], original_same_process_edges=legacy['same_process_capability_edges'],
        cross_process_packets_are_binding_data_only=True, all_capabilities_verified=False)


def build_catalog(repo):
    repo = Path(repo)
    admission_raw = verified_bytes(repo/(BASE + 'admission_repair.json'),
        dict(bytes=21981, sha256='f147def983e56f538dc3252d270ad335b83f5a381853c8a42deb281d2ead7244'))
    admission = json.loads(admission_raw)
    require(admission['source_epoch'] == 'acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875', 'fixed predecessor epoch required')
    source_pins = admission['source_pins']
    require(len(source_pins) == 49 and sum(v['bytes'] for v in source_pins.values()) <= 2*1024**2, 'Source49 bounds')
    inputs = {name: verified_bytes(repo/name, expected) for name, expected in source_pins.items()}
    profile_raw = verified_bytes(repo/(BASE + 'import_policy.json'), dict(bytes=3797, sha256='1010bb4d10f29551ea3c4cdd639697ade004321fe70dcec0efe422e1b128acb9'))
    profile = json.loads(profile_raw)
    require(Path(sys.executable).absolute() == Path(profile['executable_path']).absolute()
        and sys.version == profile['python'] and sys.flags.optimize == 0 and sys.dont_write_bytecode and sys.flags.no_user_site == 1,
        'fixed compute compiler/runtime required')
    verified_bytes(profile['executable_path'], profile['executable_pin'])
    legacy_raw = verified_bytes(repo/LEGACY, dict(bytes=45257, sha256='8e9771fa2531cca8dcd6f7abb6c1d123acd40a086005265316565f4af7cd0f16'))
    legacy = json.loads(legacy_raw)
    modules = {module_name(name): StaticModule(module_name(name), name, raw) for name, raw in inputs.items() if name.endswith('.py')}
    external_pins = {}
    for path, expected in profile['external_sources'].items():
        raw = verified_bytes(path, expected)
        match = [name for name in EXTERNAL_MODULES if path.replace('\\', '/').endswith('/' + name.replace('.', '/') + '.py')]
        require(len(match) == 1, 'closed external Python source mapping')
        name = match[0]
        modules[name] = StaticModule(name, path, raw); external_pins[path] = expected
    require(len(external_pins) == 4, 'four external source modules required')
    entry = modules[module_name(ENTRY)]
    current = ['module:' + module_name(p) for p in (ENTRY, ADAPTER)]
    current += [module_name(ENTRY) + '::' + n for n in ENTRY_ROOTS]
    current += [module_name(ENTRY) + '::' + n for n in entry.symbols if '.' not in n and n.startswith(('validate_saved_', 'compose_saved_'))]
    current += [module_name(ADAPTER) + '::' + n for n in ADAPTER_ROOTS]
    current += [m + '::' + n for m, names in {
        'pyomo.common.deprecation': ('MovedModuleFinder', 'MovedModuleLoader', 'deprecation_warning'),
        'pyomo.common.dependencies': ('DeferredImportCallbackFinder', 'DeferredImportCallbackLoader')}.items() for n in names]
    require(len(current) == len(set(current)), 'duplicate current root')
    legacy_disposition = {}
    for key in legacy['roots']:
        path, name = key.split('::')
        legacy_disposition[key] = dict(current_symbol=module_name(path) + '::' + name,
            disposition='scientific_adapter_requires_successor_live_binding' if path == ADAPTER else 'legacy_entry_contract_requires_explicit_successor_bridge',
            current_root_replacement=None, successor_bridge_implemented=False, runtime_reusable=False)
    require(len(legacy_disposition) == 33, 'complete legacy33 disposition required')
    graph = ReferenceGraph(modules).build(sorted(set(current) | {v['current_symbol'] for v in legacy_disposition.values()}))
    result = dict(schema='staged_saved_F_successor_static_root_catalog_v1', authority='DRAFT_NONAUTHORITATIVE',
        source_epoch=admission['source_epoch'], source_pins=source_pins, external_source_pins=external_pins,
        analysis_runtime=dict(executable_path=profile['executable_path'], executable_pin=profile['executable_pin'],
            python=sys.version, optimize=0, dont_inherit=True, dont_write_bytecode=True,
            no_user_site=True,
            analysis_TCB_external_authority=False),
        input_provenance='accepted predecessor development epoch; not independent host authority',
        predecessor_pins={BASE+'admission_repair.json': pin(admission_raw), BASE+'import_policy.json': pin(profile_raw),
            LEGACY: pin(legacy_raw), CAPABILITY: CAPABILITY_PIN},
        current_roots=sorted(current), legacy33_disposition=legacy_disposition, reference_graph=graph,
        required_evidence_dag=evidence_dag(), source_file_roles={name: ('runtime_candidate' if name.startswith(('src/', 'experiments/')) else 'input_non_runtime') for name in source_pins},
        successor_interfaces_open=['independently_pinned_pre_ENTRY_stdlib_bootstrap', 'live_transitive_runtime_lease',
            'broker_START_context_ACK', 'controller_successor_bootstrap_store_issuer',
            'parent_successor_bootstrap_store_issuer', 'fresh_successor_bootstrap_full_hold', 'retained_owner_one_shot_permit'],
        semantic_limits=['static declaration reference graph; not complete runtime call graph',
            'builtin lookups require actual module builtins and startup TCB comparison',
            'local/object attribute dispatch and dynamic imports remain open',
            'finder mapping/callback contents and warning transitive behavior remain open',
            'initial B and system site/pth/customize provenance remain open',
            'no unobserved RAM/native ABA or hidden native I/O certification'], **FALSE_GATES)
    require(len(canonical(result)) <= 4*1024**2, 'single catalog byte cap')
    # Close the static read window; this is not a retained filesystem HANDLE lease.
    for name, expected in source_pins.items():
        verified_bytes(repo/name, expected)
    for path, expected in external_pins.items():
        verified_bytes(path, expected)
    verified_bytes(profile['executable_path'], profile['executable_pin'])
    return result
