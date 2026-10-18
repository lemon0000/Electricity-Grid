"""Explicit invocation paths and boundary origin checks; no discovery cache."""
from hashlib import sha256
from importlib.machinery import FileFinder, PathFinder, SourceFileLoader
import json
from pathlib import Path
import sys
from types import ModuleType


def _binding(value):
    function = getattr(value, '__func__', value)
    return (value, getattr(function, '__code__', None),
        repr(getattr(function, '__defaults__', None)), repr(getattr(function, '__kwdefaults__', None)))


class InterpreterPathPolicy:
    def __init__(self, declaration):
        self.declaration = json.loads(json.dumps(declaration))
        self._declaration_pin = self._policy_pin()
        self.paths = tuple(self.declaration['configured_paths'])
        if not self.paths or len(self.paths) != len(set(self.paths)):
            raise ValueError('explicit unique interpreter path vector required')
        self._finder = _binding(PathFinder.__dict__['find_spec'])
        self._bindings = tuple((owner,name,_binding(owner.__dict__[name])) for owner,names in (
            (PathFinder,('find_spec','_get_spec','_path_importer_cache','_path_hooks')),
            (FileFinder,('find_spec','_get_spec'))) for name in names)
        self._path_object,self._meta_object = sys.path,sys.meta_path
        self._hooks_object,self._cache_object = sys.path_hooks,sys.path_importer_cache
        self._hooks = tuple(sys.path_hooks)
        self._baseline = tuple(sys.meta_path)
        self._pyomo = self._pyomo_owner = self._pytest_hook = None
        self._moved = self._moved_owner = self._pyomo_loader_type = None
        self._moved_binding = None
        self._pyomo_bindings = ()
        self._pytest_active = False
        self._loaded = {}
        self.failure = None
        self.observations = []
        self._accept_pyomo()
        self._accept_moved_finder()

    def _policy_pin(self):
        return sha256(json.dumps(self.declaration,sort_keys=True,separators=(',',':')).encode()).hexdigest()

    def _flags(self):
        if (not sys.flags.isolated or not sys.flags.ignore_environment or not sys.flags.no_user_site
                or not sys.flags.safe_path or sys.flags.dont_write_bytecode != 1 or not sys.dont_write_bytecode
                or str(Path(sys.executable)) != self.declaration['executable']
                or sys.prefix != self.declaration['prefix']):
            raise ValueError('fixed -I -B compute interpreter required')

    def _accept_pyomo(self):
        module = sys.modules.get('pyomo.common.dependencies')
        if module is None:return
        expected = self.declaration['pyomo_loader_owner']
        if (not isinstance(module,ModuleType) or vars(module).get('__file__') != expected['file']
                or sha256(Path(expected['file']).read_bytes()).hexdigest() != expected['sha256']):
            raise ValueError('Pyomo loader owner origin differs')
        finder = module._DeferredImportCallbackFinder
        if type(finder) is not module.DeferredImportCallbackFinder:
            raise ValueError('exact Pyomo callback finder required')
        if self._pyomo is None:
            self._pyomo,self._pyomo_owner = finder,module
            self._pyomo_loader_type=module.DeferredImportCallbackLoader
            self._baseline = tuple(item for item in self._baseline if item is not finder)
            targets = ((module.DeferredImportCallbackFinder,'find_spec'),
                (module.DeferredImportCallbackLoader,'create_module'),
                (module.DeferredImportCallbackLoader,'exec_module'))
            self._pyomo_bindings = tuple((o,n,_binding(vars(o)[n])) for o,n in targets)
        if (finder is not self._pyomo or module is not self._pyomo_owner
                or module.DeferredImportCallbackLoader is not self._pyomo_loader_type):
            raise ValueError('Pyomo callback finder identity changed')
        if any(_binding(vars(o)[n]) != pin for o,n,pin in self._pyomo_bindings):
            raise ValueError('Pyomo callback finder or loader code changed')

    def _accept_moved_finder(self):
        module=sys.modules.get('pyomo.common.deprecation')
        if module is None:return
        expected=self.declaration['pyomo_moved_owner']
        if (not isinstance(module,ModuleType) or vars(module).get('__file__')!=expected['file']
                or sha256(Path(expected['file']).read_bytes()).hexdigest()!=expected['sha256']):
            raise ValueError('Pyomo moved finder owner differs')
        matches=[item for item in sys.meta_path if type(item) is module.MovedModuleFinder]
        if len(matches)!=1 or sys.meta_path[-1] is not matches[0]:
            raise ValueError('one final Pyomo moved finder required')
        if self._moved is None:
            self._moved,self._moved_owner=matches[0],module
            self._baseline=tuple(item for item in self._baseline if item is not self._moved)
            self._moved_binding=(module.MovedModuleFinder,_binding(vars(module.MovedModuleFinder)['find_spec']))
        cls,pin=self._moved_binding
        if (module is not self._moved_owner or matches[0] is not self._moved
                or module.MovedModuleFinder is not cls or _binding(vars(cls)['find_spec'])!=pin):
            raise ValueError('Pyomo moved finder identity changed')

    def _environment(self):
        self._flags()
        if self._policy_pin() != self._declaration_pin:
            raise ValueError('interpreter path policy declaration changed')
        if (sys.path is not self._path_object or sys.meta_path is not self._meta_object
                or sys.path_hooks is not self._hooks_object or sys.path_importer_cache is not self._cache_object
                or tuple(sys.path_hooks) != self._hooks):
            raise ValueError('import environment containers or path hooks changed')
        if any(_binding(vars(o)[n]) != pin for o,n,pin in self._bindings):
            raise ValueError('stock import path finder changed')
        self._accept_pyomo()
        self._accept_moved_finder()
        extras=[item for item in (self._pyomo,self._moved,self._pytest_hook if self._pytest_active else None) if item is not None]
        rest=tuple(item for item in sys.meta_path if not any(item is extra for extra in extras))
        if (len(rest)!=len(self._baseline) or any(a is not b for a,b in zip(rest,self._baseline))
                or any(sum(item is extra for item in sys.meta_path)!=1 for extra in extras)
                or sum(item is PathFinder for item in sys.meta_path)!=1):
            detail=dict(baseline=[repr(item) for item in self._baseline],
                current=[repr(item) for item in sys.meta_path],allowed=[repr(item) for item in extras])
            raise ValueError('import meta finders changed: '+json.dumps(detail))
        if self._pyomo is not None and sys.meta_path.index(self._pyomo)>sys.meta_path.index(PathFinder):
            raise ValueError('Pyomo callback finder order changed')

    def _importer_cache(self):
        for root in self.paths:
            if root not in sys.path_importer_cache:continue
            finder=sys.path_importer_cache[root]
            if root.endswith('python312.zip') and not Path(root).exists() and finder is None:continue
            if type(finder) is not FileFinder or finder.path!=root:
                raise ValueError('stock configured-root importer required: '+root)

    def begin_pytest(self,config):
        module=sys.modules['_pytest.assertion.rewrite']
        hooks=[item for item in sys.meta_path if type(item) is module.AssertionRewritingHook]
        if len(hooks)!=1 or hooks[0].config is not config or self._pytest_active:
            raise ValueError('exact pytest assertion hook required')
        self._pytest_hook,self._pytest_active=hooks[0],True
        return self.admit('pytest_configure_before_collection')

    def end_pytest(self):
        self._pytest_active=False
        return self.admit('pytest_return')

    def configure(self):
        self._flags()
        if sys.path != self.declaration['isolated_base_paths']:
            raise ValueError('unexpected isolated startup search paths')
        sys.path[:] = self.paths
        return self.admit('before_repository_imports')

    def admit(self, boundary):
        if self.failure is not None:
            raise ValueError('interpreter path policy poisoned at '+self.failure['boundary'])
        try:row=self._admit(boundary)
        except BaseException as error:
            self.failure=dict(boundary=boundary,error=repr(error))
            raise
        self.observations.append(row)
        return row

    def _admit(self,boundary):
        self._environment()
        # Only exact duplicates are removed. Unknown entries/order changes fail;
        # case folding, canonical alias merging and broad path filtering are absent.
        unique = list(dict.fromkeys(sys.path))
        if tuple(unique) != self.paths:
            raise ValueError('configured interpreter search paths changed')
        if _binding(PathFinder.__dict__['find_spec']) != self._finder:
            raise ValueError('stock import path finder changed')
        sys.path[:] = unique
        self._importer_cache()
        observed = {}
        for name, expected in self.declaration['top_level_origins'].items():
            spec = PathFinder.find_spec(name, unique)
            if (spec is None or spec.origin != expected['file']
                    or type(spec.loader) is not SourceFileLoader):
                raise ValueError('planned top-level import origin differs: ' + name)
            path = Path(expected['file'])
            if path != path.resolve(strict=True) or sha256(path.read_bytes()).hexdigest() != expected['sha256']:
                raise ValueError('planned top-level origin bytes differ: ' + name)
            module = sys.modules.get(name)
            if module is None:
                observed[name] = 'resolved_not_loaded'
                if name in self._loaded:
                    raise ValueError('previously loaded top-level module disappeared: ' + name)
                continue
            actual = vars(module) if isinstance(module, ModuleType) else {}
            actual_spec = actual.get('__spec__')
            loader = actual.get('__loader__')
            inner=loader
            if self._pyomo_owner is not None and type(loader) is self._pyomo_owner.DeferredImportCallbackLoader:
                inner=loader._loader
            package=[str(path.parent)]
            if (actual.get('__file__') != expected['file'] or actual_spec is None
                    or actual_spec.name!=name or actual_spec.origin != expected['file']
                    or actual_spec.loader is not loader or type(inner) is not SourceFileLoader
                    or inner.name!=name or inner.path!=expected['file']
                    or list(actual.get('__path__',()))!=package
                    or list(actual_spec.submodule_search_locations or ())!=package):
                raise ValueError('loaded top-level module origin differs: ' + name)
            identities = (module, actual_spec, loader, inner)
            if name in self._loaded and any(a is not b for a,b in zip(self._loaded[name],identities)):
                raise ValueError('loaded top-level module identity changed: ' + name)
            self._loaded[name] = identities
            observed[name] = 'loaded_origin_current_file_verified'
        self._importer_cache()
        support=Path(self.declaration['support_root']);support_modules=[]
        for name,module in tuple(sys.modules.items()):
            if not isinstance(module,ModuleType):continue
            file=vars(module).get('__file__')
            if type(file) is not str or not Path(file).is_relative_to(support):continue
            pin=self.declaration['support_files_sha256'].get(file)
            if (name.split('.')[0] not in self.declaration['support_top_levels'] or pin is None
                    or sha256(Path(file).read_bytes()).hexdigest()!=pin):
                raise ValueError('unfixed user-site module loaded: '+name)
            support_modules.append(name)
        self._environment()
        row = dict(boundary=boundary, effective_sys_path=list(sys.path), modules=observed,
            support_modules=sorted(support_modules),
            python_flags=repr(sys.flags), helper_distribution_result_cache=False,
            stock_metadata_finder_unchanged=True, formal_result=False)
        return row

    def receipt(self):
        return dict(schema='h1_explicit_interpreter_path_policy_receipt_development_v1',
            observations=self.observations,first_failure=self.failure, helper_distribution_result_cache=False,
            sdk_preimports_added=False, origin_checks_at_boundaries_only=True,
            current_origin_file_bytes_checked=True,loaded_bytes_attested=False,
            entire_sdk_provenance_claimed=False, formal_result=False)
