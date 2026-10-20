# 批量跨小时后继 PRE_SEAL findings

2026-10-20，DRAFT_NONAUTHORITATIVE。root为唯一writer，独立只读sol_reviewer沿agent.md第7节进行pre-seal adversarial audit；本文件由root整理，不签official verdict、review receipt或运行权限。

当前exact SHA256：owner `92a9174ba706ab18d00e3d6ab9a56e8baad3abe1a76befac7c4f83da5022fdac`；source `b03080f38cc9a4e9151eee3d479e045da0a586ff3ad98ce2bf9d060959600636`；historical `4843a1031b0998f84516995073bfc038d52373e4a4390ead025a7a2f64760335`；test `c852fc1f09121d4553554fcd3d511dc8bd0da76d1cf1febac7743dc34a55b57a`。

| finding | 修补与证据 | 范围状态 |
|---|---|---|
| HIGH owner动态替换prepare_many/接受旧source数据 | 固定原callable；构造首行、活体_check与_currents前后检查；exact type/keyset/canonical audit/schema/implementation/hour/pins/scientific核验 | 当前2h后继闭合 |
| HIGH source动态替换historical reader | 固定原replay_prefixes，入口与bookend检查；计数改为真实Reader返回的非权威数据 | 当前2h后继闭合 |
| MEDIUM close失败未清空capture | 尝试全部close，清空captured，primary优先；reader/lease及有无primary四故障覆盖 | 当前2h后继闭合 |
| MEDIUM 内存表述过宽/统计累积 | 帽仅覆盖selected frames与materialization，整体RSS另计；cost数据2048条硬帽、source前拒绝 | 当前保护闭合；192h预算OPEN |
| 测试observer替换入口及v1 audit伪作v2 fixture | 删除observer与该持久owner fixture；旧guard明确回归v1；新v2对真实返回数据做故障矩阵 | 当前路径闭合，早期原件保留原范围 |
| 双遍历collector与调用层级 | 保留constructor inspect及显式inspect；collector每完整遍历重置；API20/28与parent40/56分别列报 | 当前计数闭合 |
| unit/JUnit exact源绑定 | 核unit02/03 request/snapshot与适用current SHA；unit03只在未选probe函数添负例，其余完整module AST相同 | 当前复用边界闭合 |
| LOW 派生量依赖未绑定 | 保留原postcheck，以新dependency JSON绑定static bookends、trace、旧result/request/terminal及保存oracle | 当前report依赖补齐 |
| 中文文书编码损失 | 本次DRAFT报告按显式UTF8重写；新建可读性能复核；启动原计划及快照保留 | 可读交付修复，原件问题如实记录 |

units_03 23passed6.17s/outer10.875s/exit0；saved_probe_02 1passed168.04s/outer173.625s/exit0，203旧normal文件不变，8+3+3+4故障拒绝。PhaseController/Selector/capability代码块文本与v1一致，复用v1的36 guard，不称作v2的59项通过。units_02最后新纯数学测试误传records元组exit1，修测试后03补验，失败原件保留。

独立只读终态重算确认：connected_01 exit0/1passed503.18s、outer509.516s；事件intent/outcome/attempt/intent/outcome；两个唯一Job PID40564/47320 exit0/quiescent；212文件集合匹配保存result，SQLite读前后DB SHA相同；新旧projection仅去request namespace后全等，最终state全等；三lane q/r/debt/power以Fraction重算相同，metrics20/28/40/56。观察6PID退出，完整未观察进程树证明仍false，monitor/cleanup0、source unchanged。

当前2h synthetic范围未发现阻断性未闭合finding。完整168+24、phase边界、正网络/事故修复、右删失/终结、真实RTS、writer重建、持久atomic-live认证、生产预算、seal与official review仍OPEN。raw Job数值/资源认证flag及formal/native/resource门保持false；旧Common/source-factory findings保留。
