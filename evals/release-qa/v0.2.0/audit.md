# Independent implementation review

The independent reviewer inspected the changed runtime, tests, installer and actual dot-state PNG. The review found three reproducible problems, all corrected before the final package:

1. Same-version installation compared only manifests. A retained older renderer could be reported as installed. The installer now compares the complete relative file set and each file's SHA-256; a stale-cache regression fails and restores the prior source and catalog.
2. Package structure checks omitted mandatory profile and legend helpers. The validator now requires both helpers and the palette catalog. Source and extracted-ZIP missing-resource regressions reject the incomplete package. Legitimate older source versions can still be backed up and upgraded.
3. A shared continuous scale accepted identical endpoints, which the renderer expanded silently. Named shared scales now require a strictly increasing range; standalone constant-data automatic ranges retain their established behavior.

The final profile tests inspect actual SVG marker dimensions as well as scatter areas. Equal supplied quantities retain equal physical sizes across panels with different dimensions and observed maxima. Category subsets and reorderings retain their shared colors, and profile conflicts fail explicitly.

The dot-state output retains every supplied row and exact observed area, distinguishes explicit unmeasured data from absent coordinates, and uses separate nonquantitative glyphs for measured zero and optional tiny positive values. The actual PNG's state legend, marks and coordinates were readable with no clipping. The reviewer found no additional reproducible blocking defect in this scope.

This is a code and output review. It does not establish arbitrary-data performance, a new interactive desktop model turn, or application UI display.
