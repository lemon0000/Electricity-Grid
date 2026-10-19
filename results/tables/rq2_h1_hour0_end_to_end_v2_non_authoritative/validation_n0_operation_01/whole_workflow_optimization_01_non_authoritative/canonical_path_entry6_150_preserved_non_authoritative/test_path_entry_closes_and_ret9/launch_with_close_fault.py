
import ctypes
from ctypes import wintypes
import runpy
import sys
ORIGINAL=ctypes.WinDLL
def load(*args,**kwargs):
    library=ORIGINAL(*args,**kwargs)
    caller=sys._getframe(1)
    if caller.f_code.co_name!='_kernel_api' or not caller.f_code.co_filename.endswith('h1_canonical_path_lease_development_v1.py'):
        return library
    actual_close=library.CloseHandle
    actual_close.argtypes=(wintypes.HANDLE,);actual_close.restype=wintypes.BOOL
    calls=[0]
    def close(handle):
        calls[0]+=1
        if 'cleanup_persistent'=='cleanup_persistent' or calls[0]==1:
            if 'cleanup_persistent'=='cleanup_raise':raise OSError('expected injected path CloseHandle raise')
            return False
        return actual_close(handle)
    class Proxy:
        def __getattr__(self,name):return getattr(library,name)
    proxy=Proxy();proxy.CloseHandle=close
    return proxy
ctypes.WinDLL=load
sys.argv=sys.argv[1:]
runpy.run_path(sys.argv[0],run_name='__main__')
