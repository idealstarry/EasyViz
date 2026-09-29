# Adopted plot specification

Track: `reproduce`; input mode: `image-data`. Inputs are the supplied source table, reference image and request, copied beside the script. No author code was supplied, sought or accessed.

Required: one 180 × 125 mm panel; Arial 8 pt for all visible text; PDF, SVG and PNG; no overall title or explanatory prose. Preserve first appearance order for all eight populations and eight markers. Circle area is exactly proportional to detected_fraction on 0–1; color uses the supplied mean_scaled_expression on a fixed linear −2 to 2 scale centered at zero. No aggregation, inference from image values, row sorting or rescaling of source expression.

Missing semantics: explicitly complete the 8 × 8 grid in plotting data, preserving a `measured` flag. The three absent pairs are small gray x marks, decoded as Not measured. Two measured detection fractions of zero have zero circle area and therefore a blank cell; a blank outlined key box labeled 0 (measured) identifies this state. No nonzero size is added to measured zero. Their supplied expression remains in plotting data, even though an area-zero mark cannot show its color.

Preferred reference structure: rows and columns remain in the reference orientation; vertical marker labels; borderless circular marks; no frame/grid; pale horizontal rules after the same named row pairs (Nonclassical monocytes and Inflammatory macrophages). New populations are kept in their requested final rows without invented group names, separators or annotations. Keep a vertical blue–white–pink colorbar to the right and a compact horizontal size guide beneath the matrix. Existing original rows remain unchanged in order.

Flexible: physical margins and guide positions are adapted for eight rows, long population names, and the two missingness keys. Use a shared maximum dot area chosen to fit the fixed physical layout; the same area transform applies to plotted dots and all quantitative guide circles. Marker outline policy is borderless. The missing x and outlined blank decoding swatch are separate presence indicators, not quantitative circular marks.

Statistical layers: none requested or calculated. Upstream sample definitions and scaling method are unknown and remain caveats in the separate caption.

Palette: estimate visible blue/near-white/pink colors from the supplied image only; save actual chosen hex colors and normalization in figure-settings.json. Reference typography cannot be recovered from pixels; the user supplies Arial 8 pt explicitly. Reference dimensions and absolute marker area are unknown, so this is a structural reproduction using new data rather than an exact pixel replication.

Actual measurements, palette, font path, mark sizes, guide bounds and export results will be recorded by the final rendering script. The main matrix must remain visually primary, and all required labels must remain inside the canvas.
