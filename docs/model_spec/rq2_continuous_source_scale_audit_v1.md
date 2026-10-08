# 连续真实来源与选择器规模核查

日期：2026-09-20。性质：只读库存与现有代码调用数核查，DRAFT_NONAUTHORITATIVE。
本记录没有执行solver、生成连续dispatch、选择新策略或改变任何预算与正式门禁。

## 本次直接核验

读取本地 `data/raw/rts_gmlc/v0.2.3/upstream`，先比较SHA256SUMS自身的固定SHA256：
`95c1294626cdf00ee029659108bf1f30d4ec176a258192b784f097462226a914`，
再调用 `src.grid.rts_gmlc.verify_sha256_manifest`，25条文件记录全部通过。
通过现有 `load_rts_gmlc_chronological_data` 加载，得到73 buses、120 AC branches、1 DC branch、158 generators。
dispatch_mode分布为73 committable、51 fixed、29 curtailable、5 disabled。
8,784个hourly points从2020-01-01T00:00:00到2020-12-31T23:00:00；全部为naive timestamp，相邻差均为3600秒。
命令使用 `D:/Miniconda3/envs/compute/python.exe -B -`，exit 0；未进行外部下载。
本轮create-only机器记录：`results/tables/rq2_continuous_source_scale_audit_v1_non_authoritative/inventory.json`，
SHA256 `6fd8396855a69c7605722427957553695e20708ed1e99572997ca9f0ff24d770`。
记录绑定源manifest与七个相关源码hash，`solver_calls=0`、`model_builds=0`；五个文档列出的源码hash已逐一与实际文件比较通过。

这些是本地固定benchmark源的完整性和库存证据，不是AI数据中心实际运行、业务deadline、事故联合分布或恢复能力观测。
文件校验通过也不能补出连续机组初态或合法normal assignment。

## 现有实现的预算差距

`grid_information.prepare_normal_information`沿用全部generator UID，包括disabled和fixed机组。
reference selector依次选择请求、L1偏离和全部UID发电量，共n+2级；actual selector为L1偏离及全部UID，共n+1级。
`episode_coordinator._requirements`在四臂同时运行时预留 `(n+2)+4*(n+1)=5n+6` 次调用。
这不是实测运行时间，也不是每个小时必然发生的调用数；失败或停止可能减少实际调用，但完整episode在运行前按最坏情况准入。

| 对象 | 当前完整调用预留 |
|---|---:|
| 单小时reference | 160 |
| 单小时单臂actual | 159 |
| 单小时reference与四臂actual | 796 |
| 24小时四臂 | 19,104 |
| 48小时四臂 | 38,208 |
| 72小时四臂 | 57,312 |
| 168小时四臂 | 133,728 |

当前 `GridDevelopmentBudget`单selector上限20次调用，`EpisodeBudget`整窗上限120次调用/60秒预留。
因此完整158 UID输入连单小时selector准入都不能通过，不能把已有小例接通解释为真实网络可运行。
即使去掉固定或停用UID，也必须证明其阶段恒定及数值锁定等价；不能任意换成加权目标或截断UID来缩减调用数。
独立于调用数，既有normal H=25构模记录为22,275变量/28,004约束，超过现有短预算20,000变量上限。
该H=25记录引用 `rq2_continuous_grid_normal_v1.md`，本轮未重新构模或求解，不将历史记录冒充本轮测量。
独立只读核查仅找到三处一致的文字记录，未找到绑定具体25小时、初态、request和源码身份的机器构模产物。
因此该计数还需在真实来源组装完成后补可重算的build-only记录；现有合成H=25测试不能替代它。

## 来源适配必须保留的语义

1. 旧 `run_rts_gmlc_public_grid_need_dispatch_v4._normal_baseline`以 `hourly_points[hour]` 取值，source_hour为zero-based。
   `continuous_grid_normal._validate`以 `hourly_points[h-1]` 取值，source_hour为one-based。适配必须显式转换并逐小时核对timestamp，不能只复制字段名。
   对旧小时k：continuous小时为k+1、outage索引为k、incoming边界为k；首个源小时0和首个动作前边界0不是同一状态。
2. 原始timestamp无时区。现有 `naive_source_labelled_utc` 是显式标签解释，不能当作从源确认了UTC时区或与工作负载同钟。
3. 旧free-boundary逐块normal不提供连续carry-in。合法连续初态必须独立声明来源/机制身份并满足首小时ramp及残余min-up/down。
4. `prepare_normal_information`会重审完整normal assignment才发布信息对象。源库存适配不能绕过此门伪造normal plan。
5. 正常预测信息是预先发布的机制假设；当小时实际披露、事故索引、training/holdout身份仍需独立绑定。

## 下一实现顺序

先以当前158 UID规模设计并审查可扩展的选择/执行合同，保留原数值目标、界、残差与状态递推验收；
并行可准备纯来源适配与索引反例，但不能声称它已经提供完整连续网侧输入。
若保持现有全部词典序阶段，需为新执行合同提供显式调用/内存/时间预算与中断证据；不能直接扩大旧开发上限。
若减少阶段或改变tie-break，必须先证明等价或明确登记为新的机制策略，并验证四臂公平性和重放身份。
随后再接真实normal见证、共同请求和四臂输入。训练容量绑定、完整恢复及right-censoring、科学协议和正式运行授权仍开放。

## 被核查源码SHA256

- `src/grid/rts_gmlc.py`: `4180ab5ce86eb34a9de9e058ff9c56275ace3a6ffab06dbb464d93ef23382448`
- `reference_selector.py`: `2554da17477580396ae698e91f9d8c6f755968c218b1801e521dd11e478eae48`
- `actual_dispatch_selector.py`: `57953126a88f7516b328f23f6e3e72e4660a771fc2fac9d5e170a0a3a2071957`
- `episode_coordinator.py`: `18b703ed033c8f1012a9725207dc2f27fb0d18e6c1c28f9558f3f0b62ba89725`
- `grid_information.py`: `957af693018cd99aefa2d32bc599a1482d81cbc8cba05d686266393f9d38d69e`

除首项外均位于 `src/rq2_joint_deliverability_boundary_v1/`。上述为开发证据定位，不是production seal。
