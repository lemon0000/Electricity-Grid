# Objective / bound 来源采集开发记录

2026-09-28；DRAFT_NONAUTHORITATIVE。对应 H25 诊断的 1 ULP 界交叉。

实现：`src/solvers/rq2_objective_provenance_v1.py`。
在 direct solver 尚未关闭、显式 load 完成后调用 `capture_direct`，不执行求解或加载。
旧 normal runner、adapter、验收谓词和已完成 attempt 保持原样；该模块尚未接入 successor runner。

采集内容：原生 Status/SolCount/ModelSense、ObjVal/ObjBound/ObjBoundC/Runtime；
Pyomo termination/status/lower/upper；loaded canonical 目标；原生及 Pyomo 的线性目标项、
常数、binary64 hex 和 Fraction 精确点积。全部 referenced 变量逐项比对 native X 与 loaded 值。
缺少 incumbent、非有限数值、赋值不一致及非线性/非最小化目标会拒绝。
报告绑定 collector SHA 和现有 adapter identity；调用方仍须绑定拥有的 solve、结构、来源和归档。
采集器本身不提供执行真实性认证，也不证明输入模型在求解前后未变。

本地 Pyomo 6.10.1 `GurobiDirect._postsolve` 的可复核映射是：

| 模型 | Pyomo lower | Pyomo upper |
|---|---|---|
| MIP 最小化 | ObjBound | ObjVal |
| 连续模型最小化 | ObjVal | ObjVal |

因此不能笼统把所有 Pyomo lower 都解释为独立对偶界。报告同时保存原生字段和实际映射，
缺失的原生属性明确标记 unavailable。`compare_channels` 只作精确比较，保留交叉和差值，
不加 epsilon、不剪裁 LB、不用 optimal 终态替代数学证明。
原生与 canonical 精确目标一致也不等于赋值精确可行；运行资源及公开数据真实性由原有链路负责。

验证命令：

```text
D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_rq2_objective_provenance_v1.py tests/test_rq2_scale_normal_v1.py
```

组合 57 项通过（44.26s）。后续增加原生目标项、目标篡改反例及合成 TIME_LIMIT 原生通道，
最终新测试 12 项通过（1.48s）。6 个实际 LP/MIP 小例分别为正、负、零目标，每次 native 上限 1 秒。
TIME_LIMIT 是明确注入的测试通道，不是实际长运行观测；还覆盖 1 ULP 正/负/零交叉、
非有限值、Pyomo 上界改变、目标改变及 loaded assignment 改变。
首次测试的 3 个失败来自 LP 夹具 `domain=None` 被解释为 Any；改为 Reals 后通过。

独立限定预审前两次调用返回 model capacity，第三次已执行并提出 findings。
据此新增按变量聚合、去零、排序的精确目标代数 inventory，区分点值相等和表达式相等；
保存 Pyomo solution status，并显式比较原生/包装层 optimal 声明。
该 consistency 字段只检查 optimal 声明，不验证全部终态映射。
原生可选属性的已知 DATA_NOT_AVAILABLE 错误明确记录缺失，其余异常继续抛出。
新反例包括系数与常数抵消后点值相同但代数不同、重复项聚合、solver/solution/termination
各状态改变、缺失属性及非预期错误传播。最终新测试 16 项通过（1.70s）。
独立限定复核确认 findings 1–3 闭合，无新增实质问题；这是 collector 草稿的限定复核，非 official verdict。
接入 H25 successor 前，调用方还必须声明完整 payload 上限并绑定持久归档；当前接口不提供资源门。

已按既有 inventory 逐项核对已完成 H25 attempt 的 14 个文件，bytes/hash 全部保持一致；
`git diff --check` 通过。没有修改旧结果、配置、runner 或 native 接口。

下一项：独立预审完成后，将采集器接入版本化 successor 的一次求解与独立归档回放。
旧 H25 没有保存原生目标通道，不能通过零 solver 重放补造。只有取得相应通道及赋值/结构绑定后，
才能区分导出差异、目标求值差异和数值可行性影响，并决定可证明的界处理。
完整连续服务合同、全支持计算路线、训练容量与 holdout 证书另有开放条件；本项不打开正式实验门。
