import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync, copyFileSync, rmSync, symlinkSync, realpathSync, existsSync, readdirSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
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

test('short install commands retain the chosen client and reject a conflicting target', (t) => {
  const f = fixture(t);
  for (const [command, flag, script] of [
    ['deepseek', '--dsh-home', 'install_harness.py'], ['codex', '--home', 'install_plugin.py'],
  ]) {
    const selectedHome = path.join(f.temporary, `${command} home`);
    const result = invoke(f, [command, flag, selectedHome]);
    assert.equal(result.status, 0, result.stderr);
    assert.deepEqual(JSON.parse(result.stdout), { script, args: ['--source', f.payload, flag, selectedHome] });
    assert.throws(() => parseArguments([command, '--target', 'codex']), /Repeated option/);
    assert.equal(parseArguments([command, '--help']).command, 'help');
  }
  assert.throws(() => parseArguments(['deepseek', '--home', '/tmp/codex']), /only to codex/);
  assert.throws(() => parseArguments(['codex', '--dsh-home', '/tmp/dsh']), /only to deepseek/);
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

test('ordinary npm Git installation and npm exec build ignored resources through prepare',
  { skip: process.platform === 'win32', timeout: 60000 }, (t) => {
    const npm = spawnSync('npm', ['--version'], { encoding: 'utf8', timeout: 10000 });
    const git = spawnSync('git', ['--version'], { encoding: 'utf8', timeout: 10000 });
    if (npm.status !== 0 || git.status !== 0) {
      t.skip('npm and Git are required for the local Git lifecycle integration test.');
      return;
    }
    const temporary = realpathSync(mkdtempSync(path.join(os.tmpdir(), 'easyviz-npm-git-')));
    t.after(() => rmSync(temporary, { recursive: true, force: true }));
    const source = path.join(temporary, 'source');
    const prefix = path.join(temporary, 'prefix');
    const cache = path.join(temporary, 'cache');
    mkdirSync(source);
    mkdirSync(prefix);
    writeFileSync(path.join(prefix, 'package.json'), '{"name":"easyviz-lifecycle-consumer","private":true}');
    writeFileSync(path.join(source, 'package.json'), JSON.stringify({
      name: '@idealstarry/easyviz', version: '0.5.2', type: 'module',
      bin: { easyviz: 'cli.mjs' }, files: ['cli.mjs', 'prepare.mjs', 'payload.json'],
      scripts: { prepare: 'node prepare.mjs' },
    }));
    writeFileSync(path.join(source, 'prepare.mjs'),
      'import { writeFileSync } from "node:fs"; writeFileSync(new URL("payload.json", import.meta.url), JSON.stringify({prepared: true}));\n');
    writeFileSync(path.join(source, 'cli.mjs'),
      '#!/usr/bin/env node\nimport { readFileSync } from "node:fs"; console.log(readFileSync(new URL("payload.json", import.meta.url), "utf8"));\n');
    writeFileSync(path.join(source, '.gitignore'), 'payload.json\n');
    const userConfig = path.join(temporary, 'npm-user.conf');
    const globalConfig = path.join(temporary, 'npm-global.conf');
    writeFileSync(userConfig, '');
    writeFileSync(globalConfig, '');
    const runGit = (args) => {
      const result = spawnSync('git', ['-c', 'core.hooksPath=/dev/null', ...args], {
        cwd: source, encoding: 'utf8', timeout: 10000,
      });
      assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
      return result.stdout.trim();
    };
    runGit(['init', '--quiet', '--template=']);
    runGit(['add', 'package.json', 'cli.mjs', 'prepare.mjs', '.gitignore']);
    runGit(['-c', 'user.name=EasyViz test', '-c', 'user.email=test@example.invalid',
      '-c', 'commit.gpgsign=false', 'commit', '--quiet', '-m', 'Local lifecycle fixture']);
    const revision = runGit(['rev-parse', 'HEAD']);
    const spec = `git+${pathToFileURL(source).href}#${revision}`;
    const result = spawnSync('npm', ['install', '--prefix', prefix, '--cache', cache,
      '--userconfig', userConfig, '--globalconfig', globalConfig,
      '--offline', '--no-audit', '--no-fund', spec], {
      cwd: temporary, encoding: 'utf8', timeout: 45000, maxBuffer: 1024 * 1024,
      env: { ...process.env, npm_config_update_notifier: 'false' }, shell: false,
    });
    assert.equal(result.status, 0, `${result.error ?? ''}\n${result.stdout}\n${result.stderr}`);
    const installed = path.join(prefix, 'node_modules/@idealstarry/easyviz');
    assert.ok(existsSync(path.join(installed, 'payload.json')), JSON.stringify({
      stdout: result.stdout, stderr: result.stderr,
      files: existsSync(installed) ? readdirSync(installed) : readdirSync(path.join(prefix, 'node_modules')),
      logs: readdirSync(path.join(cache, '_logs')).map(name => readFileSync(path.join(cache, '_logs', name), 'utf8')).join('\n').split('\n').filter(line => /prepare|error|reify|git dep/.test(line)),
    }));
    assert.deepEqual(JSON.parse(readFileSync(path.join(installed, 'payload.json'), 'utf8')), { prepared: true });
    const command = spawnSync(process.execPath, [path.join(prefix, 'node_modules/.bin/easyviz')], {
      cwd: temporary, encoding: 'utf8', timeout: 10000,
    });
    assert.equal(command.status, 0, command.stderr);
    assert.deepEqual(JSON.parse(command.stdout), { prepared: true });
    const oneShot = spawnSync('npm', ['exec', '--yes', `--package=${spec}`,
      '--cache', path.join(temporary, 'exec-cache'), '--userconfig', userConfig,
      '--globalconfig', globalConfig, '--offline', '--no-audit', '--no-fund', '--', 'easyviz'], {
      cwd: temporary, encoding: 'utf8', timeout: 45000, maxBuffer: 1024 * 1024,
      env: { ...process.env, npm_config_update_notifier: 'false' }, shell: false,
    });
    assert.equal(oneShot.status, 0, `${oneShot.error ?? ''}\n${oneShot.stdout}\n${oneShot.stderr}`);
    assert.deepEqual(JSON.parse(oneShot.stdout), { prepared: true });
    assert.equal(readFileSync(userConfig, 'utf8'), '');
    assert.equal(readFileSync(globalConfig, 'utf8'), '');
  });
