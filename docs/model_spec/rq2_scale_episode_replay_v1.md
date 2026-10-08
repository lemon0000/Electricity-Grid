# 连续episode离线核验

状态：DRAFT_NONAUTHORITATIVE。`scale_episode_replay.py`接受独立typed输入窗口、reference/四臂起点、预算、环境，以及外部保留的header、有序intent/result摘要和audit实现pin。核验不调用episode执行owner、Job创建或solver，不写科研结果、不返回可执行cursor。

外部输入现同时要求原始`resource_plan`。读取root之前重算声明和实际窗口/来源/五role预算；header须与独立声明一致。仅有共同摘要不足以通过核验。绑定及资源证据边界见`rq2_scale_episode_resources_v1.md`。

## 完整前缀

持episode root lease核header与独立输入一致，要求连续小时记录与最多一个末尾pending intent。对完成小时逐一核完整五phase：固定canonical task路径，嵌套task/archive leases，核receipt/store/result与hour evidence交叉摘要、文件身份、controller identity。独立重算固定worker argv、scratch环境、host身份及process identity，核task request、intent、launch和observation相互一致；要求完整字段、合法PID/creation、recorded正常退出与quiet、资源峰值在声明上限内。

进程状态只按保存记录核对，不认证历史OS执行或当前整个Job静默；相应verified/native认证标志保持false。合作式lease不能代替原生执行真实性。

正常退出要求exact int的exit code 0、无resource errors、无observation error，并且stop markers恰为direct_child_exit_observed。布尔False不能替代退出码；与正常退出矛盾的失败字段会拒绝，即使调用方重算了全部摘要。

从固定输入回放reference并映射共同请求，按规范四臂重建业务候选与actual请求，再回放actual记录并成对提交内存状态。跨小时使用刚重建的前驱，不直接反序列化归档游标。整个hour body（包括publication、arms、results和预算）要求一致。完成小时的子目录集合恰为实际执行的phase；跳过臂不能隐藏额外task root。

## 未完成与证据限制

末尾pending intent全额占用该小时预留，报告pending_unknown，不读取其子任务数据库，不推断零调用、不可行、实际调用次数或资源静默。只允许该pending小时的规范任务目录存在，存在本身不代表已完成执行。

actual unresolved记录可以产生同样的保守halt事务，但其数值失败细节未被完整重放，报告单列unresolved_phase_records及unresolved_numerical_details_replayed=false。selected阶段才计入selected_phase_chains_replayed。观察窗口消费完不等于完整履约或恢复完成，complete_service_certified保持false。source/normal最优性、公共数据语义、末端右删失和正式验收继续依赖各自证据。

## 验证记录

首轮6项通过（48.45秒）。补独立process身份及目录inventory后，修复局部变量覆盖问题，9项通过（117.43秒），含真实连续两小时离线核验、跳过臂却出现task目录、外层重hash的phase/cursor/预算篡改，以及末尾pending intent全额占用且不执行。

独立pre-seal要求进一步收紧child_exited字段一致性，修复后正常前缀及5类联动重hash进程伪造反例6项通过（40.67秒、exit0）；未重复未受影响的两小时执行fixture。git diff --check通过。测试只使用合成数据与pytest目录；读取时明确禁止controller执行入口和native solve。此处核验不提升formal、native执行真实性、完整服务或resume权限。
