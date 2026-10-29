# F：retained Parent40、profile 关系与失败封存普通验证

2026-10-29，DRAFT_NONAUTHORITATIVE，登记前自身受控费用 0。承接 [bootstrap actor v3](continuation_handoff_20261029_saved_fresh_bootstrap_actor_v3.md)。root 唯一 writer；retained_lifecycle_review 独立只读 PRE_SEAL。完整 F、真实 grant、Native/P1、whole-workflow 准入均保持 OPEN，不重跑 NFC12 或旧 export 70 项。

## 具体问题与实现范围

Parent39 仍只支持 construction；旧 data replay2 的 quiet/raw/source 三个独立参数不能证明同一个 direct child。新 Parent40 是外层已另获授权并创建 child 后的唯一 post-spawn owner，提供 outer 绑定 source raw 的 held dispatcher，不包含 launcher、P1 reader 或授权发行。Parent40、complete validator1、QuietActor2 为本包可登记后继；旧 Parent39、QuietActor1、replay2、Core44/Probe42、LC6/Helper7/Permission1/Coordinator2 全部保留原字节。

Parent 持有 immutable program 闭集、namespace/function/class/constants/native-builtins witness，在 entry 从隔离原 CodeTypes 核对。唯一 quiet actor 执行 release → drain → close HANDLE → finish；validator 由 exact type、creator、registry 和 held finish 取得 quiet，逐项绑定原 manifest/transport/argv/streams、kernel identity、release frame 与 memory guard 的同一 parent/child。producer 只能从该 child 单一 canonical report 的 producer_result 派生，并与 bootstrap actor/probe 的 terminal、permission、namespace、packet/stages/pins 交叉一致。Parent 逐 683 内容读取仍为 0。

startup/import profile 关系要求更早独立 accepted receipt、profile、manifest、admission、registration 完整原流及 scope/pin 重开，当前 observado profile 必须 exact。可信 external registration anchor 固定 None，两个非 startup case 的精确 graph contract 固定 None；graph 256 仅作 stop cap，不能打开 accepted。真实 pre-spawn reservation、身份/期限/nonce 绑定、profile 在 spawn 前的可信 publication 及专项授权仍待 outer 后继，当前五件自洽数据不产生授权。

capture、run、JSON/cap、quiet retire 前后和 parent commit 的失败必须保留原 primary、递归 cause/group/secondary，形成固定失败数据。退休绑定 immutable terminal snapshot/result bytes，删除 exact registry row；foreign row 不删除。无物理/事实闭合时保存 UNRESOLVED 和可观察失败，不能宣称 retention 已关闭。晚期错误不能替换已有 primary，不能生成 accepted profile 或重跑 child。

## 唯一普通验证与资源边界

唯一 23 项 unittest：15 项完整数据/跨证据/profile/source-factory、8 项 immutable witness/capture/晚期 JSON/cap/retire 前后/foreign registry/失败重开。只运行两个固定 stdlib 微型 Popen，读取 system temp 的合成 payload 和固定 release，查询自身 PID/creation/command，输出合成 probe/trace。它们不执行项目 Source49 目标、P1 内容、项目 Native owner、角色、模型或 solver。两个 child 各 drain 1s，退出/关闭均有固定界；factory 一次失败 sticky，不重建 child。其余故障是明确 private CodeType/数据夹具，不能视为真实 Native graph/profile/permission 证据。

private positive 夹具仅使用显式 synthetic exact graph 和 registration anchor 来覆盖后续分支；默认生产 None gate 另有拒绝用例。复用旧 private export 构造完整 packet，不运行其 70 个 test 方法。检查内容包括：原始流/manifest/transport/release pins，source/packet、actor/probe/namespace/permission 一致性，独立 profile 整套工件/旧进程关系，严格 JSON/压缩终态、stage/census/graph 形状，live/saved memory pair，source metadata drift、原 primary 与 registry 生命周期。

DAG：register → 唯一 23 项 unit → 独立 PRE_SEAL findings 保存 → saved 原 stdout/stderr 重开 → checkpoint → scoped Git。各阶段仅一次；拒绝后只保全账和冻结记录。阶段帽 5/12/5/5/5 秒，unit child 10s，static 25/unit 15/总 40s；ordinary capture stdout 128KiB/stderr 32KiB，256MiB/process/512MiB pair；root 10 文件/4MiB、单 record 1MiB、checkpoint 预留 1MiB。不得通过扩大帽或原路径重试得到接受。

## 账源与继承

固定 predecessor CP：369a5b87a1c979d357e3dcad6fa952d019e4c61d1dfbdad7b976102cb0e467d4，10325B；root 6 文件 777498B。累计 static 631.4034837999891s、pytest 366.48897970000326s、unittest 311.70168629997715s，总 1309.5941497999695s，51 条不接受记录。旧费用不退款，剩余不转用。

继承 expanded 1391 加 root 6 扣 driver overlap 1，精确 1396 inputs；archive 255 文件 28622080B。own 8 项为 Parent40、QuietActor2、complete validator1、本测试、scope、driver、Capture1、DRAIN1，重叠 2，effective 1402。登记核 exact union、完整 archive、known/charged record pins 与全部历史失败；登记后 own/input 字节冻结。Source49 epoch/NFC12 全 16 文件、原 39 项并行 worktree 字节、B1–B3、原 P2 七输入保持。

本包仅支持 retained parent/profile/failure 的普通实现验证；不打开 role/permit/science/resource/formal/run/F gates，不构成 production seal 或 official review verdict。
