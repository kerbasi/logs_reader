import sys
import os
import re
import subprocess
from typing import List, Dict

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def format_description(raw: str) -> str:
    """
    Reformats a raw .mlnx description line for readability.

    Raw:  2026|03|26|13.27.08:SN[612X7520230219]:ULT[N/A]:00:30:42:Fail:4-722-8357:ALL_VOLTAGE-...
    Out:  2026-03-26  13:27:08  SN[612X7520230219]  00:30:42  Fail  4-722-8357  ALL_VOLTAGE-...
    """
    m = re.match(
        r'(\d{4})\|(\d{2})\|(\d{2})\|(\d{2})\.(\d{2})\.(\d{2})'  # date + time
        r':SN\[([^\]]+)\]'                                          # SN[...]
        r':ULT\[[^\]]*\]'                                           # ULT[...] — dropped
        r':(\d{2}:\d{2}:\d{2})'                                    # duration
        r':([^:]+)'                                                  # status
        r':([^:]+)'                                                  # code
        r':(.*)',                                                    # remainder
        raw.strip()
    )
    if not m:
        return raw  # unrecognised format — return as-is

    year, month, day, hh, mm, ss, sn, duration, status, code, rest = m.groups()
    date = f"{year}-{month}-{day}"
    time = f"{hh}:{mm}:{ss}"
    parts = [date, time, f"SN[{sn}]", duration, status, code]
    if rest.strip():
        parts.append(rest.strip())
    return "  ".join(parts)


def print_header(text: str):
    print(f"{Colors.BOLD}{Colors.OKBLUE}=== {text} ==={Colors.ENDC}")

def print_error(text: str):
    print(f"{Colors.FAIL}Error: {text}{Colors.ENDC}")

def print_success(text: str):
    print(f"{Colors.OKGREEN}{text}{Colors.ENDC}")

def display_results(logs: List[Dict[str, str]]):
    if not logs:
        print(f"\n{Colors.WARNING}No logs found.{Colors.ENDC}\n")
        return

    print(f"\n{Colors.UNDERLINE}Found Logs:{Colors.ENDC}")
    # Sort by date
    logs.sort(key=lambda x: x['date'], reverse=True)
    
    for idx, log in enumerate(logs, 1):
        # Format timestamp if needed, for now just name
        tags_str = ""
        if log.get('tags'):
             tags_str = " ".join([f"{Colors.FAIL}[{t}]{Colors.ENDC}" for t in log['tags']]) + " "

        # Determine text color based on description
        name_color = Colors.OKBLUE # Default neutral
        if log.get('description'):
            desc_lower = log['description'].lower()
            if "pass" in desc_lower:
                name_color = Colors.OKGREEN
            elif any(x in desc_lower for x in ["fail", "error", "timeout", "exception"]):
                name_color = Colors.FAIL

        print(f"{Colors.BOLD}[{idx}]{Colors.ENDC} {tags_str}{name_color}{log['name']}{Colors.ENDC}")
        print(f"    {Colors.WARNING}Path:{Colors.ENDC} {log['path']}")
        
        if log.get('description'):
            print(f"    {Colors.OKBLUE}Info:{Colors.ENDC} {format_description(log['description'])}")
        
        # Add a separator blank line
        print()

def select_log(logs: List[Dict[str, str]]) -> int:
    while True:
        try:
            choice = input(f"\n{Colors.BOLD}Enter number to view, 's' to search again, or 'q' to quit: {Colors.ENDC}").strip()
            if choice.lower() == 'q':
                return -1
            if choice.lower() == 's':
                return -2 # Signal to restart
            
            idx = int(choice)
            if 1 <= idx <= len(logs):
                return idx - 1
            else:
                print(f"{Colors.FAIL}Invalid number.{Colors.ENDC}")
        except ValueError:
            print(f"{Colors.FAIL}Please enter a number.{Colors.ENDC}")

def view_file(filepath: str):
    """
    Opens file in 'less' or suitable viewer.
    """
    print_header(f"Opening {filepath}")
    
    # Check if 'less' is available (common on Linux)
    try:
        subprocess.call(['less', '-r', filepath])
    except FileNotFoundError:
        # Fallback for systems without less (e.g. Windows testing)
        if os.name == 'nt':
            subprocess.call(['more', filepath], shell=False)
        else:
            subprocess.call(['cat', filepath])
