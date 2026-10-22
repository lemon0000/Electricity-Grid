"""Private one-shot constructor result capture; detached development data only.

No source/current/registry result survives an operation. This mixin carries no
owner, writer, solver or execution capability.
"""
import os
from threading import get_ident

SCHEMA = 'h1_constructor_inspection_capture_development_v1'
_EMPTY = object()


class ConstructorInspectionCapture:
    def __init__(self, *args, **kwargs):
        _check_definition()
        self._cic_creator = os.getpid(), get_ident()
        self._cic_constructing = True
        self._cic_inspecting = False
        self._cic_value = _EMPTY
        self._cic_taken = False
        try:
            super().__init__(*args, **kwargs)
        except BaseException:
            self._cic_value = _EMPTY
            raise
        finally:
            self._cic_constructing = False

    def _cic_owner(self):
        if (os.getpid(), get_ident()) != self._cic_creator:
            raise ValueError('constructor inspection creator differs')

    def inspect(self):
        self._cic_owner()
        _check_definition()
        if not self._cic_constructing or self._cic_inspecting or self._cic_value is not _EMPTY:
            raise ValueError('exactly one constructor inspection required')
        self._cic_inspecting = True
        try:
            value = super().inspect()
            self._cic_value = value
            return value
        finally:
            self._cic_inspecting = False

    def _take_constructor_inspection(self):
        self._cic_owner()
        _check_definition()
        if self._cic_constructing or self._cic_taken or self._cic_value is _EMPTY:
            raise ValueError('completed unused constructor inspection required')
        value = self._cic_value
        self._cic_value = _EMPTY
        self._cic_taken = True
        return value

    def close(self):
        self._cic_owner()
        self._cic_value = _EMPTY
        return super().close()

    def __copy__(self):
        raise TypeError('constructor inspection cannot be copied')

    def __deepcopy__(self, memo):
        raise TypeError('constructor inspection cannot be copied')

    def __reduce_ex__(self, protocol):
        raise TypeError('constructor inspection cannot be serialized')


def _check_definition():
    if tuple(vars(ConstructorInspectionCapture)) != _CLASS_KEYS:
        raise ValueError('constructor capture class layout changed')
    for name, function, code, defaults in _DEFINITIONS:
        if (vars(ConstructorInspectionCapture).get(name) is not function
                or function.__code__ is not code or function.__defaults__ is not defaults):
            raise ValueError('constructor capture definition changed')


_DEFINITIONS = tuple((name, function, function.__code__, function.__defaults__)
    for name, function in vars(ConstructorInspectionCapture).items()
    if callable(function) and hasattr(function, '__code__'))
_CLASS_KEYS = tuple(vars(ConstructorInspectionCapture))
