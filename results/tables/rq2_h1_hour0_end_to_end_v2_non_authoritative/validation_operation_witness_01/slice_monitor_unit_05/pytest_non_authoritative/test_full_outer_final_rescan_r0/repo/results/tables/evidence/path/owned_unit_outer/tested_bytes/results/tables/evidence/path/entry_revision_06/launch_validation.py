import sys
from pathlib import Path
root=Path(__file__).parent/sys.argv[3]
root.mkdir()
(root/'fast.bin').write_bytes(b'x'*(1024**2))
