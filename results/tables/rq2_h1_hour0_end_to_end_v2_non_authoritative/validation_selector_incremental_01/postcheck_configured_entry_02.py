"""Compare the two already-finished interpreter trials; never rerun an audit."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
COMPUTE = Path('D:/Miniconda3/envs/compute')
SUPPORT = Path('C:/Users/Psychobabble/AppData/Roaming/Python/Python312/site-packages')


def read(folder, name):
    return json.loads((HERE / folder / name).read_bytes())


def beneath(value, parent):
    return Path(value).is_relative_to(parent)


def main():
    left, right = 'standard_entry_02', 'configured_entry_02'
    requests = [read(folder, 'request.json') for folder in (left, right)]
    terminals = [read(folder, 'terminal.json') for folder in (left, right)]
    origins = [read(folder, 'module_origins.json') for folder in (left, right)]
    pins = [read(folder, 'module_origin_sha256.json') for folder in (left, right)]
    for key in ('source_sha256', 'saved_sha256', 'route_identity',
                'fixed_byte_and_metadata_parse_package_sha256'):
        assert requests[0][key] == requests[1][key], key
    assert requests[0]['saved_sha256'] == read('real_identity_pair_01', 'request.json')['saved_sha256']
    for collection in ('source_sha256', 'saved_sha256'):
        for path, expected in requests[0][collection].items():
            assert sha256(Path(path).read_bytes()).hexdigest() == expected, path
    for terminal in terminals:
        assert terminal['exit_code'] == 0
        assert terminal['source_unchanged'] and terminal['saved_unchanged']
        assert terminal['saved_files'] == 140 and terminal['real_native_calls'] == 0
        assert not terminal['static_identity_shortcut']
        assert terminal['code_read_hits'] == 74477 and terminal['metadata_parse_hits'] == 6017
    assert 'isolated=0' in terminals[0]['python_flags']
    assert 'isolated=1' in terminals[1]['python_flags']
    paths = terminals[1]['effective_sys_path']
    assert len(paths) == len(set(paths)) == 8
    assert paths.index(str(SUPPORT)) < paths.index(str(COMPUTE / 'Lib/site-packages'))

    shared = sorted(origins[0].keys() & origins[1].keys())
    for name in shared:
        assert origins[0][name] == origins[1][name], name
        assert pins[0].get(name) == pins[1].get(name), name
    required = ('pyomo', 'highspy', 'numpy', 'scipy', 'pypower', 'yaml', 'osqp', 'gurobipy', 'pytest')
    for name in required:
        assert name in origins[1] and name in pins[1], name
        assert beneath(origins[1][name], COMPUTE / 'Lib/site-packages'), name
    assert beneath(origins[1]['pygments'], SUPPORT)
    # Pyomo exposes aliases to stdlib modules (e.g. ctypes.util). Classify them
    # explicitly after exact baseline origin/hash equality, rather than mistaking
    # a module-name prefix for an assertion about every re-export's origin.
    stdlib_aliases = {}
    for name in shared:
        if name.split('.')[0] not in required:
            continue
        path = origins[1][name]
        if not beneath(path, COMPUTE / 'Lib/site-packages'):
            assert beneath(path, COMPUTE / 'Lib') and name in pins[1], (name, path)
            stdlib_aliases[name] = dict(path=path, sha256=pins[1][name])

    measured = []
    for lane in ('Rref', 'A'):
        rows = [read(left, lane + '_standard.json'), read(right, lane + '_configured.json')]
        for key in ('projection', 'bridge_implementation_identity', 'capture_mode'):
            assert rows[0][key] == rows[1][key], (lane, key)
        baseline, candidate = (row['audit_seconds'] for row in rows)
        measured.append(dict(lane=lane, standard_seconds=baseline, configured_seconds=candidate,
            reduction_fraction=1-candidate/baseline, exact_scientific_projection=True,
            selector_record_sha256=rows[0]['projection']['selector_record_sha256']))
    result = dict(status='DRAFT_NONAUTHORITATIVE', observed_at_utc=datetime.now(timezone.utc).isoformat(),
        decision='INTEGRATE_EXPLICIT_PATH_CONFIGURATION_IN_VERSIONED_VALIDATION_ENTRY',
        comparison_script_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
        audit_route_sha256=requests[0]['route_identity'], attempts=[left, right],
        measurements=measured, shared_module_origins_and_file_hashes_equal=True,
        shared_module_count=len(shared), top_level_compute_module_allowlist=list(required),
        required_support_module='pygments', explicit_stdlib_reexports=stdlib_aliases,
        standard_only_modules={name:origins[0][name] for name in origins[0].keys()-origins[1].keys()},
        configured_only_modules={name:origins[1][name] for name in origins[1].keys()-origins[0].keys()},
        source_pin_count=len(requests[0]['source_sha256']), saved_file_count=140,
        current_sources_and_saved_files_unchanged=True, stock_metadata_finder_unchanged=True,
        helper_distribution_discovery_cache=False, helper_static_identity_cache=False,
        full_chain_passed=False, whole_workflow_performance_review_complete=False,
        long_chain_launch_admitted=False, formal_result=False, resource_admission=False,
        formal_execution_ready=False, native_execution_authorized=False)
    with (HERE / 'configured_entry_comparison_02.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
