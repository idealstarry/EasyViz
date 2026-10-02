"""Generated portable cases must not retain removed files or follow symlinks."""
from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/sync_skill_cases.py'
loader = importlib.util.spec_from_file_location('easyviz_sync_cases_test', SCRIPT)
sync_cases = importlib.util.module_from_spec(loader)
loader.loader.exec_module(sync_cases)


class SyncSkillCasesTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='easyviz-sync-test-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.assets = self.root / 'assets'
        self.patch = mock.patch.object(sync_cases, 'ASSETS', self.assets)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def sync(self):
        with redirect_stdout(io.StringIO()):
            sync_cases.sync()

    def test_refresh_removes_deleted_and_excluded_files_without_changing_sources(self):
        source = sync_cases.ROOT / 'examples/no-author-code/xiang-bubble-volcano'
        before = {str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in source.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
        self.sync()
        case = self.assets / 'cases/xiang-bubble-volcano'
        stale = [case / 'removed-data.csv', case / 'first-render/removed-archive.xlsx',
                 case / 'access-log.json', case / '__pycache__/removed.pyc']
        for path in stale:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'left over from a previous generated case')
        recipe = self.assets / 'recipes/annotated-heatmap'
        manual = [recipe / 'README.md', recipe / 'caption-template.md',
                  self.assets / 'fixtures/hand-maintained.txt']
        for path in manual:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'hand-maintained asset')
        self.sync()
        self.assertTrue((case / 'source-data.csv').is_file())
        self.assertTrue((recipe / 'plot.py').is_file())
        for path in stale:
            self.assertFalse(path.exists(), f'Stale file must not enter the next package: {path}')
        for path in manual:
            self.assertEqual(path.read_bytes(), b'hand-maintained asset')
        after = {str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in source.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
        self.assertEqual(before, after)

    def test_case_directory_symlink_is_rejected_before_any_target_is_cleared(self):
        outside = self.root / 'outside'
        outside.mkdir()
        note = outside / 'keep.txt'
        note.write_bytes(b'outside source stays untouched')
        first = self.assets / 'cases' / sync_cases.GENERATED_CASES[0]
        first.mkdir(parents=True)
        existing = first / 'existing.txt'
        existing.write_bytes(b'previous generated content')
        link = self.assets / 'cases/xiang-bubble-volcano'
        link.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symlink assets path'):
            self.sync()
        self.assertEqual(note.read_bytes(), b'outside source stays untouched')
        self.assertEqual(existing.read_bytes(), b'previous generated content')
        self.assertTrue(link.is_symlink())

    def test_cases_parent_symlink_is_rejected(self):
        outside = self.root / 'outside'
        outside.mkdir()
        note = outside / 'keep.txt'
        note.write_bytes(b'outside')
        self.assets.mkdir()
        (self.assets / 'cases').symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symlink assets path'):
            self.sync()
        self.assertEqual(note.read_bytes(), b'outside')
        self.assertEqual(list(outside.iterdir()), [note])

    def test_hand_maintained_recipe_output_symlink_is_not_followed(self):
        outside = self.root / 'outside-script.py'
        outside.write_bytes(b'outside script')
        recipe = self.assets / 'recipes/annotated-heatmap'
        recipe.mkdir(parents=True)
        (recipe / 'plot.py').symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'symlink assets path'):
            self.sync()
        self.assertEqual(outside.read_bytes(), b'outside script')
        self.assertFalse((self.assets / 'cases').exists())

    def test_repository_asset_ancestor_symlink_is_rejected_before_external_deletion(self):
        for ancestor in ('skills', 'skills/easyviz'):
            with self.subTest(ancestor=ancestor):
                repository = self.root / ancestor.replace('/', '-')
                repository.mkdir()
                outside = repository / 'external'
                suffix = Path('skills/easyviz').relative_to(ancestor)
                external_assets = outside / suffix / 'assets'
                marker = external_assets / 'cases/xiang-bubble-volcano/keep.bin'
                marker.parent.mkdir(parents=True)
                marker.write_bytes(b'external case must never be deleted')
                link = repository / ancestor
                link.parent.mkdir(parents=True, exist_ok=True)
                link.symlink_to(outside, target_is_directory=True)
                assets = repository / 'skills/easyviz/assets'
                with mock.patch.object(sync_cases, 'ROOT', repository), \
                        mock.patch.object(sync_cases, 'ASSETS', assets):
                    with self.assertRaisesRegex(ValueError, 'symlink assets path'):
                        self.sync()
                self.assertTrue(link.is_symlink())
                self.assertEqual(marker.read_bytes(), b'external case must never be deleted')
                self.assertEqual(list(external_assets.rglob('*')), [
                    external_assets / 'cases',
                    external_assets / 'cases/xiang-bubble-volcano', marker,
                ])


if __name__ == '__main__':
    unittest.main()
