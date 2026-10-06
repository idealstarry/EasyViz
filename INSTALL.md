# Install EasyViz with an Agent

Give your local Agent the repository URL and this request:

> Install or update https://github.com/idealstarry/EasyViz in my local ChatGPT Desktop. Read its INSTALL.md and complete the installation for me.

The Agent handles acquisition, packaging, installation, and verification. The user does not need to copy a sequence of terminal commands. This installs the local plugin for compatible ChatGPT Desktop/Codex clients; it does not publish to the public plugin directory or import conversation history.

## Instructions for the Agent

1. Read this file and the repository's `AGENTS.md`. Use the current approved source in an existing EasyViz checkout when the user is maintaining it. For a new external installation, default to the latest **published stable release** and its matching tagged source; exclude drafts and prereleases. Clone `https://github.com/idealstarry/EasyViz.git` into a writable directory and select the verified release tag, or obtain that tag's source archive. Use the development branch only when the user requests development changes. Preserve uncommitted work in an existing checkout; do not reset it just to update.
2. Find Python 3.11 or newer and a local Codex CLI that supports `plugin add --json`. The installer checks the executable on `PATH`, common macOS locations, and `--codex` when supplied. If the installed client lacks that command, report the detected limitation and help update the user's selected client. Do not claim that a package is installed because its files were downloaded.
3. Run `python scripts/install_plugin.py --build` in the checkout, using the selected Python interpreter. The builder and installer use the standard library; scientific plotting packages are not needed to install. From another directory, use the script's absolute path and `--source /absolute/path/to/EasyViz --build`.
4. Read the installer's JSON result. It must report `status: installed`, the manifest version, the selected plugin ID, and a cache path. The installer copies a standalone source, merges the existing personal marketplace, calls the supported CLI install command, and confirms that EasyViz is installed and enabled. It keeps existing marketplace entries and backs up the prior EasyViz source and marketplace.
5. Verify that all three packaged skills exist in that cache: `easyviz`, `easyviz-reference-reader`, and `easyviz-figure-reviewer`. When the client exposes skill discovery, verify them in a fresh chat too. Report package checks and client discovery separately. Start a new chat for first use; if the running desktop has not refreshed its directory, explain that restarting it may be needed. Do not close or restart the user's app without authorization.
6. Give the user a short completion report with the installed version and one usable prompt. Include any actual client-discovery limitation. Do not ask the user to perform the steps the Agent can complete.

An installation request authorizes these local plugin changes. Follow the current environment's real permissions, and report a precise failure if they prevent installation.

## Updates and paths

Use the same installer to update or reinstall. For a maintained checkout, package its current approved changes. For an external installation, acquire the intended release or updated source first; avoid silently switching a user who requested a pinned version to the latest branch.

The default source is the checkout's `dist/easyviz/`. `--build` refreshes it first. `--source` also accepts an extracted standalone `easyviz/` directory. The installer keeps a copy under `$CODEX_HOME/plugins/easyviz/` (normally `~/.codex/plugins/easyviz/`) and updates only the EasyViz entry in `~/.agents/plugins/marketplace.json`. Existing catalog names, metadata and other plugins are preserved. CLI installation refreshes the client cache and enabled state; its returned path must match the selected marketplace/version cache, and every packaged file is verified.

Existing EasyViz sources, the personal marketplace and an existing same-version cache receive dated backups. For caught failures, the installer restores the prior source/cache and rolls back its own catalog entry while retaining observed unrelated changes. Incomplete rollback is reported explicitly; this does not promise restoration of every CLI-managed setting or a power-loss transaction. It does not manually edit account credentials or replace the user's `config.toml`.

Cooperating EasyViz installations share process locks. If another installation is running, preserve the current files and retry after it finishes. External editors do not acquire these locks; detected catalog changes are preserved and rejected. Source and output links, conflicting archive names and packages over the documented extraction budgets are rejected before the corresponding copies/writes.

`--home /absolute/path/to/temporary-home` is for isolated verification. It places files and the CLI cache under that directory, leaves the real OS home unchanged, and uses a uniquely named test marketplace so the CLI cannot confuse it with the user's Personal source. `--codex /absolute/path/to/codex` selects an explicit executable. This test mode does not install into the user's desktop account.

## Plotting after installation

For a plotting task, the Agent checks the selected Python environment against the installed `skills/easyviz/scripts/requirements.txt`, installs missing declared packages in that environment when authorized, and checks font availability. Installation does not silently change the user's scientific environment.

Example first request:

> Use $easyviz to make a dot plot from my source table. Use Arial 8 pt, a 180 × 120 mm panel, and separate PDF, SVG, PNG and caption files.

## Optional MCP and local review

The ordinary plugin installation does not enable an MCP server or install its
optional SDK. When the user wants a connected review workflow, establish the
authorized project directory, choose a Python environment with the plotting
dependencies, and install the packaged `skills/easyviz/scripts/requirements-mcp.txt`
there. Follow the packaged [MCP guide](skills/easyviz/references/mcp.md) to
configure the selected client's supported STDIO connection. Verify actual tool
discovery and a read of the intended attempt in that client.

For a Codex CLI that supports the documented command, the Agent can register a
distinct project connection using:

```sh
codex mcp add easyviz-project -- /absolute/path/to/python \
  /absolute/path/to/installed/easyviz/scripts/easyviz_mcp.py \
  --project-dir /absolute/path/to/authorized-project
```

Resolve all paths from the real installation result, retain other connections,
and check the client's current help before applying configuration. An MCP
registration does not install the skill or verify drawing dependencies. Do not
claim desktop discovery until checked in a refreshed client. Use the same
project scope when launching the [workbench](skills/easyviz/references/figure-workbench.md).
It can generate supported cosmetic previews itself; custom instructions remain
work for the active Agent.

## Client support and evidence

The local installation mechanism follows [OpenAI's plugin packaging documentation](https://developers.openai.com/plugins/build/plugins). The available CLI commands are checked on the installed client. Local registration, an extracted Python run, desktop display, and skill discovery are distinct checks; report only those completed. Public plugin-directory availability, web/cloud installation and arbitrary desktop versions are not established by this installer.
