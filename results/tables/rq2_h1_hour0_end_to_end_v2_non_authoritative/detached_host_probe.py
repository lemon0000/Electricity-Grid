"""Short hosting probe only; no project imports or experiment execution."""
import json
import os
from pathlib import Path
import sys
import time

out = Path(sys.argv[1])
def save(name, body):
    with (out / name).open('x', encoding='utf8') as stream:
        json.dump(body, stream, indent=2)
save('started.json', dict(pid=os.getpid(), parent_pid=os.getppid(), argv=sys.argv,
                          cwd=os.getcwd(), formal_result=False))
time.sleep(12)
save('terminal.json', dict(pid=os.getpid(), exit_code=0, elapsed_wait_seconds=12,
                           formal_result=False))
