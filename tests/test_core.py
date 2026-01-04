import unittest
import tempfile
import shutil
import os
from pathlib import Path
import sys

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.core import LogSearcher, ProductResolver

class TestLogSearcher(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp()
        self.root = Path(self.test_dir)
        
        # Setup dummy log structure
        # Structure: root/S12345/2024/01/S12345.mlnx
        #            root/S12345/2024/01/DEBUG/log_SN123.gz
        
        self.pn = "S12345"
        self.sn = "SN123"
        
        year_dir = self.root / self.pn / "2024" / "01"
        year_dir.mkdir(parents=True)
        
        # Create index file
        index_file = year_dir / f"{self.pn}.mlnx"
        with open(index_file, 'w') as f:
            f.write(f"Some info... {self.sn} ... more info\n")
            
        # Create debug dir and log file
        debug_dir = year_dir / "DEBUG"
        debug_dir.mkdir()
        
        log_file = debug_dir / f"some_log_{self.sn}.gz"
        with open(log_file, 'w') as f:
            f.write("Log content")
            
        # Create a dummy file that shouldn't match
        (debug_dir / "other_log.gz").touch()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_search_finds_log(self):
        searcher = LogSearcher([str(self.root)])
        results = searcher.search(self.pn, self.sn)
        
        self.assertEqual(len(results), 1)
        self.assertIn(self.sn, results[0]['name'])
        self.assertTrue(results[0]['path'].startswith(str(self.root)))

    def test_search_no_match(self):
        searcher = LogSearcher([str(self.root)])
        results = searcher.search(self.pn, "WRONGSN")
        self.assertEqual(len(results), 0)

if __name__ == '__main__':
    unittest.main()
