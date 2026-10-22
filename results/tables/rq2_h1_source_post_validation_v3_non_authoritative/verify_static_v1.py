"""Narrow syntax, successor diff and whitespace checks; no numerical execution."""
import ast
import difflib
from hashlib import sha256
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
pairs=[
    ('experiments/h1_phase_historical_batch_development_v2.py','experiments/h1_phase_historical_batch_development_v3.py'),
    ('experiments/h1_phase_exact_source_batch_development_v2.py','experiments/h1_phase_exact_source_batch_development_v3.py'),
    ('experiments/h1_constructor_source_batch_validation_development_v1.py','experiments/h1_constructor_source_batch_validation_development_v2.py'),
]
files=[REPO/new for old,new in pairs]
files += [REPO/'experiments/h1_constructor_runtime_guard_development_v1.py',
          REPO/'tests/test_h1_source_post_validation_development_v3.py']
files += sorted(HERE.glob('*.py'))
bad=[]
for path in files:
    text=path.read_text(encoding='utf-8')
    ast.parse(text,filename=str(path))
    bad += [dict(path=str(path),line=index) for index,line in enumerate(text.splitlines(),1) if line.rstrip()!=line]
if bad:raise ValueError('new-file trailing whitespace: '+repr(bad))
diff=''.join(''.join(difflib.unified_diff((REPO/old).read_text(encoding='utf-8').splitlines(True),
    (REPO/new).read_text(encoding='utf-8').splitlines(True),fromfile=old,tofile=new)) for old,new in pairs)
(HERE/'successor_diff_v1.patch').write_text(diff,encoding='utf-8')
result=dict(status='DRAFT_NONAUTHORITATIVE',python_sources_parsed=len(files),
    new_source_trailing_whitespace=[],diff_scope='three direct versioned successors; new guard/test separate',
    code_sha256={str(path):sha256(path.read_bytes()).hexdigest() for path in files},
    git_tracked_diff_check=subprocess.run(['git','diff','--check'],cwd=REPO,capture_output=True,text=True).__dict__,
    code_or_science_execution=False,new_normal_jobs=0,real_native_calls=0,formal_result=False)
# CompletedProcess stores only serializable command/returncode/stdout/stderr.
with (HERE/'static_verification_v1.json').open('x',encoding='utf-8') as stream:
    json.dump(result,stream,indent=2);stream.write('\n')
print(json.dumps(dict(parsed=len(files),whitespace_errors=len(bad),tracked_diff_check=result['git_tracked_diff_check']['returncode'])))
