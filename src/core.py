import os
import subprocess
import re
import json
import sys
from pathlib import Path
from typing import List, Dict, Optional

from .ict_index import get_index


class ICTLogSearcher:
    def search(self, sn: str) -> List[Dict]:
        return get_index().search(sn)


class ProductResolver:
    """
    Resolves Serial Number (SN) to Product Part Number (PN) 
    using the QMS3 service.
    """
    def __init__(self, site_file: str = '/usr/flexfs/qms3/site.ws'):
        self.site_file = site_file
        self.site_url = self._get_site_url()

    def _get_site_url(self) -> str:
        try:
            if not os.path.exists(self.site_file):
                # Fallback for dev/testing on non-target env
                return "localhost" 
            with open(self.site_file, 'r') as f:
                return f.read().strip()
        except Exception as e:
            print(f"Warning: Could not read site file: {e}")
            return "localhost"

    def get_product_pn(self, sn: str) -> Optional[str]:
        """
        Calls the external service via curl to get the PN.
        """
        if self.site_url == "localhost":
             # Mock return for testing if we can't reach the real service
             # In real usage on the server, this branch won't match if file exists
             return None

        url = f"http://{self.site_url}/OperationServices/Product/Get_ProductPN"
        payload = json.dumps({"SN": sn})
        
        # Construct curl command
        # curl -d '{"SN":"..."}' -H "Content-Type: application/json" -X POST URL
        cmd = [
            'curl', 
            '-s', # Silent mode
            '-d', payload,
            '-H', 'Content-Type: application/json',
            '-X', 'POST',
            url
        ]

        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=10)
            if result.returncode != 0:
                print(f"Error: QMS3 service call failed (curl exit {result.returncode}): {result.stderr.strip()}", file=sys.stderr)
                return None

            match = re.search(r'"PN"\s*:\s*"([^"]+)"', result.stdout)
            if match:
                return match.group(1)

            print(f"Error: Could not find 'PN' in service response. Raw response: {result.stdout[:200]!r}", file=sys.stderr)
            return None

        except subprocess.TimeoutExpired:
            print(f"Error: QMS3 service at {self.site_url} did not respond within 10s. Check network or use --pn to skip lookup.", file=sys.stderr)
            return None
        except FileNotFoundError:
            print("Error: 'curl' not found. Install curl or use --pn to specify the Product Number manually.", file=sys.stderr)
            return None
        except Exception as e:
            print(f"Error: Unexpected failure resolving SN via QMS3: {e}", file=sys.stderr)
            return None

