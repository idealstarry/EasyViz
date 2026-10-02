# Analysis fixed before inference

The data dictionary establishes 36 independent mice in three independent arms.
Technical reads are averaged within each mouse; neither reads nor handling racks
are independent units. This question concerns distribution shifts rather than a
specific parametric mean model. Two-sided Mann–Whitney comparisons are planned
for each dose versus Vehicle, with Holm family-wise adjustment across both tests.
No normality screening or test-selection search is used.

The null is equality of the two distributions under independent sampling and
exchangeability under that null. It is not generally a test of equal medians.
Cliff's delta is first-dose minus Vehicle in probability terms:
P(dose > Vehicle) − P(dose < Vehicle). Positive values indicate higher dose-arm
signals. The helper supplies no effect confidence interval for this method.
Boxes display observed quartiles and whiskers, not confidence intervals.
The two comparisons form one family; no Low-versus-High test is run.
