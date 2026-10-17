#!/usr/bin/env node
import { spawnSync } from 'node:child_process';
import { constants } from 'node:os';
import { existsSync, readFileSync, realpathSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

export const PACKAGE_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
export const SKILLS = ['easyviz', 'easyviz-reference-reader', 'easyviz-figure-reviewer'];

const HELP = `EasyViz — scientific plotting skills and local figure review

Usage:
  easyviz install [--target codex|deepseek-harness] [--python PATH]
    Codex:   [--home OS_HOME] [--codex PATH]
    Harness: [--project DIRECTORY | --dsh-home DIRECTORY]
  easyviz path [--skill ${SKILLS.join('|')}]
  easyviz workbench --project-dir DIRECTORY [--figure-dir DIRECTORY]
    [--compare-dir DIRECTORY] [--port 0..65535] [--open | --no-open] [--python PATH]
  easyviz mcp --project-dir DIRECTORY [--figure-dir DIRECTORY] [--python PATH]
  easyviz --version

The path command prints the bundled plugin directory, or the selected skill.
Python 3.11+ is required for install, workbench and MCP; EASYVIZ_PYTHON may
select it. Plotting and optional MCP dependencies are installed separately.
Installation changes only the explicitly selected client's EasyViz resources.
MCP runs on stdio; this command does not register it with an Agent.
`;

const OPTIONS = {
  install: new Set(['--target', '--python', '--home', '--codex', '--project', '--dsh-home']),
  path: new Set(['--skill']),
  workbench: new Set(['--project-dir', '--figure-dir', '--compare-dir', '--port', '--open', '--no-open', '--python']),
  mcp: new Set(['--project-dir', '--figure-dir', '--python']),
};
const SWITCHES = new Set(['--open', '--no-open']);

export function parseArguments(argv) {
  if (argv.length === 0 || (argv.length === 1 && ['--help', '-h', 'help'].includes(argv[0]))) {
    return { command: 'help', options: {} };
  }
  if (argv.length === 1 && ['--version', '-v'].includes(argv[0])) {
    return { command: 'version', options: {} };
  }
  const [command, ...rest] = argv;
  if (!Object.hasOwn(OPTIONS, command)) throw new Error(`Unknown command: ${command}. Use --help.`);
  const options = {};
  for (let i = 0; i < rest.length; i += 1) {
    const option = rest[i];
    if (['--help', '-h'].includes(option) && rest.length === 1) return { command: 'help', options: {} };
    if (!OPTIONS[command].has(option)) throw new Error(`Unknown ${command} option: ${option}`);
    if (Object.hasOwn(options, option)) throw new Error(`Repeated option: ${option}`);
    if (SWITCHES.has(option)) {
      options[option] = true;
    } else {
      const value = rest[++i];
      if (!value || value.startsWith('--')) throw new Error(`${option} requires a value.`);
      options[option] = value;
    }
  }
  if (command === 'install') {
    const target = options['--target'] ?? 'codex';
    if (!['codex', 'deepseek-harness'].includes(target)) throw new Error(`Unsupported target: ${target}`);
    options['--target'] = target;
    if (target === 'codex' && (options['--project'] || options['--dsh-home'])) {
      throw new Error('--project and --dsh-home apply only to deepseek-harness.');
    }
    if (target === 'deepseek-harness' && (options['--home'] || options['--codex'])) {
      throw new Error('--home and --codex apply only to codex; use --dsh-home for Harness.');
    }
    if (options['--project'] && options['--dsh-home']) throw new Error('Choose --project or --dsh-home.');
  }
  if (command === 'path' && options['--skill'] && !SKILLS.includes(options['--skill'])) {
    throw new Error(`Unknown skill: ${options['--skill']}`);
  }
  if (['workbench', 'mcp'].includes(command) && !options['--project-dir']) {
    throw new Error(`${command} requires an explicit --project-dir.`);
  }
  if (options['--open'] && options['--no-open']) throw new Error('Choose --open or --no-open.');
  if (options['--port'] !== undefined &&
      (!/^\d+$/.test(options['--port']) || Number(options['--port']) > 65535)) {
    throw new Error('--port must be an integer from 0 to 65535.');
  }
  return { command, options };
}

export function detectPython(explicit, {
  env = process.env, platform = process.platform, spawn = spawnSync,
} = {}) {
  const selected = explicit || env.EASYVIZ_PYTHON;
  const candidates = selected ? [[selected, []]] : [
    ['python3', []], ['python', []], ...(platform === 'win32' ? [['py', ['-3']]] : []),
  ];
  for (const [executable, prefix] of candidates) {
    const probe = spawn(executable, [...prefix, '-c',
      'import sys; print("%d.%d" % sys.version_info[:2]); sys.exit(0 if sys.version_info >= (3, 11) else 1)'],
    { env, encoding: 'utf8', shell: false, windowsHide: true, timeout: 10000 });
    const version = /^(\d+)\.(\d+)\s*$/.exec(probe.stdout ?? '');
    if (!probe.error && probe.status === 0 && version &&
        (Number(version[1]) > 3 || (Number(version[1]) === 3 && Number(version[2]) >= 11))) {
      return { executable, prefix };
    }
  }
  throw new Error(selected
    ? `Selected Python is unavailable or older than 3.11: ${selected}`
    : 'Python 3.11+ was not found. Install it, then use --python PATH or EASYVIZ_PYTHON.');
}

export function payloadDirectory(root = PACKAGE_ROOT) {
  const payload = path.join(root, 'dist', 'npm', 'easyviz');
  if (!existsSync(path.join(payload, '.codex-plugin', 'plugin.json'))) {
    throw new Error('Bundled EasyViz resources are missing. In a source checkout run npm pack first.');
  }
  const manifest = JSON.parse(readFileSync(path.join(payload, '.codex-plugin', 'plugin.json'), 'utf8'));
  const metadata = JSON.parse(readFileSync(path.join(root, 'package.json'), 'utf8'));
  if (manifest.name !== 'easyviz' || manifest.version !== metadata.version) {
    throw new Error('Bundled EasyViz version does not match this npm package.');
  }
  return payload;
}

export function main(argv, {
  root = PACKAGE_ROOT, env = process.env, platform = process.platform, spawn = spawnSync,
  stdout = process.stdout, stderr = process.stderr,
} = {}) {
  try {
    const { command, options } = parseArguments(argv);
    if (command === 'help') { stdout.write(HELP); return 0; }
    if (command === 'version') {
      stdout.write(`${JSON.parse(readFileSync(path.join(root, 'package.json'), 'utf8')).version}\n`);
      return 0;
    }
    const payload = payloadDirectory(root);
    if (command === 'path') {
      const selected = options['--skill'] ? path.join(payload, 'skills', options['--skill']) : payload;
      if (!existsSync(selected)) throw new Error('Selected bundled skill is missing. Reinstall the npm package.');
      stdout.write(`${selected}\n`);
      return 0;
    }
    const python = detectPython(options['--python'], { env, platform, spawn });
    let script;
    const forwarded = [];
    if (command === 'install') {
      script = path.join(root, 'scripts', options['--target'] === 'codex' ? 'install_plugin.py' : 'install_harness.py');
      forwarded.push('--source', payload);
      for (const flag of ['--home', '--codex', '--project', '--dsh-home']) {
        if (options[flag]) forwarded.push(flag, options[flag]);
      }
    } else {
      script = path.join(payload, 'skills', 'easyviz', 'scripts',
        command === 'workbench' ? 'easyviz_workbench.py' : 'easyviz_mcp.py');
      for (const flag of ['--project-dir', '--figure-dir', '--compare-dir', '--port']) {
        if (options[flag] !== undefined) forwarded.push(flag, options[flag]);
      }
      for (const flag of ['--open', '--no-open']) {
        if (options[flag]) forwarded.push(flag);
      }
    }
    if (!existsSync(script)) throw new Error(`Bundled entry point is missing: ${path.basename(script)}`);
    const result = spawn(python.executable, [...python.prefix, script, ...forwarded],
      { env, stdio: 'inherit', shell: false, windowsHide: true });
    if (result.error) throw new Error(`Could not start Python: ${result.error.message}`);
    if (result.signal) return 128 + (constants.signals[result.signal] ?? 1);
    return Number.isInteger(result.status) ? result.status : 1;
  } catch (error) {
    stderr.write(`EasyViz: ${error.message}\n`);
    return 1;
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(realpathSync(process.argv[1])).href) {
  process.exitCode = main(process.argv.slice(2));
}
