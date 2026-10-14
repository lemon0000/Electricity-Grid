from pathlib import Path
import sys
p=Path(__file__).parent/sys.argv[1]/"complete_integration_report.md"
with p.open("x") as f:f.write("ISOLATED FAKE ORCHESTRATION FIXTURE ONLY")
