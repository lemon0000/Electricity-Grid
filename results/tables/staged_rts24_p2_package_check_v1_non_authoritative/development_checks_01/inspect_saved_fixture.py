"""Read only an explicitly named ordinary synthetic fixture; phase diagnosis."""
import json
from pathlib import Path
import sys
import threading
import time
import traceback

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from src import staged_rts24_p2_package_check_v1 as d

if __name__=='__main__':
    fixture=Path(sys.argv[1]).absolute();reg_path=fixture/'registration.json';reg=json.loads(reg_path.read_bytes());worker=Path(reg['output'])
    assert worker.resolve()==(fixture/'worker').resolve() and 'pytest-of-' in str(fixture)
    main=threading.get_ident()
    def observe():
        for delay in (15,15,15):
            time.sleep(delay);print('ORDINARY STACK SNAPSHOT',file=sys.stderr,flush=True);traceback.print_stack(sys._current_frames()[main],file=sys.stderr)
    threading.Thread(target=observe,daemon=True).start()
    original=d.inventory
    def inventory(path):
        start=time.perf_counter();print('inventory_start',flush=True);value=original(path)
        print(json.dumps(dict(phase='inventory_end',seconds=time.perf_counter()-start,files=len(value['pins']))),flush=True);return value
    d.inventory=inventory
    raw=d.context_bytes(ROOT,worker,fixture/'parent',reg_path,ROOT/'results/tables/staged_rts24_p2_packet_v1_non_authoritative/packet_01',reg['pins']['legacy_scientific_and_P1_runtime']['executable'])
    result=d.inspect_package(raw,d.pin(raw)['sha256'],json.loads((worker/'launcher.json').read_bytes()),json.loads(raw)['startup'])
    print(json.dumps(dict(status=result['inspection_status'],error=result['protocol_error'])),flush=True)
