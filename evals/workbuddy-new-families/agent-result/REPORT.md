# EasyViz ECDF 试跑报告（Urschel et al. 数据）

日期：2026-10-02 · 工作目录：/private/tmp/easyviz-workbuddy-new-families/ecdf

## EasyViz 资源的选用

- 入口：`skills/easyviz/SKILL.md`。任务为从数据新建指定图型，走 **create** 轨道；图型已在需求中定为经验累计分布，故直接使用共享资源 **Empirical cumulative distributions**（`references/ecdf-plot.md`）及其脚本 `scripts/ecdf_plot.py`。
- 未使用 palette 目录：需求显式给出 Before `#5278A8` / After `#C2764E`，脚本对显式颜色不依赖调色板。
- 图例布局由 `legend_layout.py` / `auto_layout.py` 自动完成（脚本内部调用），无需手工设置边距。
- 未使用 reproduce 轨道、参考图读取器（easyviz-reference-reader）与 figure-reviewer：本任务无参考图像。

## 规格与设置（实际采用）

- 图型 `ecdf`；`value=IgG_BAU_ml`，`group=时间点`，`unit=受试者`（脚本校验每位受试者在每个时间点恰好一条记录，254 行全部通过，未静默丢弃）。
- 画布 105×85 mm，Arial 8 pt，300 dpi，导出 pdf/svg/png；对数横轴 10–100000，主刻度 10¹–10⁵（`x_tick_format: "power10"`），纵轴累计比例 0–1；线宽 0.8 pt，无网格，无标题/副标题/脚注。
- 曲线为右连续经验阶梯 F(x)=count(≤x)/127，保留重复值跳跃；无分箱、平滑、检验或区间（`stats.json` 明确记录）。
- 规格文件：`ecdf-spec.json`；输出与审计文件均在 `output/`（plotting-data.csv 保留全部 254 行及 source_cell 等来源列；cumulative-data.csv 含组内排序值、跳跃数、分母 127 与来源行号；settings.json 含输入/规格/脚本哈希与运行环境）。

## 实际执行的检查

1. 脚本 QA（`qa.json`）：status=pass；254/254 观测经源-图审计（独立重读 CSV 复核计数与并列值）；无文本裁切、无刻度重叠、无缺失字形；图例占绘图区 1.3%，无重叠告警。
2. 尺寸复核：PNG 1240×1004 px = 105×85 mm @300 dpi；PDF 页面 105×85 mm；SVG `text_preserved: true`，含 14 个可编辑 `<text>` 元素，字体引用 Arial。
3. 视觉检查：实际查看渲染 PNG。两条阶梯曲线清晰可分，阶梯与重复值跳跃可见；主刻度正确显示 10¹–10⁵ 幂形式；图例（Before/After，线形键）位于图下方，留白协调；Before 曲线约在 4×10³ 达 1 后的水平延尾为显示延拓，未添加观测。

## 修改轮次

首轮渲染即通过全部技术与视觉检查，未触发修改（限额两轮内使用 0 次）。

## 遇到的问题

- 无阻塞性问题。唯一需要判断的点：脚本自动图例位置候选含 right/bottom/top，本次自动选择 bottom（绘图区面积最大），经视觉确认合适。

## 剩余限制与未检查项

- **未做独立图像评审**：视觉检查由本会话直接查看 PNG 完成，未调用 easyviz-figure-reviewer 子技能（任务限定不调用其他 Agent），评审非独立。
- **未验证系统字体渲染之外的 Arial 嵌入**：SVG 以 font-family 引用 Arial 而非嵌入字体文件，组装系统需装有 Arial（qa.json 已注明）。
- 统计层面：脚本不建立实验独立性、不做配对效应推断；感染分组（64/63）仅合并汇总，未按组分层绘图——这是需求规定，非脚本限制。
- 公开来源核查引用既有 `input-provenance.json` 与 `public-source-check.md` 记录，本次未重新联网核验（任务限定离线）。

## 复现方式

```sh
/Users/starry/Desktop/EasyViz/.venv/bin/python skills/easyviz/scripts/ecdf_plot.py \
  --data prepared.csv --spec ecdf-spec.json --out output
```
