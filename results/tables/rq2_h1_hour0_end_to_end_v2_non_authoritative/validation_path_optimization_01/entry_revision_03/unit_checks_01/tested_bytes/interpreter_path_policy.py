"""Explicit invocation paths and boundary origin checks; no discovery cache."""
from hashlib import sha256
from importlib.machinery import PathFinder, SourceFileLoader
from pathlib import Path
import sys
from types import ModuleType


def _binding(value):
    function = getattr(value, '__func__', value)
    return (value, getattr(function, '__code__', None),
        repr(getattr(function, '__defaults__', None)), repr(getattr(function, '__kwdefaults__', None)))


class InterpreterPathPolicy:
    def __init__(self, declaration):
        self.declaration = declaration
        self.paths = tuple(declaration['configured_paths'])
        if not self.paths or len(self.paths) != len(set(self.paths)):
            raise ValueError('explicit unique interpreter path vector required')
        self._finder = _binding(PathFinder.__dict__['find_spec'])
        self._loaded = {}
        self.observations = []

    def _flags(self):
        if (not sys.flags.isolated or not sys.flags.ignore_environment or not sys.flags.no_user_site
                or not sys.flags.safe_path or not sys.dont_write_bytecode
                or str(Path(sys.executable)) != self.declaration['executable']
                or sys.prefix != self.declaration['prefix']):
            raise ValueError('fixed -I -B compute interpreter required')

    def configure(self):
        self._flags()
        if sys.path != self.declaration['isolated_base_paths']:
            raise ValueError('unexpected isolated startup search paths')
        sys.path[:] = self.paths
        return self.admit('before_repository_imports')

    def admit(self, boundary):
        self._flags()
        # Only exact duplicates are removed. Unknown entries/order changes fail;
        # case folding, canonical alias merging and broad path filtering are absent.
        unique = list(dict.fromkeys(sys.path))
        if tuple(unique) != self.paths:
            raise ValueError('configured interpreter search paths changed')
        if _binding(PathFinder.__dict__['find_spec']) != self._finder:
            raise ValueError('stock import path finder changed')
        sys.path[:] = unique
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
            if (actual.get('__file__') != expected['file'] or actual_spec is None
                    or actual_spec.origin != expected['file']
                    or type(loader) is not SourceFileLoader or actual_spec.loader is not loader):
                raise ValueError('loaded top-level module origin differs: ' + name)
            identities = (module, actual_spec, loader)
            if name in self._loaded and any(a is not b for a,b in zip(self._loaded[name],identities)):
                raise ValueError('loaded top-level module identity changed: ' + name)
            self._loaded[name] = identities
            observed[name] = 'loaded_origin_verified'
        row = dict(boundary=boundary, effective_sys_path=list(sys.path), modules=observed,
            python_flags=repr(sys.flags), helper_distribution_result_cache=False,
            stock_metadata_finder_unchanged=True, formal_result=False)
        self.observations.append(row)
        return row

    def receipt(self):
        return dict(schema='h1_explicit_interpreter_path_policy_receipt_development_v1',
            observations=self.observations, helper_distribution_result_cache=False,
            sdk_preimports_added=False, origin_checks_at_boundaries_only=True,
            entire_sdk_provenance_claimed=False, formal_result=False)
