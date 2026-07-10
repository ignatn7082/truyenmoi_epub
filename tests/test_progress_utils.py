import os
import tempfile
import unittest

from services.progress import read_progress, write_progress


class ProgressUtilsTests(unittest.TestCase):
    def test_write_and_read_progress_payload(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            write_progress('abc123', 'SCAN', 35, 'Đang quét mục lục...', 12)
            payload = read_progress('abc123')

            self.assertEqual(payload['phase'], 'SCAN')
            self.assertEqual(payload['progress'], 35)
            self.assertEqual(payload['message'], 'Đang quét mục lục...')
            self.assertEqual(payload['total_chapters'], 12)


if __name__ == '__main__':
    unittest.main()
