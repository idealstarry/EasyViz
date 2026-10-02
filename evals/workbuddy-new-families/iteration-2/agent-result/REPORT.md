# EasyViz ECDF 修正验证报告（iteration-2，Urschel 数据）

日期：2026-10-02 · 工作目录：/private/tmp/easyviz-workbuddy-new-families/ecdf/iteration-2

## 更新内容与本轮选用

与首轮快照逐文件 diff 确认，本次更新涉及：`references/ecdf-plot.md`、`scripts/ecdf_plot.py`（以及 paired/replicate 相关资源和 examples、literature-source-data，与本图无关）。对本图生效的三项更新：

1. **观察单元语义**（参考文档新增）：观察单元是单次测量；组/时间点标签只是合并观测的标签，不是观察单元。已据此改写 caption。
2. **ECDF 图例线键默认宽 6 mm**（脚本 + 文档）：曲线键需可读的线段而非共享的圆形标记足迹；`settings.json` 新增 `resolved_legends` 记录。
3. **精确值文本保留**：绘图数据新增 `_easyviz_source_value_text` 列，保留 CSV 中数值的原始拼写，防止数值序列化悄悄改写十进制形式。
4. **并列值（ties）核查指引**（文档新增）：宣称"重复值跳跃"前须先核查数据；并列值支持不等于本数据集存在并列值。

## 实际输入核验

- `prepared.csv` 与首轮逐字相同（`diff` 逐行比较，IDENTICAL）：254 行、127 位受试者、Before/After 各 127 条。
- 实际计数核查：每个时间点 127 个值全部唯一，**无并列值**（`cumulative-data.csv` 中 254 行 jump_count 全为 1；qa 源审计 `unique_values=127`）。caption 已按此事实改写，不再暗示图中出现并列值跳跃。

## 规格（与首轮一致）

`ecdf-spec.json`：ecdf；value=IgG_BAU_ml、group=时间点、unit=受试者；对数横轴 10–100000，主刻度 10¹–10⁵（power10）；纵轴 0–1；Before #5278A8、After #C2764E；105×85 mm、Arial 8 pt、300 dpi；pdf/svg/png；线宽 0.8 pt；无网格、无标题、无脚注；无检验/平滑/区间（stats.json 记录）。

## 实际检查（本次真实运行）

- 脚本 QA：status=pass，254/254 观测源-图审计通过；无文本裁切、无刻度重叠、无缺失字形。
- 尺寸：PNG 1240×1004 px = 105×85 mm @300 dpi；PDF 105×85 mm；SVG text_preserved=true、14 个可编辑 `<text>`、font-family Arial。
- 更新特性验证：
  - `resolved_legends` 已写入 settings.json：`{"position": "bottom", "key_width_mm": 6.0}`；
  - `_easyviz_source_value_text` 存在于 plotting-data.csv（首行 3356.73，与解析值一致）；
  - 图例为 bottom 线形键、6 mm 键宽、8 pt；实测查看 PNG，键线段明显比首轮（1.5 mm 级）更长更可读，位置与留白合适。
- 视觉检查：实际查看渲染 PNG。两曲线阶梯清晰、幂形式主刻度正确、图例无重叠；Before 曲线约 4×10³ 达 1 后的水平延尾为显示延拓。
- 无需修改轮次（0 次，限额内）。

## 执行事故与影响评估（如实记录）

- **事故**：一次中间运行因 shell 工作目录被重置回旧目录，用**旧脚本 + 旧目录输入**在旧目录 `output/` 内重新生成了首轮的 panel 与审计文件（时间戳 16:21），违反"不改首轮结果"的字面要求。
- **影响评估**：所用脚本与输入和首轮完全相同，且经核查导出的 PDF 无 CreationDate、SVG 无日期元数据，导出为确定性输出，故重新生成的文件在内容上应与首轮一致；`ecdf-spec.json`、输入 CSV、settings/qa 记录的哈希均与首轮相同。**但首轮原始字节已不可恢复，无法做逐字节等值证明——此项明确标记为未验证。**首轮的 caption.md 与 REPORT.md 未被触碰。
- **防范**：本轮最终成图改用全绝对路径运行，产物确认落在 `iteration-2/output/`。

## 剩余限制与未检查项

- **未做独立图像评审**（未调用 easyviz-figure-reviewer；任务限定不调用其他 Agent），视觉评审非独立。
- **未验证 Arial 嵌入**：SVG 仅以 font-family 引用 Arial，组装系统需安装该字体。
- 事故中旧目录文件的逐字节等值性未验证（见上）。
- 公开来源沿用 input-provenance.json 与 public-source-check.md 记录，未重新联网核验（离线限定）。
- 更新涉及的 paired/replicate 资源与本图无关，未审阅其改动细节（仅确认文件有差异）。

## 复现方式

```sh
/Users/starry/Desktop/EasyViz/.venv/bin/python \
  /private/tmp/easyviz-workbuddy-new-families/ecdf/iteration-2/skills/easyviz/scripts/ecdf_plot.py \
  --data /private/tmp/easyviz-workbuddy-new-families/ecdf/iteration-2/prepared.csv \
  --spec /private/tmp/easyviz-workbuddy-new-families/ecdf/iteration-2/ecdf-spec.json \
  --out /private/tmp/easyviz-workbuddy-new-families/ecdf/iteration-2/output
```
