# H1 N0 registration operation development v2

状态：`DRAFT_NONAUTHORITATIVE`。本规格只定义 hour-0 N0 登记的校验优化；M2、正式运行、resource admission 和 native authority 均未闭合。

## 实际接线与边界

三个后继模块为 `h1_historical_n0_verifier_development_v2.py`、`h1_bootstrap_integration_development_v3.py`、`h1_owned_bootstrap_controller_development_v3.py`。旧模块和已启动 attempt 保持原字节。

接线为 `bootstrap → _continue_registered_development → _finish_N0_terminal(create_local=True)`。owned controller 完整返回、关闭其 leases 后，bootstrap 在同一次 operation lock/nonce 内登记 N0。初始 state、claim/release、ready/pins 和 retained heads 检查完成后建立 scope；最终 `pending_post_N` 构造和失败清理受同一 scope 约束。

四个独立 build 按顺序执行：

| site | 位置 | full numerical / fresh context revalidation |
|---|---|---|
| `explicit_primary` | 第一次 `_build_N0_terminal`，local append 前 | 4 / 4 |
| `explicit_after_local` | local retention 后重新构建 | 0 / 8 |
| `registry_before` | global retention 后 `_replay` 的首次 `_registry` | 0 / 8 |
| `registry_after` | 同次 `_replay.finish` 的第二次 `_registry` | 0 / 8 |

每个 prepare 仍保留两个独立 prefix、各四个 inspection site、每 site 的 before/after context，共 16 次 context evaluations。四次合计保持 64 次，full numerical 总量由 16 变为 4，fresh revalidations 由 16 变为 28。这是调用量合同，耗时必须单独实测。

首次 prepare 只生成 candidate proof。整个首个 build 的 source/head/route 尾检和 body 构造成功返回后，才以 exact ticket、body、audit、envelope 和 execution identity 确认；之后三个 build 才能复用。未确认前的第二次 prepare、重复确认、错误 site/ordinal、第五次 build 都失败，不回退为重算。

## 保持的科学与观察合同

- 保持 predecessor 的 `decision_bytes`、raw `audit_payload`、科学实现身份、数值阈值和失败解释。相同 saved root/pins 上以旧 verifier v1 为独立差分 oracle。
- 沿用原 numerical inspector 和原 `_HourScope._context`，不缓存输入、目录、结果文件或 metadata discovery，不删除任何 before/after observation。
- proof 绑定 canonical root、binding/terminal pins、arm/slot、nonce、creator PID/thread、live bootstrap guard/declaration 和定义时 dispatch。任一漂移 poison；proof 不跨 `bootstrap()`、inspect 或 reconcile。
- `create_local=False`、不在当前 slot 的 registry reconstruction 和独立 verifier 调用走完整数值校验；不因持有其他 slot 的 operation 获得复用。
- 不改变 power/service balance、F/X、lead time、nonanticipativity、shared flexibility budget、recovery debt、train/holdout 或 right-censoring。

## stable body 与实际执行回执

durable N0 body 使用新 `historical_verifier_schema`、`historical_validation_contract` 和 verifier identity。旧 `4/4` 只出现在标注为 predecessor scientific projection 的 `legacy_compatibility_execution_metadata` 子字段，不能解释成本次实际工作量。body 不含每次变化的 session、mode 或 execution counts，以保持四次重建和关闭重开的一致性。

`bootstrap()` 的返回值必须另外包含 `N0_validation_execution_receipt` canonical bytes，记录四次实际 execution、64 observations、body SHA、envelope、proof basis、active identity、session 和按顺序连接的 confirmed-build digest。仅有 durable body 不能证明实际执行了 `4/28/64`；完整集成 harness 必须保存并核验该返回回执。

私有 closure 记录持有原 guard、creator、declaration、session 和 canonical prepare/build evidence。受控 finish/confirm 转换后才更新。发布前比较这些证据，拒绝可变 aliases、回执字段、ordinal、mode、链或计数的修改。cleanup 持有原 callable/guard；主体和清理同时失败时保留主体异常及附加 cleanup notes。

## 验收与证据范围

必须覆盖 64 个 context failure edges、确认时序、root/pins/slot/nonce、PID/thread、helper/method/code/default/instance shadow、body/envelope/receipt 篡改、local/global append 前后、两次 registry、最终结果和 cleanup。reconcile 与 foreign-slot fallback 另行覆盖。

隔离协议 unit 使用显式 synthetic numerical/journal seams，只证明对应控制流。saved differential 只证明一个代表 arm 的科学等价和校验成本。二者均不能替代 fresh owned Job → N0 registration，更不能替代三 arm → common → Rref/Actual → paired commit → reopen/replay 的完整 M2 验收。

进入更大验证前，按 `agent.md` 第 9 节重新核对完整调用 DAG、昂贵失败分支、资源预算和停止条件；禁止用本段提速比例外推全链时长。seal 后另需全新 reviewer 审查 exact sealed bytes，正式实验仍需具体运行授权。
