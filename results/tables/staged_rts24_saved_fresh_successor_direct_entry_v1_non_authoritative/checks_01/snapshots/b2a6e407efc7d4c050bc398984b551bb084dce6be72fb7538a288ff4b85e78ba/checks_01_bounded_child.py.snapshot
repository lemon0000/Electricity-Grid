"""Fixed-capacity pipe drains for one ordinary process; no scientific imports."""
import subprocess
import threading
import time

STDOUT_BYTES=131073
STDERR_BYTES=4096

def drain_child(process,seconds=2):
    buffers=[bytearray(STDOUT_BYTES),bytearray(STDERR_BYTES)];sizes=[0,0]
    stop=threading.Event();errors=[];reason=[None];threads=[]
    def reader(index,stream):
        try:
            while True:
                raw=stream.read1(4096)
                if not raw:return
                remaining=len(buffers[index])-sizes[index];take=min(remaining,len(raw))
                buffers[index][sizes[index]:sizes[index]+take]=raw[:take];sizes[index]+=take
                if index==1 or take<len(raw):
                    reason[0]=reason[0] or ('stderr_nonempty' if index else 'stdout_limit');stop.set();return
        except BaseException as error:errors.append(('pipe_read',repr(error)));reason[0]='pipe_read';stop.set()
    for index,name in enumerate(('stdout','stderr')):
        thread=threading.Thread(target=reader,args=(index,getattr(process,name)),daemon=True)
        threads.append(thread);thread.start()
    deadline=time.monotonic()+seconds;killed=False
    while process.poll() is None:
        if stop.is_set() or time.monotonic()>=deadline:
            reason[0]=reason[0] or 'timeout'
            try:process.kill();killed=True
            except BaseException as error:errors.append(('kill',repr(error)))
            break
        stop.wait(.005)
    try:process.wait(timeout=1)
    except BaseException as error:errors.append(('terminal_wait',repr(error)))
    for thread in threads:thread.join(1)
    pipes_closed=True
    for name,thread in zip(('stdout','stderr'),threads):
        if thread.is_alive():errors.append(('pipe_thread',name));pipes_closed=False;continue
        try:getattr(process,name).close()
        except BaseException as error:errors.append(('pipe_close',repr(error)));pipes_closed=False
    return dict(stdout=bytes(buffers[0][:sizes[0]]),stderr=bytes(buffers[1][:sizes[1]]),
        exit_code=process.returncode,stop_reason=reason[0],kill_requested=killed,pipes_closed=pipes_closed,
        reader_threads_terminal=not any(t.is_alive() for t in threads),cleanup=errors,
        stdout_capacity=STDOUT_BYTES,stderr_capacity=STDERR_BYTES,chunk_bytes=4096)
