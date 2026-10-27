# C/F：静态方法表示的显式修复后继

2026-10-27，DRAFT_NONAUTHORITATIVE。首次 cookie 修复登记、29 项重测、独立 discovery_repair 和 profile admission 成功；首个 normal 冷探针在 SELF 阶段因 `compiled bootstrap binding differs` 失败，self 未开、Source49 open=0、stderr 空、parent HANDLE/pipe/thread 已关闭。原 probes.exit、normal plan/receipt 及全部前驱保留，累计不接受记录为 14。

原因是 Python 建类自动将 `__new__` 存为 staticmethod；原检查将类字典成员一律当作裸 FunctionType。后继只为 `_LocalInputs.__new__` 要求精确 staticmethod descriptor，再按原规则核底层 function/code/default/closure/global。同时强持 descriptor 自身及其 __func__，替换 wrapper 或底层 callable 都须拒绝。新增实际编译 namespace 正例和 descriptor 替换反例；不放宽其余方法。

v1 四 helper、两 controller、全部记录冻结。新 v2 core/parent/probe/test 以及 `descriptor_repair_02/driver.py` 独立；后继先绑定原结果根 34 文件的整集 hash 和 v1 revision，再登记新 helper/transport/scope pins。新 raw helper snapshots 合在单个 base64 bundle；九例 probe receipt 合在 append-only JSONL，逐例 plan 仍 create-only，保留每次 raw、异常与资源终态。原根与子目录合计仍 ≤64 files/8MiB，不另开存储账或删除历史。

时间沿同一 static50 / unittest30 / total80 账累计，包括两次失败。初始登记、cookie 修订登记及本登记共享 3s；显式新增 descriptor unit ≤8s、discovery ≤5s、admission ≤2s，均在原总帽内；九例 cold 的剩余预算为原30s减已失败 probes 实测费用，不退款；每例仍3s、timeout1.5s；saved ≤8s。此前“仅一次 repair”的次数安排由此显式修订，原上限与每次失败记录不改。编辑/审查/Git不冒充workflow wall。

新画像只由新 discovery 产生，再独立 admission；不复用旧 transport 的 profile。顺序为登记→unit→discovery→profile_admission→九例 probes→saved metadata。仍只运行新 bootstrap/probe、编译持有 ENTRY raw；不执行 ENTRY、科学 adapter、F、OwnedChild/Job 或 native solver。条件性 TCB、E/U OPEN、P/D/L 区分、全部科学/资源/正式/运行权限 false 均保持。
