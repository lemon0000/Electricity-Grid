from pathlib import Path
import hashlib,json,sys
base=Path(__file__).parent/sys.argv[1]
artifact=base.parents[3]/'saved_artifacts'
names=('postcheck_launch/terminal.json','postcheck/completed.json',
       'postcheck/postcheck_manifest.json','postcheck/chain_postcheck.json',
       'postcheck/fresh_process_replay/terminal.json','postcheck/fresh_process_replay/result.json')
for name in names:
    p=base/name
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text('{"FAKE_FIXTURE":true}')
request=dict(artifact_root=str(artifact),artifact_files_sha256={
    'report.json':hashlib.sha256((artifact/'report.json').read_bytes()).hexdigest()})
(base/'postcheck/fresh_process_replay/request.json').write_text(json.dumps(request))
