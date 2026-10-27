"""Exact output/core/probe relocation; frozen helper and packing are retained."""
def replace(source, pairs):
    for before, after, count in pairs:
        assert source.count(before) == count, (before, source.count(before))
        source = source.replace(before, after, count)
    return source.encode('utf-8')


def core(source):
    return replace(source, [('nfc_v2_non_authoritative', 'nfc_v3_non_authoritative', 2)])


def probe(source):
    return replace(source, [('nfc_v2_non_authoritative', 'nfc_v3_non_authoritative', 1)])


def parent(source):
    source=replace(source, [('nfc_v2_non_authoritative', 'nfc_v3_non_authoritative', 1),
        ('lease_v29.py', 'lease_v30.py', 1), ('probe_v27.py', 'probe_v28.py', 1)]).decode('utf-8')
    before="        admission=json.loads((OUT/'profile_admission.json').read_bytes())"
    assert source.count(before)==1
    after="""        packed=json.loads((OUT/'profile_admission.exit.json').read_bytes());assert packed['accepted'] is True
        item=packed['embedded_artifacts']['admission'];assert item['encoding']=='canonical_json'
        raw=base64.b64decode(item['raw_base64'],validate=True);assert pin(raw)==item['pin']
        admission=json.loads(raw);assert canonical(admission)==raw"""
    return source.replace(before,after,1).encode('utf-8')
