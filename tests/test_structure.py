import unittest
import tempfile
import shutil
import os
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))
from src.core import LogSearcher

class TestLogSearcherStructure(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.root = Path(self.test_dir)
        self.pn = "S555"
        self.sn = "SN555"
        
        # Setup DIRECT YYYYMM structure (e.g. root/S555/202401/S555.mlnx)
        self.target_dir = self.root / self.pn / "202401"
        self.target_dir.mkdir(parents=True)
        
        (self.target_dir / f"{self.pn}.mlnx").write_text(f"found {self.sn} here")
        
        self.debug_dir = self.target_dir / "DEBUG"
        self.debug_dir.mkdir()
        (self.debug_dir / f"log_{self.sn}.gz").touch()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_finds_in_yyyymm_structure(self):
        searcher = LogSearcher([str(self.root)])
        results = searcher.search(self.pn, self.sn)
        self.assertEqual(len(results), 1)
        self.assertIn("log_SN555.gz", results[0]['name'])

if __name__ == '__main__':
    unittest.main()
