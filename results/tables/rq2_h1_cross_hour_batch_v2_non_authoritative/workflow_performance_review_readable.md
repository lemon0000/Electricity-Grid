# 整链性能可读复核

2026-10-20，DRAFT_NONAUTHORITATIVE。此文件在终态后整理。原`design_and_performance_review.md`的最初主体保留，后续部分中文追加段在PowerShell管道中发生ASCII替换；原文件及各attempt启动快照保持原字节。这里依据启动request、实际runner/代码、保存oracle与终态重述，不替代启动原件或生成运行权限。

DAG：fixture/源输入 → N0受限fake Job → owner genesis历史batch → ready历史batch → 独立current/共同Rref/三个Actual → 保存intent/ticket/原科学transition → 第二次独立current → paired outcome/ticket → 完整replay → 下一小时先durable attempt → 原normal controller/N1 Job → 同样current/selector/paired/replay → 全部close → 新owner完整batch/原FSM → 独立historical/snapshot → close/全文件SHA → 报告与只读补验。normal/selector/数值、业务与holder记录保持原合同。

优化及复用：旧chain07主体/后验、旧06保存数据及同字节guard复用；单次_restore内以两次最大前缀观察构造逐小时current，保留普通current和paired前独立fresh。current/frame/proof不跨调用缓存。正常三个Actual串行共享本小时current，各自carry独立。test-only静态身份memo不代表生产开销；其它registry/source加载与校验保留。未引入跨小时可信checkpoint，也未并行共享动态carry。

在连续T个合法active小时、每小时一次run_next、末尾一次只读reopen、无额外inspect/alternate/pending/no-need终结的条件下：

- 原owner fresh为`T²+5T+2`，历史API为其2倍，API prefix-hour为`2*[2+2T+T(T+1)(2T+1)/6+3T(T+1)/2]`。
- 新owner历史API为`8T+4`，API prefix-hour为`4+4T(T+1)`；T=2实测20/28，T=192代码推导1540/148228。
- 每个API内Reader constructor inspect+显式inspect实际执行两遍，当前parent40遍/56 prefix-hour。独立historical/snapshot、内部anchor、完整episode终结、normal/controller、registry及科学重放另计，完整192h成本未知。

预算在各request.json中固定：units_02/03 120s；保存probe02 240s，0新Job/native；connected_01 900s、2模拟小时/3lane、2个每Job180s上限的fake Windows Jobs、18 selector captures、0 real native。采样树RSS1GiB、logical128MiB、5s监测、120s无进展。超限停止owned进程并保留原件；运行中未顺延。原06同规模outer604.266s，保存probe02 outer173.625s支持短诊断；没有据此启动192h或真实native。

实测closed path：connected_01 outer509.516s、pytest503.18s；采样RSS397242368 bytes、logical21538126 bytes，6观察PID退出，source unchanged，monitor/cleanup errors空。API20/28、parent40/56与公式一致；同小时h0单独/含h1 batch audit一致，科学量对原prepare一致；原业务、数值上限、非预见性、债务和共享预算保留。新旧科学projection及最终state一致，新request命名空间单列。

故障路径：新入口替换在任何建root/source/selector/intent前拒绝；错terminal链、registry/schema/implementation/hour与proof/统计错位拒绝；reader/lease close失败尝试所有close并保留primary；reducer失败清空batch；当前无自动retry或fallback。原v1 guard块同字节复用，v2差异由23边界、保存oracle故障矩阵和完整链覆盖。

内存帽仅针对选中frames与materialization；owner cost数据有2048条帽，整体RSS另采样，生产成本仍未知。normal原Job的数值/资源认证flags仍false。下一包必须继续界定未覆盖的phase/事故/修复/右删失/终结与完整窗口成本；整体审查只在当前2h synthetic诊断范围形成证据，formal/resource/native门保持false。

绑定依赖见connected_01/request.json、connected_01_postcheck.json及connected_01_dependency_bindings.json；三者分别绑定启动代码/config/input/plan、补验代码/DB/保存结果与计时/baseline/static bookends。原计划编码缺陷不改变机器记录的实际规模、预算与终态。
