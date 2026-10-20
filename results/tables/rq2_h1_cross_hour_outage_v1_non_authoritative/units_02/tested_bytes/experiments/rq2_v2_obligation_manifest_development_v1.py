"""Proof-aware factorized obligation manifest; no executable task admission.

All labels and graph edges are controller/audit bookkeeping, not policy input.
Resolver snapshots are immutable development evidence, not live run authority.
"""
from dataclasses import dataclass, field
import json
from pathlib import Path

from experiments import rq2_v2_cfe_exclusion_development_v1 as exclusion

io, inventory = exclusion.io, exclusion.inventory
ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'rq2_v2_obligation_manifest_development_v1'
CAP = 16 * 1024 * 1024
REPORT = 'results/tables/rq2_v2_cfe_exclusion_v1_non_authoritative/cell_exclusion_audit_v2_final.json'
REPORT_PIN = '2e8c9f07db03426c02f3c38f5f938231cb6ca47f30537ad0d740ed9e22341e7c'
CATALOG = exclusion.CATALOG
CATALOG_PIN = exclusion.PINS[CATALOG]
FLAGS = dict(complete_executable_task_inventory=False,causal_request_keys_materialized=False,
    solver_reuse_verified=False,resource_discounts_applied=False,resource_admission=False,
    formal_execution_ready=False,formal_result=False,native_execution_authorized=False,
    bookkeeping_labels_are_policy_inputs=False)
MISSING = dict(training_lb='same_contract_offline_relaxation_missing',
    training_ub='named_causal_policy_full_training_witness_missing',
    training_b6_actual='training_planning_UB_and_shared_policy_missing',
    holdout='training_feasible_UB_and_named_policy_missing')


def _node(kind, payload, parents):
    record = dict(schema=SCHEMA,kind=kind,payload=payload,
        edges=[dict(parent=p,kind=k,solver_reuse_edge=False) for p,k in parents],
        solver_task_id=None,causal_key=None,runtime_request=None)
    return dict(node_id=io.digest(io.encode(record)),record=record)


def _compile(catalog, report, implementation_pin):
    nodes = []
    def add(kind,payload,parents=()):
        node = _node(kind,payload,parents)
        nodes.append(node)
        return node['node_id']
    protocol = add('approved_contract',dict(sha256=report['protocol_sha256']))
    catalog_node = add('obligation_catalog',dict(sha256=CATALOG_PIN))
    overlay = add('exclusion_overlay',dict(report_sha256=REPORT_PIN,
        protocol_sha256=report['protocol_sha256'],catalog_sha256=CATALOG_PIN,
        implementation_sha256=implementation_pin),
        [(protocol,'proof_reference'),(catalog_node,'proof_reference')])
    witness = add('training_source_witness',dict(report_sha256=REPORT_PIN,
        witness_sha256=report['witness_sha256']),[(protocol,'proof_reference')])
    groups = {pin:add('exact_arithmetic_group',dict(group_sha256=pin,arithmetic=value),
        [(protocol,'proof_reference'),(witness,'proof_reference')])
        for pin,value in sorted(report['arithmetic_groups'].items())}
    proofs = {}
    for pin, proof in sorted(report['proofs'].items()):
        group = io.digest(io.encode(proof['arithmetic']))
        proofs[pin] = add('positive_local_contradiction',dict(proof_sha256=pin,proof=proof),
            [(groups[group],'logical_implication')])
    cells = []
    for cell in report['cells']:
        binding = dict(theta_index=cell['theta_index'],alpha_index=cell['alpha_index'],
            theta=cell['theta'],alpha=cell['alpha'],cell_sha256=cell['cell_sha256'],
            arithmetic_node=groups[cell['arithmetic_group_sha256']],cell_proof_node=None,
            arm_implication_nodes={})
        if cell['proof_sha256'] is not None:
            cell_node = add('cell_contradiction_binding',dict(cell_sha256=cell['cell_sha256'],
                theta=cell['theta'],alpha=cell['alpha'],proof_sha256=cell['proof_sha256']),
                [(catalog_node,'proof_reference'),(proofs[cell['proof_sha256']],'logical_implication')])
            binding['cell_proof_node'] = cell_node
            for arm in exclusion.ARMS:
                binding['arm_implication_nodes'][arm] = add('arm_cell_implication',
                    dict(cell_sha256=cell['cell_sha256'],arm=arm,
                        conclusion='no_complete_training_UB_at_any_registered_D'),
                    [(cell_node,'logical_implication')])
        cells.append(binding)
    return dict(schema=SCHEMA,status='DRAFT_NONAUTHORITATIVE',implementation_sha256=implementation_pin,
        catalog_sha256=CATALOG_PIN,exclusion_report_sha256=REPORT_PIN,
        protocol_sha256=report['protocol_sha256'],catalog=catalog,
        witness_windows={k:report['witness'][k+'_window'] for k in ('power','workload')},
        cells=cells,nodes=nodes,catalog_node=catalog_node,exclusion_overlay_node=overlay,
        source_witness_node=witness,
        arithmetic_group_count=len(groups),positive_proof_group_count=len(proofs),
        contradicted_cell_count=report['contradicted_cell_count'],
        arm_cell_implication_count=sum(len(c['arm_implication_nodes']) for c in cells),
        coverage=report['coverage'],verified_solver_reuse_edges=[],solver_calls=0,
        **FLAGS)


