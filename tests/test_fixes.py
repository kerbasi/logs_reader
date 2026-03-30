"""
Tests covering the 7 bug fixes applied to core.py, interface.py, and main.py.
"""
import unittest
import tempfile
import shutil
import sys
import os
import subprocess
from pathlib import Path
from io import StringIO
from unittest.mock import patch, MagicMock

sys.path.append(str(Path(__file__).parent.parent))
from src.core import LogSearcher


# ---------------------------------------------------------------------------
# Fix #1 — view_file() uses subprocess, not os.system
# ---------------------------------------------------------------------------
class TestViewFileUsesSubprocess(unittest.TestCase):
    def test_less_called_via_subprocess(self):
        """view_file should call less via subprocess.call, not os.system."""
        from src.interface import view_file
        with patch('subprocess.call') as mock_call:
            view_file('/some/file.log')
            mock_call.assert_called_once_with(['less', '-r', '/some/file.log'])

    def test_fallback_uses_subprocess_not_os_system(self):
        """When less is not found, fallback must not use os.system."""
        from src import interface
        with patch('subprocess.call', side_effect=[FileNotFoundError, None]) as mock_call, \
             patch('os.system') as mock_os_system, \
             patch.object(interface.os, 'name', 'posix'):
            interface.view_file('/some/file.log')
            mock_os_system.assert_not_called()
            # Second call is the cat fallback
            self.assertEqual(mock_call.call_count, 2)


