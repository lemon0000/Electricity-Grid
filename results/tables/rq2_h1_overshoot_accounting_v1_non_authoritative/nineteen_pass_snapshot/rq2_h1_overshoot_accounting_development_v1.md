# H1 overshoot accounting development v1

状态：DRAFT_NONAUTHORITATIVE / PRE_SEAL_AUDIT；R3；根代理唯一写入。新模块为只读、零native的条件账目reader，不改旧协议、阈值、bridge或resource contract。

旧 normal_h1_full_resource_contract_v3.check_plan 按每次call完整TimeLimit预留，明确non_solver allowance包括solver TimeLimit overshoot，且不假设sharing/early stopping credit。本模块直接复用其validate_work，绑定同一完整canonical stage_order、specification及逐stage specification.json中的declared solver options。每次native duration取已完整science和bridge复核的QPC区间，不能替换为native Runtime属性。声明参数和pinned apply路径不证明native参数getter读回或实际限时，actual_solver_time_limit_authenticated=false。

设同一观察窗口W、每stage实际native区间A_i、预留T_i：
- outside = W - sum(A_i)。
- aggregate overshoot = max(0,sum(A_i)-sum(T_i))，aggregate charge = W-min(sum(A_i),sum(T_i))。这是允许未用额度抵消其他stage超时的描述性下界，不可作为旧non_solver合同解释。
- stagewise overshoot = sum(max(0,A_i-T_i))，stagewise charge = outside + stagewise overshoot。在每call/no-sharing语义下这是候选合同charge；没有取得完整生命周期/observer覆盖前仍不能与2440比较。
- A=[6,0]、T=[5,5]时，aggregate overshoot=0，而stagewise overshoot=1，必须保留差异，不能用总native未超总预留掩盖单stage超时。

预留严格使用Fraction(spec.time_limit_seconds)*10^9，保留binary64实际值的有理数，不转十进制近似、不round/floor。JSON使用规范numerator/denominator整数对。拒bool、缺项、非法数值、非正预留、超过界限向量；所有计算保持精确有理数。

inspect_window以外部固定bridge binding/intent/terminal pins开始，先固定全部受控Job view，调用bridge.inspect完整重验science、时钟和历史anchor，再逐index读取timing及specification/binding。要求declared options和asdict(specification) canonical bytes相等，specification绑定相同stage binding；结尾重读clock/Job/逐文件views和implementation identity。报告绑定stage order、specification、逐stage specification pins、interval vector和legacy resource contract依赖。science后同长度/恢复mtime漂移仍拒绝。

仅返回内存dict，未引入磁盘writer、执行入口、resume或预算PASS。报告编码cap为262144 bytes；这不是全任务存储/内存/时间准入。窗口仍排除bridge confirmation tail、close/caller/全program；完整clock/parent prefix、物理时钟误差、observer separation和legacy non_solver charge均未闭合。所有formal/native/resource/coverage flags保持false。

验证：独立整数/有理数恒等式、早停抵消反例、边界/非整数预留、非法及不完整向量；真实受控短Job搭配synthetic三阶段adapter生成bridge，再fresh账目复核；spec TimeLimit变化和science后的spec/interval漂移拒绝。零真实native。独立R3开发审查与后续official review、具体native授权分开。
