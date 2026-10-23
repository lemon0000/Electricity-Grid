# C：P2完整请求图与成本准备

2026-10-23，DRAFT_NONAUTHORITATIVE。接续[完整保存编码等价](continuation_handoff_20261023_shadow_v2.md)；本包只准备原公共数值计划中的P2，不执行native、writer或reopen，不创建可运行controller、生产lease、seal或official receipt。

## 输入和固定范围

继续使用原core/codec/journal/HiGHS接口和原YAML、RTS-24具名公共case；on_time/early/full_temporal，actual h=-2..7十小时，registration_end=4与observation_end=8分别保留业务注册末端和物理观察末端，合同仅h1/2两帧各完整139。后续1431/4273及D/E范围保持。

生成器只调用原load_fixture、10次reference_requests、2次hour_requests及10次dataclasses.replace实际槽模板；构造326个PointRequest，其中7个完整compiler附带参考请求不进入319槽。0科学构模/数值import/solve/重放；候选编码器的实际执行接线另行验证。

每次独立逐槽验证另调用10次reference_requests和2次hour_requests，重建316个静态请求对象以核309个SHA。生成阶段验证一次、保存读回再验证一次，因此完整prepare为326+2×316=958个请求对象；不得只把319槽数当作全部构造工作。row与packet封闭字段，拒绝额外未来数值字段。

319槽依次为41实际轨迹和278合同点，QP160/LP159。角色：P0/actual各10、实际raw1、恢复两端各10、normal C2、fault F/raw各138。完整成功路径对应经济KKT12、child LP KKT159、primal-only148；四次构模/两次import每点的原路径为1276/638上限，不是实测次数。

309个静态request SHA由当前原compiler固定，10个actual request SHA保持null。全部BoundQuery SHA、未来parent point/KKT SHA和actual P保持未填写；parent_request_sha是已知父请求身份，不是未来数值点身份。依赖包含父slot、严格串行前驱、已接受上小时actual slot、actual当前参考集合与合同actual-finish阶段门。失败或策略提前停止时不得填造剩余节点来凑满319。

## 来源、成本与停止帽

准备工具须核原P1 postcheck anchor和完整683文件首尾、原compute环境及runtime bindings，输出新packet/source/runtime与P1成本依据；不修改P1注册或其native_authorized=false历史字节。packet必须明确native_authorized=false、execution_supported=false和resource_admission=false；P2输出执行目录不存在。

CLI在导入仓库模块前要求fresh repository scope，绑定规范module/spec/file/父包及driver argv/cwd，复用shadow v2身份前缀并核新增kernel/driver全部函数与固定source集合。保存终态只允许packet/context/observation三个普通非reparse文件，首尾核pin和完整packet验证；已有准备目录拒绝复用，失败仅写本次新建目录。

原fingerprints/preserve/fixture/cost装载为明确metadata warmup：已有pins/refs及sys.modules对象库存不得删除或替换，新增module只能是登记的新增stdlib，仓库或第三方新增拒绝。构造/保存结束再次核完整module库存和固定runtime；warmup不赋予执行权限。

来自P1的实测仅作成本分解依据：命令213.514337s、Job206.281s；31个point进程wall合计96.902s，原native内部run合计0.0856292s。point时间包含解释器/导入/核验/数值与保存，不能将差值全称启动时间。inclusive审核/摘要/journal时段重叠，不相加或直接作可节省量。五小时P1/保存shadow不补齐十小时writer增长与昂贵失败。

拟议停止帽为串行1线程/零重试、solver5s、point10s、package3600s、fresh60s、package无进展65s/fresh无进展60s；RSS1GiB、进程commit1GiB/Job2GiB、64MiB/8192文件、保留HANDLE1024。319×10=3190s与410s其余窗口是停止预算分配，不是ETA或完成保证。P1逐点形状最大18文件/79638B仅支持同网络形状下的已观察投影，未覆盖合同失败/长前缀/更大numeric输出；帽值不表示准入。

native前仍需具体P2 controller/provider/point-worker/fresh实现、完整性能与昂贵失败审查、独立审查和新的专项授权。原P1的31点cap、worker路径/注册和五小时前缀不能借用来执行319点。本工具不提供execute选项；本轮只生成一次独立准备packet，任何后续运行遵守agent第7–9节与用户“不启动长实验”的范围。

actual_finished仅表示41个actual均接受、未stopped且轨迹循环完成，不代表terminal或fresh已经发布；未来runner随后仍须finish→fresh。parent_slot须兑现父完整point与economic KKT后才物化BoundQuery。
