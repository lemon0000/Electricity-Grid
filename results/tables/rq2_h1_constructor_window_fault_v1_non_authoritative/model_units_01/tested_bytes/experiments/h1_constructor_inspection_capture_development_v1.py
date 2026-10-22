"""Private one-shot constructor result capture; detached development data only.

No source/current/registry result survives an operation. This mixin carries no
owner, writer, solver or execution capability.
"""
import os
from threading import get_ident

SCHEMA = 'h1_constructor_inspection_capture_development_v1'
_EMPTY = object()


def _build_capture():
    # Lifetime operations use the original closure bindings. Exported aliases
    # remain observed; replacing one cannot redefine an empty slot or creator.
    empty, process_id, thread_id = _EMPTY, os.getpid, get_ident
    namespace, os_module, seals = globals(), os, {}

    def check():
        if (namespace.get('_EMPTY') is not empty or namespace.get('os') is not os_module
                or os_module.getpid is not process_id or namespace.get('get_ident') is not thread_id
                or namespace.get('_check_definition') is not check
                or namespace.get('ConstructorInspectionCapture') is not ConstructorInspectionCapture):
            raise ValueError('constructor capture binding changed')
        if (tuple(vars(ConstructorInspectionCapture)) != seals['keys']
                or ConstructorInspectionCapture.__bases__ is not seals['bases']
                or ConstructorInspectionCapture.__mro__ is not seals['mro']):
            raise ValueError('constructor capture class layout changed')
        for name, function, code, defaults, default_text, kwdefaults, kw_text, closure, cells in seals['functions']:
            if ((name is not None and vars(ConstructorInspectionCapture).get(name) is not function)
                    or function.__code__ is not code or function.__globals__ is not namespace
                    or function.__defaults__ is not defaults or repr(function.__defaults__) != default_text
                    or function.__kwdefaults__ is not kwdefaults or repr(function.__kwdefaults__) != kw_text
                    or function.__closure__ is not closure
                    or any(cell.cell_contents is not value for cell, value in zip(closure or (), cells))):
                raise ValueError('constructor capture definition changed')

    def owner(self):
        if (process_id(), thread_id()) != self._cic_creator:
            raise ValueError('constructor inspection creator differs')

    class ConstructorInspectionCapture:
        _cic_owner = owner

        def __init__(self, *args, **kwargs):
            check()
            self._cic_creator = process_id(), thread_id()
            self._cic_constructing = True
            self._cic_inspecting = False
            self._cic_value = empty
            self._cic_taken = False
            try:
                super().__init__(*args, **kwargs)
            except BaseException:
                self._cic_value = empty
                raise
            finally:
                self._cic_constructing = False

        def inspect(self):
            check()
            owner(self)
            if not self._cic_constructing or self._cic_inspecting or self._cic_value is not empty:
                raise ValueError('exactly one constructor inspection required')
            self._cic_inspecting = True
            try:
                value = super().inspect()
                self._cic_value = value
                return value
            finally:
                self._cic_inspecting = False

        def _take_constructor_inspection(self):
            check()
            owner(self)
            if self._cic_constructing or self._cic_taken or self._cic_value is empty:
                raise ValueError('completed unused constructor inspection required')
            value = self._cic_value
            self._cic_value = empty
            self._cic_taken = True
            return value

        def close(self):
            # Teardown must remain possible after a dependency drift. Preserve
            # the parent's ordered cleanup/retry contract and primary error.
            if (process_id(), thread_id()) != self._cic_creator:
                raise ValueError('constructor inspection creator differs')
            self._cic_value = empty
            return super().close()

        def __copy__(self):
            raise TypeError('constructor inspection cannot be copied')

        def __deepcopy__(self, memo):
            raise TypeError('constructor inspection cannot be copied')

        def __reduce_ex__(self, protocol):
            raise TypeError('constructor inspection cannot be serialized')

    functions = [(name, value) for name, value in vars(ConstructorInspectionCapture).items()
                 if callable(value) and hasattr(value, '__code__')]
    functions.append((None, check))
    seals.update(keys=tuple(vars(ConstructorInspectionCapture)), bases=ConstructorInspectionCapture.__bases__,
        mro=ConstructorInspectionCapture.__mro__, functions=tuple(
            (name, f, f.__code__, f.__defaults__, repr(f.__defaults__), f.__kwdefaults__, repr(f.__kwdefaults__),
             f.__closure__, tuple(cell.cell_contents for cell in f.__closure__ or ())) for name, f in functions))
    return ConstructorInspectionCapture, check


ConstructorInspectionCapture, _check_definition = _build_capture()
