"""Add the checkpoint prefix while retaining unrelated live and published bodies."""
from pathlib import Path
from hashlib import sha256
import json
import subprocess
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3]
def pin(v):return dict(bytes=len(v),sha256=sha256(v).hexdigest())
rows={}
for name in ('docs/plan/科研项目执行步骤.md','docs/model_spec/blocker_register.md','paper/drafts/README.md','docs/plan/continuation_handoff_20261022.md'):
    p=ROOT/name;before=p.read_bytes()
    relative='../../docs/plan/' if name.startswith('paper/') else '../plan/' if name.startswith('docs/model_spec/') else ''
    prefix='2026-10-26 wire两项数据根风险已在声明校验范围闭合：见[最新交接]('+relative+'continuation_handoff_20261026_saved_fresh_wire_data_root_repair.md)。固定literal验证根与独立dependency image已修复，三角色startup RAM链连通；当前Source 51新＋480原回归共531目标节点终态通过。pytest含失败/重核累计288.2881149/420s，静态继续从原120s续账；保留三次不接受记录及retry归档澄清。剩余8个stage/failure/return接口、真实producer/actual F与科学/资源/正式门禁仍OPEN/false。\n\n'
    head,body=before.split(b'\n\n',1);after=head+b'\n\n'+prefix.encode()+body
    assert prefix.encode() not in before
    published_before=subprocess.run(['git','show','HEAD:'+name],stdout=subprocess.PIPE,check=True).stdout
    pubhead,pubbody=published_before.split(b'\n\n',1);published_after=pubhead+b'\n\n'+prefix.encode()+pubbody
    p.write_bytes(after);snapshot=OUT/('code_'+sha256(after).hexdigest()+'.snapshot')
    with snapshot.open('xb') as stream:stream.write(after)
    rows[name]=dict(prefix=prefix,original_pin=pin(before),checkpoint_pin=pin(after),checkpoint_snapshot=snapshot.relative_to(ROOT).as_posix(),
        published_pin=pin(published_after),published_original_pin=pin(published_before),parallel_body_changes_preserved=before!=published_before)
with (OUT/'navigation_changes.json').open('xb') as stream:stream.write(json.dumps(rows,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode())
print(json.dumps({n:r['parallel_body_changes_preserved'] for n,r in rows.items()},sort_keys=True))
