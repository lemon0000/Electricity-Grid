"""Stdlib raw-log derivation, not a live process capability or scientific oracle."""
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
MARKERS = (('invocation', b'INVOCATION_GRAPH '), ('role', b'ROLE_GRAPH '))


def canonical(value): return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('ascii')
def pin(raw): return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def derived():
    graphs = []
    for path in sorted(OUT.glob('*.stdout.log')):
        log_raw = path.read_bytes()
        for number, line in enumerate(log_raw.splitlines(), 1):
            candidates = [(kind, line.partition(marker)[2]) for kind, marker in MARKERS if marker in line]
            if not candidates: continue
            kind, raw = candidates[0]
            if not raw.startswith(b'{'): continue
            value = json.loads(raw); assert canonical(value) == raw
            label, case = path.name.removesuffix('.stdout.log'), value['case' if kind == 'invocation' else 'scenario']
            assert all(c.isalnum() or c == '_' for c in label+case)
            base = OUT/'graph_snapshots'/label/case
            result_path = base/'result.json'; result_raw = canonical(value['result'])
            files = {}; writes = {result_path: result_raw}
            for name, item in value['files'].items():
                assert '\\' not in name and not Path(name).is_absolute() and '..' not in Path(name).parts
                assert name == 'context.json' or 'hex' in item
                if name == 'context.json':
                    assert 'hex' not in item and value['context_projection_omits'] == ['environment']
                    assert value.get('projection_is_original_context', False) is False
                    projection = value['context_projection']; assert 'environment' not in projection and len(projection['environment_sha']) == 64
                    target = base/'context.projection.json'; data = canonical(projection); scope = 'projection_only'
                else:
                    data = bytes.fromhex(item['hex']); assert pin(data) == item['pin']
                    target = base/'files'/name; scope = 'exact_original_bytes'
                writes[target] = data
                files[name] = dict(archive=target.relative_to(ROOT).as_posix(), archive_pin=pin(data), original_pin=item['pin'], scope=scope)
            graphs.append((dict(graph_kind=kind, source_log=path.relative_to(ROOT).as_posix(), source_log_pin=pin(log_raw), line=number,
                label=label, case=case, result=result_path.relative_to(ROOT).as_posix(), result_pin=pin(result_raw), files=files), writes))
    return graphs


def materialize():
    target = OUT/'invocation_graph_snapshots.json'; assert not target.exists()
    rows = []
    for row, writes in derived():
        for path, raw in writes.items():
            path.parent.mkdir(parents=True, exist_ok=True); assert not path.exists(); path.write_bytes(raw)
        rows.append(row)
    target.write_bytes((json.dumps(rows, sort_keys=True, indent=2)+'\n').encode())
    return verify()


def verify():
    saved = json.loads((OUT/'invocation_graph_snapshots.json').read_bytes())
    current = derived(); assert saved == [row for row, _ in current]
    entries = results = exact = projections = 0
    for row, writes in current:
        field = 'ordinary_external_invocation_completed' if row['graph_kind'] == 'invocation' else 'ordinary_graph_completed'
        assert type(json.loads((ROOT/row['result']).read_bytes())[field]) is bool
        for path, raw in writes.items():
            assert path.read_bytes() == raw; entries += 1
        results += 1
        exact += sum(item['scope'] == 'exact_original_bytes' for item in row['files'].values())
        projections += sum(item['scope'] == 'projection_only' for item in row['files'].values())
    return dict(graphs=results, archive_entries=entries, exact_original_file_entries=exact,
        context_projections=projections, original_context_reconstructed=False)


if __name__ == '__main__': print(json.dumps(materialize() if sys.argv[1:] == ['materialize'] else verify(), sort_keys=True))
