# 绘图检查记录（真实执行结果）

日期：2026-10-02。脚本：`plot_panel.py`（工作目录内，可直接重跑：
`/Users/starry/Desktop/EasyViz/.venv/bin/python plot_panel.py`）。
输入仅 `prepared.csv`；未读取任何 EasyViz 仓库/skill/脚本或网络资源。

## 已验证项目

- **画布尺寸**：140×100 mm（5.5118×3.9370 in）；PNG 实测 1653×1179 px @300 dpi
  （matplotlib 像素取整，等效尺寸正确）。sips 实测通过。
- **字体**：Arial 8 pt。运行环境字体列表确认 Arial 存在；SVG 中 23 个 `<text>`
  元素、`font-family: 'Arial'`，文字可编辑（`svg.fonttype='none'`）。
- **PDF**：`/FontFile2`（TrueType 嵌入，fonttype 42）存在，字体名 Arial 出现。
- **数据完整性**：11 行全部绘制（脚本输出 rows plotted: 11）；
  3 个缺失组合留空且未补值、未删行：
  Background suppression/Batch B、Temperature sensitivity/Batch A、Storage response/Batch B。
- **类别顺序**：按首次出现，自上而下 Signal recovery → Low-input → Long-run drift →
  Background suppression → Temperature sensitivity → Operator transfer → Storage response
  （第一轮渲染时曾上下颠倒，已修正并在第二轮确认）。
- **空心/实心**：区间包含 1 → 空心，共 6 个点（Signal A/B、Long-run B、
  Operator A/B、Storage A）；不包含 → 实心，共 5 个点。与 CSV 逐行核对一致。
- **坐标轴**：log 横轴，主刻度 0.2/0.5/1/2/5，参考虚线在 x=1；次刻度未标注
  （第一轮曾出现次刻度科学计数标签与主标签重叠，已用 NullFormatter 修复）。
- **区间使用**：Lower 95/Upper 95 原样绘制端点帽，未重算、未拟合、未加权、未做检验。
- **图例**：置于绘图区上方，两列四项（Batch A/B 颜色 + 含 1 空心/不含 1 实心），
  不与数据重叠；无标题、无副标题、无脚注。
- **视觉迭代**：共两轮。第 1 轮修正类别顺序、次刻度标签、图例遮挡、3 行标签；
  第 2 轮收紧右侧留白（xlim 0.13–8.0）、点标记 3.6→4.0 pt。两轮均实际查看 PNG。

## 实际设置

见 `output/settings.json`（画布、DPI、字体、颜色、xlim、刻度、填充规则、
类别顺序、缺失组合清单）。绘图数据（含每行空心标志与缺失状态）见
`output/plot_data.csv`。

## 尚存问题 / 未检查项目

- **未检查**：PDF/SVG 在 Illustrator/Inkscape 中的实际打开效果（本环境无 GUI
  矢量编辑器，仅验证了 SVG `<text>` 结构与 PDF 字体对象）。
- **未检查**：打印机/期刊 specific 的线条最小宽度要求（当前线宽 1.1 pt、
  点径 4.0 pt，按 8 pt 字号比例目测协调）。
- 空心点图例示意使用黑色描边，与图中彩色描边空心点不完全一致（图例表达的是
  填充语义，属有意简化；如需可改为双示例图例）。
- 空行（缺失组合）未加任何占位符或"no data"标注，仅留白，符合任务要求但
  读者需依赖图注理解。
