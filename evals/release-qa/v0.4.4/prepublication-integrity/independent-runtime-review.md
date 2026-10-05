# Independent review: source consumption and numeric integrity

**Final decision: no remaining blocking defect found for the reviewed core patch.** The independently reproduced loaded-helper race was repaired and the fresh frozen patch passed the actual execution-boundary probe. This is a runtime/source/number audit, not aesthetic approval or whole-release certification. No authoritative sources or original scientific trial records were changed by this reviewer.

## Final frozen patch and verification

- `skills/easyviz/scripts/render.py`: `05981e39daf33cf71af6d0d421beb678a18076974f2af59cfd53418d932746a8`.
- `skills/easyviz/scripts/figure_elements.py`: `c5107c6fd6db3f889382299af111e4b7c5197a0a1088dca0fc51efaa9c2c6a76`.
- `tests/test_renderer.py`: the exact final hash is recorded in [runtime-probes.json](runtime-probes.json).
- **46 renderer tests, 11 element-map tests and 7 figure-profile tests passed**: 64 focused tests, with exact test/source hashes and captured logs in [runtime-probes.json](runtime-probes.json).
- **24 independent runtime probes passed**, covering ten malformed CSV structures/encodings; BOM/CRLF/multiline byte retention and literal IDs; CSV replacement after parsing and during export; exact CLI-spec byte capture across the parse-to-render race; profile replacement after resolution; binary64-sum and unsigned-integer-sum overflow with actual drawn bar-height inspection; both denominator-excess refusals; nonzero numeric and normalized-fraction underflow; and both extreme-exponent zero spellings.
- The repaired helper loader hashes captured bytes before executing `compile(raw, …)` rather than using independently read/cached code. Its module metadata and sibling paths remain available to portable callers. The top-level renderer compares `compile(captured_bytes, …, dont_inherit=True)` to its actual executing module code before third-party/helper imports; it refuses a timestamp/size-valid stale code cache rather than binding the replacement source to unexecuted geometry. Its digest is then taken from those captured bytes.
- **Two real execution-boundary replacement probes passed**, changing either the helper or renderer file immediately after the real helper executed. The captured digest remains the consumed original digest; both attempts invalidate QA and refuse rendering before any export. See [helper-execution-after.json](helper-execution-after.json) and [probe_helper_execution_fixed.py](probe_helper_execution_fixed.py).
- Independently inspected and executed the real stale-self regression: a copied renderer is compiled, its default point area changes from 12 to 81 while byte count and mtime are preserved, and the ordinary importlib loader selects the old cache. The source/code mismatch now raises before its export API is loaded. Actual relative and absolute portable CLI runs also pass, as do ordinary importlib/API calls. These meaningful checks avoid treating a no-cache import as evidence against stale bytecode.
- Frozen source/test hashes were checked again after probes. The latest PNG review separately covers `create_review.py` `f2db9f77…`, including unchanged legacy custom-output snapshot shape.

## Initial frozen patch

- `skills/easyviz/scripts/render.py`: `28256c31b636210a58ec32c8e28672d5ce4c501d3e5623a172bf0efc1f5c20ef`.
- `skills/easyviz/scripts/figure_elements.py`: `c5107c6fd6db3f889382299af111e4b7c5197a0a1088dca0fc51efaa9c2c6a76`.
- Independently ran 43 renderer tests, 11 element-map tests and 7 figure-profile tests. All **61 tests passed**. Those cover strict malformed CSV records and headers; consumed byte snapshots and quoted/BOM/multiline literal IDs; source/spec/profile replacement before and during export; finite input overflow under both sample-sum and supplied-denominator normalization; explicit positive underflow rejection; CLI parse-to-render spec replacement; failed spec parsing invalidating old passing QA; and literal zero with an extreme exponent.
- The actual diff preserves exact consumed CSV bytes, binds figure metadata to captured input/spec hashes, invalidates stale passing QA at the start of attempts, and computes composition sums from exact decimals. Existing profile raw-byte capture remains the upstream input for continuity checks.

## Blocking finding from an independent probe

The initial patch collected runtime helper digests **after** their `exec_module` calls. A replacement immediately after loading `figure_elements.py` could therefore be recorded as the source of an old in-memory helper.

The isolated probe changed only a temporary script copy: it replaced the helper's literal manifest scope after the loader returned. Rendering still produced `qa.valid_outputs = true`; the manifest used the actually loaded original scope, while settings claimed SHA256 `8d5668b36afb98261a90a28ee4a8dae0bfa47f653cb75d5a0e212d7afc4d01af` for an unexecuted replacement instead of original `c5107c6f…`.

This directly reproduced the initial patch's remaining race. See immutable [helper-execution-before.json](helper-execution-before.json) and reproducible [probe_helper_execution.py](probe_helper_execution.py). These original before-repair files remain unchanged; the final verification above approves the repair against fresh frozen bytes.

## Scope

This audit concerns strict source structure, consumed-source continuity, stale QA invalidation and safe composition normalization. Source hashes do not establish correct experiment design, statistical assumptions, scientific interpretation or publication aesthetics. Other custom recipes and all external dependencies are outside the core patch's source-capture scope.

The runtime digest checks describe initialization and rendering under the trusted Python entry loader. They are not a security guarantee against a replaced interpreter, malicious loader or coordinated disk changes after the final continuity observation. Actual scientific artist coverage and visual review retain their separate roles.

## Re-run

```sh
.venv/bin/python evals/release-qa/v0.4.4/prepublication-integrity/probe_runtime.py
.venv/bin/python evals/release-qa/v0.4.4/prepublication-integrity/probe_helper_execution_fixed.py
```

Each script writes only its own evidence and temporary fixtures. Do not re-run the initial probe with the immutable before-repair output path.
