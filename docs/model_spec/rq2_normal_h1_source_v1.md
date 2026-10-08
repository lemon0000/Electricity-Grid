# H1 当前小时 normal 适配与开发状态传递

2026-09-30，DRAFT_NONAUTHORITATIVE。依据已批准的有限机制协议 v2 与 H1 规则开发。

`normal_h1_source.py` 将专用静态网络、唯一当前 base row、原始 workload 和完整 normal 前状态组装为单小时输入。
静态提取只读取网络与机组字段，不读取、复制或散列 `hourly_points`。源文件认证、源小时连续性、pair/split 映射与事故原点披露须由上层来源控制器另行验证；本模块没有读取真实数据集或执行来源认证。

当前 workload 复用既有 `workload_projection.py`，固定声明 250 MW、12 位 half-even 与无 idle 的线性映射。
原值、精确投影及误差以不可变 canonical JSON bytes 保留在 audit 字段；独立 audit identity 绑定真实 timestamp、显式 source time basis、投影记录和内核输入身份，并在读取时复核。
raw > 1、正值投影为零及不能满足接口恒等式等情况拒绝组装，保持 unresolved。

三种时钟分开使用：

- `source_timestamp` 保存真实来源标签，仅作审计。
- `relative_hour` 是从零开始的 v2 episode 小时，范围 `[0,192)`。
- 内核每次只接收一行，`source_hours=(1,)`、`GridCarry.source_hour=0`。这只是局部索引映射；全部 UID 的 commitment、generation 和 committable elapsed hours 从前状态传入。

内核 row/request timestamp 统一为固定 UTC epoch 加 relative hour；period 和零业务 envelope 使用固定中性值，incidents 为空，availability 等于静态 enabled。
旧 `GridIdentity` 所需字段也使用固定内部标记，与真实 split、pair 或 outage seed 无关。
静态 inventory 按 UID 排序。共同计算键绑定这一中性编译结果、允许的物理前状态、模型/适配器/solver/预算身份；真实来源标签不进入该键。
两个 raw workload 若投影为相同 baseline，可以共享 normal 计算；各自投影来源仍保留在审计记录中。

第零小时逐 mode 创建已声明机制初态；若另传初态，必须与当前行的声明初态一致。后续小时不得重新初始化，前状态 completed hours 必须与当前 relative hour 相等，静态网络身份必须一致。
noncommittable UID 保留实际选定出力和静态 enabled；其无启停义务的 elapsed 字段保持零。
消费边界另检查逐 mode 状态/静态功率边界和 committable age 从声明初态可达的范围。当前 API 只接受由本进程组装/求解产生的 owned 类型，没有从字典或存档恢复有效 boundary 的入口；恢复时的精确 predecessor 链校验须由持久控制器实现，不能只信 evidence-role 字符串。

`replay_feasible_boundary` 重建完整约束并使用既有 H1 的 1e-9 严格 assignment 审计，产生仅供检查的 feasible candidate。
该类型不能作为下一小时有效前状态；失败不产生候选后状态。
赋值在 1e-9 容差内可行仍不保证满足可消费 carry 的精确值域：例如 off/disabled 的微正出力或微负 generation。
对此增加 carry 域门并拒绝产生后状态，保持 unresolved；不对连续原值或目标锁舍入、移动。原有 native 数值验收门保持不变。

`normal_h1_current_solve.py` 自行调用完整 owned H1 native lex chain。全部阶段通过后，才从最后 assignment 派生 numerical candidate boundary。
公开 projection 包含全部机组状态、completed hours、静态身份及 canonical 目标锁链；辅助 reserve/segment/flow 保留在 native witness，不加入 projection。
返回对象记录 before identity；任一阶段失败返回 `decision=None`。开发组合允许将完整 numerical candidate 送入下一小时继续验证，所有对象的 `published` 仍为 false。
若 native chain 已通过但 carry 域不合法，返回 `current_decision_accepted=false`、`decision=None` 和明确 `current_boundary_rejected`，同时保留完整 native evidence 与实际调用计数。
native 返回后的输入/键复核异常或漂移对应 `current_input_rejected`，同样保留 native evidence 和调用计数，且不产生 decision。

当前组件不提供持久发布、同键冲突仲裁、缓存读取认证、三链独立存储、按需后续或完整服务/容量认证。
正式控制器必须在原子发布后才更新共同 N head 或供 reference 使用；不能把本组件的开发 candidate 当作已提交状态。
