# Reference observations

Inspected input: `reference.png`, copied from `/Users/starry/Desktop/EasyViz/evals/release-qa/inputs/reproduce/reference.png`. Whole image, 1342 × 909 px. No caption, methods or author code supplied or accessed. The main agent opened the actual image with `view_image`. Independent reader delegation was attempted before implementation selection; it failed with `agent thread limit reached`, so this is an explicitly non-independent reading.

| Property | Description | Evidence state | Source | Uncertainty |
|---|---|---|---|---|
| Chart | Rectangular dot matrix, six population rows and eight marker columns | observed | Whole reference | None material |
| Row labels | Classical monocytes; Nonclassical monocytes; Resident macrophages; Inflammatory macrophages; DC2; Activated DC, top to bottom | observed | Left side | None material |
| Column labels | LYZ, S100A8, FCGR3A, HLA-DRA, C1QC, APOE, IL1B, CXCL10, left to right; vertical text | observed | Bottom axis | None material |
| Area | Variable circular dot areas and a bottom key labeled Detected (%) with 25, 50 and 100 | observed | Matrix and lower key | Image alone does not establish exact formula |
| Color | Blue low, near-white middle, pink high; right colorbar labeled Scaled expression with −2, 0, 2 | observed | Matrix and right colorbar | Exact original palette constants unknown |
| Grouping | Thin pale horizontal lines after Nonclassical monocytes and Inflammatory macrophages | observed | Across matrix | No explicit group names supplied |
| Marks | Filled circular dots, no visible black edges | observed | Matrix | Subpixel edge details cannot establish code settings |
| Axes | No outer frame, tick marks or matrix grid; black row and column labels | observed | Whole reference | None material |
| Typography | Plain sans serif; similar label and legend sizes | observed | Whole reference | Exact font, pt size, dpi and physical size unknown |
| Plot geometry | Approximate data field box [0.350, 0.060, 0.850, 0.720] in normalized top-left coordinates | observed | Whole reference | Approximate bounds, includes row/column margins |
| Colorbar geometry | Body approximately [0.900, 0.270, 0.915, 0.620]; full key/ticks/label envelope approximately [0.900, 0.260, 0.982, 0.636] | observed | Right guide | Approximate image measurement |
| Size guide geometry | Full bottom guide approximately [0.580, 0.902, 0.870, 0.980]; one horizontal row below centered heading | observed | Lower right | Approximate image measurement |
| Proportions | Colorbar body roughly half the matrix height; size key dot diameters comparable to plotted dots | observed | Guides and matrix | Relative appearance only |
| Statistics | No visible intervals, p values or fit | observed | Whole reference | Upstream data derivation, independent unit and uncertainty unknown |
| Missingness | Blank or very small locations are visible, but their scientific meaning is not established | unknown | Matrix | Cannot infer absent-vs-zero rules from pixels |

Required data meanings are the population, marker, detected fraction and scaled expression. User request establishes exact encodings and missingness semantics. No numerical values are inferred from image dots.
