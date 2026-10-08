# 规模化事务的已提交前缀诊断

状态：DRAFT_NONAUTHORITATIVE。入口为`experiments/summarize_rq2_scale_committed_prefix_v1.py`的
`summarize_cursor(cursor, declared_source_hours, expected_cursor_identity=...)`；纯函数，不执行solver或写入结果。

现有容量诊断`summarize`接受业务`CapacityPolicyCursor`。规模化事务在网侧未决时也会保留一个业务上已
验证的`business_candidate`，所以不能直接把这个候选交给旧汇总函数，称其为实际提交前缀。
新入口只接受成对状态`scale_hourly_transaction.ArmCursor`，复用旧诊断的精确能量与cohort评价。

验证包括：外部cursor摘要、当前事务实现、exact业务类型及四臂身份、固定policy、逐记录确定性重演、
全部记录已提交、逐小时匹配声明窗口连续前缀，以及业务/网侧最后源小时一致。空前缀只允许原始端点，
不能带已提交publication。实现摘要绑定旧诊断的依赖清单、cohort模块、自身及事务实现；返回前再核输入和实现。

输出仅包含已提交短缺能量/失败小时计数、剩余债务/cohort分类，以及明确的未提交源小时后缀。
不适用指标为None，适用服务在空前缀上为0；空前缀的0不表示窗口履约。容差内正短缺仍精确累计。
`halted`不用于推断尝试次数或失败小时；未提交后缀包括尚未尝试及执行未决的小时，二者不能由cursor区分。
deadline miss、unknown及right-censoring完全沿用旧cohort评价，不引入终端动作或自动清债。

这是对调用方提供的内存状态与声明窗口的机制诊断。它没有历史网侧archive重放能力，
`historical_grid_archives_replayed`、`grid_history_verified`与`empirical_risk_support_verified`均为false。
即便声明窗口已全部提交，`complete_service_result`、`risk_probability`与`training_capacity_certificate`
仍为None。不能用该入口代替完整episode独立重放、正式F/S/U分类器、风险分母/权重或容量证书。

## 验证

新18项与旧容量诊断15项合并33项通过（30.35秒）。真实求解仅现有合成小例，每级上限一秒；
timeout为显式合成native注入，固定有效赋值和唯一optimality未决原因。覆盖JOINT/B6的CFE部分响应、
网侧接受/未决、拒绝裸business candidate、N/A与空前缀、非法/改写窗口、policy及publication错配、
未提交记录伪装、halted不改变已提交统计、汇总期间cursor/实现漂移。
随后补两组正例中的业务/网侧端点错配断言，18项通过（16.43秒）。独立预审进一步发现record子类
可覆盖虚派发校验，现要求exact策略/记录类型并显式调用原始记录校验器；新增子类绕过及抹掉CFE短缺反例。
最终20项通过（17.14秒）；33项组合是此前版本，不冒充最终35项全组结果。
独立限定PRE_SEAL复核确认子类绕过finding闭合，当前范围无开放实质finding；不生成official verdict或运行权限。

旧容量诊断源码SHA保持`c72fb698175230eb434be11c027b9420fa760c180af7e8432fb3232fa86ec9dd`；
没有修改旧配置、旧诊断包、执行器或episode重放器。

```text
D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_rq2_scale_committed_prefix_diagnostics_v1.py tests/test_rq2_continuous_capacity_diagnostics_v1.py
D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_rq2_scale_committed_prefix_diagnostics_v1.py
```
