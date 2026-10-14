from pathlib import Path
import sys
(Path(__file__).parent/sys.argv[1]/'concurrent_validation_added.json').write_bytes(b"CHANGED")
