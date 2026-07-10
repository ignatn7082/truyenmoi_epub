import os
import tempfile
import unittest

from services.progress import read_progress, write_progress


class ProgressUtilsTests(unittest.TestCase):
    def test_write_and_read_progress_payload(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            write_progress(
                'abc123',
                phase='SCAN',
                progress=35,
                message='Đang quét mục lục...',
                total_chapters=12,
                completed_chapters=5,
                current_chapter=2,
                chapter_title='Chương 2',
                extra={'scanned_pages': 3}
            )
            payload = read_progress('abc123')

            self.assertEqual(payload['phase'], 'SCAN')
            self.assertEqual(payload['progress'], 35)
            self.assertEqual(payload['message'], 'Đang quét mục lục...')
            self.assertEqual(payload['total_chapters'], 12)
            self.assertEqual(payload['completed_chapters'], 5)
            self.assertEqual(payload['current_chapter'], 2)
            self.assertEqual(payload['chapter_title'], 'Chương 2')
            self.assertEqual(payload['extra']['scanned_pages'], 3)


if __name__ == '__main__':
    unittest.main()
