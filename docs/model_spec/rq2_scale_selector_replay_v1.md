# 完整UID selector归档数值回放

状态：DRAFT_NONAUTHORITATIVE。`scale_selector_replay.py`读取selector store的完整result payload，要求外部SHA256、实现identity、完整独立SelectorRequest及显式record限额。此接口验证记录相对输入的数值一致性，不认证真实数据来源或原生执行事实。

## 重建与比较

沿用新ScaleSelectorBudget的完整UID、小时、角色、solver与调用预留准入；保留旧grid replay的public类型门。新入口复用`grid_evidence_replay._replay`纯回放核，由固定reference/actual输入构造每一阶段模型，不接收外部builder，不调用solver。

每个selected阶段须有完整原生记录、一个调用、可行赋值和重现的optimal标志。重新核对模型结构、版本/选项、native/loaded赋值、canonical completion、目标、界、残差与整数违例；再重建物理witness、目标锁和gap审计，要求完整stage wire一致。最终重新计算generation carry、前驱/origin/policy链和selected request，要求整个ScaleSelectionResult字节及identity一致。

public `replay_record`仅返回诊断，私有重建对象不会经公共接口返回或成为resume授权。`unresolved`归档要求没有后继/selected request，仅报告`unresolved_archive_not_replayed`，不声称重现其失败原因或调用事实。该分支尚不覆盖完整失败记录的数值复核。

SHA256是内容pin，store binding字符串不是独立数据库来源认证。调用方仍须使用父控制器/lease确认写者静默、数据库与request关联，并独立证明normal和前驱来源。机制参数始终属于输入声明，不转换为真实观测。formal、native authentication及resume授权保持false；完整episode事务和正式实验门未打开。


## 验证记录

12项针对性测试通过（23.62秒）；另21 UID、23阶段回放1项通过（18.74秒）。旧selector/native replay相关158项通过（98.92秒）。限定独立pre-seal无待修实质finding；git diff --check通过。测试使用合成输入和临时目录，不形成真实H25或正式结果。
