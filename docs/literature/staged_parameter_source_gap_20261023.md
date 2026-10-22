# 阶段算例参数来源登记缺口

2026-10-23，DRAFT_NONAUTHORITATIVE。本页由只读来源审查形成，记录可继续推进的具体缺口，不新增参数或经验校准。依据[RTS-24配置](../../configs/staged_deliverability_rts24_v1.DRAFT.yaml)、[业务原配置](../../configs/staged_deliverability_small_case_v1.DRAFT.yaml)、[权益原配置](../../configs/staged_deliverability_network_v1.DRAFT.yaml)及[公共输入规格](../model_spec/staged_deliverability_rts24_development_v1.md)；这些既有绑定字节不修改。

现有[方法来源页](../../paper/drafts/staged_deliverability_methods_sources.md)主要完成正文节到内部规格/实现的对应。配置顶层source_class与规格已明确：公共部分是PYPOWER case24静态benchmark，其余进度、业务、设备、权益、清洁和策略为机制设定。但组级分类还不是逐配置字段的可审计登记。

| 字段范围 | 已有依据 | 待补登记与主张边界 |
|---|---|---|
| case包/版本/源SHA及bus/gen/branch/gencost | RTS配置与本机包文件；规格保留原规模 | 区分公共benchmark原字段、派生拓扑及后续选择；补原引用和许可来源资格，不能写成同址观测 |
| POI、背景缩放、候选支路、rating增量与工期/延期 | RTS配置明示具体值与规则 | 标为合成选址/工程安排；它们不是公共case的原始观测 |
| workload、设备容量/待机/投运、D、f、eta、beta、gamma和辅助功率 | 业务配置标mechanism_assumption；公共输入作200倍量纲缩放 | 逐项标原始机制假设、精确派生、单位和变换链；scale=200本身也是选择，精确算术不使输入获得经验资格 |
| F/X与X响应/爬坡/能量/事件包络 | 权益配置及公共输入规格 | 区分制度概念与机制数值；数值与包络没有项目合同/响应认证依据 |
| deadline_lag和due规则 | 业务lag=2；公共规则不截观察终点 | 2小时是机制设定；缺期限分布/实测任务来源，不能从文献模型存在推导该取值 |
| alpha、前史Y与early/late清洁序列 | 业务配置及200倍变换 | 当前值未经验校准；early/late是开发清洁时序，不能当业务快慢或独立留出 |
| 事故筛选、实际事件与响应模型 | 拓扑选择规则、合成实际事件及同小时静态纠正 | 派生事故集、合成事件和方法假设分别标记；没有经验事故率、跨小时机组或动态响应资格 |
| EDF、调用/恢复互斥、网侧优先与独立加总 | A规格与有效实现 | 作为本文机制/策略选择登记；既有概念文献不能替代具体合同或数值校准 |

下一份参数sidecar应在不改三份原YAML的前提下，逐叶记录配置文件、JSON pointer、原值、单位、来源类别、直接来源、变换、使用/未采用状态、经验资格和主张限制。覆盖检查应拒绝漏字段/重复pointer及错误来源或缩放链；原两母线的标量供电和response标签须标明未进入公共实际模型，不能因继承文件而当作有效公共参数。

可复用[合同证据表](contract_evidence_matrix.csv)、[文献矩阵](literature_matrix.csv)及[建设证据表](construction_evidence_20261021.csv)的既有概念支持，但须与数值来源分列。上述表按各自核验时点保留，本轮未重查外部页面，不重新认证其现时有效性。

该登记可先做纯静态覆盖与绑定检查，不需要native或新外部下载。它只能关闭“来源分类是否逐字段可追溯”的缺口；真实业务快慢路径、设备/任务校准、合同、清洁归属、延期率及同址联合观测仍需相应证据。公共代表成本、C/D/E预算和P1专项授权保持开放。
