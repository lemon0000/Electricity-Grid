"""Attribute the measured common-arm cost with bounded GIL sampling, no speed claim."""
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
value=json.loads((HERE/'bounded_common_arm_plan_01.json').read_bytes())
changed={'h1_historical_n0_verifier_development_v3.py','test_h1_registry_validation_operation_development_v1.py'}
for group in ('source_sha256','code_lease_sha256'):
    for name in value[group]:
        if Path(name).name in changed:value[group][name]=sha256(Path(name).read_bytes()).hexdigest()
sources=value['source_sha256']
for path in (Path(__file__),HERE/'measure_bounded_common_sample_v1.py',HERE/'run_bounded_common_sample_v1.py',
        REPO/'tests/h1_gil_stack_observer_development_v1.py',
        HERE/'bounded_common_arm_monitor_01/terminal.json',
        HERE/'bounded_common_arm_01_non_authoritative/terminal.json'):
    sources[str(path)]=sha256(path.read_bytes()).hexdigest()
assert all(sha256(Path(p).read_bytes()).hexdigest()==pin for p,pin in sources.items())
assert all(sha256(Path(p).read_bytes()).hexdigest()==pin for p,pin in value['saved_sha256'].items())
value.update(question='Which stacks account for the original common._arm cost after allocation/guard fixes?',
    attempts=1,common_arm_calls=1,synthetic_jobs=0,native_calls=0,
    sampling=dict(interval_seconds=.1,max_samples=1024,max_frames=128,max_bytes=16*1024**2,
        no_profile_or_trace_hook=True,no_source_or_locals_read=True),
    inner_output=str(HERE/'bounded_common_sample_01_non_authoritative'),
    outer_output=str(HERE/'bounded_common_sample_monitor_01'),
    basetemp='D:/h1_bounded_common_sample_01_non_authoritative',
    limits=dict(wall_seconds=120,sampled_rss_bytes=768*1024**2,storage_bytes=128*1024**2),
    authorized_source_delta='draft v3 store-registry definition/runtime repair and its protocol fixture; neither is imported by original common._arm',
    order_effects='sampling attribution only; elapsed includes observation overhead and cannot establish speedup',
    dag=['fixed saved/source and controlled interpreter','entry before original fixture imports',
        'locked metadata','one original common._arm with .1s GIL observer',
        'sampler stop/join/close','science and full audit exact comparison',
        'metadata close before fixture undo','entry close and source/saved/process postcheck'])
out=HERE/'bounded_common_sample_plan_01.json'
with out.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
print(json.dumps(dict(plan_sha256=sha256(out.read_bytes()).hexdigest(),source_files=len(sources))))
