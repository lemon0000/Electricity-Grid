"""Verified marginal source windows; no coupling, power mapping or dispatch."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import platform

import yaml

from . import continuation_audit as audit


def _hash(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def _sha(value):
    if type(value) is not str or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError('built-in lowercase SHA256 required')


def _select(rows, chains, kind, split, start, hours, seed):
    if kind not in ('power', 'workload') or split not in ('training', 'holdout'):
        raise ValueError('explicit marginal kind and split required')
    if type(start) is not int or start < 0 or type(hours) is not int or hours <= 0:
        raise ValueError('nonnegative raw start and positive integer hours required')
    if (kind == 'power' and (type(seed) is not int or seed < 0)) or (kind == 'workload' and seed is not None):
        raise ValueError('power requires an explicit seed; workload has no outage seed')
    candidates = [c for c in chains if c['split'] == split
        and (kind != 'power' or c['outage_seed'] == seed)
        and c['source_start'] <= start and start+hours-1 <= c['source_end']]
    if len(candidates) != 1:
        raise ValueError('window not contained in one verified same-split source chain')
    chain = candidates[0]
    field = 'source_hour' if kind == 'power' else 'source_relative_hour'
    selected = [r for r in rows if r['split'] == split
        and (kind != 'power' or int(r['outage_seed']) == seed)
        and start <= int(r[field]) < start+hours]
    selected.sort(key=lambda r: int(r[field]))
    if [int(r[field]) for r in selected] != list(range(start, start+hours)):
        raise ValueError('missing or duplicate source hour in requested window')
    if any(r['block_id'] not in chain['block_ids'] for r in selected):
        raise ValueError('row block outside verified chain')
    return deepcopy(selected), deepcopy(chain)


def load_source_window(kind, split, raw_start, hours, *, outage_seed=None,
                       config_path=audit.DEFAULT_CONFIG, expected_config_sha256):
    """Return source strings and provenance for one marginal, not executable inputs."""
    _sha(expected_config_sha256)
    path = Path(config_path)
    audit._verify_hash(path, expected_config_sha256, 'window config')
    config = audit._load_config(path)
    if kind not in ('power', 'workload'):
        raise ValueError('explicit marginal kind required')
    binding = config['inputs'][kind]
    package, summary = audit._verify_package(binding, kind)
    audit._verify_summary(binding, summary, kind)
    if kind == 'power':
        _, chains, _ = audit._power_audit(package, summary, binding)
        filename, fields = 'power_system_blocks.csv.gz', audit.POWER_FIELDS
    else:
        _, chains = audit._workload_audit(package, summary, binding)
        if any(summary.get(k) is not False for k in ('workload_fraction_is_power',
                'flexible_fraction_inferred', 'deadline_observed', 'checkpoint_observed', 'recoverability_observed')):
            raise ValueError('workload evidence status drifted')
        filename, fields = 'workload_blocks.csv.gz', audit.WORKLOAD_FIELDS
    rows = audit._read_gzip_csv(package / filename, fields)
    selected, chain = _select(rows, chains, kind, split, raw_start, hours, outage_seed)
    # Verify again after parsing, without claiming protection from hostile ABA.
    audit._verify_package(binding, kind)
    audit._verify_hash(path, expected_config_sha256, 'window config')
    result = {'status': 'DRAFT_NONAUTHORITATIVE', 'kind': kind, 'split': split,
        'raw_start': raw_start, 'hours': hours, 'outage_seed': outage_seed,
        'config_sha256': expected_config_sha256, 'package_manifest_sha256': binding['manifest_sha256'],
        'members': deepcopy(binding['members']), 'chain': chain, 'rows': selected,
        'continuous_power_source_hours': list(range(raw_start+1, raw_start+hours+1)) if kind == 'power' else None,
        'implementation_sha256': sha256(Path(__file__).read_bytes()).hexdigest(),
        'audit_implementation_sha256': sha256(Path(audit.__file__).read_bytes()).hexdigest(),
        'python_version': platform.python_version(), 'pyyaml_version': yaml.__version__,
        'solver_calls': 0, 'formal_result': False, 'registered_coupling': False,
        'shared_observed_clock': False, 'continuous_dispatch_verified': False,
        'workload_fraction_clipped': False, 'executable_episode_input': False}
    result['window_identity'] = _hash(result)
    return result
