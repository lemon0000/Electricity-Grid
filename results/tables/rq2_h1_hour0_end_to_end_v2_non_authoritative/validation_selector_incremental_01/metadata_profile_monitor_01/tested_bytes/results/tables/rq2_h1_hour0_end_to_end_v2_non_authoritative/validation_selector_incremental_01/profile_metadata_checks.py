"""100 real distribution lookups: separate discovery from parser-lease guards."""
import cProfile
from hashlib import sha256
import importlib.metadata as metadata
import json
from pathlib import Path
import pstats
import sys
from time import perf_counter
from types import ModuleType

HERE = Path(__file__).resolve().parent
PRIOR = HERE.parent / 'validation_io_optimization_01'
label, = sys.argv[1:]
if not label.replace('_', '').isalnum():
    raise ValueError('unique diagnostic label required')
out = HERE / label
out.mkdir(exist_ok=False)
names = ('Pyomo', 'highspy', 'numpy', 'scipy', 'PYPOWER', 'PyYAML', 'osqp', 'gurobipy')


def save(name, value):
    with (out / name).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)


manifest = (PRIOR / 'package_manifest_v1.json').read_bytes()
if sha256(manifest).hexdigest() != '0cd4511072ee11cc89a942b3eb76a3a91de4390ca1af5febe0981c216976a59a':
    raise ValueError('fixed package differs')
members = json.loads(manifest)['files_sha256']
for name, pin in members.items():
    if sha256((PRIOR / name).read_bytes()).hexdigest() != pin:
        raise ValueError('fixed package member differs')
package = ModuleType('performance')
package.__path__ = [str(PRIOR)]
sys.modules['performance'] = package
for name in ('code_read_lease', 'metadata_parse_lease'):
    path = PRIOR / (name + '.py')
    module = ModuleType('performance.' + name)
    module.__file__, module.__package__ = str(path), 'performance'
    sys.modules[module.__name__] = module
    exec(compile(path.read_bytes(), str(path), 'exec'), vars(module))
parsed = sys.modules['performance.metadata_parse_lease']
expected = json.loads((PRIOR / 'metadata_allowlist_v1.json').read_bytes())['files_sha256']
save('request.json', dict(question='Break down 100 stock metadata.version lookups under existing parse lease',
    names=names, warmup_calls=8, profiled_calls=100, profiling=True,
    static_identity_shortcut=False, distribution_discovery_cached=False,
    fixed_package_sha256=sha256(manifest).hexdigest(),
    source_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
    metadata_sha256=expected, formal_result=False, resource_admission=False, real_native_calls=0))
start = perf_counter()
with parsed.MetadataParseLease(expected) as lease:
    baseline = {name: metadata.version(name) for name in names}
    values = []
    profile = cProfile.Profile()
    profile.enable()
    for i in range(100):
        name = names[i % len(names)]
        values.append((name, metadata.version(name)))
    profile.disable()
    if any(version != baseline[name] for name, version in values):
        raise ValueError('real distribution version changed')
    receipt = lease.receipt()
profile.dump_stats(str(out / 'metadata.pstats'))
stats = pstats.Stats(profile)
rows = [dict(file=file, line=line, function=function, primitive_calls=row[0], calls=row[1],
    self_seconds=row[2], cumulative_seconds=row[3]) for (file, line, function), row in stats.stats.items()]
rows.sort(key=lambda row: row['cumulative_seconds'], reverse=True)
save('profile.json', dict(total_profiled_seconds=stats.total_tt, top_cumulative=rows[:35],
    top_self=sorted(rows, key=lambda row: row['self_seconds'], reverse=True)[:25],
    cumulative_times_overlap=True, profiling_overhead_present=True))
result = dict(exit_code=0, elapsed_seconds=perf_counter() - start, profiled_calls=100,
    versions_unchanged=True, lease_receipt=receipt, distribution_discovery_cached=False,
    formal_result=False, resource_admission=False, real_native_calls=0,
    scope='metadata diagnostic only; no pipeline performance or admission claim')
save('terminal.json', result)
print(json.dumps(dict(exit_code=0, elapsed_seconds=result['elapsed_seconds'],
    total_profiled_seconds=stats.total_tt, top_cumulative=rows[:5])), flush=True)
