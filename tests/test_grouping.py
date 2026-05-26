"""Tests for _group_logs — SUMMARY companion grouping in SN text results."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Import only the module-level helpers; no display needed.
from gui import _group_logs


def _make_log(name: str, parent: str = "/logs/dir") -> dict:
    return {"name": name, "path": f"{parent}/{name}", "tags": [], "description": "", "date": 0}


class TestGroupLogsDatedFiles(unittest.TestCase):
    """Files with parseable dates — matched by (parent, dt) key."""

    def test_single_pair_grouped(self):
        main = _make_log("y2026_m04_d16_10.07.26_SN123.csv")
        summ = _make_log("SUMMARY_y2026_m04_d16_10.07.26_SN123.csv")
        result = _group_logs([main, summ])
        self.assertEqual(len(result), 1)
        m, children = result[0]
        self.assertIs(m, main)
        self.assertEqual(children, [summ])

    def test_two_pairs_each_grouped_separately(self):
        main1 = _make_log("y2026_m04_d16_10.07.26_SN123.csv")
        summ1 = _make_log("SUMMARY_y2026_m04_d16_10.07.26_SN123.csv")
        main2 = _make_log("y2026_m05_d01_08.00.00_SN123.csv")
        summ2 = _make_log("SUMMARY_y2026_m05_d01_08.00.00_SN123.csv")
        result = _group_logs([main1, summ1, main2, summ2])
        self.assertEqual(len(result), 2)
        names = {r[0]["name"] for r in result}
        self.assertIn(main1["name"], names)
        self.assertIn(main2["name"], names)
        for m, children in result:
            self.assertEqual(len(children), 1)
            self.assertIn("SUMMARY", children[0]["name"])


class TestGroupLogsUndatedFiles(unittest.TestCase):
    """Files without parseable dates — positional pairing within same directory."""

    def test_undated_pair_grouped_positionally(self):
        main = _make_log("log_SN123.csv")
        summ = _make_log("SUMMARY_SN123.csv")
        result = _group_logs([main, summ])
        self.assertEqual(len(result), 1)
        m, children = result[0]
        self.assertIs(m, main)
        self.assertEqual(children, [summ])

    def test_two_undated_mains_one_summary_each(self):
        """Two undated mains and two undated SUMMARYs — each gets one companion."""
        main1 = _make_log("log_SN1.csv")
        main2 = _make_log("log_SN2.csv")
        summ1 = _make_log("SUMMARY_SN1.csv")
        summ2 = _make_log("SUMMARY_SN2.csv")
        result = _group_logs([main1, summ1, main2, summ2])
        self.assertEqual(len(result), 2)
        for m, children in result:
            self.assertEqual(len(children), 1, f"{m['name']} should have exactly 1 companion")

    def test_undated_summary_without_main_appears_standalone(self):
        summ = _make_log("SUMMARY_SN999.csv")
        result = _group_logs([summ])
        self.assertEqual(len(result), 1)
        m, children = result[0]
        self.assertIs(m, summ)
        self.assertEqual(children, [])

    def test_more_summaries_than_mains_extras_standalone(self):
        main = _make_log("log_SN1.csv")
        summ1 = _make_log("SUMMARY_SN1.csv")
        summ2 = _make_log("SUMMARY_SN2.csv")  # no matching main
        result = _group_logs([main, summ1, summ2])
        self.assertEqual(len(result), 2)
        paired = [(m, c) for m, c in result if m is main]
        standalone = [(m, c) for m, c in result if m is summ2]
        self.assertEqual(len(paired[0][1]), 1)
        self.assertEqual(standalone[0][1], [])


class TestGroupLogsMixed(unittest.TestCase):
    """Non-SUMMARY files that don't contain SUMMARY pass through unchanged."""

    def test_non_summary_files_all_numbered(self):
        logs = [_make_log(f"log_{i}.csv") for i in range(3)]
        result = _group_logs(logs)
        self.assertEqual(len(result), 3)
        for m, children in result:
            self.assertEqual(children, [])

    def test_ict_csv_files_not_grouped(self):
        """ICT files (no SUMMARY in name) are never treated as companions."""
        logs = [_make_log(f"TRI401_SN123_run{i}.csv") for i in range(2)]
        result = _group_logs(logs)
        self.assertEqual(len(result), 2)


if __name__ == "__main__":
    unittest.main()
