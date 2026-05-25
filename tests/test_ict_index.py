import unittest
import tempfile
import shutil
import json
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.append(str(Path(__file__).parent.parent))

from src.ict_index import _parse_oper_id, ICTIndex, get_index


class TestParseOperId(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.dir_path = Path(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_parse_oper_id_simple(self):
        csv_file = self.dir_path / "test1.csv"
        csv_file.write_text("Col1,Col2,OperID,Col4\nval1,val2,12345,val4\n")
        val = _parse_oper_id(csv_file)
        self.assertEqual(val, "12345")

    def test_parse_oper_id_variations(self):
        # Test OPER_ID
        csv_file = self.dir_path / "test2.csv"
        csv_file.write_text("Col1,Col2,OPER_ID,Col4\nval1,val2,20992,val4\n")
        val = _parse_oper_id(csv_file)
        self.assertEqual(val, "20992")

        # Test oper id
        csv_file = self.dir_path / "test3.csv"
        csv_file.write_text("Col1,Col2,oper id,Col4\nval1,val2,21465,val4\n")
        val = _parse_oper_id(csv_file)
        self.assertEqual(val, "21465")

    def test_parse_oper_id_nonexistent(self):
        val = _parse_oper_id(self.dir_path / "nonexistent.csv")
        self.assertIsNone(val)

    def test_parse_oper_id_missing(self):
        csv_file = self.dir_path / "test_missing.csv"
        csv_file.write_text("Col1,Col2,Col3\nval1,val2,val3\n")
        val = _parse_oper_id(csv_file)
        self.assertIsNone(val)

    def test_parse_oper_id_at_limit(self):
        # Header at line 28 (0-indexed, so 29th line)
        lines = ["dummy,col"] * 28 + ["Col1,OperID", "val1,19455"]
        csv_file = self.dir_path / "test_limit.csv"
        csv_file.write_text("\n".join(lines))
        val = _parse_oper_id(csv_file)
        self.assertEqual(val, "19455")

        # Header at line 30 (which is i = 30, outside the loop limit)
        lines = ["dummy,col"] * 30 + ["Col1,OperID", "val1,19455"]
        csv_file2 = self.dir_path / "test_limit2.csv"
        csv_file2.write_text("\n".join(lines))
        val = _parse_oper_id(csv_file2)
        self.assertIsNone(val)


class TestICTIndex(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.root = Path(self.test_dir)
        self.index_file = self.root / "ict_log_index.json"

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_ict_index_scan_and_search(self):
        # Prepare mock directory structure
        # BASE_PATH/TRI401/202605/log_SN789.csv
        machine = "TRI401"
        month = "202605"
        log_dir = self.root / machine / month
        log_dir.mkdir(parents=True)
        
        log_file = log_dir / "test_SN789.csv"
        log_file.write_text("Col1,OperID\nval1,5590\n")
        
        # Instantiate index using a subclass/patch of BASE_PATH
        # We need to temporarily disable background loop to avoid side effects during test
        with patch("src.ict_index.HOT_REBUILD_INTERVAL", 99999), \
             patch("src.ict_index.FULL_REBUILD_INTERVAL", 99999), \
             patch.object(ICTIndex, "BASE_PATH", str(self.root)):
            
            # Start fresh index
            idx = ICTIndex(index_path=str(self.index_file))
            # Manually trigger a full build to populate mock files
            idx._build(months=None)
            
            # Search
            results = idx.search("SN789")
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["name"], "test_SN789.csv")
            self.assertEqual(results[0]["oper_id"], "5590")
            self.assertEqual(results[0]["tags"], ["ICT", machine])
            
            # Search non-existent
            results_none = idx.search("SN99999")
            self.assertEqual(len(results_none), 0)

            # Test reload from file
            idx2 = ICTIndex(index_path=str(self.index_file))
            self.assertIn(f"{machine}/{month}", idx2._data)
            self.assertEqual(idx2._data[f"{machine}/{month}"], ["test_SN789.csv"])


if __name__ == "__main__":
    unittest.main()
