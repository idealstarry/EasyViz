"""Build output must stay within owned destinations and preserve user files."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import build_plugin
from check_package import (CURATED_CREATE_RESOURCES, V050_REPRODUCE_RESOURCES, V050_RUNTIME_RESOURCES,
                           V051_RUNTIME_RESOURCES, extract_package, validate_resource_tree)


class BuildPluginTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='easyviz-build-test-')
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.root = self.base / 'repository'
        self.root.mkdir()
        self.dist = self.root / 'dist'
        self.manifest = self.root / 'plugins/easyviz/.codex-plugin/plugin.json'
        resources = {
            'plugins/easyviz/.codex-plugin/plugin.json': json.dumps({'name': 'easyviz', 'version': '1.0.0'}),
            'plugins/easyviz/assets/logo.svg': '<svg/>\n',
            'plugins/easyviz/README.md': 'Portable EasyViz\n',
            'skills/easyviz/SKILL.md': 'Scientific figures\n',
            'skills/easyviz/scripts/render.py': 'print("figure")\n',
            'skills/easyviz/scripts/figure_handoff.py': '# Bound custom source handoff\n',
            'skills/easyviz/scripts/observation_clipping.py': '# Final observation envelope check\n',
            'skills/easyviz/scripts/__pycache__/render.pyc': 'generated cache',
            'LICENSE': 'License\n',
            'THIRD_PARTY_NOTICES.md': 'Attribution\n',
        }
        for case, names in (CURATED_CREATE_RESOURCES | V050_REPRODUCE_RESOURCES).items():
            for name in names:
                resources[f"skills/easyviz/assets/cases/{case}/{name}"] = "portable curated source resource\n"
        for name in V050_RUNTIME_RESOURCES + V051_RUNTIME_RESOURCES:
            resources[f"skills/easyviz/scripts/{name}"] = "runtime test resource\n"
        for name, content in resources.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        for patch in (mock.patch.object(build_plugin, 'ROOT', self.root),
                      mock.patch.object(build_plugin, 'DIST', self.dist)):
            patch.start()
            self.addCleanup(patch.stop)
        patch = mock.patch.object(build_plugin, 'sync')
        self.sync = patch.start()
        self.addCleanup(patch.stop)
        # These ownership/transaction fixtures omit chart-specific resources.
        # The full resource validator has separate installer/extracted tests.
        patch = mock.patch.object(build_plugin, 'validate_plugin', side_effect=lambda path:
                                  json.loads((path / '.codex-plugin/plugin.json').read_text()))
        self.validate_plugin = patch.start()
        self.addCleanup(patch.stop)

    def external_marker(self, name='outside'):
        outside = self.base / name
        marker = outside / 'easyviz/keep.bin'
        marker.parent.mkdir(parents=True)
        marker.write_bytes(b'external files must stay untouched')
        return outside, marker

    def output_bytes(self):
        return {path.relative_to(self.dist).as_posix(): path.read_bytes()
                for path in self.dist.rglob('*') if path.is_file()}

    def test_failed_copy_or_zip_preserves_previous_package_and_summary(self):
        build_plugin.build()
        (self.dist / 'easyviz/previous.txt').write_bytes(b'previous package note')
        (self.dist / 'unrelated.bin').write_bytes(b'unrelated distribution file')
        before = self.output_bytes()
        (self.root / 'plugins/easyviz/README.md').write_text('new candidate readme\n')
        real_copy = build_plugin.shutil.copytree
        def interrupted_copy(source, target, *args, **kwargs):
            result = real_copy(source, target, *args, **kwargs)
            if Path(source) == self.root / 'plugins/easyviz/assets':
                raise OSError('copy interrupted after partial staging')
            return result
        with mock.patch.object(build_plugin.shutil, 'copytree', side_effect=interrupted_copy):
            with self.assertRaisesRegex(OSError, 'copy interrupted'):
                build_plugin.build()
        self.assertEqual(self.output_bytes(), before)
        real_write = zipfile.ZipFile.writestr
        calls = 0
        def interrupted_zip(package, *args, **kwargs):
            nonlocal calls
            calls += 1
            real_write(package, *args, **kwargs)
            if calls == 3:
                raise OSError('ZIP interrupted after partial archive')
        with mock.patch.object(zipfile.ZipFile, 'writestr', interrupted_zip):
            with self.assertRaisesRegex(OSError, 'ZIP interrupted'):
                build_plugin.build()
        self.assertEqual(self.output_bytes(), before)
        self.assertFalse(list(self.dist.glob('.easyviz-build-*')))

    def test_failed_summary_publication_restores_all_previous_outputs(self):
        build_plugin.build()
        (self.dist / 'easyviz/previous.txt').write_bytes(b'previous package note')
        before = self.output_bytes()
        (self.root / 'plugins/easyviz/README.md').write_text('new candidate readme\n')
        real_replace = Path.replace
        failed = False
        def interrupted_replace(source, target):
            nonlocal failed
            if not failed and source.name == 'build.json' and source.parent.name.startswith('.easyviz-build-'):
                failed = True
                raise OSError('summary publication interrupted')
            return real_replace(source, target)
        with mock.patch.object(Path, 'replace', interrupted_replace):
            with self.assertRaisesRegex(OSError, 'summary publication interrupted'):
                build_plugin.build()
        self.assertTrue(failed)
        self.assertEqual(self.output_bytes(), before)
        self.assertFalse(list(self.dist.glob('.easyviz-build-*')))

    def test_incomplete_candidate_keeps_previous_valid_package(self):
        build_plugin.build()
        before = self.output_bytes()
        self.validate_plugin.side_effect = ValueError('Missing portable resource')
        with self.assertRaisesRegex(ValueError, 'Missing portable resource'):
            build_plugin.build()
        self.assertEqual(self.output_bytes(), before)
        self.assertFalse(list(self.dist.glob('.easyviz-build-*')))

    def test_manifest_changed_during_copy_does_not_publish_wrong_archive_version(self):
        build_plugin.build()
        before = self.output_bytes()
        self.validate_plugin.side_effect = lambda path: {'name': 'easyviz', 'version': '2.0.0'}
        with self.assertRaisesRegex(ValueError, 'manifest changed'):
            build_plugin.build()
        self.assertEqual(self.output_bytes(), before)

    def assert_rejected_without_sync(self, dist=None, pattern='symlink build path'):
        with self.assertRaisesRegex(ValueError, pattern):
            build_plugin.build(dist)
        self.sync.assert_not_called()

    def test_dist_symlink_preserves_external_directory_before_deletion(self):
        outside, marker = self.external_marker()
        self.dist.symlink_to(outside, target_is_directory=True)
        self.assert_rejected_without_sync()
        self.assertTrue(self.dist.is_symlink())
        self.assertEqual(marker.read_bytes(), b'external files must stay untouched')
        self.assertEqual(list(outside.iterdir()), [outside / 'easyviz'])

    def test_repository_ancestor_symlink_is_rejected(self):
        outside, marker = self.external_marker()
        link = self.root / 'generated'
        link.symlink_to(outside, target_is_directory=True)
        self.assert_rejected_without_sync(link / 'nested/dist')
        self.assertEqual(marker.read_bytes(), b'external files must stay untouched')
        self.assertFalse((outside / 'nested').exists())

    def test_build_directory_symlink_is_rejected(self):
        outside, marker = self.external_marker()
        self.dist.mkdir()
        target = self.dist / 'easyviz'
        target.symlink_to(outside / 'easyviz', target_is_directory=True)
        self.assert_rejected_without_sync()
        self.assertTrue(target.is_symlink())
        self.assertEqual(marker.read_bytes(), b'external files must stay untouched')

    def test_dangling_dist_and_output_symlinks_are_rejected(self):
        for relative in ('dist', 'dist/easyviz', 'dist/easyviz-1.0.0.zip', 'dist/build.json'):
            with self.subTest(path=relative):
                link = self.root / relative
                link.parent.mkdir(parents=True, exist_ok=True)
                link.symlink_to(self.base / 'missing')
                try:
                    self.assert_rejected_without_sync()
                    self.assertTrue(link.is_symlink())
                    self.assertFalse((self.base / 'missing').exists())
                finally:
                    link.unlink()

    def test_archive_and_summary_symlinks_preserve_external_files_and_previous_build(self):
        build_plugin.build()
        self.sync.reset_mock()
        previous = self.dist / 'easyviz/previous.txt'
        previous.write_bytes(b'previous build stays intact')
        outside = self.base / 'outside.bin'
        outside.write_bytes(b'unrelated external bytes')
        for name in ('easyviz-1.0.0.zip', 'build.json'):
            with self.subTest(path=name):
                output = self.dist / name
                original = output.read_bytes()
                output.unlink()
                output.symlink_to(outside)
                try:
                    self.assert_rejected_without_sync()
                    self.assertEqual(outside.read_bytes(), b'unrelated external bytes')
                    self.assertEqual(previous.read_bytes(), b'previous build stays intact')
                finally:
                    output.unlink()
                    output.write_bytes(original)

    def test_unidentified_existing_easyviz_directory_is_preserved(self):
        marker = self.dist / 'easyviz/keep.txt'
        marker.parent.mkdir(parents=True)
        marker.write_bytes(b'user directory')
        self.assert_rejected_without_sync(pattern='not identified as EasyViz')
        self.assertEqual(marker.read_bytes(), b'user directory')

    def test_parent_traversal_is_rejected(self):
        self.assert_rejected_without_sync(self.dist / '..' / 'outside', pattern='parent traversal')
        self.assertFalse((self.root / 'outside').exists())

    def test_unlisted_source_file_and_directory_links_preserve_previous_build(self):
        build_plugin.build()
        self.sync.reset_mock()
        previous = self.dist / 'easyviz/previous.txt'
        previous.write_bytes(b'previous build stays intact')
        archive = self.dist / 'easyviz-1.0.0.zip'
        original_archive = archive.read_bytes()
        outside, marker = self.external_marker()
        links = ((self.root / 'skills/easyviz/private.txt', marker),
                 (self.root / 'plugins/easyviz/assets/private-directory', marker.parent),
                 (self.root / 'plugins/easyviz/.codex-plugin/private.txt', marker))
        for link, destination in links:
            with self.subTest(path=link):
                link.symlink_to(destination, target_is_directory=destination.is_dir())
                try:
                    self.assert_rejected_without_sync(pattern='Symlink or special')
                    self.assertEqual(previous.read_bytes(), b'previous build stays intact')
                    self.assertEqual(archive.read_bytes(), original_archive)
                    self.assertEqual(marker.read_bytes(), b'external files must stay untouched')
                finally:
                    link.unlink()

    def test_source_ancestor_and_document_links_are_rejected(self):
        outside = self.base / 'external-document.txt'
        outside.write_bytes(b'private external document')
        for path in (self.root / 'plugins/easyviz/README.md', self.root / 'LICENSE',
                     self.root / 'THIRD_PARTY_NOTICES.md'):
            with self.subTest(path=path):
                content = path.read_bytes()
                path.unlink()
                path.symlink_to(outside)
                try:
                    self.assert_rejected_without_sync(pattern='Symlink or special')
                    self.assertEqual(outside.read_bytes(), b'private external document')
                    self.assertFalse(self.dist.exists())
                finally:
                    path.unlink()
                    path.write_bytes(content)
        plugins = self.root / 'plugins'
        external_plugins = self.base / 'external-plugins'
        plugins.rename(external_plugins)
        plugins.symlink_to(external_plugins, target_is_directory=True)
        self.assert_rejected_without_sync(pattern='Symlink or special')
        self.assertFalse(self.dist.exists())

    def test_special_source_resource_is_rejected_before_sync(self):
        fifo = self.root / 'skills/easyviz/private.pipe'
        os.mkfifo(fifo)
        self.assert_rejected_without_sync(pattern='Symlink or special')
        self.assertFalse(self.dist.exists())

    def test_link_introduced_by_sync_preserves_previous_build(self):
        build_plugin.build()
        self.sync.reset_mock()
        previous = self.dist / 'easyviz/previous.txt'
        previous.write_bytes(b'previous build stays intact')
        archive = self.dist / 'easyviz-1.0.0.zip'
        original_archive = archive.read_bytes()
        outside, marker = self.external_marker()
        link = self.root / 'skills/easyviz/generated-private.txt'
        self.sync.side_effect = lambda: link.symlink_to(marker)
        with self.assertRaisesRegex(ValueError, 'Symlink or special'):
            build_plugin.build()
        self.sync.assert_called_once()
        self.assertEqual(previous.read_bytes(), b'previous build stays intact')
        self.assertEqual(archive.read_bytes(), original_archive)
        self.assertEqual(marker.read_bytes(), b'external files must stay untouched')

    def test_build_destinations_overlapping_source_trees_are_rejected(self):
        before = {path.relative_to(self.root): path.read_bytes()
                  for path in self.root.rglob('*') if path.is_file()}
        for dist in (self.root / 'plugins', self.root / 'plugins/easyviz/output', self.root / 'skills/output'):
            with self.subTest(dist=dist):
                self.assert_rejected_without_sync(dist, pattern='overlaps the source tree')
        after = {path.relative_to(self.root): path.read_bytes()
                 for path in self.root.rglob('*') if path.is_file()}
        self.assertEqual(after, before)

    def test_external_ancestor_alias_into_source_is_rejected_before_recursive_copy(self):
        before = {path.relative_to(self.root): path.read_bytes()
                  for path in self.root.rglob('*') if path.is_file()}
        alias = self.base / 'outside-source-alias'
        alias.symlink_to(self.root / 'skills', target_is_directory=True)
        self.assert_rejected_without_sync(alias / 'generated-build', pattern='overlaps the source tree')
        self.assertFalse((self.root / 'skills/generated-build').exists())
        after = {path.relative_to(self.root): path.read_bytes()
                 for path in self.root.rglob('*') if path.is_file()}
        self.assertEqual(after, before)

    def test_default_build_is_valid_repeatable_and_preserves_unrelated_files(self):
        self.dist.mkdir()
        sibling = self.dist / 'unrelated.txt'
        sibling.write_bytes(b'keep sibling')
        summary = build_plugin.build()
        archive = self.dist / summary['archive']
        first = archive.read_bytes()
        self.assertEqual(summary, json.loads((self.dist / 'build.json').read_text()))
        self.assertEqual(summary['sha256'], hashlib.sha256(first).hexdigest())
        with zipfile.ZipFile(archive) as package:
            self.assertIsNone(package.testzip())
            self.assertIn('easyviz/.codex-plugin/plugin.json', package.namelist())
            self.assertIn('easyviz/skills/easyviz/scripts/render.py', package.namelist())
            for helper in ('figure_handoff.py', 'observation_clipping.py'):
                self.assertEqual(package.read('easyviz/skills/easyviz/scripts/' + helper),
                                 (self.root / 'skills/easyviz/scripts' / helper).read_bytes())
            for case, names in CURATED_CREATE_RESOURCES.items():
                for name in names:
                    relative = f"skills/easyviz/assets/cases/{case}/{name}"
                    self.assertEqual(package.read("easyviz/" + relative),
                                     (self.root / relative).read_bytes())
            self.assertFalse(any('__pycache__' in name for name in package.namelist()))
            self.assertTrue(all(info.date_time == (1980, 1, 1, 0, 0, 0) for info in package.infolist()))
            self.assertEqual(len(package.infolist()), summary['files'])
        stale = self.dist / 'easyviz/stale.txt'
        stale.write_bytes(b'old generated resource')
        self.assertEqual(build_plugin.build(), summary)
        self.assertEqual(archive.read_bytes(), first)
        self.assertFalse(stale.exists())
        self.assertEqual(sibling.read_bytes(), b'keep sibling')
        self.assertEqual((self.root / 'LICENSE').read_text(), 'License\n')

    def test_real_archive_omits_workbench_state_but_retains_scientific_examples_and_source(self):
        example = 'skills/easyviz/assets/cases/local-review'
        kept = {
            f'{example}/plot.py': b'print("scientific plotting source")\n',
            f'{example}/inputs/data.csv': b'group,value\nA,3\n',
            f'{example}/output/requests.json': b'{"requests": []}\n',
            f'{example}/output/figure-info.json': b'{"name": "Reviewed panel"}\n',
            f'{example}/output/panel.ev': b'portable example project\n',
            f'{example}/.easyviz-service-guide.md': b'legitimate descriptive resource\n',
        }
        omitted = {
            f'{example}/output/.requests.lock': b'local lock\n',
            f'{example}/.easyviz-service/registry.json': b'local private connection state\n',
            'plugins/easyviz/assets/.easyviz-service/registry.json': b'local asset review state\n',
            'plugins/easyviz/.codex-plugin/.requests.lock': b'local manifest lock\n',
        }
        for relative, content in (kept | omitted).items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        before = {path.relative_to(self.root): path.read_bytes()
                  for path in self.root.rglob('*') if path.is_file()}
        summary = build_plugin.build()
        with zipfile.ZipFile(self.dist / summary['archive']) as package:
            names = package.namelist()
            self.assertIsNone(package.testzip())
            self.assertFalse(any(part in ('.requests.lock', '.easyviz-service')
                                 for name in names for part in Path(name).parts))
            for relative, content in kept.items():
                self.assertEqual(package.read('easyviz/' + relative), content)
                self.assertEqual((self.dist / 'easyviz' / relative).read_bytes(), content)
            self.assertEqual(package.read('easyviz/skills/easyviz/scripts/render.py'),
                             (self.root / 'skills/easyviz/scripts/render.py').read_bytes())
        for relative, content in before.items():
            self.assertEqual((self.root / relative).read_bytes(), content)

    def test_archive_runtime_state_is_rejected_before_extraction_writes(self):
        summary = build_plugin.build()
        clean = (self.dist / summary['archive']).read_bytes()
        for member in ('easyviz/skills/easyviz/output/.requests.lock',
                       'easyviz/skills/easyviz/.easyviz-service/registry.json',
                       'easyviz/skills/easyviz/.easyviz-service/'):
            with self.subTest(member=member):
                archive = self.base / 'unexpected-state.zip'
                archive.write_bytes(clean)
                with zipfile.ZipFile(archive, 'a') as package:
                    package.writestr(member, b'local runtime state')
                destination = self.base / 'extracted'
                with self.assertRaisesRegex(ValueError, 'Workbench runtime state in ZIP'):
                    extract_package(archive, destination)
                self.assertFalse(destination.exists())

    def test_unpacked_package_runtime_state_is_rejected(self):
        for relative in ('.requests.lock', '.easyviz-service/registry.json'):
            with self.subTest(relative=relative):
                package = self.base / ('package-lock' if relative == '.requests.lock' else 'package-service')
                runtime = package / relative
                runtime.parent.mkdir(parents=True)
                runtime.write_bytes(b'local runtime state')
                with self.assertRaisesRegex(ValueError, 'Workbench runtime state in package'):
                    validate_resource_tree(package)

    def test_explicit_external_output_is_supported_and_preserves_unrelated_files(self):
        dist = self.base / 'custom-output/nested/dist'
        unrelated = self.base / 'custom-output/keep.txt'
        unrelated.parent.mkdir()
        unrelated.write_bytes(b'custom output neighbour')
        summary = build_plugin.build(dist)
        self.assertTrue((dist / summary['archive']).is_file())
        self.assertTrue((dist / 'easyviz/skills/easyviz/SKILL.md').is_file())
        self.assertEqual(unrelated.read_bytes(), b'custom output neighbour')
        self.assertFalse(self.dist.exists())

    def test_explicit_external_output_symlink_is_rejected(self):
        outside, marker = self.external_marker()
        dist = self.base / 'custom-output'
        dist.symlink_to(outside, target_is_directory=True)
        self.assert_rejected_without_sync(dist)
        self.assertEqual(marker.read_bytes(), b'external files must stay untouched')


if __name__ == '__main__':
    unittest.main()
