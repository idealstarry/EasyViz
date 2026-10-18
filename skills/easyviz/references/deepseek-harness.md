# DeepSeek Harness

Use the same Create or Reproduce workflow. Read this reference only for host
setup, skill discovery or the local editing connection.

## Skills and plotting

EasyViz installs three complete skill folders into the default filesystem
provider's user root, `$DSH_HOME/skills` (normally `~/.dsh/skills`), or the
selected project's `.dsh/skills`. Keep `easyviz`, `easyviz-reference-reader` and
`easyviz-figure-reviewer` together. Project skills can shadow user skills with
the same name; check which `SKILL.md` the current session actually loads.

After installation, open or refresh the Harness session and verify that its
skill tools discover all three names. Then load `easyviz` for the plotting task;
resolve scripts and references relative to that installed skill directory.
Python 3.11+ and the packages in `scripts/requirements.txt` are still required
for drawing. Installing the skill does not install those scientific packages.

Use the host's available image/file tools for actual-image inspection. A
text-only model or an unavailable image tool cannot establish visual quality;
report that limitation. If independent Agents are unavailable, follow the
documented self-review fallback rather than inventing an independent review.

## Workbench and edits

Deliver reviewed figures and handle small revisions in the current chat by
default. The shared first-use introduction and two-round intake limit in
[EasyViz](../SKILL.md#first-use-and-focused-intake) apply in Harness too.

When the user requests visual annotations, launch
`scripts/easyviz_workbench.py` with the authorized project directory.
The user can select SVG elements or regions and save numbered comments. On
the user's next message in this same Harness session, read and apply those
comments through the ordinary [edit application](apply-figure-requests.md)
workflow. No new Codex session is needed.

For an explicitly requested MCP connection, follow [MCP setup](mcp.md) with
the selected Python environment, `easyviz_mcp.py` and the same project root.
Use Harness's supported MCP configuration and verify tool discovery before
claiming a connection. The npm installer leaves that configuration unchanged.
Pass `host="deepseek-harness"` and the real current Harness session identifier
to `connect_session`. If that identifier is unavailable, use saved comments
in the current chat instead of fabricating an identity.

`wait_for_submission` delivers a submitted batch only to an actively waiting
Agent. MCP registration does not wake an idle Harness session. Preserve the
original conversation; do not silently launch the optional Codex worker.

The filesystem roots are verified against the official
[`dsh-skill-filesystem` documentation](https://github.com/deepseek-ai/deepseek-harness/tree/master/packages/skill/skill-filesystem)
and the published `@deepseek-ai/dsh-skill-filesystem@0.2.0-rc.2` provider.
Filesystem discovery and a successful model-driven plotting task are separate
checks; report only what was actually run in the selected host.
