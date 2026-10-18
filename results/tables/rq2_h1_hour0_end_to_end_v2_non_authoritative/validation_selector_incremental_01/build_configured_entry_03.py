"""Prepare an unsealed successor without altering either tested predecessor."""
from hashlib import sha256
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PATH_ROOT = HERE.parent / 'validation_path_optimization_01'
OLD = PATH_ROOT / 'entry_revision_02'
NEW = PATH_ROOT / 'entry_revision_03'
raw = (OLD / 'package_manifest_v1.json').read_bytes()
assert sha256(raw).hexdigest() == '6592f996e4a02b6e4ee3f510d9f7c24db1061a1ffcd56ba476d2d5f8b8f9fb10'
members = json.loads(raw)['files_sha256']
assert all(sha256((OLD/name).read_bytes()).hexdigest() == pin for name,pin in members.items())
NEW.mkdir(exist_ok=False)
for path in OLD.iterdir():
    if path.is_file() and path.name not in ('package_manifest_v1.json', 'launch_validation.py'):
        (NEW/path.name).write_bytes(path.read_bytes())
(NEW/'path_predecessor_package_manifest.json').write_bytes(raw)
(NEW/'launch_validation.py').write_bytes((OLD/'launch_validation.py').read_bytes())
terminal = json.loads((HERE/'configured_entry_02/terminal.json').read_bytes())
origins = json.loads((HERE/'configured_entry_02/module_origins.json').read_bytes())
pins = json.loads((HERE/'configured_entry_02/module_origin_sha256.json').read_bytes())
names = ('pyomo','highspy','numpy','scipy','pypower','yaml','osqp','gurobipy','pytest','pygments')
policy = dict(schema='h1_explicit_interpreter_path_policy_development_v1',
    executable='D:\\Miniconda3\\envs\\compute\\python.exe',
    prefix='D:\\Miniconda3\\envs\\compute',
    isolated_base_paths=['D:\\Miniconda3\\envs\\compute\\python312.zip',
        'D:\\Miniconda3\\envs\\compute\\DLLs','D:\\Miniconda3\\envs\\compute\\Lib',
        'D:\\Miniconda3\\envs\\compute','D:\\Miniconda3\\envs\\compute\\Lib\\site-packages'],
    configured_paths=terminal['effective_sys_path'],
    top_level_origins={name:dict(file=origins[name],sha256=pins[name]) for name in names},
    baseline_evidence='validation_selector_incremental_01/configured_entry_comparison_02.json',
    helper_distribution_result_cache=False, stock_metadata_finder_unchanged=True,
    formal_result=False, formal_execution_ready=False, native_execution_authorized=False)
with (NEW/'interpreter_path_policy_v1.json').open('x',encoding='utf-8') as stream:
    json.dump(policy,stream,indent=2)
print(str(NEW))