@dataclass(frozen=True,init=False)
class Resolver:
    """Public construction requires build/inspect and fresh evidence validation.

    resolve() is a pure projection of that snapshot, not a new freshness check.
    No caller-owned dictionaries or mutable caches are retained.
    """
    _raw: bytes = field(repr=False)
    _axes: tuple = field(repr=False)
    _cells: tuple = field(repr=False)
    _witness: tuple = field(repr=False)
    _catalog_node: str
    _overlay_node: str
    _protocol: str
    _alpha_count: int

    def __init__(self,*args,**kwargs): raise ValueError('build or fresh inspect required')

    def __copy__(self): raise ValueError('copy requires fresh inspect of raw bytes')

    def __deepcopy__(self,memo): raise ValueError('copy requires fresh inspect of raw bytes')

    def __reduce_ex__(self,protocol): raise ValueError('pickle requires fresh inspect of raw bytes')

    @property
    def raw(self): return self._raw

    @property
    def identity(self): return io.digest(self._raw)

    def data(self): return json.loads(self._raw)

    def _family(self, family):
        if type(family) is not str: raise ValueError('declared family required')
        for name, axes in self._axes:
            if name == family: return axes
        raise ValueError('declared family required')

    def encode_coordinate(self, family, coordinate):
        axes = self._family(family)
        if type(coordinate) is not dict or set(coordinate) != {n for n,v in axes}:
            raise ValueError('exact family coordinate axes required')
        ordinal = 0
        for name, values in axes:
            try: index = values.index(io.encode(coordinate[name]))
            except (ValueError,TypeError) as exc: raise ValueError('coordinate outside pinned axis') from exc
            ordinal = ordinal*len(values)+index
        return ordinal

    def resolve(self, family, ordinal):
        axes = self._family(family)
        if type(ordinal) is not int or ordinal < 0: raise ValueError('bounded exact ordinal required')
        remainder, coordinate, indices = ordinal, {}, {}
        for name, values in reversed(axes):
            remainder,index = divmod(remainder,len(values))
            coordinate[name],indices[name] = json.loads(values[index]),index
        if remainder: raise ValueError('ordinal outside family')
        cell = json.loads(self._cells[indices['theta']*self._alpha_count+indices['alpha']])
        cell_pin = io.digest(io.encode(dict(protocol_sha256=self._protocol,
            theta=coordinate['theta'],alpha=coordinate['alpha'])))
        if cell_pin != cell['cell_sha256']: raise ValueError('full cell identity differs')
        arm = coordinate['arm']
        parent = cell['arm_implication_nodes'].get(arm)
        direct = all(io.encode(coordinate[k]) == value for k,value in self._witness)
        if parent is None:
            disposition, missing = 'unresolved_no_certificate', MISSING[family]
        elif family in ('training_b6_actual','holdout'):
            disposition, missing = 'conditional_prerequisite_false_not_executed', None
        else:
            disposition = 'direct_analytic_witness' if direct else 'not_scheduled_due_to_parent_cell_proof'
            missing = None
        identity = dict(catalog_sha256=CATALOG_PIN,family=family,ordinal=ordinal,
            axis_order=[n for n,v in axes],coordinate=coordinate)
        obligation_pin = io.digest(io.encode(dict(schema=SCHEMA,**identity)))
        payload = dict(identity,obligation_sha256=obligation_pin,cell_sha256=cell_pin,
            split='holdout' if family == 'holdout' else 'training',
            disposition=disposition,missing_dependency=missing,
            direct_named_witness_pair=direct and family in ('training_lb','training_ub'),
            individual_pair_failure=False,native_status=None,frozen_training_ub=None,
            bookkeeping_labels_are_policy_inputs=False)
        parents = [(self._catalog_node,'proof_reference'),(self._overlay_node,'proof_reference')]
        if parent is not None: parents.append((parent,'logical_implication'))
        return _node('obligation_projection',payload,parents)


