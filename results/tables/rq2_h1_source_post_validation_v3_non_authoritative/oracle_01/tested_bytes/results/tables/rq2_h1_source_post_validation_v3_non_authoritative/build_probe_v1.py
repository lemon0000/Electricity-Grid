"""Reuse the original saved-case diagnostic with only declared substitutions."""
from pathlib import Path
from hashlib import sha256
import json

HERE=Path(__file__).resolve().parent
PRIOR=HERE.parent/'rq2_h1_constructor_window_fault_v1_non_authoritative'
REPO=HERE.parents[2]
original=PRIOR/'run_saved_validation_v1.py'
text=original.read_text(encoding='utf-8')
text=text.replace("'oracle_saved_v2.py'","'oracle_saved_v3.py'")
text=text.replace("if mode == 'short':\n", "if mode == 'short':\n    raise ValueError('only one H3 saved batch is budgeted here')\n")
needle="for path in new:\n"
addition="""new += [
    REPO/'experiments/h1_constructor_runtime_guard_development_v1.py',
    REPO/'experiments/h1_constructor_rejection_support_development_v1.py',
    REPO/'experiments/h1_phase_historical_batch_development_v3.py',
    REPO/'experiments/h1_phase_exact_source_batch_development_v3.py',
    REPO/'experiments/h1_constructor_source_batch_validation_development_v2.py',
    REPO/'tests/test_h1_source_post_validation_development_v3.py',
    HERE/'unit_07/request.json',HERE/'unit_07/terminal.json',HERE/'unit_07/pytest.xml',
    HERE/'probe_budget_v1.json',HERE/'generation_record_v1.json',HERE/'build_probe_v1.py',
    HERE/'preseal_findings_v1.json',
]
"""
if text.count(needle)!=1:raise ValueError('one runner insertion point required')
text=text.replace(needle,addition+needle)
target=HERE/'run_saved_validation_v3.py'
with target.open('x',encoding='utf-8',newline='\n') as stream:stream.write(text)
(HERE/'probe_generation_record_v1.json').write_text(json.dumps(dict(status='DRAFT_NONAUTHORITATIVE',
    original=str(original),original_sha256=sha256(original.read_bytes()).hexdigest(),
    successor=str(target),successor_sha256=sha256(target.read_bytes()).hexdigest(),
    substitutions=['new worker','disallow short comparison','append exact successor/units/budget/review pins'],
    resource_and_cleanup_program_unchanged=True),indent=2)+'\n',encoding='utf-8')
