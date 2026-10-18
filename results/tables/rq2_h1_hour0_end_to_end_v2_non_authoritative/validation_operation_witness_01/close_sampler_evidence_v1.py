"""Close the event PID-and-creation fence over the preserved short pair."""
from hashlib import sha256
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
OUT = HERE/'stack_sampler_churn_pair_01'
prior_path = OUT/'postcheck_and_erratum_01.json'
prior = json.loads(prior_path.read_bytes())
for name,pin in prior['files_sha256'].items():
    assert sha256((REPO/name).read_bytes()).hexdigest() == pin
comparison = json.loads((OUT/'comparison.json').read_bytes())
c = comparison['results']['c_timer']
event = prior['native_event']['event_data']
event_unix = int(event['ProcessCreationTime'], 16)/10_000_000-11_644_473_600
assert int(event['ProcessId'], 16) == c['pid']
assert abs(event_unix-c['creation_time']) < 1e-6
prior.update(pid_creation_correspondence=True,
    event_creation_time_unix=event_unix, terminal_creation_time_unix=c['creation_time'],
    absolute_creation_time_difference_seconds=abs(event_unix-c['creation_time']))
for path in (prior_path, Path(__file__)):
    prior['files_sha256'][path.relative_to(REPO).as_posix()] = sha256(path.read_bytes()).hexdigest()
with (OUT/'postcheck_and_erratum_02.json').open('x',encoding='utf-8',newline='\n') as stream:
    json.dump(prior,stream,indent=2)
print(json.dumps(dict(output=str(OUT/'postcheck_and_erratum_02.json'),
    pid_creation_correspondence=True,delta_seconds=abs(event_unix-c['creation_time']))),flush=True)
