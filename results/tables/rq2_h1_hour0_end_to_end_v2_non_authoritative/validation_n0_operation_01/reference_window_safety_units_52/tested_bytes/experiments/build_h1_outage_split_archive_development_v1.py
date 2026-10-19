"""Offline lossless split extraction; never an operational source reader."""
import gzip
import json
from pathlib import Path

from experiments import audit_h1_outage_origin_replay_development_v1 as frozen


def encode(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode()


def build(destination):
    """Offline only: this builder may parse the original mixed-split CSV."""
    before = frozen._hash(__file__)
    if frozen._hash(frozen.CONFIG) != frozen.CONFIG_SHA:
        raise ValueError('generator config drift')
    config = frozen.yaml.safe_load(frozen.CONFIG.read_bytes())
    package = frozen.ROOT/config['output']['directory']
    frozen.builder._verify_package(package, frozen.PACKAGE_SHA)
    summary = json.loads((package/'summary.json').read_bytes())
    if summary['config_sha256'] != frozen.CONFIG_SHA:
        raise ValueError('package/config mismatch')
    member = package/'power_system_blocks.csv.gz'
    member_sha = frozen._hash(member)
    rows = frozen._read_rows(member)
    if any(r['split'] not in ('training', 'holdout') for r in rows):
        raise ValueError('unexpected source split')
    target = Path(destination)
    target.mkdir(parents=True, exist_ok=True)
    manifest = dict(schema='h1_outage_lossless_split_archive_v1', status='DRAFT_NONAUTHORITATIVE',
        source_package_manifest_sha256=frozen.PACKAGE_SHA,
        source_member_path=member.relative_to(frozen.ROOT).as_posix(), source_member_sha256=member_sha,
        generator_config_sha256=frozen.CONFIG_SHA, builder_sha256=before,
        split_hour=summary['split_hour'], source_horizon_hours=summary['hours'],
        fields=list(rows[0]), source_rows=len(rows), members={},
        extraction_role='offline_lossless_original_string_fields',
        operational_source_authorized=False, formal_result=False)
    for split in ('training', 'holdout'):
        selected = [r for r in rows if r['split'] == split]
        for r in selected:
            h = int(r['source_hour'])
            if not (0 <= h < summary['split_hour'] if split == 'training'
                    else summary['split_hour'] <= h < summary['hours']):
                raise ValueError('source split/hour mismatch')
        payload = encode(dict(split=split, rows=selected))
        packed = gzip.compress(payload, mtime=0)
        name = split+'.json.gz'
        with (target/name).open('xb') as stream:
            stream.write(packed)
        from hashlib import sha256
        manifest['members'][split] = dict(path=name, sha256=sha256(packed).hexdigest(),
            content_sha256=sha256(payload).hexdigest(), row_count=len(selected),
            ordered_row_hashes_sha256=sha256(encode([sha256(encode(r)).hexdigest() for r in selected])).hexdigest())
    frozen.builder._verify_package(package, frozen.PACKAGE_SHA)
    if (frozen._hash(frozen.CONFIG) != frozen.CONFIG_SHA or frozen._hash(__file__) != before
            or frozen._hash(member) != member_sha):
        raise ValueError('source changed during extraction')
    with (target/'manifest.json').open('xb') as stream:
        stream.write(encode(manifest))
    return manifest
