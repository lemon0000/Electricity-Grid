"""Bind the explicit support packages and existing Pyomo import wrapper source."""
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
entry=HERE.parent/'validation_path_optimization_01/entry_revision_03'
path=entry/'interpreter_path_policy_v1.json'
policy=json.loads(path.read_bytes())
support=Path('C:/Users/Psychobabble/AppData/Roaming/Python/Python312/site-packages')
owner=Path('D:/Miniconda3/envs/compute/Lib/site-packages/pyomo/common/dependencies.py')
moved=owner.with_name('deprecation.py')
policy.update(pyomo_loader_owner=dict(file=str(owner),sha256=sha256(owner.read_bytes()).hexdigest()),
    pyomo_moved_owner=dict(file=str(moved),sha256=sha256(moved.read_bytes()).hexdigest()),
    support_root=str(support),support_top_levels=['pygments','colorama'],
    support_files_sha256={str(p):sha256(p.read_bytes()).hexdigest()
        for name in ('pygments','colorama') for p in sorted((support/name).rglob('*.py'))},
    boundary_admission_only=True,loaded_bytes_attested=False,pytest_plugin_autoload=False)
path.write_text(json.dumps(policy,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(support_files=len(policy['support_files_sha256']))))
