from pathlib import Path
import sys
base=Path(__file__).parent/sys.argv[1]
(base/'complete_integration_report.md').write_text('FAKE ORCHESTRATION ONLY\n')
(base/"postcheck/completed.json").write_bytes(b"ALTERED AFTER POSTCHECK")
