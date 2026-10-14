from pathlib import Path
import sys
(Path(__file__).parent/sys.argv[1]/'stdout.log').write_bytes(b"CHANGED")
