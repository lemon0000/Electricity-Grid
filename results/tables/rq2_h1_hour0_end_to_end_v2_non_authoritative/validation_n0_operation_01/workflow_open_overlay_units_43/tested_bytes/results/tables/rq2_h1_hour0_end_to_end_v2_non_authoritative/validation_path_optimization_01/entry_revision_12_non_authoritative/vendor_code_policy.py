"""Fixed extension of the predecessor code allowlist; no discovery/result cache."""
from hashlib import sha256
from importlib.machinery import SourceFileLoader
import json
from pathlib import Path
from types import ModuleType

REPOSITORY_ALLOWLIST_SHA='93eef2e8a4f71c3fe359ce417985d96169530449d45b39f77effd11efee90142'
VENDOR_ROOT=Path('D:/Miniconda3/envs/compute/Lib/site-packages/pyomo')
VENDOR_PINS={'D:\\Miniconda3\\envs\\compute\\Lib\\site-packages\\pyomo\\solvers\\plugins\\solvers\\GUROBI.py': '745c0712aec2e2ccbb38faa8e977df009e2e5f7b68a45cf09278cb8c51ed3da8', 'D:\\Miniconda3\\envs\\compute\\Lib\\site-packages\\pyomo\\solvers\\plugins\\solvers\\gurobi_direct.py': 'cef4ef2bc51d819a83ad4a3ce467fb6cbde6594b201c8ee34e9649953cf451e6', 'D:\\Miniconda3\\envs\\compute\\Lib\\site-packages\\pyomo\\solvers\\plugins\\solvers\\direct_solver.py': 'a89da088e10445b71ce4feb48e612aa585f6a83069f732bacac835f51526f2d5', 'D:\\Miniconda3\\envs\\compute\\Lib\\site-packages\\pyomo\\solvers\\plugins\\solvers\\direct_or_persistent_solver.py': '9fbf3cfd5f33d320891fc557a03d286fe66678eace0553941bd51ae25b9132a7', 'D:\\Miniconda3\\envs\\compute\\Lib\\site-packages\\pyomo\\opt\\results\\results_.py': '9d7b37d99bda53d5645f50a44af05adb5a9f618856fc897da5aed21239039b1a', 'D:\\Miniconda3\\envs\\compute\\Lib\\site-packages\\pyomo\\opt\\results\\solution.py': '20313703115e77b215b1848403142be29e0bfd8958af925ae25a2bdd9cec3097', 'D:\\Miniconda3\\envs\\compute\\Lib\\site-packages\\pyomo\\opt\\results\\solver.py': 'e45a0d14a7f5ca1b4e4ddb3c196b5dfa90abb18aba9b108040ddd5fb25898aae'}
MODULE_PATHS={
    'pyomo.solvers.plugins.solvers.GUROBI':'solvers/plugins/solvers/GUROBI.py',
    'pyomo.solvers.plugins.solvers.gurobi_direct':'solvers/plugins/solvers/gurobi_direct.py',
    'pyomo.solvers.plugins.solvers.direct_solver':'solvers/plugins/solvers/direct_solver.py',
    'pyomo.solvers.plugins.solvers.direct_or_persistent_solver':'solvers/plugins/solvers/direct_or_persistent_solver.py',
    'pyomo.opt.results.results_':'opt/results/results_.py',
    'pyomo.opt.results.solution':'opt/results/solution.py',
    'pyomo.opt.results.solver':'opt/results/solver.py'}


def no_duplicates(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('duplicate vendor JSON key')
        result[key]=value
    return result


def vendor_files(repository_raw,vendor_raw):
    if sha256(repository_raw).hexdigest()!=REPOSITORY_ALLOWLIST_SHA:
        raise ValueError('exact predecessor repository allowlist required')
    declaration=json.loads(vendor_raw,object_pairs_hook=no_duplicates)
    expected=dict(schema='h1_fixed_vendor_code_allowlist_development_v1',
        root=str(VENDOR_ROOT),files_sha256=VENDOR_PINS)
    if declaration!=expected:raise ValueError('exact seven vendor paths and pins required')
    return {Path(name):pin for name,pin in declaration['files_sha256'].items()}


def assert_unloaded(modules):
    if any(name in modules for name in MODULE_PATHS):
        raise ValueError('vendor modules must not precede union code lease')


def origins(modules,*,required=False):
    result={}
    for name,relative in MODULE_PATHS.items():
        module=modules.get(name)
        if module is None:
            if required:raise ValueError('required vendor module absent: '+name)
            continue
        expected=str(VENDOR_ROOT/relative)
        spec=getattr(module,'__spec__',None)
        loader=getattr(module,'__loader__',None);inner=loader
        owner=modules.get('pyomo.common.dependencies')
        if owner is not None and type(loader) is getattr(owner,'DeferredImportCallbackLoader',None):
            inner=loader._loader
        if (not isinstance(module,ModuleType) or getattr(module,'__file__',None)!=expected
                or spec is None or getattr(spec,'origin',None)!=expected or spec.name!=name
                or spec.loader is not loader or type(inner) is not SourceFileLoader
                or inner.name!=name or inner.path!=expected):
            raise ValueError('fixed vendor module origin differs: '+name)
        result[name]=expected
    return result
