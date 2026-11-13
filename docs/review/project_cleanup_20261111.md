# 项目整理记录（2026-11-11）

整理后的入口为根目录[README](../../README.md)。当前双语介绍、计划、图件和规格分别有精简导航；旧论文介绍索引及图件说明覆盖前已备份，原日期信息可追溯。

## 已执行

- 归档3份不再用于当前主线、且在所扫描源码及文档范围内没有按文件名入链的候选／方案评估笔记：`heterogeneous_recovery_mechanism_candidate_20261109.md`、`scheme_a_novelty_assessment_20261109.md`、`scheme_a_ukpn_control_mapping_20261110.md`。这不表示其研究内容已失效或已被否定。
- 归档旧 `article_*`、`scheme_a_*` 图件的12张PNG导出件；SVG、PDF、原素材、脚本与历史检查记录保留。历史检查清单中的PNG现需从归档读取；脚本重建时会重新生成原路径。
- 迁移11处Python缓存目录及pytest缓存，共97个缓存文件。自动审批拒绝了永久删除缓存的命令，随后采用可恢复迁移，未永久删除。
- 重写根目录、论文材料、图件的导航；新增计划和规格目录README。旧导航备份在归档的 `navigation_before/`。

文档及图件共15项、25,668,113字节；缓存97项、2,180,968字节。全部移动前后SHA-256一致。本次整理减少工作目录杂项，不释放磁盘总空间。

## 归档与恢复

归档目录为 `D:/CUHKSZ/Research Project/electricity-grid-maintenance-archive/20261111_project_cleanup/`。

- `manifest.json`：15项旧文档及PNG的原路径、归档路径、大小与SHA-256。
- `cache_manifest.json`：97个缓存文件的同类记录；归档路径在 `caches/` 内。
- `navigation_before/`：覆盖前的README原字节。

恢复时按清单中的原路径移回；原路径已存在时先比较，不覆盖较新工作。已归档笔记的相对链接仍按清单中的原始目录解释，如需继续编辑，先恢复到原位置。

## 保留边界与核查

扫描了 `docs/plan/`、`docs/model_spec/`、`paper/` 及源码、配置、测试中的文档引用。仅“没有按文件名引用”不能证明某个合同可删除，因此历史规格、scope、冻结配置、失败探针与阴性结果继续保留。数据、结果、检查点、源代码、测试源码、三个repair备份及原日志保持原位。

导航本地链接、归档哈希和目标不存在检查见[机器记录](project_cleanup_20261111.json)。本次未运行实验，也未提交或推送Git。
