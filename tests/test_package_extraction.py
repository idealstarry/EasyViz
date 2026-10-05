"""Archives fail preflight without overwrites or unbounded expansion."""
from pathlib import Path
import stat
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


if __name__ == "__main__":
    unittest.main()
