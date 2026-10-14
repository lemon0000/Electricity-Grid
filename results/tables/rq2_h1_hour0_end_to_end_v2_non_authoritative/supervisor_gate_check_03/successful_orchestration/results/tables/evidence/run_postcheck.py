from pathlib import Path
import sys
base=Path(__file__).parent/sys.argv[1]
names=("postcheck_launch/terminal.json","postcheck/completed.json","postcheck/postcheck_manifest.json","postcheck/chain_postcheck.json","postcheck/fresh_process_replay/terminal.json","postcheck/fresh_process_replay/result.json")
for name in names:
 p=base/name
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open("x") as f:f.write("{\"FAKE_FIXTURE\":true}")
