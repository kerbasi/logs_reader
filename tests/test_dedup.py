"""
Tests for DEBUG-vs-parent deduplication rule:
  If DEBUG contains any match for an SN, parent dir files are ignored entirely.
"""
import unittest
import tempfile
import shutil
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))
from src.core import LogSearcher


class TestDebugTakesPriority(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.root = Path(self.test_dir)
        self.pn = "S400"
        self.sn = "SN400"
        self.month_dir = self.root / self.pn / "2024" / "01"
        self.debug_dir = self.month_dir / "DEBUG"
        self.month_dir.mkdir(parents=True)
        self.debug_dir.mkdir()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def _make(self, directory, filename):
        (directory / filename).write_text("data")

    def test_debug_file_suppresses_same_name_in_parent(self):
        """Exact same filename in DEBUG → parent copy must not appear."""
        self._make(self.debug_dir, f"log_{self.sn}.gz")
        self._make(self.month_dir, f"log_{self.sn}.gz")

        results = LogSearcher([str(self.root)]).search(self.pn, self.sn)

        self.assertEqual(len(results), 1)
        self.assertIn("DEBUG", results[0]['path'])

    def test_debug_file_suppresses_different_name_in_parent(self):
        """Different filenames but same SN: DEBUG match suppresses ALL parent matches."""
        self._make(self.debug_dir, f"log_{self.sn}_v2.gz")
        self._make(self.month_dir, f"log_{self.sn}_v1.gz")

        results = LogSearcher([str(self.root)]).search(self.pn, self.sn)

        self.assertEqual(len(results), 1)
        self.assertIn("DEBUG", results[0]['path'])
        self.assertIn("v2", results[0]['name'])

    def test_debug_file_suppresses_multiple_parent_files(self):
        """Multiple parent matches are all suppressed when DEBUG has any match."""
        self._make(self.debug_dir, f"log_{self.sn}.gz")
        self._make(self.month_dir, f"log_{self.sn}_a.gz")
        self._make(self.month_dir, f"log_{self.sn}_b.gz")

        results = LogSearcher([str(self.root)]).search(self.pn, self.sn)

        self.assertEqual(len(results), 1)
        self.assertIn("DEBUG", results[0]['path'])

    def test_parent_shown_when_debug_has_no_match(self):
        """DEBUG exists but has no SN match → parent files are shown."""
        self._make(self.debug_dir, "unrelated_file.gz")   # does not match SN
        self._make(self.month_dir, f"log_{self.sn}.gz")

        results = LogSearcher([str(self.root)]).search(self.pn, self.sn)

        self.assertEqual(len(results), 1)
        self.assertNotIn("DEBUG", results[0]['path'])

    def test_parent_shown_when_no_debug_dir(self):
        """No DEBUG directory at all → parent files are shown normally."""
        self.debug_dir.rmdir()
        self._make(self.month_dir, f"log_{self.sn}.gz")

        results = LogSearcher([str(self.root)]).search(self.pn, self.sn)

        self.assertEqual(len(results), 1)
        self.assertNotIn("DEBUG", results[0]['path'])

    def test_multiple_debug_files_all_shown(self):
        """Multiple files in DEBUG all appear (only parent is suppressed)."""
        self._make(self.debug_dir, f"log_{self.sn}_a.gz")
        self._make(self.debug_dir, f"log_{self.sn}_b.gz")
        self._make(self.month_dir, f"log_{self.sn}_old.gz")

        results = LogSearcher([str(self.root)]).search(self.pn, self.sn)

        self.assertEqual(len(results), 2)
        self.assertTrue(all("DEBUG" in r['path'] for r in results))


if __name__ == '__main__':
    unittest.main()
