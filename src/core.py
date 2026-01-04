import os
import subprocess
import re
import json
from pathlib import Path
from typing import List, Dict, Optional

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
                print(f"Error calling service: {result.stderr}")
                return None
            
            # The original script output seems to be something like:
            # {"d":"[{\"PN\":\"S123456\"}]"} or similar depending on the messy parsing in original.
            # Original script did: my_new_split = (my_split.split(":")[3].split(",")[0])
            # This implies the output is likely JSON wrapped in string or similar.
            # Let's try to parse it cleanly, or use the regex approach if it's text.
            
            # Crude parsing to match original behavior's logic but safer
            # Expected pattern in response: ... "PN":"<LogPrefix>" ...
            # Original script variable name is `my_new_split`, which seems to be the directory name.
            
            # Let's try flexible regex to find the value after "PN":"
            match = re.search(r'"PN"\s*:\s*"([^"]+)"', result.stdout)
            if match:
                return match.group(1)
            
            # Fallback: maybe the response is just the string? 
            # Original script: my_new_split = my_split.split(":")[3].split(",")[0]
            # This is very fragile. We will stick to regex which is more robust.
            return None

        except subprocess.TimeoutExpired:
            print("Timeout calling QMS3 service.")
            return None
        except FileNotFoundError:
            print("Error: 'curl' command not found. Is this Linux?")
            return None
        except Exception as e:
            print(f"Unexpected error resolving SN: {e}")
            return None

class LogSearcher:
    """
    Searches for log files in a given directory structure.
    """
    
    def __init__(self, root_dirs: List[str]):
        self.root_dirs = root_dirs

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
        index_file = dir_path / f"{pn}.mlnx"
        
        if index_file.exists():
            if self._grep_file(index_file, sn):
                # scan DEBUG folder
                debug_dir = dir_path / "DEBUG"
                if debug_dir.exists():
                    found_logs.extend(self._find_logs_in_debug(debug_dir, sn))
        


    def _grep_file(self, file_path: Path, pattern: str) -> bool:
        """Check if pattern exists in file. Efficient line-by-line."""
        try:
            with open(file_path, 'r', errors='ignore') as f:
                for line in f:
                    if pattern in line:
                        return True
        except Exception:
            return False
        return False

    def _find_logs_in_debug(self, debug_dir: Path, sn: str) -> List[Dict[str, str]]:
        """List files in debug folder matching SN."""
        results = []
        try:
            # Original script: ls -ltr ... | grep sn
            # We just filter files by name containing SN
            for f in debug_dir.iterdir():
                if f.is_file() and sn in f.name:
                    tags = []
                    # Check if path indicates a debug environment
                    # Check for '/dbg/' in the full path (case insensitive just in case)
                    # We strictly want /dbg/ roots, avoiding the leaf 'DEBUG' folder common to all logs
                    if "/dbg/" in str(f.absolute()).lower():
                         tags.append("DEBUG")

                    results.append({
                        "path": str(f.absolute()),
                        "name": f.name,
                        "date": f.stat().st_mtime,
                        "tags": tags
                    })
        except Exception:
            pass
        return results
