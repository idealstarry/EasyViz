import { readFileSync, existsSync } from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { PACKAGE_ROOT, detectPython, payloadDirectory } from '../bin/easyviz.mjs';

function prepare() {
  const metadata = JSON.parse(readFileSync(path.join(PACKAGE_ROOT, 'package.json'), 'utf8'));
  const sourceManifest = path.join(PACKAGE_ROOT, 'plugins', 'easyviz', '.codex-plugin', 'plugin.json');
  // A tarball already carries its built payload. Rebuilding an installed
  // package must not require the source checkout or run Python again.
  if (!existsSync(sourceManifest)) {
    payloadDirectory(PACKAGE_ROOT);
    return;
  }
  const manifest = JSON.parse(readFileSync(sourceManifest, 'utf8'));
  if (metadata.version !== manifest.version) throw new Error('npm and plugin versions must match before packing.');
  if (!existsSync(path.join(PACKAGE_ROOT, 'scripts', 'install_harness.py'))) {
    throw new Error('Harness installer is missing; refusing to pack incomplete installation support.');
  }
  const python = detectPython();
  const result = spawnSync(python.executable, [...python.prefix, '-c',
    'import json, sys; from pathlib import Path; sys.path.insert(0, sys.argv[1]); from build_plugin import build; print(json.dumps(build(Path(sys.argv[2])), indent=2))',
    path.join(PACKAGE_ROOT, 'scripts'), path.join(PACKAGE_ROOT, 'dist', 'npm')],
  { cwd: PACKAGE_ROOT, env: process.env, stdio: 'inherit', shell: false, windowsHide: true });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(`Portable resource build failed (${result.status ?? result.signal}).`);
}

try {
  prepare();
} catch (error) {
  console.error(`EasyViz npm preparation: ${error.message}`);
  process.exitCode = 1;
}
