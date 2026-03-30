"""Tests for format_description()."""
import unittest
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from src.interface import format_description


class TestFormatDescription(unittest.TestCase):
    RAW = "2026|03|26|13.27.08:SN[612X7520230219]:ULT[N/A]:00:30:42:Fail:4-722-8357:ALL_VOLTAGE-SYSTEM_POWER_ON-STEP_TIMEOUT; (CTR6,flexc74)"

    def test_date_formatted(self):
        out = format_description(self.RAW)
        self.assertIn("2026-03-26", out)

    def test_time_formatted(self):
        out = format_description(self.RAW)
        self.assertIn("13:27:08", out)

    def test_ult_removed(self):
        out = format_description(self.RAW)
        self.assertNotIn("ULT", out)

    def test_sn_preserved(self):
        out = format_description(self.RAW)
        self.assertIn("SN[612X7520230219]", out)

    def test_duration_preserved(self):
        out = format_description(self.RAW)
        self.assertIn("00:30:42", out)

    def test_status_preserved(self):
        out = format_description(self.RAW)
        self.assertIn("Fail", out)

    def test_remainder_preserved(self):
        out = format_description(self.RAW)
        self.assertIn("ALL_VOLTAGE-SYSTEM_POWER_ON-STEP_TIMEOUT", out)

    def test_pipe_separators_gone(self):
        out = format_description(self.RAW)
        self.assertNotIn("|", out)

    def test_unknown_format_returned_as_is(self):
        raw = "some unstructured description"
        self.assertEqual(format_description(raw), raw)

    def test_full_output(self):
        expected = "2026-03-26  13:27:08  SN[612X7520230219]  00:30:42  Fail  4-722-8357  ALL_VOLTAGE-SYSTEM_POWER_ON-STEP_TIMEOUT; (CTR6,flexc74)"
        self.assertEqual(format_description(self.RAW), expected)


if __name__ == '__main__':
    unittest.main()
