import sys
import unittest
from pathlib import Path
from unittest.mock import patch, mock_open

sys.path.insert(0, str(Path(__file__).parent.parent))

from gui import _load_runners

class TestRunnersLoader(unittest.TestCase):
    def setUp(self):
        self.default_runners = {
            "19476": "Daniel Suima",
            "20992": "Oleg Karonin",
            "21465": "Dan Trievus",
            "19455": "Maxim Malabaev",
            "5590": "Vladimir Volik",
        }

    @patch("gui.Path.exists", return_value=False)
    @patch("builtins.open", new_callable=mock_open)
    def test_load_runners_fallback_when_no_file(self, mock_file, mock_exists):
        # Setup: Neither Path("runners.txt") nor _get_base_dir() / "runners.txt" exists
        # It should try to write the defaults and return them.
        runners = _load_runners()
        self.assertEqual(runners, self.default_runners)
        # Verify it tried to write to the base dir
        mock_file.assert_called_once()
        # Verify the first argument to open contained runners.txt
        opened_path = mock_file.call_args[0][0]
        self.assertTrue(str(opened_path).endswith("runners.txt"))
        self.assertEqual(mock_file.call_args[0][1], "w")

    @patch("gui.Path.is_file", return_value=True)
    @patch("gui.Path.exists", return_value=True)
    def test_load_runners_from_file(self, mock_exists, mock_is_file):
        mock_data = """
# This is a comment

12345: Test Runner
67890 = Another Runner
  spaced_id  :  Spaced Name  
invalidline
"""
        with patch("builtins.open", mock_open(read_data=mock_data)) as mock_file:
            runners = _load_runners()
            
            expected_result = {
                "12345": "Test Runner",
                "67890": "Another Runner",
                "spaced_id": "Spaced Name"
            }
            self.assertEqual(runners, expected_result)

    @patch("gui.Path.is_file", return_value=True)
    @patch("gui.Path.exists", return_value=True)
    def test_load_runners_empty_file_fallback(self, mock_exists, mock_is_file):
        with patch("builtins.open", mock_open(read_data="")) as mock_file:
            runners = _load_runners()
            # Should fallback to defaults since file is empty
            self.assertEqual(runners, self.default_runners)

if __name__ == "__main__":
    unittest.main()
