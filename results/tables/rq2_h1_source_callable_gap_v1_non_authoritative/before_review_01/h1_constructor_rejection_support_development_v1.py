"""Detached rejection/namespace support; not installed in an H1 source Reader.

DRAFT_NONAUTHORITATIVE. Preserve the exact timed-parent close program while
avoiding dynamic super().close() after a parent descriptor/code drift.
"""
from pathlib import Path
from types import FunctionType
import dis

from experiments import h1_phase_historical_batch_development_v2 as candidate

SCHEMA='h1_constructor_rejection_support_development_v1'


def _build_teardown():
    candidate._check_dependencies()
    parent=candidate.binding.snapshot.parent.SourceParent
    program=vars(parent)['close']
    driver=candidate.prior._close_replay
    if program.__closure__ or driver.__closure__:
        raise ValueError('the original closure-free teardown programs are required')
    # These exact programs LOAD_GLOBAL only these builtins. Copying the small
    # namespace prevents module/global rebinding from changing their resolution.
    builtins=dict(getattr=getattr,setattr=setattr,BaseException=BaseException,reversed=reversed,list=list)
    for function in (program,driver):
        if function.__defaults__ is not None or function.__kwdefaults__ is not None:
            raise ValueError('the original no-default teardown programs are required')
        if {op.argval for op in dis.get_instructions(function) if op.opname=='LOAD_GLOBAL'}-builtins.keys():
            raise ValueError('teardown program requires an unregistered global')
    frozen_parent=FunctionType(program.__code__,{'__builtins__':dict(builtins)})
    frozen_driver=FunctionType(driver.__code__,{'__builtins__':dict(builtins)})
    capture=candidate.ConstructorInspectionCapture
    historical=candidate.HistoricalTimedSnapshot
    empty=candidate.capture._EMPTY
    expected_bases=(capture,historical)
    expected_mro=(capture,)+historical.__mro__

    def close_replay(reader,leases,captured,completed,primary):
        class Teardown:
            def close(self):
                if (type(reader).__bases__!=expected_bases
                        or type(reader).__mro__[1:]!=expected_mro):
                    raise ValueError('exact detached Reader MRO required for this teardown program')
                reader._cic_value=empty
                return frozen_parent(reader)
        return frozen_driver(None if reader is None else Teardown(),leases,captured,completed,primary)
    return close_replay


close_replay=_build_teardown()


def observe_parent_names(root,*,completed_hours,declared_hours,retained):
    """Replay the predecessor's three parent namespace grammars, including suffixes.

    This checks names/types/retained entry identities only. The caller must keep
    original content, lease, correspondence and source checks independently.
    """
    if (type(completed_hours) is not int or type(declared_hours) is not int
            or not 1<=completed_hours<=declared_hours<=192 or type(retained) is not dict):
        raise ValueError('bounded positive completed/declared hours and retained dict required')
    root=Path(root)
    grammar=(
        (root,{'execution.lock','parent_events_non_authoritative','parent_anchor_non_authoritative'},
            r'hour_([0-9]{3})_non_authoritative',0,declared_hours-1,True,range(completed_hours)),
        (root/'parent_events_non_authoritative',{'execution.lock','header.json'},
            r'([0-9]{3})',1,2*declared_hours,True,range(1,2*completed_hours+1)),
        (root/'parent_anchor_non_authoritative',{'execution.lock','header.json'},
            r'([0-9]{3})\.json',0,2*declared_hours,False,range(2*completed_hours+1)),
    )
    for path,base,pattern,low,high,directories,required in grammar:
        found=candidate.history._inventory(path,base,pattern=pattern,low=low,high=high,
            directories=directories,retained=retained)
        if not set(required)<=found:raise ValueError('complete parent namespace prefix required')
