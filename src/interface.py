import sys
import os
from subprocess import call
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
        print(f"{Colors.BOLD}[{idx}]{Colors.ENDC} {log['name']}")
        print(f"    {Colors.OKCYAN}{log['path']}{Colors.ENDC}")

def select_log(logs: List[Dict[str, str]]) -> int:
    while True:
        try:
            choice = input(f"\n{Colors.BOLD}Enter number to view (or 'q' to quit): {Colors.ENDC}").strip()
            if choice.lower() == 'q':
                return -1
            
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
        call(['less', '-r', filepath])
    except FileNotFoundError:
        # Fallback for systems without less (e.g. Windows testing)
        # Use 'more' on windows or just cat it
        if os.name == 'nt':
             os.system(f'more "{filepath}"')
        else:
             os.system(f'cat "{filepath}"')
