"""Ordinary isolated units with an explicit, non-authoritative read-lease closure."""
from contextlib import ExitStack
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
ENTRY=HERE.parent/'validation_path_optimization_01/entry_revision_07'
sys.path.insert(0,str(REPO))
package=ModuleType('performance');package.__path__=[str(ENTRY)];sys.modules['performance']=package
def load(name):
    qualified='performance.'+name
    if qualified in sys.modules:return sys.modules[qualified]
    spec=importlib.util.spec_from_file_location(qualified,ENTRY/(name+'.py'))
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module
    spec.loader.exec_module(module);return module
expected={Path(k):v for k,v in json.loads((ENTRY/'code_allowlist_v3.json').read_bytes())['files_sha256'].items()}
vendor=json.loads((ENTRY/'vendor_code_allowlist_v1.json').read_bytes())
expected.update(load('vendor_code_policy').vendor_files((ENTRY/'code_allowlist_v3.json').read_bytes(),
    (ENTRY/'vendor_code_allowlist_v1.json').read_bytes()))
for name in ('h1_historical_n0_verifier_development_v2.py','h1_bootstrap_integration_development_v3.py',
        'h1_owned_bootstrap_controller_development_v3.py'):
    path=REPO/'experiments'/name;expected[path]=sha256(path.read_bytes()).hexdigest()
metadata={Path(k):v for k,v in json.loads((ENTRY/'metadata_allowlist_v1.json').read_bytes())['files_sha256'].items()}
with ExitStack() as stack:
    stack.enter_context(load('code_read_lease').CodeReadLease(expected,root=Path('D:/')))
    stack.enter_context(load('metadata_parse_lease').MetadataParseLease(metadata))
    import pytest
    code=pytest.main(['-q','--disable-warnings','--maxfail=1','-p','no:cacheprovider',*sys.argv[1:]])
sys.exit(code)
