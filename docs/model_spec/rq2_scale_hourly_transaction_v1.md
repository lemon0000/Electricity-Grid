# 回放结果与四臂分阶段事务

状态：DRAFT_NONAUTHORITATIVE。`scale_hourly_transaction.py`提供纯内存分阶段接口，接入新selector归档回放；旧mapping、hourly transaction和episode类型门保持原样。

`publish_common_record`只从完整重放的reference生成共同请求，保持精确有理MW/归一化映射、业务活动分辨率、source audit、训练/holdout身份和跨小时前驱。输入映射继续明确为mechanism_assumption，不把输入声明当作真实观测。所有臂消费同一publication；跨小时共同policy、mapping、normal/prepared audit来源固定。

四臂role顺序为network-only、CFE-only、joint-correct、joint-B6对应actual:0..3。`prepare_arm`复用现有capacity policy计算业务candidate；失败时不创建dispatch request。成功时验证服务平衡，按实际削减与恢复计算PrescribedDcPower，绑定独立actual前驱、小时、UID及固定policy。

ArmCursor在初始化时固定business policy identity及包含reference origin、业务、电网、mapping的origin identity，后续游标保持两者；prepare在业务推进前拒绝同臂不同policy替换。业务参数固定与电网selector policy固定分别验证。

`finish_arm`回放actual归档，只有完整接受时同时返回业务与电网后继。业务拒绝或物理未解决时保留候选作诊断，已提交业务/电网状态保持原值并halt。CFE-only的grid-service failure不适用，但仍接受实际功率的物理网络检查；候选服务失败与已提交服务失败分开。重复publication不能被新cursor再次消费。

这些接口不调用solver，不提供持久episode owner或一次性执行授权；返回的pair是内存事务，不是磁盘原子发布。调用方仍须连接受控selector执行、静默后的可信归档读取、episode总预算/公平性检查及持久游标。坏归档抛出异常，由外层保持未提交状态；unresolved不变成不可行证明。完整来源、normal最优性、终端右删失、正式资源和科学验收仍未解决。

## 验证范围

真实合成selector归档覆盖四臂：共同request为精确1/3；三臂成对提交债务与电网状态，CFE-only的物理未解决保持前值。两小时案例覆盖债务由1/3累积到2/3，以及恢复功率高于baseline时债务下降。另有错误role、重复publication、业务拒绝及同臂policy替换反例。新旧事务/映射组合69项通过（75.80秒）；该组合在policy finding修复前完成，修复后另跑新接口全套。

修复后新接口最终9项通过（44.91秒、exit0）。业务policy finding经独立限定复核闭合，当前scope无剩余实质finding；git diff --check通过。
