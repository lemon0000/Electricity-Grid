# C/F：pre-ENTRY cookie 清理修订

2026-10-27，DRAFT_NONAUTHORITATIVE，接续已登记的 [本地输入租约范围](staged_deliverability_c_saved_fresh_pre_entry_lease_scope_v1.md)。原登记、控制器、29 项单测及首次 discovery 的 raw、exit、receipt、plan、code/transport snapshots 全部保持。首次 discovery 因 probe 已成功关闭 DLL 目录 cookie、loader finally 再次 close 导致 TypeError 而不接受；stdout 中的 profile 不可采用。累计不接受记录由 12 增至 13。

只修复 core/parent/probe 的 discovery_repair 分支及 cookie 收尾：共享 attempted 状态，调用原 cookie.close 前置位；loader 只在未尝试时调用。close 抛错时不重试、不掩盖 probe secondary。该对象不是 Win32 HANDLE，原范围“幂等收尾”的假设已被实际失败推翻。普通 self process/thread HANDLE 的独立清理语义不变。

独立 repair_driver.py 先核固定原 registration SHA、成功单测与失败 discovery 的全部前驱 pins，并以原 helper snapshots 到新 helper 的精确 diff 登记 revision_01。只有三个 helper 可变，测试、原 controller、Source49、runtime 文件及旧记录保持。修订登记与初始登记共享 3s；新增 discovery_repair 是明确的一次修复采集 ≤5s，仍计原 static 50s、总 80s，不抹去原 discovery 5s 的失败。29 项当前字节重测使用原已预留 unittest_repair 12s，原 unittest 30s 不变。后续 profile_admission 2s、九例 probes 30s、saved 8s、64 files/8MiB 均不变。

顺序固定为原 unit accepted / 原 discovery failed → 修订登记 → unittest_repair → discovery_repair → create-only profile admission → 九例 cold probes → saved metadata 核验。新 admission 绑定修订 helper/transport 和 probe_discovery_repair.receipt.json；原失败不被覆盖或当作成功前驱。所有实际开销继续累加；编辑、审查及 Git 不冒充完整流程 wall time。只读 PRE_SEAL 后才执行有界检查，所有科学、F、native solver、角色、资源及正式权限继续 false。
