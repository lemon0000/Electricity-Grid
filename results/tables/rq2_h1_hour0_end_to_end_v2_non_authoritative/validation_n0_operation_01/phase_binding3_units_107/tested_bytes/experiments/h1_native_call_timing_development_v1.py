# _apply_body is adapted from Pyomo gurobi_direct.py.
# # LICENSE
# 
# Copyright (c) 2008-2026 National Technology and Engineering Solutions of
# Sandia, LLC. Under the terms of Contract DE-NA0003525 with National
# Technology and Engineering Solutions of Sandia, LLC, the U.S.
# Government retains certain rights in this software.
# 
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 
# * Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
# 
# * Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
# 
# * Neither the name of the Sandia National Laboratories nor the names of
#   its contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
# TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""Pinned Pyomo apply copy with durable intent and optimize-only wall interval.

Can optimize when called with a real adapter: separate explicit authorization
and Job supervision are prerequisites. No CLI or native authority is supplied.
"""
import ast
import inspect as reflection
import os
import stat
from pathlib import Path
import textwrap
import threading
import time
import uuid

import pyomo.version
import pyomo.solvers.plugins.solvers.gurobi_direct as vendor
from experiments import h1_raw_ingress_development_v1 as io

SCHEMA = 'h1_native_call_timing_development_v1'
VERSION = '6.10.1'
FILE_SHA = 'cef4ef2bc51d819a83ad4a3ce467fb6cbde6594b201c8ee34e9649953cf451e6'
APPLY_SHA = 'c70bf75f5dd72012a742a98673c50a025e27e531381ce02cd9fd977164434f0d'
OPTIONS_SHA = '18a102fe4a5aa013df5a6d48fab0b9fa89038ea0b716bf61c704f9ba27a20b8f'
GurobiDirect = vendor.GurobiDirect
_ORIGINAL_APPLY = GurobiDirect._apply_solver
StaleFlagManager, capture_output = vendor.StaleFlagManager, vendor.capture_output
_set_options, re, gurobipy, Bunch = vendor._set_options, vendor.re, vendor.gurobipy, vendor.Bunch
FLAGS = dict(instrumentation_coverage_verified=False, observer_overhead_separated=False,
    component_budget_verified=False, resource_admission=False, formal_execution_ready=False,
    formal_result=False, native_execution_authenticated=False, native_execution_authorized=False)


def _apply_body(self, measurement):
    StaleFlagManager.mark_all_as_stale()
    with capture_output(capture_fd=True):
        self._solver_model.setParam('LogToConsole', int(bool(self._tee)))
    if self._keepfiles:
        self._solver_model.setParam('LogFile', self._log_file)
        print('Solver log file: ' + self._log_file)
    if self._env_options:
        new_options = {key: option for key, option in self.options.items()
                       if key not in self._env_options or self._env_options[key] != option}
    else:
        new_options = self.options
    _set_options(self._solver_model, new_options)
    if self._version_major >= 5:
        for suffix in self._suffixes:
            if re.match(suffix, 'dual'):
                self._solver_model.setParam(gurobipy.GRB.Param.QCPDual, 1)
    measurement.invoke(self._solver_model.optimize, self._callback)
    self._needs_updated = False
    if self._keepfiles:
        self._solver_model.setParam('LogFile', 'default')
    return Bunch(rc=None, log=None)


def validate_vendor():
    if (pyomo.version.version != VERSION or io.digest(Path(vendor.__file__).read_bytes()) != FILE_SHA
            or vendor.GurobiDirect._apply_solver is not _ORIGINAL_APPLY or vendor._set_options is not _set_options
            or vendor.capture_output is not capture_output or vendor.StaleFlagManager is not StaleFlagManager
            or io.digest(reflection.getsource(_ORIGINAL_APPLY).encode()) != APPLY_SHA
            or io.digest(reflection.getsource(_set_options).encode()) != OPTIONS_SHA):
        raise ValueError('pinned installed apply implementation differs')
    try:
        original = ast.parse(textwrap.dedent(reflection.getsource(_ORIGINAL_APPLY))).body[0]
        copied = ast.parse(textwrap.dedent(reflection.getsource(_apply_body))).body[0]
        if not isinstance(original, ast.FunctionDef) or not isinstance(copied, ast.FunctionDef):
            raise ValueError('apply function definition required')
    except (SyntaxError, OSError, TypeError, IndexError) as error:
        raise ValueError('apply source unavailable or malformed') from error
    copied.name = original.name
    copied.args.args = copied.args.args[:1]
    count = 0
    for node in ast.walk(copied):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id == 'measurement':
            if node.func.attr != 'invoke' or len(node.args) != 2 or node.keywords:
                raise ValueError('unexpected timing insertion')
            node.func, node.args = node.args[0], node.args[1:]
            count += 1
    if count != 1 or ast.dump(original) != ast.dump(copied):
        raise ValueError('apply copy differs beyond optimize timing insertion')


def implementation_identity():
    return io.digest(io.encode(dict(schema=SCHEMA, version=VERSION, vendor_file=FILE_SHA,
        apply=APPLY_SHA, options=OPTIONS_SHA, own=io.digest(Path(__file__).read_bytes()),
        io=io.digest(Path(io.__file__).read_bytes()))))


def integer(value):
    if type(value) is not int or not 0 <= value < 2**63: raise ValueError('bounded clock integer required')
    return value


def _root_identity(root):
    if root.resolve() != root: raise ValueError('canonical timing root required')
    info = root.stat(follow_symlinks=False)
    if not stat.S_ISDIR(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
        raise ValueError('plain timing directory required')
    return info.st_dev, info.st_ino


def _names(root):
    names = set()
    with os.scandir(root) as entries:
        for item in entries:
            names.add(item.name)
            if len(names) > 4: raise ValueError('timing entry cap')
    return names


class Measurement:
    def __init__(self, root, request_sha256, stage, *, clock=time.perf_counter_ns):
        io.pin(request_sha256)
        if type(stage) is not int or not 0 <= stage < 232: raise ValueError('bounded stage required')
        validate_vendor()
        self.root = Path(root).absolute()
        if self.root.resolve() != self.root: raise ValueError('canonical timing root required')
        self.root.mkdir(exist_ok=False)
        self.root_identity = _root_identity(self.root)
        self.clock, self.owner = clock, (os.getpid(), threading.get_ident())
        self.guard = threading.Lock()
        self.started = self.called = self.poisoned = self.closed = False
        self.implementation = implementation_identity()
        self.binding = dict(schema=SCHEMA, request_sha256=request_sha256, stage=stage,
            clock_domain=uuid.uuid4().hex, pid=self.owner[0], thread_id=self.owner[1],
            implementation=self.implementation, **FLAGS)
        self.binding_pin = io.write_metadata(self.root/'binding.json', self.binding)

    def _check(self):
        if (self.owner != (os.getpid(), threading.get_ident()) or self.poisoned or self.closed
                or _root_identity(self.root) != self.root_identity
                or implementation_identity() != self.implementation or
                io.read_stable(self.root/'binding.json', io.META_CAP)[0] != io.encode(self.binding)):
            raise ValueError('measurement owner/state/binding differs')

    def invoke(self, optimize, callback):
        self._check()
        if not self.started or self.called or callback is not None: raise ValueError('single callback-free optimize required')
        self.called = True
        intent_pin = io.write_metadata(self.root/'intent.json', dict(schema=SCHEMA,
            binding_sha256=self.binding_pin, state='optimize_intended'))
        self.start = integer(self.clock())
        result = optimize(callback)
        self.end = integer(self.clock())
        if self.end < self.start: raise ValueError('native clock reversal')
        self.completion_pin = io.write_metadata(self.root/'completion.json', dict(schema=SCHEMA,
            binding_sha256=self.binding_pin, intent_sha256=intent_pin,
            native_start_ns=self.start, native_end_ns=self.end, state='optimize_returned'))
        return result

    def apply(self, solver):
        if not self.guard.acquire(blocking=False): raise ValueError('measurement active')
        try:
            self._check()
            if self.started: raise ValueError('measurement consumed')
            self.started = True
            validate_vendor()
            if type(solver) is not GurobiDirect or solver._callback is not None:
                raise ValueError('exact callback-free direct adapter required')
            native = solver._solver_model
            left = integer(self.clock())
            result = _apply_body(solver, self)
            right = integer(self.clock())
            if solver._solver_model is not native or not self.called or not left <= self.start <= self.end <= right:
                raise ValueError('native identity or interval containment differs')
            self._check(); validate_vendor()
            pin = io.write_metadata(self.root/'terminal.json', dict(schema=SCHEMA,
                binding_sha256=self.binding_pin, completion_sha256=self.completion_pin,
                apply_start_ns=left, apply_end_ns=right, **FLAGS))
            checked = inspect(self.root, expected_binding_sha=self.binding_pin,
                expected_terminal_sha=pin, expected_implementation=self.implementation)
            self._check()
            self.closed = True
            return result, dict(checked, terminal_sha256=pin, binding_sha256=self.binding_pin)
        except BaseException:
            self.poisoned = True
            raise
        finally:
            self.guard.release()


def inspect(root, *, expected_binding_sha, expected_terminal_sha, expected_implementation):
    for pin in (expected_binding_sha, expected_terminal_sha, expected_implementation): io.pin(pin)
    validate_vendor()
    if implementation_identity() != expected_implementation: raise ValueError('timing implementation differs')
    root = Path(root).absolute()
    root_identity = _root_identity(root)
    names = {'binding.json', 'intent.json', 'completion.json', 'terminal.json'}
    if _names(root) != names: raise ValueError('timing topology differs')
    views = {n: io.read_stable(root/n, io.META_CAP) for n in names}
    import json
    docs = {n: json.loads(raw) for n, (raw, _) in views.items()}
    if any(io.encode(docs[n]) != views[n][0] for n in names): raise ValueError('canonical timing JSON required')
    binding, intent, completion, terminal = (docs[n] for n in ('binding.json','intent.json','completion.json','terminal.json'))
    if (set(binding) != {'schema','request_sha256','stage','clock_domain','pid','thread_id','implementation'} | set(FLAGS)
            or binding['schema'] != SCHEMA or binding['implementation'] != expected_implementation
            or type(binding['stage']) is not int or not 0 <= binding['stage'] < 232
            or type(binding['clock_domain']) is not str or re.fullmatch('[0-9a-f]{32}', binding['clock_domain']) is None
            or integer(binding['pid']) == 0 or integer(binding['thread_id']) == 0
            or any(binding[k] is not v for k,v in FLAGS.items())):
        raise ValueError('timing binding differs')
    io.pin(binding['request_sha256'])
    if io.digest(views['binding.json'][0]) != expected_binding_sha or io.digest(views['terminal.json'][0]) != expected_terminal_sha:
        raise ValueError('external timing pin differs')
    start, end = integer(completion['native_start_ns']), integer(completion['native_end_ns'])
    left, right = integer(terminal['apply_start_ns']), integer(terminal['apply_end_ns'])
    if not left <= start <= end <= right: raise ValueError('timing containment differs')
    expected = {
        'intent.json': dict(schema=SCHEMA,binding_sha256=expected_binding_sha,state='optimize_intended'),
        'completion.json': dict(schema=SCHEMA,binding_sha256=expected_binding_sha,
            intent_sha256=io.digest(views['intent.json'][0]),native_start_ns=start,native_end_ns=end,state='optimize_returned'),
        'terminal.json': dict(schema=SCHEMA,binding_sha256=expected_binding_sha,
            completion_sha256=io.digest(views['completion.json'][0]),apply_start_ns=left,apply_end_ns=right,**FLAGS)}
    if any(io.encode(doc) != views[n][0] for n,doc in expected.items()): raise ValueError('timing chain differs')
    if (_root_identity(root) != root_identity or _names(root) != names or
            any(io.read_stable(root/n, io.META_CAP) != view for n,view in views.items()) or
            implementation_identity() != expected_implementation): raise ValueError('timing view changed')
    return dict(native_interval_ns=end-start, apply_window_ns=right-left,
        non_native_apply_window_ns=right-left-(end-start), interval_complete=True,
        owned_apply_return_observed=False, **FLAGS)
