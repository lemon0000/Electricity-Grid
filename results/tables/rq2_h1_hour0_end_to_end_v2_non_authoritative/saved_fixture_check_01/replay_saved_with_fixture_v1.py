"""Separate-process synthetic replay with the complete original fixture seams.

No producer, solver, new retention or formal result is authorized by this entry.
The saved reader remains byte-pinned by the external postcheck launcher.
"""
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from tests import h1_hour0_saved_replay_v2 as saved


def complete_fixture(original):
    def install(base):
        patch=original(base)
        try:
            binding=saved.historical.binding
            raw=(binding.ROOT/binding.MANIFEST).read_bytes()
            if hashlib.sha256(raw).hexdigest()!=binding.MANIFEST_PIN:
                raise ValueError('synthetic fixture manifest pin differs')
            resolver=binding.manifest._resolver(raw)
            patch.setattr(binding,'open_manifest',lambda:resolver)
            patch.setattr(binding,'precheck',lambda resolver,declaration,**kw:
                resolver.resolve(kw['family'],kw['ordinal']))
            patch.setattr(binding,'prevalidate_enrollment',
                lambda *a,**kw:dict(test_only_synthetic_source=True))
            return patch
        except BaseException:
            patch.undo()
            raise
    return install


def main():
    base,packet,pin,report,report_pin,output=sys.argv[1:]
    original=saved.synthetic_source
    saved.synthetic_source=complete_fixture(original)
    try:
        result=saved.replay(Path(base),Path(packet),pin,Path(report),report_pin)
    finally:
        saved.synthetic_source=original
    with Path(output).open('x',encoding='utf-8') as stream:
        json.dump(result,stream,indent=2)
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
