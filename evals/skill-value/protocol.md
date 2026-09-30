# First source-backed EasyViz value pilot

Frozen 2026-09-30, before either arm rendered. This is an exploratory paired case comparison, not an effectiveness estimate or statistical test. It is outside plugin installation and runtime.

## Comparison

Two agents with the same inherited default model configuration and no model override receive the same request, sources, 90 × 70 mm canvas, Arial 8 pt typography, formats and delivery requirements. One agent completes both tasks without reading EasyViz or any other plotting Skill. The other reads canonical EasyViz and relevant create/layout/review references, then uses a custom renderer. It does not reuse examples or the changing core renderer. The contrast therefore exercises Skill guidance beyond a deliberately competent prompt, not the quality of packaged renderer features.

Each arm works in its own folder and must not inspect the other arm. Each task preserves the first complete rendering in `initial/` and the delivered version in `final/`. Own-author visual repairs before submission are permitted and recorded. Neither agent receives independent reviewer feedback before its final output is frozen. A separate agent sees anonymously labeled A/B final panels and captions, the identical reading tasks and output specification, without access to scripts, arms, previous repo examples or the treatment key. One comparison reverses A/B mapping to reduce stable-label bias. Numerical and physical-size verification is conducted separately after rendering. Reviewer preference is not a scientific-value check.

The baseline and EasyViz receive exactly `required-spec.md`, `inputs/SOURCES.md`, the same two CSVs and `inputs/provenance.json`. The EasyViz receives the additional canonical Skill/reference allowance; baseline receives an explicit instruction not to read plotting Skills or repo examples/tests/scripts. Neither is given a preferred answer, a prescribed chart/palette, a hypothesis that EasyViz is better, or expected failure traps.

## Data

The two domains—NOAA annual atmospheric CO2 and USGS January 2024 earthquake events—had no matching examples in the repository when selected. They are real official public inputs, with field meanings and public-domain distribution conditions linked in `inputs/SOURCES.md`. Full downloaded bodies stay in a temporary folder; only necessary observations/fields and provenance/hashes are committed. This establishes unfamiliarity to this repository, not to the pretrained model: NOAA CO2 is a well-known scientific record. The month and source restrictions are fixed before rendering; task selection was not changed after observing outputs.

## Recorded checks

- Source value fidelity: full data coverage, IDs/year order, units, transformations and uncertainty endpoints/meaning.
- Export fidelity: PNG dimensions/dpi, PDF media box, SVG view box/physical size and 8 pt actual font metadata.
- Independent visual reading: preference or tie, task answers available from panel/caption, clipping/overlap/visibility failures, uncertainty and metadata caveats.
- First-to-final changes: actual author repairs and their scope, separate from reviewer feedback.
- Work: UTC start/end, wall-clock time and observed tool calls from each arm, files read, token accounting if the tooling supplies it.

## Uncontrolled factors and claims excluded

Token limits and sampling seeds cannot be imposed or recovered from the collaboration tools in this run; no equal-budget claim is made. Token usage is unavailable unless an arm obtains genuine tool-backed accounting. Two agents draw both tasks; tasks within one arm are not independent replicates, and author ability/stochastic variation remains confounded with Skill use. Parallel work may share machine load; wall-clock differences are descriptive only. One independent reviewer with two cases provides no population-level preference estimate. Both arms already receive strong source and export instructions, so a tie can be informative but cannot prove the Skill is unnecessary. A preferred rendering can support only that case's reader task. Broad quality, speed, error-rate or generalization advantages require repeated randomized runs, more domains and reviewers, and controlled budgets.

Environment note: the bundled artifact Python initially suggested to both agents does not include Matplotlib. Both received the same correction to use the repository's existing `.venv/bin/python` (Matplotlib 3.11.1, pandas 3.0.5, Pillow and pypdf). Their environment probes remain in their reported times/tool counts. No dependency was installed for the pilot.

Treatment context limitation: the canonical Skill was undergoing the authorized repository update while the authors worked. The pre-dispatch `frozen-hashes.json` Skill digest differs from the EasyViz author's saved `guidance-hashes.json` digest; the latter includes actual text snapshots retained during that arm. The pilot therefore identifies guidance by its recorded snapshot and does not claim to isolate one released plugin version. The EasyViz author also read the shared memory registry, whose panel-text conventions were already explicit in the common task. Neither author read existing plotting examples/tests, and neither used the changing core renderer. These extra-context differences remain part of the exploratory arm comparison.
