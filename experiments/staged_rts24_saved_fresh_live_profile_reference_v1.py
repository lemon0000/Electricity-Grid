"""Frozen NFC9 observation reference for a conditional local LIVE diagnostic."""
from hashlib import sha256
import json
from pathlib import Path

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def load_reference():
    # Expected bytes are code literals; neither caller nor observed child chooses them.
    profile_pin=dict(bytes=501203,sha256='a61fb973180f4031ebc024bb69ab162460955594c4bb53cc182d3da70559d3b6')
    checkpoint_sha='5fb9c83a6ec9e7933e684a7f4ca2491fa52d9d7e1a6a8b7cc3740d9eb30428da'
    origin=Path('D:/CUHKSZ/Research Project/electricity-grid/results/tables/staged_rts24_saved_fresh_nfc_v9_non_authoritative')
    checkpoint_raw=(origin/'checkpoint.json').read_bytes();assert pin(checkpoint_raw)['sha256']==checkpoint_sha
    cp=json.loads(checkpoint_raw);assert canonical(cp)==checkpoint_raw
    assert cp['accepted'] is True and cp['diagnostic_accepted'] is True and cp['prior_not_accepted_count']==38
    assert cp['source_epoch']=='acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875'
    assert cp['acceptance_scope']=='packed_metadata_and_post_return_diagnostic_only'
    assert cp['import_profile_pin']==cp['root_map_before_checkpoint']['import_profile.json']==profile_pin
    raw=(origin/'import_profile.json').read_bytes();assert pin(raw)==profile_pin
    profile=json.loads(raw);assert canonical(profile)==raw
    assert profile['authority']=='DRAFT_NONAUTHORITATIVE' and profile['loaded_python_graph_attested'] is False
    assert profile['registry_contents_verified'] is False and profile['native_behavior_verified'] is False
    ref=dict(path=str(origin/'import_profile.json'),pin=profile_pin)
    return dict(reference=ref,source_checkpoint=dict(path=str(origin/'checkpoint.json'),pin=pin(checkpoint_raw)),
        source_epoch=cp['source_epoch'],source_diagnostic_accepted=True,external_expected_truth_verified=False,
        independent_tcb_authenticated=False,resource_admission=False,formal_result=False),raw


def reference():return load_reference()[0]


def raw_reference():
    return load_reference()


def admission(parent,code):
    path=parent.OUT/'profile_admission.exit.json';raw=path.read_bytes();exit=json.loads(raw)
    assert canonical(exit)==raw and exit['accepted'] is True and exit['label']=='profile_admission'
    assert all(exit[key] is False for key in parent.FALSE_FIELDS)
    items=exit['embedded_artifacts'];item=items['admission']
    import base64
    body=base64.b64decode(item['raw_base64'],validate=True);assert item['encoding']=='canonical_json' and pin(body)==item['pin']
    admitted=json.loads(body);assert canonical(admitted)==body
    assert set(admitted)=={'accepted','authority','profile_pin','transport_pin','helper_pins','environment_pin','registration_pin','discovery_receipt_pin','reference_source',*parent.FALSE_FIELDS}
    assert admitted['accepted'] is True and admitted['authority']=='DRAFT_NONAUTHORITATIVE'
    assert all(admitted[key] is False for key in parent.FALSE_FIELDS)
    assert admitted['transport_pin']==pin(code) and admitted['environment_pin']==pin(canonical(parent.environment()))
    registration_raw=(parent.OUT/'registration.json').read_bytes();registration=json.loads(registration_raw)
    assert canonical(registration)==registration_raw and admitted['registration_pin']==pin(registration_raw)==exit['registration_pin']
    assert registration['transport_pin']==admitted['transport_pin'] and registration['helper_pins']==admitted['helper_pins']
    assert registration['source_epoch']==parent.SOURCE_SHA
    assert admitted['discovery_receipt_pin']==pin((parent.OUT/'probe_discovery.receipt.json').read_bytes())
    assert admitted['profile_pin']==pin((parent.OUT/'startup_profile.json').read_bytes())
    for path,expected in admitted['helper_pins'].items():assert pin(Path(path).read_bytes())==expected,path
    assert canonical(admitted['reference_source'])==canonical(reference())
    assert admitted['reference_source']['source_epoch']==parent.SOURCE_SHA
    return admitted,pin(raw)


def context(parent,code,plan,manifest_raw):
    admitted,admission_pin=admission(parent,code);source=reference()
    assert canonical(plan)==manifest_raw and plan['case']=='normal'
    assert plan['authority']=='DRAFT_NONAUTHORITATIVE' and plan['source_epoch']==source['source_epoch']==parent.SOURCE_SHA
    assert plan['source_pins']==parent.source() and plan['bootstrap_pin']==pin(code)
    assert plan['startup_profile']==dict(path=str(parent.OUT/'startup_profile.json'),pin=admitted['profile_pin'])
    assert plan['import_profile']==source['reference']
    actual=(parent.OUT/'probe_normal.plan.json').read_bytes();assert actual==manifest_raw
    return dict(admission_pin=admission_pin,manifest_pin=pin(manifest_raw),reference_source=source,
        transport_pin=pin(code),registration_pin=admitted['registration_pin'],helper_pins=admitted['helper_pins'])


def compare_profile(profile):
    source,expected_raw=raw_reference();observed=None if profile is None else canonical(profile)
    exact=observed==expected_raw
    expected=json.loads(expected_raw)
    assert profile is None or type(profile) is dict and len(profile)<=32 and all(type(key) is str and len(key)<=160 for key in profile)
    differences=[] if profile is None else [key for key in sorted(set(expected)|set(profile)) if key not in profile or key not in expected or canonical(profile[key])!=canonical(expected[key])]
    return dict(expected_import_profile_pin=source['reference']['pin'],observed_import_profile_pin=None if observed is None else pin(observed),
        frozen_nfc9_import_profile_exact_match=exact,observed_profile_present=observed is not None,
        differing_fields=differences,reference_source=source,diagnostic_diff_used_for_acceptance=False)
