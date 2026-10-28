# F：原始stage pin表示兼容后继

2026-10-29，DRAFT_NONAUTHORITATIVE，登记前自身受控费用0。继承[v1完整合同](staged_deliverability_c_saved_fresh_producer_export_scope_v1.md)的科学、权限、数据输出、cleanup、Parent、真实尺寸及whole-workflow边界；完整F保持OPEN。原v1全部source/scope/input/result及失败流不变，不在旧root重试。

v1唯一unit出现69项start/end进度，随后错误栈触发32KiB stderr帽；child被kill，stderr_truncated=true、capture_error=output_limit_or_reader_error，没有最终canonical report。即使有逐项进度，也不构成69项通过或完整终态验证。登记1.0121395000023767s、unit7.483748499973444s、checkpoint0.558679999987362s；package9.054567999963183s。CP accepted/accounting_complete=true仅保全账，diagnostic_accepted=false；原stdout/stderr/kill和输入pins均保留。

实际缺陷一：LC原stage evidence使用native `(bytes,sha256)` tuple，序列化后为list；v1 codec错误按dict验证，成功关闭在packet生成时被拒。packet v2严格接受len2 tuple/list并逐项验证exact int/SHA，再转换为dict与原raw_pins比较；保持Source49和LC原stage语义与表示，不接受dict或额外项。wire不兼容，因此packet schema升v2、retained observation升v3、complete data/replay升v2。LC6更新内嵌codec及observation tag，Coordinator2更新complete tag，Helper7更新lifecycle pin；Parent2绑定新codec/schema且仍exec已核同一raw。原LC5/Helper6/Parent1/packet1/Coordinator1保留。

缺陷二：旧expiry private fixture全局替换stdlib time.monotonic，现在LC新增time依赖的TCB正确先拒绝导入边漂移，故未到达expiry分支。新test_v2只在private mechanical permission模块使用time proxy，不改stdlib/LC时间，不改registry-bound deadline；原expiry断言保留。test52按原serialized pair的index1篡改SHA。其余原69项方法和断言保持，新增test70同时检查native/serialized pair可接受且dict拒绝；这些合成正例不形成真实outer/P1权限。

唯一70项ordinary：31项原生命周期+17项权限+22项本轮数据/失败/顺序。重跑整个矩阵，覆盖可逆包、exact内部gates/maps/metadata、原期限、压缩边界、独立revoke与retire verifier故障、LC sticky secondary/runtime_close、实际bridge release与late wire/cap/JSON失败保留，以及固定DISABLED issuer。无Source49目标执行、真实P1读取、Native owner、角色/模型/solver、NFC12重跑或新模拟跨度。

DAG仍为register → 唯一unit → 独立只读PRE_SEAL保存 → saved原流重开 → checkpoint → scoped Git，各一次；拒绝后只保全checkpoint。own字节登记即冻结，修补另建successor。static25/unit15/总40秒；阶段5/12/5/5/5秒、child10秒、stdout128KiB/stderr32KiB、sampled256MiB/process及512MiB/pair、root10文件/4MiB、单record1MiB并预留checkpoint1MiB均保持。未因失败扩大帽、退款、重置旧费用或转用旧剩余。

账源固定v1 CP 65f3050be22825b955415280b0151b8479e6223a756ff29589eb2410e23ffa50，9220B；root4文件812661B。累计static620.0386164999902、pytest366.48897970000326、unittest287.31596829997216，总1273.8435644999656秒，拒绝49。完整继承expanded1345与root4扣driver重叠1后1348 inputs，archive235文件25455480B；自身12、重叠2，精确union1358，完整源/归档逐pin核验。

root唯一writer，retained_lifecycle_review独立只读PRE_SEAL；不产生official verdict、receipt、production seal或运行授权。原39项并行字节、Source49/NFC12及全部失败/冻结记录保留。真实issuer、Helper7与真实bootstrap接线、Parent held quiet及逐文件P1核验、真实packet代表尺寸、整链wall/RAM/storage准入仍待完成；role/permit/science/resource/formal/run/F门保持false。
