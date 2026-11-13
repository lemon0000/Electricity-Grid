# 当前论文材料（2026-11-11）

主线：**计及任务补做期限、随达产状态变化的智算中心分阶段鲁棒接入设计。**

| 语言 | 正文 | 阅读PDF |
|---|---|---|
| 中文 | [项目介绍](project_introduction.md) | [6页PDF](project_introduction.pdf) |
| English | [Introduction](project_introduction_en.md) | [7-page PDF](project_introduction_en.pdf) |

两版包含摘要、引言、问题定义、初步可行性证据与12条一致参考文献。Firm需求与期限敏感性两幅图取自当前demo。图件见[图件目录](../figures/README.md)，正文与PDF指纹见[渲染清单](render_manifest.json)。

完整demo位于相邻 [ramp_flex_robust/paper](../../../ramp_flex_robust/paper/)，可行性结论见[RESULTS_complete_v1.md](../../../ramp_flex_robust/RESULTS_complete_v1.md)。该目录不属于本仓库Git范围。

重建当前两版PDF：

```powershell
python paper/render_current_drafts.py
```

旧草稿、旧同步检查与重复素材已按2026-11-11用户要求删除，[删除清单](../../docs/review/drafts_deleted_20261111.json)记录原路径、大小与指纹。历史规格、交接与审计中提及这些旧路径时，应按其原日期及Git版本追溯。