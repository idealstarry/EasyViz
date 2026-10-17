import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync, copyFileSync, rmSync, symlinkSync, realpathSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { test } from 'node:test';
import { detectPython, parseArguments, SKILLS } from '../bin/easyviz.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

function fixture(t) {
  const temporary = realpathSync(mkdtempSync(path.join(os.tmpdir(), 'easyviz npm CLI ')));
  t.after(() => rmSync(temporary, { recursive: true, force: true }));
  const root = path.join(temporary, 'installed package');
  const payload = path.join(root, 'dist', 'npm', 'easyviz');
  for (const folder of ['bin', 'scripts', 'dist/npm/easyviz/.codex-plugin']) {
    mkdirSync(path.join(root, folder), { recursive: true });
  }
  writeFileSync(path.join(root, 'package.json'), JSON.stringify({ type: 'module', version: '0.5.2' }));
  writeFileSync(path.join(payload, '.codex-plugin/plugin.json'), JSON.stringify({ name: 'easyviz', version: '0.5.2' }));
  copyFileSync(path.join(ROOT, 'bin/easyviz.mjs'), path.join(root, 'bin/easyviz.mjs'));
  for (const skill of SKILLS) mkdirSync(path.join(payload, 'skills', skill), { recursive: true });
  const fakeScript = 'import json, os, sys\nprint(json.dumps({"script": os.path.basename(__file__), "args": sys.argv[1:]}))\nsys.exit(int(os.environ.get("EASYVIZ_TEST_EXIT", "0")))\n';
  for (const script of ['install_plugin.py', 'install_harness.py']) writeFileSync(path.join(root, 'scripts', script), fakeScript);
  mkdirSync(path.join(payload, 'skills/easyviz/scripts'), { recursive: true });
  for (const script of ['easyviz_workbench.py', 'easyviz_mcp.py']) writeFileSync(path.join(payload, 'skills/easyviz/scripts', script), fakeScript);
  const cwd = path.join(temporary, 'unrelated current directory');
  mkdirSync(cwd);
  return { root, payload, cwd, temporary };
}

function invoke(f, args, extraEnv = {}) {
  return spawnSync(process.execPath, [path.join(f.root, 'bin/easyviz.mjs'), ...args], {
    cwd: f.cwd, env: { ...process.env, ...extraEnv }, encoding: 'utf8', shell: false,
  });
}

test('argument validation rejects conflicting targets, extra options and unbounded runtime arguments', () => {
  assert.equal(parseArguments(['install']).options['--target'], 'codex');
  for (const args of [
    ['install', '--target', 'unknown'], ['install', '--target', 'deepseek-harness', '--codex', 'codex'],
    ['install', '--target', 'deepseek-harness', '--home', '/tmp/user'], ['install', '--project', '/tmp/project'],
    ['install', '--target', 'deepseek-harness', '--project', '/tmp/project', '--dsh-home', '/tmp/home'],
    ['workbench'], ['mcp'], ['mcp', '--project-dir', '/tmp/project', '--eval', 'x'],
    ['workbench', '--project-dir', '/tmp/p', '--port', '65536'],
    ['workbench', '--project-dir', '/tmp/p', '--port', '-1'],
    ['workbench', '--project-dir', '/tmp/p', '--open', '--no-open'],
    ['install', '--python'], ['install', '--python', '--home'],
    ['path', '--skill', '../outside'], ['install', '--target', 'codex', '--target', 'codex'],
  ]) assert.throws(() => parseArguments(args), undefined, args.join(' '));
});

test('explicit Python failures cannot silently select another interpreter or use a shell', () => {
  const calls = [];
  assert.throws(() => detectPython('/path with spaces/python', { spawn: (...args) => {
    calls.push(args); return { status: 1, stdout: '3.10\n' };
  } }), /Selected Python/);
  assert.equal(calls.length, 1);
  assert.equal(calls[0][0], '/path with spaces/python');
  assert.equal(calls[0][2].shell, false);
  const selected = detectPython(undefined, { env: { EASYVIZ_PYTHON: '/selected/python' }, spawn: (...args) => {
    assert.equal(args[0], '/selected/python'); return { status: 0, stdout: '3.12\n' };
  } });
  assert.equal(selected.executable, '/selected/python');
});

test('Windows Python launcher fallback retains its -3 prefix', () => {
  const selected = detectPython(undefined, { env: {}, platform: 'win32', spawn: (command) =>
    command === 'py' ? { status: 0, stdout: '3.12\n' } : { error: new Error('not found') } });
  assert.deepEqual(selected, { executable: 'py', prefix: ['-3'] });
});

