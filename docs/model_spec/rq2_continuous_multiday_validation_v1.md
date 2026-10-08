# 连续多日服务 v1 开发验证记录

日期：2026-09-12。状态：`DRAFT_NONAUTHORITATIVE`；验证对象为协议草案与显式合成动作回放。
本记录不是production manifest、review receipt或正式运行授权。

## 环境与输入

完整读取`AGENTS.md`与`agent.md`，核对执行计划、blocker register、boundary规格/实现、旧estimands和最新交付。
编辑前检查`git status --short`：仓库已有大量修改与未跟踪数据，原样保留；本轮未清理仓库。
使用`Get-CimInstance Win32_Process`筛选python/gurobi/highs，开发前及回归间未发现相关活跃正式进程。
Python：`D:/Miniconda3/envs/compute/python.exe`；所有运行加`-B`。没有新solver调用、外部查询、下载或正式实验。

## 已执行命令与观察

1. `python -B -m experiments.prepare_rq2_public_data_delivery_v1 --verify-existing`
   成功验证12包、261字段、744 Google小时、31 raw-origin blocks及全部交付绑定；summary hash与草案一致。
   Alibaba 6条raw>1值保留，最大值`1.070370705271957780430251624`。原有unknown/gates保持。
2. `python -B -m pytest -q tests/test_rq2_continuous_multiday_service_v1.py tests/test_rq2_joint_deliverability_boundary_v1.py tests/test_rq2_joint_deliverability_continuation_audit_v1.py`
   首轮`91 passed in 30.12s`。包括48小时分块等价与解析prefix oracle、跨chunk约束拒绝、恢复因果性和身份隔离。
   既有测试同时核对sealed v5 config/outer、旧v2 scenarios/model及power/workload input manifest hashes。
3. `python -B -m pytest -q tests/test_rq2_public_data_delivery_v1.py tests/test_rq2_joint_deliverability_preregistration_successor_v5.py`
   `50 passed, 1 failed in 47.43s`。失败项为旧v5的
   `test_manifest_unknown_keys_duplicate_json_and_symlink_fail_closed`，在`alias.symlink_to(target)`处收到
   `WinError 1314`（当前Windows token无创建symlink权限）。未执行到symlink拒绝断言；不记为该分支通过。
   未修改旧冻结代码/测试，不把失败改成skip。其余旧v5协议检查与交付测试通过。
4. `git diff --check`：通过。6个新增文件的UTF-8解码、replacement/mojibake检查及尾空白检查通过。
   额外逐字节核对sealed v5 outer绑定inner及5个inner成员，全部匹配；旧boundary/continuation的4个summary/cells/chains结果hash均与登记值一致。

## 验证解释与剩余门

synthetic fixture：1个连续48小时period，调用发生于source hours 23/24/25，各为0.25；
恢复发生于26/27/28，各为0.3125，eta=0.8。hour 24末debt=0.5、event duration=2；
hour 25末debt=0.75、duration=3；最终debt=0、累计调用energy=0.75、event count=1。
零末债务只是这条显式合成轨迹的算术结果，不是观测末端普遍保证。
非零carry-in情景完整携带debt/energy=0.125、count=1、prior=true、rest=2小时，最终debt=0.125、energy=0.875、count=2。

独立只读`sol_reviewer`按`agent.md`第7节执行non-authoritative草案审查。首轮发现state未绑定anchor、
envelope可在次日漂移，以及原始值/effective值的容差记账表述差异；已作以下开发修正：

- 使用immutable `JointReplayCursor`将state、最后观测identity与固定envelope绑定；continuation入口不再接受替换anchor/envelope。
- 新增轨迹/seed/split/provenance漂移、调用者修改原envelope、第二天替换限额及cursor不可变测试。
- power balance与energy/debt使用一致的effective q/r，文档显式说明微小原始调用的累计误差边界。
- cursor修正后的中间focused为`26 passed in 0.25s`，中间相关回归为`98 passed in 27.78s`。
- 复核补充发现非零初始debt测试未携带其历史energy/event；已改为完整可达carry-in并增加两项partial-history拒绝测试。
  同时将参数表核对升级为精确20项、无重复、实证列全部null及处理/需求列非空；其科学分类仍依赖本地来源审阅。
  此次修改后focused为`28 passed in 0.27s`，相关回归为`100 passed in 27.83s`。
- 进一步在初始化检查初始debt/energy/count/duration限额，阻止首步恢复掩盖初始prefix违规，并增加对应测试。
  **最终字节重跑第2条完整命令：`101 passed in 28.08s`**；以下hash绑定该次测试使用的最终实现/config/tests。

最终开发字节标识（仅供复核，不是seal）：

| 文件 | SHA-256 |
|---|---|
| configs/rq2_continuous_multiday_service_v1.DRAFT.yaml | `15645853d5ec9129cd5b274ed73179cbcf6204fa7a780061dfc51dc1d619d84d` |
| src/rq2_joint_deliverability_boundary_v1/multiday.py | `be47674948198c1e611ff6da0dfe02dc3a6ace6f23cd6eaf28cb9ed24ffbf295` |
| tests/test_rq2_continuous_multiday_service_v1.py | `4bb5bd1f40cf9c6aaa9df5434d294aef342e64df7e4f0c77b708de6bd451a4b0` |

独立草案复核：`sol_reviewer`在最终实现上运行`29 passed in 0.25s`，确认上述实现finding闭合，
参数分类与catalog/dictionary人工核对未见错分，未发现新的实现或科学语义缺口。
reviewer指出的中间报告hash/计数陈旧问题已由本记录的最终101项结果与对应hash更新；旧v5 symlink分支仍保留环境限制。
该结论仅为non-authoritative pre-seal findings复核，不是official verdict，也不打开任何gate。

正式注册、deadline/多period、四臂planner/B6共享执行、因果holdout、数据参数与全部正式运行门未关闭。
旧v5 Windows symlink验收须在具备该权限的环境执行后才能记为通过；本轮不声明完整PRE_SEAL验收完成。
