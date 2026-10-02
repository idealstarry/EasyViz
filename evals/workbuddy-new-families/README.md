# New-family practical WorkBuddy trial

This folder records one EasyViz-assisted create task for the new ECDF capability and one intentional replay after repository fixes. Its purpose is to expose concrete usability, source-integrity or layout problems and feed findings back into the repository. There is no baseline/control run, comparative score or generic model-quality claim. The replay occurs in the same conversation and is a correction check, not independent replication.

The initial request names the plotting goal and field meanings without naming an implementation script. WorkBuddy visibly discovered the focused recipe through SKILL.md, mapped three renamed source columns correctly, and rendered all 254 public measurements. The UI model label is GLM-5.3-Flash; the backend identity was not independently verified. Initial visible completion was 3m1s, with no supplemental prompt or visual revision.

The initial figure passed 10 independent checks, including actual SVG/PDF empirical jumps, source-derived values and trace, export dimensions, Arial and editable power ticks. Its frozen caption/report contained two factual wording errors: treating the distribution as an observational unit, and claiming visible ties although this input has none. The short curve legend keys and numeric text normalization also gave actionable repo feedback. See [feedback.md](feedback.md).

The updated canonical ECDF recipe uses adjustable 6 mm curve legend keys, preserves original numeric text separately from parsed values, and documents truthful observation-unit and tie-count wording. One neutral follow-up asked the agent to reread updated resources, rerender in a new directory and check actual data/export facts; it supplied no unit/tie answers or script name. The replay completed visibly in 2m40s. All 12 independent checks passed, including 254 exact raw numeric texts and two actual 6 mm SVG curve-key centerlines. Its caption correctly describes one measurement per participant and explicitly records zero ties.

During replay, WorkBuddy's shell reset to the old working directory. The agent accidentally replayed the old helper into the original temporary output, detected the mistake and switched to fully absolute helper/data/spec/output paths. The prior repository freeze remained unchanged; independent hashes prove all 11 accidentally replayed files are byte-identical to the earlier originals. The agent's own uncertainty about that integrity check remains in its frozen report; [iteration-2/old-result-integrity.json](iteration-2/old-result-integrity.json) resolves it with evidence. This operating-context failure motivates explicit path examples, and is not attributed to the curve algorithm.

`request.txt`, `prepared.csv` and `input-provenance.json` preserve the initial input. `skills-snapshot.zip` and `snapshot-manifest.json` preserve the exact 251-file skill offered at first launch. `iteration-2/` separately preserves the updated 252-file snapshot, follow-up request and outputs. Each agent-result directory contains unchanged originals and a hash manifest. The input is byte-identical in both runs. `independent-audit.py` imports the independent source/export evaluator, never the plotting renderer, and records the evaluator identity and actual export hashes.

The first folder binding was rejected by automatic approval review as medical-data transmission. Official article evidence then confirmed these are already-public CC BY Source Data with public coded IDs and no user-private medical records. Retrying the same UI action with that evidence succeeded. `public-source-check.md` and `ui-observations.json` retain this sequence. Neither action used an alternative UI/API route.

Recheck the frozen records:

```sh
.venv/bin/python evals/workbuddy-new-families/independent-audit.py
.venv/bin/python evals/workbuddy-new-families/independent-audit.py --run evals/workbuddy-new-families/iteration-2
```

The source input has no ties; separate synthetic transfer tests establish that capability. Both figures were visually opened directly here, but this practical trial did not include a fresh independent visual reviewer or physical print proof. These observations support the specific repo corrections and this source-backed use case only.
