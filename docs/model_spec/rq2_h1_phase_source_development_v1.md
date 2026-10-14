# Phase source/controller record drafts

2026-10-09，DRAFT_NONAUTHORITATIVE；承接phase owner，根唯一writer。
新文件：h1_phase_obligation_controller、h1_phase_historical_controller、
h1_phase_exact_source_current的development_v1。旧168h文件与证据保持原字节。

controller只接受从genesis声明192h的新parent，使用phase_obligation_binding的同family/ordinal、
同source origin及原168h enrollment预检；hour0..167=enrollment，168..191=followup。
普通step入口直接拒绝；owner/bootstrap的受控入口尚未实现。
私有_step_development保留数值Job fixture路径，仍接受已读source identity且能够调用底层Job；
它没有need gate或bootstrap authority，不能被正式入口直接复用为生产许可。
测试只以合成source和saved reports替换真实solver，短Windows Job本身是真实机制测试。

新historical reader只接受phase schema/hours192，完整replay指定accepted prefix，并重验source、
parent/anchor、Job/clock和逐小时phase binding；inventory覆盖0..191，拒绝192及更远suffix。
沿用同句柄文件身份/双次重放观察，未使用后缀内容决定当前数值；历史prefix不能认证live release。
新exact-current通过此reader构造fresh normal envelope、outage registry和当前来源join，
复用原exact workload/CFE projection与物理私有join，不放宽科学阈值或重解释输入。

验证分层：

- 新controller root上两个短synthetic Windows Jobs及实际记录重放：检查parent/carry、phase header、
  clock/Job链、历史prefix及旧reader拒绝新header；不代表真实RTS accepted root或192h运行。
- 167/168/191/192的namespace测试只证明目录边界，不证明对应小时求解成功。
- exact-current复用固定contract测试的数值断言，通过明确historical seam检查新版API；
  192调用能进入reader的guard测试也不是accepted192 prefix。

缺口：公共owner/bootstrap/controller互相绑定、先need/attempt后source、完整192h accepted prefix、
typed failure、真实Rref/A ingress和Job、所有任务家族/reuse DAG、完整资源准入均仍开放。
phase owner目前仍使用旧adapter并在h168前拒绝；本组通过必要测试和独立审查前不接换其来源。
本草稿不生成official receipt、native授权或正式结果。
resource_admission、formal_execution_ready、formal_result保持false。
