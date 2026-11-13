# 方案A机制演示

2026-11-10，DRAFT_NONAUTHORITATIVE，formal_result=false。

直接用浏览器打开[交互页面](attempt_01/index.html)。页面自带数据，离线可用，无须启动服务器。选择场景后查看逐时段动作、可用容量、实际功率、剩余工作与未持久化进度。

## 先看三个现象

1. 30分钟升级、零通知、batch Firm=0.5：强制关闭不通过，允许保活通过。差异来自控制权限，实际取电也可能不同。
2. 30分钟升级、batch Firm=0：零通知不通过，20分钟通知通过。提前时间允许保存状态。
3. 升级推迟到50分钟：本例在全部通知档位均需batch Firm=1。更长通知不能代替不足的期限前执行资源。

|控制与升级|零通知最低batch Firm|10分钟通知|20分钟通知|
|---|---:|---:|---:|
|强制关闭、30分钟升级|1|1|0|
|允许保活、30分钟升级|0.5|0.5|0|
|允许保活、50分钟升级|1|1|1|

本例基荷为1，总Firm需另加1；功率归一化，不能当MW、投资节省或实测效果。固定工作R=11，初始未保存进度0，暂存10分钟再落盘5分钟，事件20—30分钟，原期限60分钟，batch保活0.25。三控制域包含允许同步/异步域，其接纳结果在本例相同。

## 核验范围

复用既有模型，对两个升级时点×三种通知×三个Firm档位×三种控制域，共54次DP。exact、greedy和capacity_only与旧报告54/54逐项相同，轨迹连续、功率和余额断言通过。JSON/CSV重读、工件SHA和JavaScript语法检查通过；本轮未做实际浏览器渲染与点击验收。构造、求解、输出与重读至完成记录前约0.056秒，不包括完成记录自身的写出，未测RSS。

可行case展示一条精确可行见证；不可行case仅展示直接工作策略的失败轨迹。该失败轨迹不独立证明不可能，exact=false来自DP对允许动作的穷举。状态的before/after保存在JSON，页面显示after。动作save_sync为开始同步保存，save_async为开始异步暂存，advance为继续保存阶段；等待/保活不产生有效工作。

## 工件与复现

- [JSON数据及轨迹](attempt_01/data.json)
- [54例摘要CSV](attempt_01/summary.csv)
- [完成记录与SHA](attempt_01/completion.json)
- [生成脚本](../../../experiments/scheme_a_demo_v1.py)
- [运行契约](../../../docs/plan/scheme_a_demo_v1_contract.md)
- [研究方案全文](../../../docs/plan/scheme_a_research_design_and_evidence_v1.md)

生成命令为`python experiments/scheme_a_demo_v1.py`，工作目录为仓库根。已完成的attempt_01不覆盖；再次运行会拒绝覆盖，复跑须保留原工件并采用独立后继输出路径。查看演示只需打开HTML，不必复跑。

该demo覆盖给定阶段容量下的单任务机制，不是完整三条达产进度、实际网络、小时CFE或已成立创新的验证。
