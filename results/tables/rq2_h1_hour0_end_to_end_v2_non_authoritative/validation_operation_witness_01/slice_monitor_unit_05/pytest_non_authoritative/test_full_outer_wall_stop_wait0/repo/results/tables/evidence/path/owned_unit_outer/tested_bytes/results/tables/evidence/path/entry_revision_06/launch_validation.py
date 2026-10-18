import sys
from pathlib import Path
root=Path(__file__).parent/sys.argv[3]
root.mkdir()
import subprocess,time,json
child=subprocess.Popen([sys.executable,"-B","-c","import time; time.sleep(30)"])
(root/"grandchild.json").write_text(json.dumps(child.pid))
time.sleep(30)
