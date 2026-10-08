# 固定RTS来源到连续normal输入的开发适配

日期：2026-09-20。状态：DRAFT_NONAUTHORITATIVE。

`source_normal.py`复用现有ContinuousNormalInputs和normal审计核，不新增调度约束。
调用方必须显式提供完整request、initial、carry与时钟解释。适配器验证固定RTS SHA256SUMS自身哈希和全部文件，
加载数据后再核一次来源，要求carry来源哈希等于该manifest，将连续zero-based源索引逐项映射为one-based模型索引。
request里的时钟、需求、availability及initial/carry由原验证器对照，任何不一致都拒绝，不静默更正。

输入身份绑定原索引、源manifest、完整normal输入及其依赖、适配器源码。
`validate_source_assembly`用当前源重新组装，并严格核对三个built-in lowercase SHA256字段及输入身份；
下游应使用它返回的重建对象。普通dataclass不是owned求解见证或认证，不能据此发布normal plan。
源加载前后校验可发现普通并发修改，不提供恶意ABA防护或文件写锁。

RTS文件完整性不认证调用方的split、trajectory、seed或incoming history。
本层未绑定旧power-block manifest，也没有生成完整业务/事故episode输入；这些仍是后续来源拼接义务。
尤其不能把旧free-boundary反推初态当作已验证continuous carry。

## 可重算H=25构模记录

命令从仓库根运行：

```powershell
D:/Miniconda3/envs/compute/python.exe -B -m experiments.audit_rq2_source_normal_build_v1 --source-root data/raw/rts_gmlc/v0.2.3/upstream --output results/tables/rq2_continuous_source_scale_audit_v1_non_authoritative/build_h25_source_bound_non_authoritative.json
```

输出只能create-only写入新`*_non_authoritative.json`；重算时须给另一个新路径，不能覆盖已存在记录。
构模场景是显式开发机制：首25源小时、POI108、250MW正常基线、零业务柔性、热机全关/零出力/已满足minimum-down age。
非热机初始commitment取enabled，出力为0；该初态没有被证明为可行前序网络状态，也不是实际观测。
training标签及seed0仅是此build例的声明，未认证为训练样本或已冻结事故序列。

记录保存完整request、initial、carry、源小时映射、时钟解释、normal/assembly身份、源码及runtime依赖、
实际导入的适配与模型计数模块hash、runner自身hash和模型规模。没有求解、赋值、normal计划或物理可行性判断。
前两份`build_h25_non_authoritative.json`、`build_h25_verified_non_authoritative.json`保留为开发中间记录，
不作为最终源码的验收证据。历史文字计数一致不代表旧输入初态已被重建。

## 验证

24项适配测试覆盖连续/越界/跨日索引、源校验失败、加载期间/之后源漂移、时钟/需求/初态不一致、
carry来源错配、嵌套可变数据、caller copy隔离和自定义摘要比较绕过。
与normal和grid information相关回归共142项通过（17.06s，exit 0）。
测试使用合成源以构造反例；真实来源验收由上述独立build-only命令承担。
计数不涉及solver capacity/license测试。正式规模预算、真实normal assignment、训练容量与策略绑定、
完整恢复与right-censoring以及科学/正式运行门继续开放。

最终真实build命令exit 0，22,275 variables / 28,004 constraints；报告SHA256：
`ebb6b1d33a4742325e92f93550c0799bd1f28c0ca70adde870479f89b0d8070e`。
落盘后核对runner/adapter/模型计数模块hash、0..24到1..25映射、carry边界0、跨午夜timestamp、
solver_calls=0及全部非认证flags，断言通过。`git diff --check`通过。

最终开发源码SHA256：

- source_normal：`3d31668a3aa5c4de1af3e10d1efca7ab75348b27d0befd19620b4868794c00ad`
- test_rq2_source_normal_v1：`615f021c2b7d2fd994fd7c5f0519bc35d12c7c58df0e9a610256a162e0933e3f`
- audit_rq2_source_normal_build_v1：`d45d7494ca2a4f67ed3d776c7d0301f2b83ca9408a120f26d8bf006e7490e441`

独立pre-seal对最终字节复跑24项通过（2.04s），来源错配、摘要伪装和计数模块来源绑定findings已闭合，
限定范围无开放实质finding。独立核对最终JSON哈希、runner/adapter/计数模块及40个依赖源码hash均匹配；
输入边界、时钟、规模与非认证flags复核通过。该预审不构成official verdict、seal或运行授权。
