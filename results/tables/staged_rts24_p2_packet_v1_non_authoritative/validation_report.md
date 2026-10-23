# P2完整请求图准备检查

2026-10-23，DRAFT_NONAUTHORITATIVE。范围按[准备合同](../../../docs/plan/staged_deliverability_c_p2_preparation_contract_v1.md)，仅生成原数值栈的P2元数据；没有P2 controller、native执行、journal writer/reopen或资源准入。

## 保存结果

唯一`--prepare`命令exit0、外部wall6.760574s、准备主体5.059443s，stderr为空；[三个保存文件](packet_01/packet.json)共505285B。这些时间只描述元数据准备，未采样RAM，不是P2性能测量或ETA。

固定on_time/early/full_temporal，实际h=-2..7十小时，registration_end=4、observation_end=8；合同h1/2各完整139槽。319槽=41 actual+278 contract，160QP/159LP，证据类别12 economic KKT/159 child LP KKT/148 primal-only；原四构模/两import成功路径上限1276/638仍是结构数。

309个静态request SHA由原compiler逐槽重建核对；10个动态actual request SHA保持null，全部BoundQuery/父point/父economic KKT SHA保持null。parent_request_sha只绑定已知请求，不预填未来数值。DAG保存严格串行、同小时父slot、上小时已接受actual carry、当前参考集合与合同actual_finished阶段。actual_finished只表示actual循环接受完成，未来仍需finish→fresh；父完整point+economic KKT是BoundQuery物化前置。

本次prepare请求对象构造工作为326生成+316独立验证+316保存读回验证=958，不是958槽、科学查询或实测solve。958为实现路径的静态会计。后续1431/4273与完整F/X时序、D/E范围保持。

`context.json`绑定55源、40 application modules、74 functions、20类、211 stdlib modules和原P1 runtime。warmup只新增email.feedparser/email.parser；已有module对象不得增删替换，保存末端再次核库存/runtime/source。P2执行目录未创建。native_authorized、execution_supported、resource_admission、formal_result均false。

## 验证与保留

- 最终针对性普通检查38 passed/22.05s，六源首尾相同；覆盖封闭schema、309静态SHA的错误替换、动态身份空值、DAG/carry/phase、目录复用/额外文件/reparse、保存失败、runtime/module漂移。最初单位检查12 failed/10 passed来自注册末端误读，修复为4后通过；原日志保留。
- 相关冻结普通回归为60 passed/1 failed/60.16s。唯一失败是旧`test_clean_interpreter_preservation_matches_legacy_without_importing_psutil`最后要求P1目录尚不存在；已完成P1使该历史前置条件不成立。独立新进程诊断exit0，prior/cores/numeric三组保持相同、psutil未导入，P1确实已存在。原测试、失败日志与诊断共同保留，未称整组通过。
- 只读PRE_SEAL实现和领域复核未见剩余High/Medium；这不是official verdict、seal、review receipt或运行许可。
- [独立stdlib-only后核验](postcheck_01/postcheck.py)的`packet_03`exit0：三保存文件、独立角色/事故ID/边会计、schedule SHA、55源与160个runtime文件匹配。原P1683文件/2950863B、B1–B3保存118文件及685前序路径保持；此前四个发布包的196路径保持。原P1/profile/v1失败shadow/v2 shadow四份旧postcheck stdout精确复现，没有新科研重放。

后核验草稿的前两次失败与源码副本保留：初稿误将37/32事故ID当连续编号，已按原YAML排除branch10/generator14；第二稿将Conda标准库hardlink误按仓库普通文件拒绝，已限制仅声明runtime文件允许hardlink。原packet与科学源码未变，最终后核验单独保存。

## 后续边界

[编码接线成本决定](../../../docs/plan/staged_deliverability_c_candidate_integration_cost_decision_v1.md)保留plain_v2候选。2254个原类getter和118个child旧别名使局部facade不能兑现candidate-only路径；真正版本化接线涉及类型/codec/journal身份，当前先准备原栈P2。

3600s、1GiB/Job2GiB、64MiB/8192文件等只是拟议停止帽，不是资源准入或预计完成时间。原P1的point wall96.902s与native内部0.0856292s不能直接作为可节省时间；十小时writer增长、完整合同与昂贵失败仍缺实测。下一步是具体P2 controller/provider/point-worker/fresh的无原生开发、完整DAG/失败路径成本审查及独立验证，再按规则取得专项native授权。原P1一次授权已用，不启动长实验。C整体性能、139数值/F-X时序和D/E现实输入/选择/留出继续OPEN。