test('payload and skill paths resolve from installed package, even from another directory with spaces', (t) => {
  const f = fixture(t);
  let result = invoke(f, ['path']);
  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.stdout.trim(), f.payload);
  result = invoke(f, ['path', '--skill', 'easyviz-reference-reader']);
  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.stdout.trim(), path.join(f.payload, 'skills/easyviz-reference-reader'));
  writeFileSync(path.join(f.payload, '.codex-plugin/plugin.json'), '{"name":"easyviz","version":"0.0.0"}');
  result = invoke(f, ['path']);
  assert.equal(result.status, 1);
  assert.match(result.stderr, /version does not match/);
});

test('Codex and Harness dispatch preserve exact arguments and installer exit codes', (t) => {
  const f = fixture(t);
  const python = detectPython().executable;
  const selectedHome = path.join(f.temporary, 'selected home');
  let result = invoke(f, ['install', '--python', python, '--home', selectedHome, '--codex', '/a client/codex'],
    { EASYVIZ_TEST_EXIT: '17' });
  assert.equal(result.status, 17, result.stderr);
  assert.deepEqual(JSON.parse(result.stdout), { script: 'install_plugin.py', args: [
    '--source', f.payload, '--home', selectedHome, '--codex', '/a client/codex',
  ] });
  result = invoke(f, ['install', '--target', 'deepseek-harness', '--project', f.cwd], { EASYVIZ_PYTHON: python });
  assert.equal(result.status, 0, result.stderr);
  assert.deepEqual(JSON.parse(result.stdout), { script: 'install_harness.py', args: ['--source', f.payload, '--project', f.cwd] });
  result = invoke(f, ['install', '--target', 'deepseek-harness', '--dsh-home', selectedHome], { EASYVIZ_PYTHON: python });
  assert.equal(result.status, 0, result.stderr);
  assert.deepEqual(JSON.parse(result.stdout).args, ['--source', f.payload, '--dsh-home', selectedHome]);
});

test('workbench and MCP forward only declared project options without registration or environment installation', (t) => {
  const f = fixture(t);
  const python = detectPython().executable;
  const result = invoke(f, ['workbench', '--project-dir', f.cwd, '--port', '0', '--no-open'], { EASYVIZ_PYTHON: python });
  assert.equal(result.status, 0, result.stderr);
  assert.deepEqual(JSON.parse(result.stdout), { script: 'easyviz_workbench.py', args: [
    '--project-dir', f.cwd, '--port', '0', '--no-open',
  ] });
  const mcp = invoke(f, ['mcp', '--project-dir', f.cwd], { EASYVIZ_PYTHON: python });
  assert.equal(mcp.status, 0, mcp.stderr);
  assert.deepEqual(JSON.parse(mcp.stdout), { script: 'easyviz_mcp.py', args: ['--project-dir', f.cwd] });
});

test('npm-style symlink command executes its real entry point', { skip: process.platform === 'win32' }, (t) => {
  const f = fixture(t);
  const link = path.join(f.temporary, 'easyviz');
  symlinkSync(path.join(f.root, 'bin/easyviz.mjs'), link);
  const result = spawnSync(process.execPath, [link, '--version'], { encoding: 'utf8', cwd: f.cwd });
  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.stdout.trim(), '0.5.2');
});

test('help and version work without Python, and package has no client installation lifecycle hooks', (t) => {
  const f = fixture(t);
  for (const args of [['--help'], ['--version']]) {
    const result = invoke(f, args, { EASYVIZ_PYTHON: '/missing/python' });
    assert.equal(result.status, 0, result.stderr);
    assert.ok(result.stdout.length > 0);
  }
  const metadata = JSON.parse(readFileSync(path.join(ROOT, 'package.json'), 'utf8'));
  for (const hook of ['preinstall', 'install', 'postinstall']) assert.equal(metadata.scripts[hook], undefined);
  assert.equal(metadata.scripts.prepare, 'node scripts/prepare_npm.mjs');
  assert.equal(metadata.dependencies, undefined);
  assert.equal(metadata.optionalDependencies, undefined);
});

test('prepare on an already bundled tarball validates its version without source checkout or Python', (t) => {
  const f = fixture(t);
  const script = path.join(f.root, 'scripts/prepare_npm.mjs');
  copyFileSync(path.join(ROOT, 'scripts/prepare_npm.mjs'), script);
  let result = spawnSync(process.execPath, [script], {
    cwd: f.cwd, env: { ...process.env, EASYVIZ_PYTHON: '/missing/python' }, encoding: 'utf8',
  });
  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.stdout, '');
  writeFileSync(path.join(f.payload, '.codex-plugin/plugin.json'), '{"name":"easyviz","version":"0.0.0"}');
  result = spawnSync(process.execPath, [script], { cwd: f.cwd, encoding: 'utf8' });
  assert.equal(result.status, 1);
  assert.match(result.stderr, /version does not match/);
});
