"""Read-only derivation oracle: raw pytest stdout -> exact ordinary archives."""
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent


def pin(raw): return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def verify():
    raw = (OUT/'role_graph_03.stdout.log').read_bytes()
    manifest = json.loads((OUT/'ordinary_graph_snapshots.json').read_bytes())
    graphs = {}
    for line in raw.splitlines():
        if b'ROLE_GRAPH ' not in line: continue
        graph = json.loads(line.partition(b'ROLE_GRAPH ')[2]); name = graph['scenario']
        assert name not in graphs; graphs[name] = graph
    assert set(graphs) == set(manifest) and len(graphs) == 9
    count = 0
    for scenario, graph in graphs.items():
        archived = manifest[scenario]
        result = ROOT/archived['result']
        assert result.resolve().is_relative_to(OUT/'graph_snapshots_03')
        assert pin(result.read_bytes()) == archived['result_pin'] and json.loads(result.read_bytes()) == graph['result']
        assert set(archived['files']) == set(graph['files'])
        for name, value in graph['files'].items():
            item = archived['files'][name]; path = ROOT/item['archive']
            assert path.resolve().is_relative_to(OUT/'graph_snapshots_03')
            data = path.read_bytes(); assert pin(data) == item['archive_pin']
            assert item['original_pin'] == value['pin']
            if name == 'context.json':
                assert item['projection_omits'] == ['environment'] and 'hex' not in value
                assert json.loads(data) == graph['context_projection'] and 'environment' not in json.loads(data)
            else:
                assert data == bytes.fromhex(value['hex']) and pin(data) == value['pin']
            count += 1
    return dict(authority='DRAFT_NONAUTHORITATIVE', graph_cases=9, exact_archived_files_and_projections=count,
        source_log_pin=pin(raw), manifest_pin=pin((OUT/'ordinary_graph_snapshots.json').read_bytes()),
        verifier_pin=pin(Path(__file__).read_bytes()), original_context_reconstructed=False,
        F_launch_admitted=False, scientific_evidence_adopted=False, resource_admission=False, formal_result=False)


if __name__ == '__main__': print(json.dumps(verify(), sort_keys=True, indent=2))
