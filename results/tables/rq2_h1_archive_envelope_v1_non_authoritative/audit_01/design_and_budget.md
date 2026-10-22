# Owner / holder 容量边界审计

本 scope 为 DRAFT_NONAUTHORITATIVE，只补整链预算，不建立执行准入或科学结论。root 是唯一 writer；现有 phase_budget_review 只做 non-authoritative PRE_SEAL 只读审查。应用 agent.md §7 / §9，保留原 3h case、失败记录及已完成绑定包。

本次仅做整数/编码单元测试和只读静态审计：固定读取旧 case 的 9 条 SQLite events、9 份 holder ticket、header/lock 和已绑定的 465 case / 444 owned 文件；核验最近 constructor 及 business 证据的 hashes。SQLite 用 mode=ro，禁止实例化 owner/producer/source Reader、创建 Job 或调用 solver。普通单元/静态检查按 §9 无需递归性能诊断。

测试上限 30s，静态审计上限 30s，输出只写本 non-authoritative scope，预计输出 < 2MiB；不复制历史数据、不下载、不改数据库。若遇绑定漂移、原件变化或 cap/编码关系无法证明，保留失败终态并暂停相应推导。没有 owner 长链或正式/native 启动。

验收：以实际 encoder 验证 Base64 舍入与 wrapper 字节；独立枚举小范围合法 records / tickets；从原 source 路径证明 128KiB source audit cap 与 source→owner 编码关系；核对每 selector 独立预算；区分 575 paired / 576 terminal、alternate、pending attempt 及 holder prepared tail。容量公式只覆盖声明语法下 logical content，不扩展为数值报告可达性、SQLite / filesystem 上界或 wall/RSS 准入。

整链 wall、RSS、SQLite/journal、normal/selector 档案、scratch、checkpoint、报告与失败收尾仍按证据逐项登记，未证部分保留 null。旧 toy 的 cap 不足只说明该配置不能承载目标工作量。
