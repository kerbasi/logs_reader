import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from gui import _color_tag_for_log

class TestStatusColoring(unittest.TestCase):
    def test_pure_pass_log(self):
        log = {
            "name": "test_run_123.csv",
            "description": "2026-05-01 12:00:00  Pass  Everything works"
        }
        self.assertEqual(_color_tag_for_log(log), "pass_tag")

    def test_pure_fail_log(self):
        log = {
            "name": "test_run_123.csv",
            "description": "2026-05-01 12:00:00  Fail  Step 4 failed"
        }
        self.assertEqual(_color_tag_for_log(log), "fail_tag")

    def test_step_pass_but_run_fails(self):
        # Description contains 'pass' as substring in step name 'bypass', but also contains 'fail'
        log = {
            "name": "test_run_123.csv",
            "description": "2026-05-01 12:00:00  Fail  voltage_bypass_test: Fail"
        }
        # Precedence should prioritize Fail over Pass
        self.assertEqual(_color_tag_for_log(log), "fail_tag")

    def test_pass_step_name_with_fail_status(self):
        # Description has step name 'low_pass_filter' and status 'Error' or 'Fail'
        log1 = {
            "name": "test_run_123.csv",
            "description": "2026-05-01 12:00:00:low_pass_filter:Fail"
        }
        log2 = {
            "name": "test_run_123.csv",
            "description": "2026-05-01 12:00:00:first_pass:Error"
        }
        self.assertEqual(_color_tag_for_log(log1), "fail_tag")
        self.assertEqual(_color_tag_for_log(log2), "fail_tag")

    def test_conflict_in_filename(self):
        # If the file name itself contains conflicting keywords
        log = {
            "name": "log_FAIL_PASS.csv",
            "description": "Some neutral info"
        }
        self.assertEqual(_color_tag_for_log(log), "fail_tag")

if __name__ == "__main__":
    unittest.main()
