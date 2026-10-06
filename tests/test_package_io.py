"""Publication rollback must preserve the actual recoverable prior bytes."""
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from package_io import OutputRollbackError, file_sha256, replace_outputs, staging_directory


class PackageIOTests(unittest.TestCase):
    def test_hash_is_identical_without_materializing_the_whole_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'resource.bin'
            content = b'portable resource\0' * 150000
            path.write_bytes(content)
            expected = hashlib.sha256(content).hexdigest()
            with mock.patch.object(Path, 'read_bytes', side_effect=AssertionError('unbounded read')):
                self.assertEqual(file_sha256(path), expected)

    def test_failed_rollback_retains_recovery_directory_and_previous_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            target = parent / 'output.txt'
            target.write_bytes(b'previous valid output')
            real_replace = Path.replace
            def interrupted_replace(source, destination):
                if source.name in ('candidate.txt', '0'):
                    raise OSError('publication and restoration unavailable')
                return real_replace(source, destination)
            with self.assertRaisesRegex(OutputRollbackError, 'recovery retained at'):
                with staging_directory(parent, '.test-stage-') as staging:
                    source = staging / 'candidate.txt'
                    source.write_bytes(b'candidate output')
                    with mock.patch.object(Path, 'replace', interrupted_replace):
                        replace_outputs([(source, target)], staging, lambda path: None)
            retained = list(parent.glob('.test-stage-*'))
            self.assertEqual(len(retained), 1)
            self.assertEqual((retained[0] / 'rollback/0').read_bytes(), b'previous valid output')


if __name__ == '__main__':
    unittest.main()
