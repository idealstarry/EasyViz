# Installation and package audit for 0.4.4

Date: 2026-10-05. Scope: the local build → package check/extraction → install/update flow. Reviewed `scripts/install_plugin.py`, `scripts/build_plugin.py`, `scripts/check_package.py`, the relevant part of `scripts/sync_skill_cases.py`, and installer/build/extraction regression tests. All reproductions used temporary directories and harmless private-file markers; no real user package or catalog was damaged.

## Reproduced defects and repairs

| Case | Before repair: actual proof | Repair and regression evidence |
| --- | --- | --- |
| Unlisted source links | An extra package file linked to an external marker passed `validate_plugin`; installation reported `installed` and copied the external bytes into both the stable source and cache. Builder `copytree` likewise turned linked skill files and linked asset directories into regular ZIP entries, hiding their origin from a later validator. | Whole source/cache resource trees reject links and special files. Builder checks source ancestors/documents and resource trees before sync, then rechecks before deleting a previous build. File links, directory links, FIFOs and links introduced by sync preserve external data and the previous build. |
| Failed same-version refresh | A test CLI replaced the selected cache, corrupted `render.py`, then failed content verification. Source/catalog were restored, but the old usable cache was lost. | The selected marketplace/version determines the only trusted cache location. The installer snapshots an owned existing cache before invoking the CLI and restores it on failed verification; a newly created failed cache is removed. Tests compare all prior source/cache content hashes, including stale-cache and interrupted-backup paths. |
| Catalog rollback destroys other edits | The CLI phase appended another plugin and then failed. Restoring the entire previous catalog deleted that unrelated plugin. | Rollback restores/removes only this transaction's EasyViz entry when it still equals the entry written by this transaction, preserving other current entries and metadata. If EasyViz itself changed, the externally edited catalog is left untouched. An unchanged catalog retains exact original bytes. |
| Concurrent catalog commit | A separate writer appended another plugin after the installer read/merged the catalog but before its atomic write. Installation succeeded and discarded that plugin. | The write checks expected bytes immediately before replacement and fails without overwriting a detected external edit. Process locks serialize cooperating installers for both the shared personal catalog and the selected client source/cache; a real subprocess regression checks rejection while locked and release after process exit. Equivalent resolved lock paths are acquired once, preserving a custom `CODEX_HOME=home/.agents`. Remaining noncooperating-writer limits are stated below. |
| Builder destination redirects deletion | `dist` linked to an external directory containing `easyviz/private-note.txt`. Running the old builder deleted that directory and wrote the archive outside the checkout. | Preflight rejects repository-owned ancestor, output-directory, archive and summary links, including dangling links, before sync/deletion. Existing generated directories must identify themselves as EasyViz. Explicit safe temporary output directories remain supported. |
| Custom output resolves into source | An external ancestor alias pointed to `skills`; `build(alias/generated-build)` passed the initial lexical guard and began copying `skills` into a directory inside itself. | Destination/source overlap is checked using both lexical and resolved paths. The regression verifies no sync, output directory or changed source bytes. |
| ZIP path aliases and conflicts | `README.md` and `./README.md` were accepted as two members but became one file with the second content. Independent review also reproduced `README.md`/`readme.md` overwriting the same inode on the local case-insensitive filesystem. | All members are preflighted using normalized paths plus Unicode NFC/casefold identities. Exact, dot/slash, case and composed/decomposed Unicode aliases, and file/directory prefix conflicts are rejected before writing any member. Existing extraction links and conflicting parents are also rejected before writes. |
| ZIP expansion has no budget | A 33,795-byte compressed fixture expanded successfully to 34,603,008 bytes; the old extractor imposed no per-member, total or entry-count bound. | Limits are 10,000 entries, 64 MiB per member and 256 MiB total expanded bytes. Fast regression fixtures lower each configured threshold to verify rejection before earlier harmless members are written. The 33 MiB example is deliberately within the new reasonable limits; the repair establishes bounded expansion rather than rejecting all well-compressed files. |
| Truthy CLI state accepted | A test CLI returned `installed: "false"` and `enabled: "false"`; the old truthiness check could report installation success. | Confirmation requires JSON booleans `true` for both fields and a matching plugin ID. Wrong/malformed installed paths are rejected; cleanup uses only the predetermined cache, never an arbitrary path returned by a failed CLI. |
| Release test fixture drift | Legacy dummy resources labeled `1.0.0` were subjected to the new 0.4.4 resource requirements, hiding installer behavior behind unrelated missing-resource failures. | Legacy fixtures now identify as 0.4.2; the version update path uses 0.4.3. A separate 0.4.4 installation fixture includes the actual bundled design-card assets and verifies the cached package against the current validator. |

The already-built 0.4.3 package contains 726 members, 21,073,543 expanded bytes and a largest member of 948,517 bytes, well below all three new limits. The final 0.4.4 package check remains part of the release validation performed by the coordinating agent.

## Verification at handoff

Runtime: Python 3.12.2 (`.venv/bin/python`), conda-forge build, macOS 27.0.1 arm64.

- `python -m unittest discover -s tests -p test_install_plugin.py -v`: **26 passed**, 2.900 s.
- `python -m unittest discover -s tests -p test_package_extraction.py -v`: **8 passed**, 0.011 s.
- `python -m unittest discover -s tests -p test_build_plugin.py -v`: **16 passed**, 0.083 s.
- Scoped `git diff --check`: passed.

Source identities recorded after the final scoped tests:

| File | SHA-256 |
| --- | --- |
| `scripts/install_plugin.py` | `da5a22c87c8bb0d6384ef8f9b2a9e5cee7ba681f140c55977e4a827afcc74d73` |
| `scripts/build_plugin.py` | `e883b23b62a2fdf6b7b7266259e4dcac0d665bac8daf089d7a33998152287e3c` |
| `scripts/check_package.py` | `7e5e590de9cb0112dd35f7fb3bfd219bc67fc4847a0df466c6bba7cc804c087b` |
| `tests/test_install_plugin.py` | `026c3c4158cd4355ec3bfe6c0e0990629f43bdc0f45cb6f07a4905bbf072a1e8` |
| `tests/test_build_plugin.py` | `a2a98a682ebb1b069a8830b5ae2a764d1fabe20bd956bf268cd3c8858ab30f28` |
| `tests/test_package_extraction.py` | `eb21393523c050f0e8aa0e291354440e5f9806335c498b25e0d612f534b76832` |

## Limits of this evidence

Installer tests use an isolated fake CLI for package/catalog/cache effects. They do not verify the desktop UI refresh or snapshot every CLI-managed enabled-state/configuration file. The actual client installation and final built ZIP must be checked separately during release validation.

The process lock protects cooperating EasyViz installers. A writer that ignores that lock can still change a catalog between the final expected-byte check and filesystem replacement; this implementation does not claim an atomic compare-and-swap against arbitrary external writers. Detected edits are preserved and rejected, and rollback preserves already-observed unrelated edits. Windows uses a standard-library byte lock, but the real subprocess lock test here ran on macOS.

The installer restores source/cache/catalog for caught failures; this is not a single durable transaction across those resources during power loss. ZIP preflight rejections produce no member writes; a subsequent I/O or CRC failure during extraction can leave partial files in the selected temporary destination, which the package checker's temporary-directory scope removes. Builder safety checks preserve prior builds on invalid input/destination, but unexpected I/O failure during a valid build is not an atomic build rollback.
