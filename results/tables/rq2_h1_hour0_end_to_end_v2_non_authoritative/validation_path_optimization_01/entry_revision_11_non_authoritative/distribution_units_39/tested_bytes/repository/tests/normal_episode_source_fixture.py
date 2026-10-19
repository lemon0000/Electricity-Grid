"""Explicit synthetic indirect packages for normal/episode plumbing tests."""
from hashlib import sha256
import json


def packages(root):
    config = {'inputs': {}}
    for kind in ('power', 'workload'):
        package = root/kind
        package.mkdir(parents=True)
        names = ['summary.json', 'training_marginal.csv.gz', 'holdout_marginal.csv.gz']
        names += ['n1_outage_events.csv.gz', 'power_system_blocks.csv.gz'] if kind == 'power' else ['workload_blocks.csv.gz']
        members = {}
        for name in names:
            raw = ('synthetic '+kind+' '+name).encode('ascii')
            (package/name).write_bytes(raw)
            members[name] = sha256(raw).hexdigest()
        manifest = json.dumps(members, sort_keys=True).encode('ascii')
        (package/'SHA256SUMS.json').write_bytes(manifest)
        item = dict(package=str(package), members=members, manifest_sha256=sha256(manifest).hexdigest())
        for key in ('builder', 'builder_config') + (('chronology',) if kind == 'power' else ()):
            path = root/(kind+'_'+key)
            path.write_bytes(('synthetic '+key).encode('ascii'))
            item[key+'_path'] = str(path)
            item[key+'_sha256'] = sha256(path.read_bytes()).hexdigest()
        config['inputs'][kind] = item
    return config
