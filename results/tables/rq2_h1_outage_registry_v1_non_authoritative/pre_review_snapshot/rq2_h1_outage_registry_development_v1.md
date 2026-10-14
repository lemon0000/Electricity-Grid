# 已批准 A/B/C 的 H1 origin/cap registry 开发实现

状态：DRAFT_NONAUTHORITATIVE。用户对提案 SHA256
`d561919a84126e6658d59c861f17353e2e0dde5304f043e50bc8bb4cad12f707`
明确回复“全部批准”。开发授权记录为
`results/tables/rq2_h1_outage_registry_v1_non_authoritative/scientific_development_authority.json`，
SHA256 `45710f18fcf98113d53c50cd74e0dfc311ad3e03cfb8ab8f75b01dc2720de0a8`。
该授权不包含真实 native、正式运行或原封存协议的原位修改。

## 来源与读取边界

`build_h1_outage_split_archive_development_v1.py` 是离线派生构建器，可以解析原混合split CSV。
它将全部原始字段字符串按split无损分离为12984条training与12720条holdout，确定性gzip保存，
绑定原package/member SHA、冻结config、extractor字节、字段清单、行数和逐行hash序列摘要。
旧package不变。派生档案位于独立non-authoritative目录；尚未production封存。

`h1_outage_registry_development_v1.py` reader仅解压所请求split的派生档案；不调用旧
`_power_audit`，不解析混合CSV或event table。对旧package及成员做完整性校验时仅作
integrity-only opaque byte hashing。holdout reader不解压或解析training档案。
静态RTS inventory、generator参数与冻结生成算法不属于training观测。

registry核验固定catalog、源配置/package/upstreams、完整211组件、显式开发授权和93机组表。
不得传入自定义protocol、repair_limits或手工构造的registry。公开prepare自行加载，再加载并
重建返回值；只提供fresh-at-return的detached开发对象，不能认证后续消费者或持久状态。

## 三种来源与动作

catalog原有每个窗口及right-censored observed end保持不变，hours为1..192且不能超出该窗口
已存在支持。普通窗口使用同split/seed连续前置行；只有三个批准的training start0及三个
holdout缺口允许另两条路径。其他缺行直接拒绝，不泛化fallback。

training raw0通过冻结生成器horizon1与原行核对，产生独立FirstAction：当前overlay即初态，
unknown onset，无report、started、ended、cap或伪造hour-1。完成首动作后completed_actions=1，
disclosure仍source0。raw1才构造source0→1的首个TransitionAction。
普通/generated来源action0则是前置boundary到raw_start的真实已揭示转换，内部neutral时钟
仍从0→1开始。两种时钟必须在后继owner分别验证；旧kernel不能直接消费FirstAction。

holdout补充只重放seed过程到raw_start-1，读取prefix末项；不查未来event end。receipt记录
generated_same_split_boundary，明确不是既有same-chain row。来源kind、seed、event ID、真实
source hour/timestamp及raw rows只留audit；decision_view仅含中性relative hour、active/
started/ended component和exact repair cap。相同可见动作的ordinary/generated来源projection
相同。完整Prefix供source重验，不得直接传给逐小时policy。

## 固定 repair cap

93行表SHA256 `6435c85b6cc99d243077bd014b1f52cc90427270a4c50cb26a67fb7e34edf031`
与冻结gen.csv逐字段重验，Fraction计算`min(PMax,60*MW/min ramp)`。精确值保留在decision
投影中；旧disclosure浮点参数要求`Fraction(str(float(cap))) == cap`。只对当前已结束generator
内部lookup，caller不能替换；branch返回、continuation、新事故和FirstAction没有cap。
仅Rref/actual后继使用，N基准、key、carry、selector保持不变。physical端仍须执行nameplate和
全部既有物理门；registry通过不意味着初态generation或动作可行。

## 验收边界

全catalog审计保留每条entry和原censoring，仅关闭本单元的source-origin/cap开发覆盖缺口。
full_boundary_coverage_verified、physical_consumer_connected、persistent_lane_owner_implemented、
full_192_hour_execution_verified、resource_admission、formal_execution_ready、formal_result和
native_execution_authorized仍false。来源是synthetic mechanism，不是经验观测或安全认证。
后继需first-aware physical/selector、fresh accepted N联接、各lane持久状态、same-key registry、
paired commit、完整资源包、successor封存和全新official审查；新native另行明确授权。
