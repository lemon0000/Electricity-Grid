# 168h/≤24h 整链预算续核

2026-10-21，DRAFT_NONAUTHORITATIVE。整链 wall/RSS/storage 准入仍未闭合。新增证据仅支持候选 source 路径的科学身份核对与H1净成本，未把局部提速乘到完整时域。

一个episode仍需完整enrollment预验证、N0/owner genesis、每小时ready replay/attempt/N更新、current join、共同Rref、各active Actual、intent/ticket、paired前fresh、paired outcome、post replay、额外terminal、外部checkpoint、close、fresh constructor/public inspect，以及独立source/Job/anchor核对、报告和失败清理。成功、提前停止、Actual未决、缺必要follow-up及不确定提交须分别有可执行分支和预算；所有档案与失败原件均保留。

原v2成功T小时路径含额外terminal及reopen constructor/public inspect时，Reader=8T+10、prefix-hour权重=4T²+10T+4。T192仍为1546 Reader/149380 prefix-hour、3092 parent遍历；源层Job replay为597520，M5为2987600次stage replay，条件M232为138624640次stage replay。这些重放不是native求解次数；独立historical/snapshot/anchor探针和normal内部成本另计。

若未来验证并接入本候选，双Reader不变，每Reader parent遍历从2减至1，对应T192条件parent=1546、源层Job replay=298760、M5 stage replay=1493800。此处仅为条件调用算术，**当前owner仍使用原合同**；不能把这些数或本次H1约51.3%差值称完整链已节约的wall。

本次H1完整batch原57.131095s、新27.815387s；H3新batch93.285154s。均不装static identity memo，仍使用保存synthetic source/catalog/manifest resolver seam，不包含真实manifest来源重审。H1只做固定old→new各一次，不提供分布或生产上界；H3没有对应未缓存原路径的完整测量。最初H3四调用诊断因call内无progress标记被120s watchdog停止，原预算设计问题和独立after核验保存，不扩时重跑该包。

结构性缺口仍包括：业务ready/post历史校验在3lane全活跃时T192的长度下界28311936；owner至少576个operational events而旧toy cap=32；科学business event cap=14与journal容量分开。还须绑定single-event/DB/holder上限、正常232-stage档案、Rref/A档案、scratch、checkpoint/report、保留失败与reserve，以及terminal/reopen和不确定失败的工作量。未测完的成本保留unknown，不按0计费。

完整研究另有1900个cell及training14644/holdout14336 pairs/cell。已有proof-aware manifest的8020个节点只有逻辑proof依赖，runtime request/causal key/solver task全null。1856个cell的CFE相关规划臂有绑定解析反例，44个cell这些臂仍unknown，全部1900 network-only仍unknown，合计2032个剩余planning arm-cells；保留所有原义务身份。相关条件holdout/B6actual未执行，不写成失败；没有solver节省或resource折扣。新清单按exact protocol/spec/agent/plan/blocker和保存结果对账，不重新求解或把旧46-cell协议当当前formal authority。

完成预算可选择验证后接入候选，也可拒绝候选并为baseline/其他合法路径取得依据。source/current/registry/head不能跨operation缓存；相同timestamp/隐藏pair标签不能建立跨任务数值或证据复用。正式solver接口/当前license/规模、objective-blind线程算法pilot、LB/UB/gap/残差/完整证书、同合同训练及holdout绑定和正式result publication均须单独登记。

`total_192h_wall_admission_seconds`、peak RSS准入、总storage准入仍为null；`overall_performance_review_complete`及长连接准入为false。下一步的真实168h/≤24h连接尚不可启动。需要先完成适用source故障/依赖证据、合法路径选择及全流程代表性预算，再验证167→168、携债followup、due先恢复、按需缺源typed右删失和真实episode terminal→checkpoint→close→fresh-process replay；writer/crash恢复、seal后fresh official review及具体formal/native授权另有门禁。
