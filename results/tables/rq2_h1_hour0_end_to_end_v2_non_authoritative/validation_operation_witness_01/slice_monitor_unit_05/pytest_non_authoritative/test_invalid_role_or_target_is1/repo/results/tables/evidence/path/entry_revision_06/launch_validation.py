import sys
from pathlib import Path
root=Path(__file__).parent/sys.argv[3]
root.mkdir()
raise AssertionError("must not launch")