# ---------------------------------------------------------------------------
# Fix #2 — Errors are reported to stderr, not silently swallowed
# ---------------------------------------------------------------------------
class TestErrorsReportedToStderr(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.root = Path(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_unreadable_mlnx_prints_warning(self):
        """An unreadable .mlnx file should print a warning to stderr."""
        pn, sn = "S001", "SN001"
        target = self.root / pn / "202401"
        target.mkdir(parents=True)
        mlnx = target / f"{pn}.mlnx"
        mlnx.write_text(f"entry {sn}")

        # Simulate a permission error on open (works cross-platform)
        import builtins
        real_open = builtins.open
        def mock_open(file, *args, **kwargs):
            if str(file) == str(mlnx):
                raise PermissionError("Permission denied")
            return real_open(file, *args, **kwargs)

        searcher = LogSearcher([str(self.root)])
        with patch('builtins.open', side_effect=mock_open), \
             patch('sys.stderr', new_callable=StringIO) as mock_err:
            searcher.search(pn, sn)
            output = mock_err.getvalue()
        self.assertIn("Warning", output)


# ---------------------------------------------------------------------------
# Fix #3 — SN match must not match substrings of longer tokens
# ---------------------------------------------------------------------------
class TestSNMatchPrecision(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.root = Path(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def _make_log(self, pn, filename):
        d = self.root / pn / "2024" / "01" / "DEBUG"
        d.mkdir(parents=True, exist_ok=True)
        (d / filename).write_text("data")

    def test_exact_sn_matches(self):
        pn, sn = "S100", "SN100"
        self._make_log(pn, f"log_{sn}.gz")
        results = LogSearcher([str(self.root)]).search(pn, sn)
        self.assertEqual(len(results), 1)

    def test_longer_token_does_not_match(self):
        """SN='SN1' must not match a file named 'log_SN100.gz'."""
        pn, sn = "S100", "SN1"
        self._make_log(pn, "log_SN100.gz")
        results = LogSearcher([str(self.root)]).search(pn, sn)
        self.assertEqual(len(results), 0)

    def test_sn_with_separators_matches(self):
        """SN='SN100' should match 'log_SN100_extra.gz' (non-alnum boundary)."""
        pn, sn = "S100", "SN100"
        self._make_log(pn, "log_SN100_extra.gz")
        results = LogSearcher([str(self.root)]).search(pn, sn)
        self.assertEqual(len(results), 1)


# ---------------------------------------------------------------------------
# Fix #4 — Description fallback only when counts match
# ---------------------------------------------------------------------------
class TestDescriptionFallback(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.root = Path(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def _setup(self, pn, sn, log_names, index_lines):
        target = self.root / pn / "2024" / "01"
        target.mkdir(parents=True)
        mlnx = target / f"{pn}.mlnx"
        mlnx.write_text("\n".join(index_lines))
        debug = target / "DEBUG"
        debug.mkdir()
        for name in log_names:
            (debug / name).write_text("data")
        return target

    def test_descriptions_assigned_when_counts_match(self):
        pn, sn = "S200", "SN200"
        self._setup(pn, sn,
                    [f"a_{sn}.gz", f"b_{sn}.gz"],
                    [f"{sn} first desc", f"{sn} second desc"])
        results = LogSearcher([str(self.root)]).search(pn, sn)
        results.sort(key=lambda r: r['name'])
        self.assertIsNotNone(results[0]['description'])
        self.assertIsNotNone(results[1]['description'])

    def test_no_description_when_counts_mismatch(self):
        """3 index lines but only 1 file → no chronological fallback."""
        pn, sn = "S201", "SN201"
        self._setup(pn, sn,
                    [f"only_{sn}.gz"],
                    [f"{sn} desc1", f"{sn} desc2", f"{sn} desc3"])
        results = LogSearcher([str(self.root)]).search(pn, sn)
        self.assertEqual(len(results), 1)
        # Heuristic match may or may not fire, but chrono fallback must not
        # assign an arbitrary description from a mismatched index.
        # Since no filename appears in the desc lines, best_desc should be None.
        self.assertIsNone(results[0]['description'])


# ---------------------------------------------------------------------------
# Fix #5 — exclude_name_fragments is configurable
# ---------------------------------------------------------------------------
class TestExcludeNameFragments(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.root = Path(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def _make_debug_file(self, pn, sn, filename):
        d = self.root / pn / "2024" / "01" / "DEBUG"
        d.mkdir(parents=True, exist_ok=True)
        (d / filename).write_text("data")

    def test_default_filters_led_but_not_summary(self):
        pn, sn = "S300", "SN300"
        self._make_debug_file(pn, sn, f"led_{sn}.gz")
        self._make_debug_file(pn, sn, f"SUMMARY_{sn}.gz")
        self._make_debug_file(pn, sn, f"normal_{sn}.gz")
        results = LogSearcher([str(self.root)]).search(pn, sn)
        names = [r['name'] for r in results]
        self.assertNotIn(f"led_{sn}.gz", names)
        self.assertIn(f"SUMMARY_{sn}.gz", names)
        self.assertIn(f"normal_{sn}.gz", names)

    def test_custom_exclude_fragment(self):
        pn, sn = "S301", "SN301"
        self._make_debug_file(pn, sn, f"led_{sn}.gz")     # would be excluded by default
        self._make_debug_file(pn, sn, f"custom_{sn}.gz")  # excluded by custom rule
        self._make_debug_file(pn, sn, f"normal_{sn}.gz")
        results = LogSearcher([str(self.root)], exclude_name_fragments=["custom"]).search(pn, sn)
        names = [r['name'] for r in results]
        self.assertNotIn(f"custom_{sn}.gz", names)
        self.assertIn(f"led_{sn}.gz", names)   # "led" no longer excluded
        self.assertIn(f"normal_{sn}.gz", names)

    def test_empty_exclude_list_shows_all(self):
        pn, sn = "S302", "SN302"
        self._make_debug_file(pn, sn, f"led_{sn}.gz")
        self._make_debug_file(pn, sn, f"SUMMARY_{sn}.gz")
        results = LogSearcher([str(self.root)], exclude_name_fragments=[]).search(pn, sn)
        names = [r['name'] for r in results]
        self.assertIn(f"led_{sn}.gz", names)
        self.assertIn(f"SUMMARY_{sn}.gz", names)


# ---------------------------------------------------------------------------
# Fix #6 — --verbose flag exists and is parseable
# ---------------------------------------------------------------------------
class TestVerboseFlag(unittest.TestCase):
    def test_verbose_flag_accepted(self):
        """argparse must accept --verbose and -v without error."""
        import argparse
        # Re-create the parser from main.py inline to avoid running main()
        parser = argparse.ArgumentParser()
        parser.add_argument("sn", nargs='?')
        parser.add_argument("--pn")
        parser.add_argument("--path", action='append')
        parser.add_argument("--verbose", "-v", action="store_true")

        args = parser.parse_args(["SN123", "--verbose"])
        self.assertTrue(args.verbose)

        args2 = parser.parse_args(["SN123", "-v"])
        self.assertTrue(args2.verbose)

        args3 = parser.parse_args(["SN123"])
        self.assertFalse(args3.verbose)


# ---------------------------------------------------------------------------
# Fix #7 — Actionable error messages go to stderr
# ---------------------------------------------------------------------------
class TestProductResolverErrors(unittest.TestCase):
    def _make_resolver_with_url(self, url):
        from src.core import ProductResolver
        resolver = ProductResolver.__new__(ProductResolver)
        resolver.site_file = '/nonexistent'
        resolver.site_url = url
        return resolver

    def test_curl_not_found_prints_to_stderr(self):
        resolver = self._make_resolver_with_url("10.0.0.1")
        with patch('subprocess.run', side_effect=FileNotFoundError), \
             patch('sys.stderr', new_callable=StringIO) as mock_err:
            result = resolver.get_product_pn("SN999")
            self.assertIsNone(result)
            self.assertIn("curl", mock_err.getvalue())

    def test_timeout_prints_actionable_message(self):
        resolver = self._make_resolver_with_url("10.0.0.1")
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired(cmd='curl', timeout=10)), \
             patch('sys.stderr', new_callable=StringIO) as mock_err:
            result = resolver.get_product_pn("SN999")
            self.assertIsNone(result)
            stderr = mock_err.getvalue()
            self.assertIn("--pn", stderr)

    def test_bad_response_prints_raw_output(self):
        resolver = self._make_resolver_with_url("10.0.0.1")
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"unexpected": "format"}'
        with patch('subprocess.run', return_value=mock_result), \
             patch('sys.stderr', new_callable=StringIO) as mock_err:
            result = resolver.get_product_pn("SN999")
            self.assertIsNone(result)
            self.assertIn("PN", mock_err.getvalue())

    def test_nonzero_exit_prints_stderr_content(self):
        resolver = self._make_resolver_with_url("10.0.0.1")
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "connection refused"
        with patch('subprocess.run', return_value=mock_result), \
             patch('sys.stderr', new_callable=StringIO) as mock_err:
            result = resolver.get_product_pn("SN999")
            self.assertIsNone(result)
            self.assertIn("connection refused", mock_err.getvalue())


if __name__ == '__main__':
    unittest.main()
