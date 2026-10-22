# C范围与保存记录结构审计

2026-10-22，`DRAFT_NONAUTHORITATIVE`。本次按[已绑定执行页](../../../../docs/plan/staged_deliverability_c_dag_and_cost_review_v1.md)完成一次只读机械核验，exit0。用户在核验后确认公共网络方向，本轮确定RTS-24为最小公共网络后继，两母线保留机制回归。运行前执行页的候选措辞保留原字节；当前范围及下一步见[C交接](../../../../docs/plan/continuation_handoff_20261022_c.md)。

## 核验结果

| 检查 | 观察 |
|---|---|
| B1–B3全部保存文件 | 118个，3,234,268B；前后size/SHA一致 |
| 历史绑定与环境 | 42仓库pin、B1九pin（包含在42中）、7选定外部及5包版本匹配；同Python/解释器/platform |
| B2/B3 completion清单 | 15/75项逐一匹配，补充说明文件单列，无failure或额外工件 |
| 保存角色独立重算 | 599点计算、84业务提案步、86网络尝试，与原runner AST登记和保存report一致 |
| 四probe | 原因、pending role/adoption、candidate state有无、已接受state关系逐项核对；发布后仅新增已保存candidate一条 |
| RTS-24源 | 本机PYPOWER case24源AST为24母线/33机组/38支路，SHA前后相同；没有执行case或构建模型 |
| 新运行工作 | 0新PYPOWER点、0 solver、0 child；未模拟新的物理小时 |

父/child三例分别140、140、82点，四probe分别56、48、63、70点。正常scenario别名不重复计；延期拒绝attempt仅计入已发生工作量，原child已接受state保持不变。745点审计访问及334编码/4,035,550B等仅与原记录对账，未在本次重新执行或测量。

脚本入口至输出0.4098294s，启动解释器至退出0.5349412s；audit生成前0.4073358s，末段观测RSS36,401,152B。这是保存核验自身的成本，不能替代B3轨迹或公共网络成本，也不称完整峰值RSS。start/audit/launcher三份机器记录共39,625B；所有记录未越过60s/512MiB/32MiB输入/单份4MiB输出上限。launcher是未seal的supplemental外层终态记录，不是运行授权或生产凭据。

10项新针对检查通过，pytest0.32s。覆盖正常别名、提案前拒绝/actual失败的不同业务步、拒绝candidate与accepted state分离、重复reopen计费、库存漂移/多余文件/failure marker、四类恢复原因与adoption篡改、全量pytest导入年龄与CLI计时隔离。没有修改旧测试、runner、源规格、fixture或保存结果。

普通只读开发审查已核对最终源与终态，未见剩余High/Medium实质发现。修复及审查范围保存在[review_findings.json](review_findings.json)，交付机械检查见[verification.json](verification.json)。本轮没有frozen candidate、seal、official verdict或receipt。

## 成本与剩余边界

结构模型明确每次prefix重放及完整state摘要的平方增长；24/192小时只有结构算术且wall为null。RTS-24尚未接staged adapter；现有B2/B3网络仅full_temporal、B3最多10小时。POI/工程/F-X/事故集/设备业务缩放输入表、三方法网络回放、一般网络独立audit、代表性query/更长cohort/失败收尾测量及D/E整链预算仍OPEN。

字节bookends仅核对可观察快照，不提供锁或同值ABA保证；7项外部不是完整生产依赖闭包。真实阻塞I/O、坏盘/掉电、kill及failure报告失败未测。完整F/X业务必要条件失败和`aggregate_contract_release=false`保持；实际路径接受不替代完整时序合同背书。未启动长实验、真实native校准或正式实验。
