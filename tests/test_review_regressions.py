import json
import io
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from gui import LogReaderApp
from src.ict_index import ICTIndex, _parse_oper_id, _parse_pn
from src.led_viewer import build_led_html


class ReviewRegressions(unittest.TestCase):
    def test_led_archive_rejects_escape(self):
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder) / 'unsafe.gz'
            with tarfile.open(str(archive), 'w:gz') as tf:
                member = tarfile.TarInfo('../escaped.jpg')
                member.size = 1
                tf.addfile(member, io.BytesIO(b'x'))
            self.assertIsNone(build_led_html(str(archive)))

    def test_led_archive_produces_gallery(self):
        import shutil
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder) / "operator's.gz"
            with tarfile.open(str(archive), 'w:gz') as tf:
                member = tarfile.TarInfo('photo.jpg')
                member.size = 1
                tf.addfile(member, io.BytesIO(b'x'))
            result = build_led_html(str(archive))
            self.assertIsNotNone(result)
            try:
                self.assertIn('"photo.jpg"', Path(result).read_text(encoding='utf-8'))
                self.assertIn('document.title = "operator\'s.gz"', Path(result).read_text(encoding='utf-8'))
            finally:
                shutil.rmtree(str(Path(result).parent))

    def test_pn_mode_uses_csv_product_number(self):
        app = Mock()
        callbacks = []
        app.root.after.side_effect = lambda delay, callback: callbacks.append(callback)
        with patch('gui.ICTLogSearcher') as searcher:
            searcher.return_value.search_by_pn.return_value = []
            LogReaderApp._search_worker(app, 'pn', 'SFG-123', [])
            searcher.return_value.search_by_pn.assert_called_once_with(
                'SFG-123', from_month=None, to_month=None)
            searcher.return_value.search.assert_not_called()
        callbacks[0]()
        app._search_done.assert_called_once_with([])

    def test_search_error_survives_deferred_callback(self):
        app = Mock()
        callbacks = []
        app.root.after.side_effect = lambda delay, callback: callbacks.append(callback)
        with patch('gui.ICTLogSearcher', side_effect=OSError('unavailable')):
            LogReaderApp._search_worker(app, 'pn', 'SFG-123', [])
        callbacks[0]()
        app._search_done.assert_called_once_with([], 'Search error: unavailable')

    def test_quoted_csv_fields_do_not_shift_columns(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'log.csv'
            path.write_text('Comment,PN,OperID\n"one, two",SFG-123,5590\n')
            self.assertEqual(_parse_pn(path), 'SFG-123')
            self.assertEqual(_parse_oper_id(path), '5590')

    def test_full_build_timestamp_survives_hot_refresh(self):
        with tempfile.TemporaryDirectory() as folder, \
                patch.object(ICTIndex, '_start_background'), \
                patch.object(ICTIndex, 'BASE_PATH', folder):
            path = Path(folder) / 'index.json'
            idx = ICTIndex(str(path))
            idx._build()
            full_stamp = json.loads(path.read_text())['_full_built_at']
            idx._build(months=['202601'])
            self.assertEqual(json.loads(path.read_text())['_full_built_at'], full_stamp)
            self.assertGreater(ICTIndex(str(path))._last_full_build, 0)

    def test_first_background_pass_builds_old_months(self):
        with tempfile.TemporaryDirectory() as folder, \
                patch.object(ICTIndex, '_start_background'), \
                patch.object(ICTIndex, 'BASE_PATH', folder):
            log_dir = Path(folder) / 'TRI401' / '202001'
            log_dir.mkdir(parents=True)
            (log_dir / 'log_SN123.csv').write_text('PN\nSFG-123\n')
            idx = ICTIndex(str(Path(folder) / 'index.json'))
            with patch('src.ict_index.time.sleep', side_effect=InterruptedError):
                with self.assertRaises(InterruptedError):
                    idx._background_loop()
            self.assertEqual(len(idx.search('SN123')), 1)


if __name__ == '__main__':
    unittest.main()
