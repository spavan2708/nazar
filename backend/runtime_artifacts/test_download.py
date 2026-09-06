"""Offline checks for the release integrity boundary; no ML or network required."""
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from download import digest, restore, run, fetch


class ArtifactIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.archive = self.root / 'bundle.tar.gz'
        self.file = dict(path='ml/model.bin', size_bytes=4, sha256=hashlib.sha256(b'test').hexdigest())

    def bundle(self, entries):
        with tarfile.open(self.archive, 'w:gz') as tar:
            for name, content, kind in entries:
                member = tarfile.TarInfo(name)
                member.type = kind
                member.size = len(content) if kind == tarfile.REGTYPE else 0
                member.linkname = '/tmp/forbidden' if kind == tarfile.SYMTYPE else ''
                tar.addfile(member, io.BytesIO(content) if member.isfile() else None)
        return dict(name=self.archive.name, size_bytes=self.archive.stat().st_size,
                    sha256=digest(self.archive), files=[self.file])

    def test_valid_bytes(self):
        bundle = self.bundle([('ml/model.bin', b'test', tarfile.REGTYPE)])
        restore(self.archive, bundle, self.root / 'out')
        self.assertEqual((self.root / 'out/ml/model.bin').read_bytes(), b'test')

    def test_invalid_members(self):
        for entries in [
            [('../escape', b'test', tarfile.REGTYPE)],
            [('ml/model.bin', b'', tarfile.SYMTYPE)],
            [('ml/model.bin', b'test', tarfile.REGTYPE)] * 2,
            [],
            [('ml/model.bin', b'test', tarfile.REGTYPE), ('extra', b'', tarfile.REGTYPE)],
        ]:
            with self.subTest(entries=entries):
                bundle = self.bundle(entries)
                with self.assertRaises(ValueError):
                    restore(self.archive, bundle, self.root / 'out')

    def test_archive_corruption(self):
        bundle = self.bundle([('ml/model.bin', b'test', tarfile.REGTYPE)])
        data = bytearray(self.archive.read_bytes()); data[-1] ^= 1
        self.archive.write_bytes(data)
        with self.assertRaisesRegex(ValueError, 'Integrity mismatch'):
            restore(self.archive, bundle, self.root / 'out')

    def test_file_corruption_even_with_valid_archive_hash(self):
        bundle = self.bundle([('ml/model.bin', b'evil', tarfile.REGTYPE)])
        with self.assertRaisesRegex(ValueError, 'Integrity mismatch'):
            restore(self.archive, bundle, self.root / 'out')

    def test_bounded_retries_and_timeout(self):
        with patch('download.urlopen', side_effect=TimeoutError) as request, patch('download.time.sleep') as sleep:
            with self.assertRaises(TimeoutError):
                fetch('https://github.com/test', self.root / 'download', 4)
            self.assertEqual(request.call_count, 3)
            self.assertTrue(all(c.kwargs['timeout'] == 60 for c in request.call_args_list))
            self.assertEqual([c.args[0] for c in sleep.call_args_list], [1, 2])

    def test_latest_url_rejected_without_network(self):
        manifest = self.root / 'manifest.json'
        manifest.write_text(json.dumps(dict(repository='spavan2708/nazar', artifact_version='v1',
            archives=[dict(name='bundle.tar.gz', url='https://github.com/spavan2708/nazar/releases/latest/download/bundle.tar.gz')])) )
        with patch('download.urlopen') as request:
            with self.assertRaisesRegex(ValueError, 'exact versioned'):
                run(manifest, self.root / 'out')
            request.assert_not_called()

    def test_unpublished_urls_fail_before_output(self):
        manifest = self.root / 'manifest.json'
        manifest.write_text(json.dumps(dict(repository='spavan2708/nazar', artifact_version='v1',
            archives=[dict(name='bundle.tar.gz', url=None)])))
        with self.assertRaisesRegex(ValueError, 'unpublished'):
            run(manifest, self.root / 'out')
        self.assertFalse((self.root / 'out').exists())


if __name__ == '__main__':
    unittest.main()
