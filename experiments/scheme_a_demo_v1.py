"""Reproducible presentation of 54 existing cases; no model changes."""
from pathlib import Path
import csv
import hashlib
import json
import time
import state_retention_probe_v1 as model

ROOT = Path(__file__).resolve().parents[1]


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    start = time.perf_counter()
    out = ROOT/'results/demos/scheme_a_v1/attempt_01'
    out.mkdir(parents=True, exist_ok=False)
    source = ROOT/'results/tables/state_retention_probe_v1_non_authoritative/attempt_01/report.json'
    deps = [Path(__file__), ROOT/'experiments/state_retention_probe_v1.py',
            ROOT/'docs/plan/scheme_a_demo_v1_contract.md', source]
    hashes = {str(p.relative_to(ROOT)):digest(p) for p in deps}
    try:
        assert digest(source) == source.with_suffix('.sha256').read_text().strip()
        old = json.loads(source.read_bytes())
        assert old['status'] == 'completed'
        assert all(digest(ROOT/p)==h for p,h in old['hashes'].items())
        index = {(r['age'],r['save_steps'],r['upgrade'],r['notice'],r['firm_ticks'],r['R'],r['mode']):r for r in old['rows']}
        model.DEADLINE = start+10
        rows = []
        for up in (6,10):
            for L in (0,2,4):
                for firm in (0,2,4):
                    for mode in model.MODES:
                        assert time.perf_counter()-start < 10
                        result = model.solve(11,0,2,up,L,firm,mode)
                        previous = index[0,2,up,L,firm,11,mode]
                        assert all(result[k]==previous[k] for k in ('exact','greedy','capacity_only'))
                        s, trace = (44,0,0,0,0,0), []
                        for t in range(12):
                            act = max(model.actions(s,model.cap_at(t,up,firm),mode),key=lambda x:x if isinstance(x,int) else -1)
                            s,rec = model.transition(t,s,act,2,up,firm,mode)
                            trace.append(rec)
                        assert (s[0]==0)==result['greedy']
                        row = dict(upgrade_minutes=up*5,notice_minutes=L*5,batch_firm=firm/4,
                                   total_firm=1+firm/4,mode=mode,**result,greedy_trace=trace)
                        for witness in (result['trace'],trace):
                            if witness is None: continue
                            assert len(witness)==12
                            for t, rec in enumerate(witness):
                                if t: assert list(witness[t-1]['after'])==list(rec['before'])
                                assert rec['after'][0]==rec['before'][0]+rec['lost']-rec['work']
                                assert rec['batch_power']<=model.cap_at(t,up,firm)
                        rows.append(row)
        payload = dict(authority='DRAFT_NONAUTHORITATIVE',formal_result=False,
                       parameters=dict(R=11,age=0,stage_minutes=10,persist_minutes=5,
                                       event_minutes=[20,30],deadline_minutes=60,base_power=1,retention_power=.25),
                       hashes=hashes,rows=rows)
        data = json.dumps(payload,ensure_ascii=False,indent=2).encode('utf-8')
        (out/'data.json').write_bytes(data)
        fields = ('upgrade_minutes','notice_minutes','batch_firm','total_firm','mode','exact','greedy','capacity_only')
        with (out/'summary.csv').open('w',encoding='utf-8-sig',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
            writer.writerows({k:r[k] for k in fields} for r in rows)
        html = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>方案A机制演示</title>
<style>body{font:16px/1.65 system-ui,sans-serif;max-width:1120px;margin:32px auto;padding:0 20px;color:#17283b;background:#f6f8fb}section{background:white;padding:20px;margin:20px 0;border:1px solid #ccd6e0;border-radius:10px}table{width:100%;border-collapse:collapse;font-size:14px}th,td{padding:7px;text-align:left;border-bottom:1px solid #dde3ea}select{font-size:16px;padding:8px;max-width:100%}.pass{color:#17643b}.fail{color:#a22d21}.event{background:#fff1d6}small{color:#485b6e}</style>
<h1>方案A：通知、Firm与任务保活</h1><p>合成机制演示 · DRAFT_NONAUTHORITATIVE · 单任务、单事件 · 不代表实测MW或创新已成立。</p>
<section><h2>固定条件</h2><p>工作量11，初始未保存进度0；暂存10分钟＋落盘5分钟；事件20—30分钟；原期限60分钟。保护基荷1，batch保活功率0.25；正常batch容量从1升到2。所有功率为归一化量。通知到达前采用同一直接工作策略。</p><p>Firm是事件期可用上限，实际取电可以更低。总Firm＝基荷1＋batch Firm。供电不足以保活才会物理丢失状态；“强制关闭”另附控制限制，作为对照。</p></section>
<section><h2>选择场景</h2><label for="case">升级时点 / 通知 / batch Firm / 控制方式</label><br><select id="case"></select><p id="verdict"></p><p id="traceNote"></p><div style="overflow-x:auto"><table><thead><tr><th>时段/分钟</th><th>动作</th><th>batch上限</th><th>batch实际功率</th><th>总实际功率</th><th>剩余工作</th><th>未保存进度</th><th>暂存/落盘剩余槽</th><th>丢失工作</th></tr></thead><tbody id="trace"></tbody></table></div></section>
<section><h2>全部54例</h2><p>容量评价忽略保存/回滚，是乐观诊断；精确DP检验本例全部允许动作。“直接工作”是固定基线。</p><div style="overflow-x:auto"><table><thead><tr><th>升级/分钟</th><th>通知/分钟</th><th>batch Firm</th><th>控制方式</th><th>容量评价</th><th>精确DP</th><th>直接工作</th></tr></thead><tbody id="all"></tbody></table></div></section>
<section><h2>如何解读</h2><p>先看30分钟升级、零通知、batch Firm=0.5：强制关闭失败，允许保活通过。再看batch Firm=0：零通知失败，20分钟通知通过。最后换成50分钟升级，观察恢复资源较晚如何限制结果。</p><p>这是给定容量、状态和信息条件的可行性演示，不是最优长期准备、完整建设规划、网络/CFE或站点实证。同步与允许异步的结果均展示；已保存见证可能选择同步动作。</p><p>不可行case显示直接工作策略的失败轨迹；该轨迹本身不证明所有策略失败，失败判定来自精确DP。任务完成时提交结果无需额外时间是本模型假设。</p></section>
<script>const DATA=__DATA__;const names={forced:'强制关闭',retain_sync:'允许保活＋同步',retain_async:'允许保活＋同步/异步'};const yn=x=>x?'通过':'不通过';const select=document.getElementById('case');
DATA.rows.forEach((r,i)=>{const o=document.createElement('option');o.value=i;o.textContent=`${r.upgrade_minutes} / ${r.notice_minutes} / ${r.batch_firm} / ${names[r.mode]}`;select.appendChild(o);document.getElementById('all').insertAdjacentHTML('beforeend',`<tr><td>${r.upgrade_minutes}</td><td>${r.notice_minutes}</td><td>${r.batch_firm}</td><td>${names[r.mode]}</td><td>${yn(r.capacity_only)}</td><td class="${r.exact?'pass':'fail'}">${yn(r.exact)}</td><td>${yn(r.greedy)}</td></tr>`)});
function draw(){const r=DATA.rows[+select.value];document.getElementById('verdict').textContent=`精确DP：${yn(r.exact)}；容量评价：${yn(r.capacity_only)}；直接工作：${yn(r.greedy)}`;document.getElementById('verdict').className=r.exact?'pass':'fail';document.getElementById('traceNote').textContent=r.exact?'下表为一条可行策略见证。':'不存在可行策略；下表仅展示直接工作基线的失败轨迹。';const a=r.trace||r.greedy_trace;document.getElementById('trace').innerHTML=a.map(v=>{const t=v.t;const cap=t===4||t===5?r.batch_firm:t*5>=r.upgrade_minutes?2:1;let act=typeof v.action==='number'?(v.work?'执行':'等待/保活'):v.action;return `<tr class="${t===4||t===5?'event':''}"><td>${t*5}—${(t+1)*5}</td><td>${act}</td><td>${cap}</td><td>${v.batch_power/4}</td><td>${1+v.batch_power/4}</td><td>${v.after[0]/4}</td><td>${v.after[1]/4}</td><td>${v.after[2]} / ${v.after[3]}</td><td>${v.lost/4}</td></tr>`}).join('')};select.onchange=draw;draw();</script></html>'''
        (out/'index.html').write_text(html.replace('__DATA__',json.dumps(payload,ensure_ascii=False)),encoding='utf-8')
        assert len(json.loads((out/'data.json').read_bytes())['rows'])==54
        with (out/'summary.csv').open(encoding='utf-8-sig',newline='') as f: assert len(list(csv.DictReader(f)))==54
        assert '__DATA__' not in (out/'index.html').read_text(encoding='utf-8')
        assert sum(p.stat().st_size for p in out.iterdir())<2*1024*1024
        assert all(digest(ROOT/p)==h for p,h in hashes.items())
        assert time.perf_counter()-start<10
        completion=dict(status='completed',authority='DRAFT_NONAUTHORITATIVE',formal_result=False,cases=54,
                        source_matches=54,wall_seconds_to_completion_record=time.perf_counter()-start,
                        artifacts={p.name:digest(p) for p in out.iterdir()})
        (out/'completion.json').write_text(json.dumps(completion,indent=2),encoding='utf-8')
        print(json.dumps(completion,indent=2))
    except Exception as exc:
        (out/'failure.json').write_text(json.dumps(dict(status='failed',error=repr(exc),hashes=hashes)),encoding='utf-8')
        raise


if __name__=='__main__':main()
