# H1 registry validation operation development v1

状态：`DRAFT_NONAUTHORITATIVE`。本后继针对重复 N0 历史校验；科学模型、输入、数值阈值和正式运行权限不变。

## 瓶颈和实际范围

bootstrap v3 的四 build 优化只复用当前 slot。已有 terminal slot 在后续 owner 的 `_registry()` 中仍反复完整数值校验。静态成功路径中，每个旧 slot 在一次 bootstrap 内至少有 26 次 full prepare；依次启动三个 arm 时已有 slot 数为 0、1、2，因此至少 78 次。这是调用下界，不是实测耗时或实际运行上限。

新三个模块为 `h1_historical_n0_verifier_development_v3.py`、`h1_bootstrap_integration_development_v4.py`、`h1_owned_bootstrap_controller_development_v4.py`。它们使用独立 schema/type/implementation identity，不覆盖 predecessor，也不修改已启动 attempt。

`RegistryValidationScope` 从真实 bootstrap 获得原 operation lock/nonce 后开始，到原执行路径完整返回、全部 root proof 清理和回执构造完成后结束。scope 内原有 `_registry`、`_replay`、`_observe_N0`、source/目录/metadata observation 及保留顺序均继续执行；只替换各个 root 的重复完整数值重放。

constructor、inspect、reconcile 等未进入该 scope 的路径仍作 full prepare。本次实现不把 scope 延伸到 roster、common、Rref、Actual 或 paired consumer。

## proof 与授权边界

- 每个 `(root, binding pin, terminal pin, completed_hours)` 有独立 proof；一个 slot 不得换 root/pins，一个 root 不得被另一个 slot 复用。
- 每个 root 首次 prepare 执行 `4 full + 4 fresh`；整个 build 的最终检查和 body 返回后才能确认。其后每个 prepare 执行 `0 full + 8 fresh`。每个 prepare 始终有 16 次 context observations。
- scope 最多 3 个 root，每个 root 最多 64 次 prepare；超限失败，不改用隐式重算，不延长预算。此开发上限不声明覆盖完整研究任务数。
- 私有 closure 保存 scope、owner、原 guard、nonce、creator PID/thread、declaration、各 root operation 和 canonical build rows。scope 查找和任何公共操作失败后 poison，调用者捕获异常也不能继续复用。
- 一次定义时 binder 只接受真实 bootstrap class 的原 `_check`，克隆该 callable并生成私有 capability。公开直接构造、伪造 exact-type owner 或外线程借锁均不得取得 scope。普通 unit 的定义前 seam 必须明确标注，不作为真实 owner 接线证据。
- 清理对所有 root 分别尝试 poison/close，保留最先异常；每个原 guard 和 proof 都必须清除。关闭后只保留非权限性的执行回执。secondary poison 错误进入回执，arm close 错误同时保存在异常 notes；后者尚不能单独作为机器可读恢复证据。

## 结果和回执

科学投影仍以 predecessor v1 的 `decision_bytes` 和 raw `audit_payload` 为 oracle。durable N0 body 采用新 verifier schema/identity，旧 `4/4` 只在明确的 predecessor compatibility 子字段中保留；随机 session 和实际执行量不写入 stable body。

成功的 `bootstrap()` 另返回 `N0_validation_execution_receipt` canonical bytes。它包含 root receipts、每次 build 的序号/slot/root/caller site/body hash/envelope/execution，以及合计 full/fresh/context 数量。冷加载单 N0 路径必须实际保存并核验：

1. site 顺序为 `N0_build, N0_build, registry, registry`；
2. prepare 序号为 1、2、3、4；
3. 首次为 produced + `4/4`，其余为 consumed + `0/8`；
4. 同一 root 的 proof basis、active identity、session 相同；
5. 原 v1 oracle 的科学 SHA 与全部 build 一致；
6. Job exit 0/quiescent，原锁和进程均已清理。

## 已有证据与开放出口

`validation_n0_operation_01/registry_unit_04`：115 passed，覆盖三个 root 各 26 轮、96 个 context failure edges、错误 root/pins/slot、prepare/root caps、owner 漂移、捕获错误后的禁止复用、无 capability 入口，以及每个 root 的 poison/close 故障。

`registry_sources_02_non_authoritative/patch_manifest.json` 和 `registry_rebuild_check_02_non_authoritative/terminal.json` 将当前三个源码从固定 predecessor bytes 确定重建并逐字节核对。原始 builder/manifest 和每次失败 attempt 保留，不能代替后续修补字节的证据。

冷加载真实单 N0、真实多 root registry 和完整三 arm hour-0 仍需分别获得终态。单 slot saved 对照的 22.0% 收益只适用于旧的四 build 后继，不是本 scope、common 或完整实验的耗时结论。M2、完整性能审查、seal、official review、资源准入和正式实验授权继续 OPEN。

## 2026-10-18 runtime registry 修复

零 Job checkpoint 定位旧 definition baseline 将 episode_store._REGISTRY 的空 set 错当静态常量，真实 owner 合法打开两把锁即触发误拒绝。当前只规范 definition view 的这一条 row 为原 set 对象身份；module/file/set/lock、结构/唯一性和其他全部 rows/files 保留，观察采用 nonblocking lock。

operation 的私有 resource record 另外保存完整 runtime 成员集和两条原 journal/genuine lease/key；进入后在所有 resource checks、build confirmation 与 cleanup 验证不变，允许进入前同进程存在其他已持有 store。原 _dispatch_view、_HourScope._context 和每 prepare 的16contexts未改。126项回归和真实owner六节点复验通过；完整四build/bootstrap尚待cold04终态。

当前三个源码以 registry_sources_03_non_authoritative/patch_manifest.json 和 registry_rebuild_check_03_non_authoritative/terminal.json 重建并逐字核对；上文 closure02 属于修复前历史字节。当前仍为 DRAFT/PRE_SEAL，不提供 official verdict 或完整链准入。
