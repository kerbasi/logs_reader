import unittest
import tempfile
import shutil
import json
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.append(str(Path(__file__).parent.parent))

from src.ict_index import _parse_oper_id, _parse_pn, ICTIndex, get_index


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


class TestParsePn(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.dir_path = Path(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_parse_pn_simple(self):
        csv_file = self.dir_path / "test.csv"
        csv_file.write_text("Col1,PN,Col3\nval1,SFG123,val3\n")
        self.assertEqual(_parse_pn(csv_file), "SFG123")

    def test_parse_pn_partno(self):
        csv_file = self.dir_path / "test.csv"
        csv_file.write_text("Col1,PartNo,Col3\nval1,SFG456,val3\n")
        self.assertEqual(_parse_pn(csv_file), "SFG456")

    def test_parse_pn_partnumber(self):
        csv_file = self.dir_path / "test.csv"
        csv_file.write_text("Col1,PartNumber,Col3\nval1,SFG789,val3\n")
        self.assertEqual(_parse_pn(csv_file), "SFG789")

    def test_parse_pn_missing(self):
        csv_file = self.dir_path / "test.csv"
        csv_file.write_text("Col1,Col2,Col3\nval1,val2,val3\n")
        self.assertIsNone(_parse_pn(csv_file))

    def test_parse_pn_nonexistent(self):
        self.assertIsNone(_parse_pn(self.dir_path / "nope.csv"))


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
            self.assertIn("test_SN789.csv", idx2._data[f"{machine}/{month}"])
            self.assertEqual(idx2._data[f"{machine}/{month}"]["test_SN789.csv"], "5590")

    def test_search_by_pn(self):
        machine = "TRI401"
        month = "202605"
        log_dir = self.root / machine / month
        log_dir.mkdir(parents=True)

        log_file = log_dir / "test_SN789.csv"
        log_file.write_text("Col1,PN,OperID\nval1,SFG-TEST,5590\n")

        with patch("src.ict_index.HOT_REBUILD_INTERVAL", 99999), \
             patch("src.ict_index.FULL_REBUILD_INTERVAL", 99999), \
             patch.object(ICTIndex, "BASE_PATH", str(self.root)):

            idx = ICTIndex(index_path=str(self.index_file))
            idx._build(months=None)

            results = idx.search_by_pn("SFG-TEST")
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["name"], "test_SN789.csv")
            self.assertEqual(results[0]["tags"], ["ICT", machine])

            results_none = idx.search_by_pn("SFG-NOPE")
            self.assertEqual(len(results_none), 0)

            # PN index persists to disk and reloads
            idx2 = ICTIndex(index_path=str(self.index_file))
            self.assertIn("SFG-TEST", idx2._pn_index)

    def test_search_month_filter(self):
        for machine in ("TRI401",):
            for month in ("202503", "202504", "202505"):
                d = self.root / machine / month
                d.mkdir(parents=True)
                (d / f"log_{machine}_{month}.csv").write_text("Col\nval\n")

        with patch("src.ict_index.HOT_REBUILD_INTERVAL", 99999), \
             patch("src.ict_index.FULL_REBUILD_INTERVAL", 99999), \
             patch.object(ICTIndex, "BASE_PATH", str(self.root)):

            idx = ICTIndex(index_path=str(self.index_file))
            idx._build(months=None)

            all_results = idx.search("TRI401")
            self.assertEqual(len(all_results), 3)

            filtered = idx.search("TRI401", from_month="202504", to_month="202504")
            self.assertEqual(len(filtered), 1)
            self.assertIn("202504", filtered[0]["path"])

            from_only = idx.search("TRI401", from_month="202504")
            self.assertEqual(len(from_only), 2)

            to_only = idx.search("TRI401", to_month="202504")
            self.assertEqual(len(to_only), 2)

    def test_hot_rebuild_deduplicates_pn_index(self):
        machine = "TRI401"
        month = "202605"
        log_dir = self.root / machine / month
        log_dir.mkdir(parents=True)

        (log_dir / "log1.csv").write_text("PN\nSFG-A\n")

        with patch("src.ict_index.HOT_REBUILD_INTERVAL", 99999), \
             patch("src.ict_index.FULL_REBUILD_INTERVAL", 99999), \
             patch.object(ICTIndex, "BASE_PATH", str(self.root)):

            idx = ICTIndex(index_path=str(self.index_file))
            idx._build(months=[month])
            idx._build(months=[month])  # second hot rebuild of same month

            paths = idx._pn_index.get("SFG-A", [])
            self.assertEqual(len(paths), 1, "hot rebuild must not duplicate PN entries")


if __name__ == "__main__":
    unittest.main()
