# Source data dictionary

The source is the complete author-released `Figure_2f.txt` table. Each of its 48 rows is a combination of one myeloid subtype and one adipose depot. The paper caption identifies Figure 2f as the myeloid counterpart of Figure 2b, which displays subtype proportions by depot.

| Original column | Interpretation and use |
|---|---|
| `seurat_clusters` | Published subtype number 0–15; mapped to `myC0`, `myC01`, … `myC15` in labels |
| `tissue` | `sc` = subcutaneous; `om` = omental; `pvat` = perivascular (displayed as `pv`) |
| `n` | Source object count for that subtype and depot; used for dot area and pooled totals |
| `percent` | `100 × n / sum(n within the same depot)`; verified numerically before plotting |
| `percent2` | Author auxiliary percentage; retained but not interpreted or plotted |
| `group` | Author labels A–D; retained but not used as display-group definitions |
| `n_cluster` | Total count of that subtype across depots; verified against the summed source counts |
| `percent_cluster` | Author auxiliary subtype percentage; retained but not plotted |
| `percent_cluster2` | Author auxiliary transformed percentage; retained but not interpreted or plotted |

The plotting script adds `depot_total`, `within_depot_percent`, and `pooled_subtype_n` in `output/plotted-data.csv`. These are simple descriptive transformations of the provided counts. The original CSV retains the exact source numeric strings.

## Annotation provenance

The `annotations.json` file is transcribed from Figure 2d on PDF page 5. It supplies the paper's subtype labels and two marker examples per subtype. Marker text follows the publication's labels, which include common aliases and combined labels; it is not a new standardized gene-identifier table.

The display groups organize the published descriptors: M2 macrophages, other macrophages (LAM, M1/M2-like, MMe, and Mox), monocytes, and dendritic cells. Grouping is for reading the figure and does not replace the source clustering or perform another analysis.

LAM: lipid-associated macrophages. MMe: metabolic-regulated macrophages. Mox: redox-regulatory metabolic macrophages. Mo: monocytes. DC2: dendritic cells of subtype 2. These definitions follow Figure 2's caption and accompanying text.
