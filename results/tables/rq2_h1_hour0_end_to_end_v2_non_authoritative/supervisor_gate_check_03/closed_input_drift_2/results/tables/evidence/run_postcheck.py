from pathlib import Path
import sys
(Path(__file__).parent/sys.argv[1]/'timing.jsonl').write_bytes(b"CHANGED")