def _resolver(raw):
    """Private compiler materialization, not a source-verification API."""
    if len(raw) > CAP: raise ValueError('manifest byte cap exceeded')
    value = json.loads(raw)
    catalog = value['catalog']
    axes = tuple((family,tuple((name,tuple(io.encode(v) for v in catalog['axes'][family][name]))
        for name in order)) for family,order in catalog['axis_order'].items())
    cells = tuple(io.encode(c) for c in value['cells'])
    witness = tuple((k,io.encode(v)) for k,v in value['witness_windows'].items())
    result = object.__new__(Resolver)
    fields = dict(_raw=raw,_axes=axes,_cells=cells,_witness=witness,
        _catalog_node=value['catalog_node'],_overlay_node=value['exclusion_overlay_node'],
        _protocol=value['protocol_sha256'],_alpha_count=len(catalog['axes']['training_lb']['alpha']))
    for name,content in fields.items(): object.__setattr__(result,name,content)
    return result


def build():
    """Fresh source-bound reconstruction; zero native calls and no writes."""
    views = {}
    for name,pin in [(CATALOG,CATALOG_PIN),(REPORT,REPORT_PIN),(__file__,None)]:
        path = ROOT/name
        raw,stamp = io.read_stable(path,CAP)
        if pin is not None and io.digest(raw) != pin: raise ValueError('pinned manifest input differs')
        views[path] = (raw,stamp)
    report = exclusion.inspect(ROOT/REPORT,expected_sha256=REPORT_PIN)
    source_views = {}
    for name,pin in report['source_sha256'].items():
        path = ROOT/name
        view = io.read_stable(path,exclusion.INPUT_CAP)
        if io.digest(view[0]) != pin: raise ValueError('proof source changed after fresh inspection')
        source_views[path] = view
    catalog = json.loads(views[ROOT/CATALOG][0])['obligation_catalog']
    value = _compile(catalog,report,io.digest(views[Path(__file__)][0]))
    raw = io.encode(value)
    for path,view in source_views.items():
        if io.read_stable(path,exclusion.INPUT_CAP) != view:
            raise ValueError('proof source changed during manifest compilation')
    for path,view in views.items():
        if io.read_stable(path,CAP) != view: raise ValueError('manifest evidence changed during build')
    return _resolver(raw)


def inspect(path, *, expected_sha256):
    raw,stamp = io.read_stable(Path(path),CAP)
    if io.digest(raw) != io.pin(expected_sha256): raise ValueError('external manifest pin differs')
    rebuilt = build()
    if rebuilt.raw != raw: raise ValueError('fresh manifest reconstruction differs')
    if io.read_stable(Path(path),CAP) != (raw,stamp): raise ValueError('manifest changed during inspection')
    return rebuilt