class LogSearcher:
    """
    Searches for log files in a given directory structure.
    """
    
    def __init__(self, root_dirs: List[str], exclude_name_fragments: List[str] = None):
        self.root_dirs = root_dirs
        self.exclude_name_fragments = exclude_name_fragments if exclude_name_fragments is not None else ["led"]

    def search(self, pn: str, sn: str) -> List[Dict[str, str]]:
        """
        scans root_dirs for:
          root_dir/PN/YEAR/MONTH/PN.mlnx (log file?) (original script line 86)
          
        Original script logic:
        For year in 2022..2025:
          For month in 01..12:
            path = /root/PN/YEAR/MONTH/PN.mlnx
            if exists:
                grep sn in path
                ls -ltr /root/PN/YEAR/MONTH/DEBUG | grep sn
        
        This seems to imply:
        1. There is a master index file `PN.mlnx` in `PN/YEAR/MONTH/`.
        2. We search THAT file for the SN.
        3. If found, we look in the sibling `DEBUG` folder for actual logs.
        """
        
        found_logs = []
        
        # We'll search slightly more intelligently than hardcoded years, 
        # but keep the structure expectation.
        
        # We iterate provided roots (like /usr/flexfs/lion_cub/log/ft, etc)
        for root in self.root_dirs:
            pn_dir = Path(root) / pn
            if not pn_dir.exists():
                continue

            # Instead of nested loops for years/months, let's walk the directory
            # looking for the expected structure or just search recursively.
            # Given the depth is fixed (Year/Month), we can glob.
            
            # Pattern: pn_dir / YYYY / MM / pn.mlnx
            # or just use os.walk to find relevant files.
            
            # Try to handle both YYYY/MM and YYYYMM structures
            # Original script seemed to use YYYYMM (e.g. 202201)
            
            for child in pn_dir.iterdir():
                if not child.is_dir():
                    continue

                # Case 1: Child is YYYY (e.g. 2024) -> Look for MM inside
                if child.name.isdigit() and len(child.name) == 4:
                     for month_dir in child.iterdir():
                        if month_dir.is_dir():
                            self._check_dir_for_logs(month_dir, pn, sn, found_logs)
                
                # Case 2: Child is YYYYMM (e.g. 202401)
                elif child.name.isdigit() and len(child.name) == 6:
                    self._check_dir_for_logs(child, pn, sn, found_logs)
        
        return found_logs

    def _check_dir_for_logs(self, dir_path: Path, pn: str, sn: str, found_logs: List[Dict]):
        """Helper to check a specific directory (YYYYMM level) for index file and logs"""
        
        # 1. Collect descriptions from ALL *.mlnx files
        descriptions = []
        try:
            for item in dir_path.glob("*.mlnx"):
                if item.is_file():
                    descriptions.extend(self._grep_file(item, sn))
        except Exception as e:
            print(f"Warning: Could not read index files in {dir_path}: {e}", file=sys.stderr)

        # 2. Search for logs in DEBUG dir (preferred source)
        debug_dir = dir_path / "DEBUG"
        if debug_dir.exists():
            debug_logs = self._find_logs_in_dir(debug_dir, sn, descriptions)
            if debug_logs:
                # DEBUG has results — use them exclusively and skip the parent dir.
                # Any file outside DEBUG is considered a lower-priority copy.
                found_logs.extend(debug_logs)
                return

        # 3. Fall back to parent dir only when DEBUG has nothing for this SN
        parent_logs = self._find_logs_in_dir(dir_path, sn, descriptions)
        found_logs.extend(parent_logs)
        


    def _grep_file(self, file_path: Path, pattern: str) -> List[str]:
        """Check if pattern exists in file. Returns ALL matching lines."""
        matches = []
        try:
            with open(file_path, 'r', errors='ignore') as f:
                for line in f:
                    if pattern in line:
                        matches.append(line.strip())
        except Exception as e:
            print(f"Warning: Could not read {file_path}: {e}", file=sys.stderr)
        return matches

    def _find_logs_in_dir(self, target_dir: Path, sn: str, descriptions: List[str] = []) -> List[Dict[str, str]]:
        """List files in debug folder matching SN."""
        results = []
        raw_logs = []
        
        try:
            # First, collect all matching files
            for f in target_dir.iterdir():
                if not f.is_file():
                    continue
                
                if any(fragment in f.name for fragment in self.exclude_name_fragments):
                    continue
                    
                if re.search(r'(?<![A-Za-z0-9])' + re.escape(sn) + r'(?![A-Za-z0-9])', f.name):
                    raw_logs.append(f)
            
            # Sort by modification time (oldest first)
            # This aligns with the assumption that lines in index file are written chronologically
            raw_logs.sort(key=lambda x: x.stat().st_mtime)

            for idx, f in enumerate(raw_logs):
                tags = []
                if "/dbg/" in str(f.absolute()).lower():
                         tags.append("DEBUG")

                # Find matching description
                best_desc = None
                file_name = f.name
                file_stem = f.stem

                # 1. Try Heuristic matching (content match)
                for desc in descriptions:
                    if file_name in desc or file_stem in desc:
                        best_desc = desc
                        break
                
                # 2. Fallback: Chronological mapping only when counts align exactly,
                # otherwise we'd assign the wrong description to the wrong file.
                if not best_desc and len(descriptions) == len(raw_logs):
                    best_desc = descriptions[idx]

                results.append({
                    "path": str(f.absolute()),
                    "name": f.name,
                    "date": f.stat().st_mtime,
                    "tags": tags,
                    "description": best_desc
                })
        except Exception as e:
            print(f"Warning: Could not list files in {target_dir}: {e}", file=sys.stderr)
        return results
