# 固定容量连续策略诊断包

DRAFT_NONAUTHORITATIVE；输入、容量和响应参数为合成机制假设。
原始请求、精确执行投影、业务候选与已提交状态分别保存；未提交候选不是实际履约。
短缺能量按归一化功率×小时精确累加，包括逐小时容差内短缺；不产生经验风险概率。
cohort仅取已提交状态，保留未知期限、逾期和右删失；完整服务结论保持null。
本地清单校验成员、依赖及确定性重放，不是正式manifest或防篡改签名。

验证：python -B experiments/export_rq2_continuous_capacity_diagnostics_v1.py --verify-existing
