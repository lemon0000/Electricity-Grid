# F：endpoint/Core 接线普通验证 scope v1

2026-10-30，DRAFT_NONAUTHORITATIVE。依 [设计v1](staged_deliverability_c_saved_fresh_endpoint_preparation_design_v1.md)，首次register后own全部冻结；首拒绝后仅checkpoint，修复进入独立successor。失败与费用不退款。

validation_methods = 99; endpoint_methods = 30; cleanup_methods = 32; role_methods = 26; integration_methods = 11

唯一账源route v2 CP：15134B / `037ec427e1f7d42592d1a0704194df21c7511676aecb3a6d0735e77e8efc6008`，accepted/accounting_complete/diagnostic_accepted=true。root6/985003B。累计static705.1804242000246、pytest366.48897970000326、unittest414.9035574999798，总1486.5729614000077秒，58条不接受记录。

完整继承input1526 + root6 − driver overlap1 = **1531/86187914B**；archive314+6 = **320/39738413B**。own21-overlap10，exact union **1542**。原42项snapshot、NFC12原16文件、Source49 epoch、WIP before_repair、B1–B3、原P2七输入及所有失败/发布绑定字节保留。每阶段fresh核input/archive/own与原F合同AST；当前handoff显式纳入own。

唯一顺序register → inspect真实transport容量 → 99方法普通unittest → 独立PRE_SEAL findings → saved独立decode与原测试记录核验 → checkpoint。预算static34/unittest35/总69秒；阶段帽6/10/35/6/6/6。每阶段独立`-B -s -S`启动控制程序，阶段内不spawn子进程；测试同进程有限执行。root10files/4MiB、record1MiB、checkpoint预留1MiB/1slot，原测试文本128KiB。阶段超限或任何拒绝保存实际费用并停止，禁止续期与重试。

每个测试使用Python管理的合成映射buffer，ctypes内存访问只触及该buffer；kernel HANDLE leaves为synthetic。未调用Capture1/DRAIN1或Native sampler，未测连续RSS。validation child0、project/fixture target child0、项目Native/P1/Source49执行/solver/full F/NFC12均0；正常stdlib与私有copy模块执行如实记录，不称目标完整启动。

唯一接受范围 `endpoint_core_ownership_synthetic_and_transport_only`。PRE_SEAL只读审查只生成非权威findings，运行/science/resource/formal/actual_F全部gate保持false。原F预算与科学阈值不变；真实Native诊断须另行准备具体包并依agent.md第9节取得专项授权。
