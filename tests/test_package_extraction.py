"""Archives fail preflight without overwrites or unbounded expansion."""
from pathlib import Path
import os
import stat
import struct
import sys
import tempfile
import unittest
from unittest import mock
import warnings
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check_package


class PackageExtractionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="easyviz-extraction-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.archive = self.root / "package.zip"
        self.destination = self.root / "extracted"

    def package(self, entries):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(self.archive, "w", compression=zipfile.ZIP_DEFLATED) as package:
                for name, content in entries:
                    package.writestr(name, content)

    def rejected_before_writes(self, message):
        with self.assertRaisesRegex(ValueError, message):
            check_package.extract_package(self.archive, self.destination)
        self.assertFalse(self.destination.exists())

    def test_normalized_aliases_are_rejected_before_any_extraction(self):
        for alias in ("easyviz/./README.md", "easyviz//README.md", "easyviz/README.md", "easyviz/readme.md"):
            with self.subTest(alias=alias):
                self.package([("easyviz/README.md", "first"), (alias, "overwritten")])
                self.rejected_before_writes("Duplicate normalized ZIP entry")

    def test_unicode_normalization_aliases_are_rejected(self):
        self.package([("easyviz/caf\u00e9.txt", "first"), ("easyviz/cafe\u0301.txt", "overwritten")])
        self.rejected_before_writes("Duplicate normalized ZIP entry")

    def test_file_directory_conflicts_are_rejected_regardless_of_entry_order(self):
        for entries in ([('easyviz/data', 'file'), ('easyviz/data/table.csv', 'rows')],
                        [('easyviz/data/table.csv', 'rows'), ('easyviz/data', 'file')],
                        [('easyviz/DATA', 'file'), ('easyviz/data/table.csv', 'rows')],
                        [('easyviz/data/', ''), ('easyviz/data', 'file')]):
            with self.subTest(entries=entries):
                self.package([("easyviz/README.md", "first safe entry"), *entries])
                self.rejected_before_writes("Conflicting file/directory ZIP paths|Duplicate normalized ZIP entry")

    def test_budget_rejections_do_not_extract_earlier_small_files(self):
        cases = [("MAX_ZIP_MEMBER_BYTES", 8,
                  [("easyviz/README.md", "small"), ("easyviz/large.txt", "x" * 9)], "ZIP member exceeds"),
                 ("MAX_ZIP_TOTAL_BYTES", 8,
                  [("easyviz/README.md", "small"), ("easyviz/other.txt", "four")], "ZIP expanded size exceeds"),
                 ("MAX_ZIP_ENTRIES", 1,
                  [("easyviz/README.md", "small"), ("easyviz/other.txt", "other")], "ZIP entry count exceeds")]
        for limit, value, entries, message in cases:
            with self.subTest(limit=limit):
                self.package(entries)
                with mock.patch.object(check_package, limit, value):
                    self.rejected_before_writes(message)

    def test_link_and_special_mode_members_are_rejected(self):
        for mode in (stat.S_IFLNK, stat.S_IFIFO, stat.S_IFSOCK):
            with self.subTest(mode=mode):
                info = zipfile.ZipInfo("easyviz/extra")
                info.create_system = 3
                info.external_attr = (mode | 0o644) << 16
                self.package([("easyviz/README.md", "small"), (info, "untrusted")])
                self.rejected_before_writes("Unsafe or unexpected ZIP entry")

    def test_existing_symlink_target_preserves_external_file_and_earlier_entries(self):
        self.destination.mkdir()
        external = self.root / "private.txt"
        external.write_text("keep private data")
        (self.destination / "easyviz").mkdir()
        (self.destination / "easyviz/README.md").symlink_to(external)
        self.package([("easyviz/first.txt", "new file"), ("easyviz/README.md", "overwrite")])
        with self.assertRaisesRegex(ValueError, "Symlink extraction path"):
            check_package.extract_package(self.archive, self.destination)
        self.assertEqual(external.read_text(), "keep private data")
        self.assertFalse((self.destination / "easyviz/first.txt").exists())

    def test_existing_parent_file_is_rejected_before_any_extraction(self):
        (self.destination / "easyviz").mkdir(parents=True)
        (self.destination / "easyviz/data").write_text("keep existing data")
        self.package([("easyviz/first.txt", "new file"), ("easyviz/data/table.csv", "rows")])
        with self.assertRaisesRegex(ValueError, "Conflicting existing extraction parent"):
            check_package.extract_package(self.archive, self.destination)
        self.assertEqual((self.destination / "easyviz/data").read_text(), "keep existing data")
        self.assertFalse((self.destination / "easyviz/first.txt").exists())

    def test_regular_archive_with_explicit_directories_extracts_normally(self):
        self.package([("easyviz/", ""), ("easyviz/data/", ""),
                      ("easyviz/README.md", "readme"), ("easyviz/data/table.csv", "x,y\n1,2\n")])
        self.assertEqual(check_package.extract_package(self.archive, self.destination), 4)
        self.assertEqual((self.destination / "easyviz/README.md").read_text(), "readme")
        self.assertEqual((self.destination / "easyviz/data/table.csv").read_text(), "x,y\n1,2\n")

    def test_late_crc_failure_preserves_previous_extracted_files(self):
        old = self.destination / 'easyviz/README.md'
        old.parent.mkdir(parents=True)
        old.write_bytes(b'previous valid package')
        with zipfile.ZipFile(self.archive, 'w', compression=zipfile.ZIP_STORED) as package:
            package.writestr('easyviz/README.md', b'new package')
            package.writestr('easyviz/late.txt', b'CRC failure')
        with zipfile.ZipFile(self.archive) as package:
            offset = package.getinfo('easyviz/late.txt').header_offset
        raw = bytearray(self.archive.read_bytes())
        name_length, extra_length = struct.unpack_from('<HH', raw, offset + 26)
        raw[offset + 30 + name_length + extra_length] ^= 1
        self.archive.write_bytes(raw)
        with self.assertRaisesRegex(zipfile.BadZipFile, 'Bad CRC-32'):
            check_package.extract_package(self.archive, self.destination)
        self.assertEqual(old.read_bytes(), b'previous valid package')
        self.assertFalse((old.parent / 'late.txt').exists())
        self.assertFalse(list(self.root.glob('.easyviz-extract-*')))

    def test_failed_extraction_publication_restores_listed_files_and_keeps_unrelated_files(self):
        old = self.destination / 'easyviz/README.md'
        old.parent.mkdir(parents=True)
        old.write_text('old readme')
        unrelated = old.parent / 'user-notes.txt'
        unrelated.write_text('user-owned notes')
        self.package([('easyviz/README.md', 'new readme'), ('easyviz/data/table.csv', 'rows')])
        real_replace = Path.replace
        failed = False
        def interrupted_replace(source, target):
            nonlocal failed
            if not failed and source.name == 'table.csv' and 'decoded' in source.parts:
                failed = True
                raise OSError('extraction publication interrupted')
            return real_replace(source, target)
        with mock.patch.object(Path, 'replace', interrupted_replace):
            with self.assertRaisesRegex(OSError, 'extraction publication interrupted'):
                check_package.extract_package(self.archive, self.destination)
        self.assertEqual(old.read_text(), 'old readme')
        self.assertEqual(unrelated.read_text(), 'user-owned notes')
        self.assertFalse((old.parent / 'data').exists())
        self.assertFalse(list(self.root.glob('.easyviz-extract-*')))

    def test_successful_merge_retains_unlisted_existing_files(self):
        notes = self.destination / 'easyviz/user-notes.txt'
        notes.parent.mkdir(parents=True)
        notes.write_text('keep user notes')
        self.package([('easyviz/README.md', 'readme')])
        self.assertEqual(check_package.extract_package(self.archive, self.destination), 1)
        self.assertEqual(notes.read_text(), 'keep user notes')

    def test_existing_hard_link_does_not_redirect_extraction_writes(self):
        external = self.root / 'private.txt'
        external.write_text('external original bytes')
        target = self.destination / 'easyviz/README.md'
        target.parent.mkdir(parents=True)
        os.link(external, target)
        self.package([('easyviz/README.md', 'new package bytes')])
        self.assertEqual(check_package.extract_package(self.archive, self.destination), 1)
        self.assertEqual(external.read_text(), 'external original bytes')
        self.assertEqual(target.read_text(), 'new package bytes')


if __name__ == "__main__":
    unittest.main()
