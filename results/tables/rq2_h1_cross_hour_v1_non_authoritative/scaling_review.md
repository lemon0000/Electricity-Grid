# 跨小时路径的规模审查

状态：DRAFT_NONAUTHORITATIVE；仅代码路径推导。未运行192小时，未形成生产预算或运行权限。

当前successor保持每次操作开始和结束完整重放、paired前独立fresh。test-only静态身份复用不改变这些动态调用。小规模功能证据可以验证连接，但其wall time不能线性外推完整窗口。

设从空owner开始连续完成T个合法active小时，每小时调用一次`run_next_development`，最后关闭并只读重开一次；不含alternate、pending tail、额外inspect、重试或episode_terminal操作。`h1_phase_owner_development_v1.DevelopmentOwner._restore`每次先做genesis fresh，再为每个已存intent做一次fresh。

| 阶段 | owner触发的phase-source fresh次数 |
|---|---:|
| 空owner创建 | 1 |
| 第h小时开始ready replay，h从0计 | h+1 |
| 第h小时current及paired前独立fresh | 2 |
| 第h小时提交后完整replay | h+2 |
| T小时后的只读重开 | T+1 |

因此成功前缀的fresh调用数为

`1 + sum(h+1 + 2 + h+2, h=0..T-1) + T+1 = T^2 + 5T + 2`。

T=2时为16次；T=192的假设路径为37826次。192仅是规模推导，不表示该路径已经通过科学或资源准入。

每个relative hour h的fresh使用`completed_hours=h+1`。`h1_phase_exact_source_current_development_v1.prepare`每次调用两遍`historical._replay_prefix`。只按这些prefix调用的`completed_hours`求和，得到一层prefix-hour权重：

`2 * [2 + 2T + T(T+1)(2T+1)/6 + 3T(T+1)/2]`。

T=2为40；T=192为4867460。该指标至少按立方量级增长，**不是实际文件读取数、模拟执行时长或完整workflow预算**。historical内部每小时还读取terminal/job/binding、request/clock，执行bridge/child replay并多次观察prefix；registry和source校验另计。

本次验收另外显式调用一次`historical.inspect(completed_hours=T)`，增加T个上述一层prefix-hour单位，随后`snapshot.inspect()`还重放normal parent T小时；它们未包含在owner公式中。测试外部的初始化、normal Jobs、selectors、数据库/holder、句柄关闭和报告也另计。

完整episode若在第T个outcome之后再调用一次`run_next_development`持久化`episode_terminal`，其ready和结束inspect额外增加`2(T+1)`次fresh，额外prefix-hour权重为`4*[1+T(T+1)/2]`；T=192时分别为386和74116。此时再核算重开及独立postcheck，不能拿仅成功prefix公式当完整episode成本。

上述公式经只读`sol_reviewer`独立沿代码复核，属于PRE_SEAL findings；未签official verdict、review receipt或打开gate。主要代码位置：phase owner的`_restore`/`_fresh`，cross-hour owner的`_paired_locked`/`run_next_development`，phase exact source的`prepare`，historical controller的`_replay_prefix`。

对后续实验的约束：先在这条跨小时路径内建立可证明的prefix复用或增量重放合同，列清依赖闭包、输入freshness、失效条件、callback/失败窗口和重开规则；用versioned successor与独立核验验证。不能把当前test-only静态memo称为解决了动态重放，也不能靠延长wall上限启动完整192h。业务数学、非预见性、独立carry、恢复债务和paired前独立鉴真仍是硬约束。
