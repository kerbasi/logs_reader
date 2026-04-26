import sys
import argparse
from pathlib import Path

# Add src to path so we can import modules
sys.path.append(str(Path(__file__).parent / "src"))

try:
    from src.core import ProductResolver, LogSearcher, ICTLogSearcher
    from src.interface import print_header, print_error, display_results, select_log, view_file, open_in_libreoffice
except ImportError as e:
    try:
        from core import ProductResolver, LogSearcher, ICTLogSearcher
        from interface import print_header, print_error, display_results, select_log, view_file, open_in_libreoffice
    except ImportError:
        print(f"Critical Error: Could not import modules: {e}")
        sys.exit(1)


# Default search paths from original script
DEFAULT_PATHS = [
    "/usr/flexfs/lion_cub/log/ft",
    "/usr/flexfs/lion_cub/log",
    "/usr/flexfs/lion_cub/log/customization",
    "/usr/flexfs/lion_cub/log/dbg/ft",
    "/usr/flexfs/lion_cub/log/dbg",
    "/usr/flexfs/lion_cub/log/dbg/customization"
]

def main():
    parser = argparse.ArgumentParser(description="Log Reader for FT/Customization Logs")
    parser.add_argument("sn", nargs='?', help="Serial Number to search for")
    parser.add_argument("--pn", help="Directly specify Product Number (skip lookup)")
    parser.add_argument("--path", action='append', help="Add extra search path (appended to defaults)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed search info")
    
    args = parser.parse_args()
    
    print_header("Log Reader V2")

    # Initial values from args
    sn = args.sn
    pn = args.pn
    verbose = args.verbose
    search_paths = DEFAULT_PATHS + (args.path or [])

    if verbose:
        print(f"Search paths ({len(search_paths)}):")
        for p in search_paths:
            print(f"  {p}")

    while True:
        # 1. Acquire SN
        if not sn:
            try:
                sn = input("Enter Serial Number (SN) (or 'q' to quit): ").strip()
            except KeyboardInterrupt:
                 sys.exit(0)
            
            if sn.lower() == 'q':
                sys.exit(0)
            if not sn:
                continue

        # 2. Resolve PN
        current_pn = pn
        if not current_pn:
            print(f"Resolving Product Number for SN: {sn}...")
            resolver = ProductResolver()
            current_pn = resolver.get_product_pn(sn)
            
            if not current_pn:
                print_error("Could not resolve PN. Please specify manually.")
                # Fallback manual entry
                current_pn = input("Enter Product Number (PN) manually: ").strip()
                if not current_pn:
                    # Reset and loop
                    sn = None
                    continue
            else:
                print(f"Resolved PN: {current_pn}")
        
        # 3. Search
        if verbose:
            print(f"Searching for SN={sn}, PN={current_pn} in {len(search_paths)} directories...")
        else:
            print(f"Searching in: {len(search_paths)} directories...")
        if current_pn.upper().startswith("SFG"):
            all_logs = ICTLogSearcher().search(sn)
            if verbose:
                print(f"PN starts with SFG — ICT search only. Found {len(all_logs)} log(s).")
            print_header("ICT Logs")
            display_results(all_logs)
        else:
            all_logs = LogSearcher(search_paths).search(current_pn, sn)
            if verbose:
                print(f"Found {len(all_logs)} standard log(s).")
            if all_logs:
                display_results(all_logs)
            else:
                all_logs = ICTLogSearcher().search(sn)
                if verbose:
                    print(f"No standard logs — ICT fallback. Found {len(all_logs)} log(s).")
                print_header("ICT Logs")
                display_results(all_logs)

        # 4. Interact
        if all_logs:
            while True:
                choice_idx = select_log(all_logs)

                if choice_idx == -1:
                    sys.exit(0)
                elif choice_idx == -2:
                    sn = None
                    pn = None
                    print("\n" + "-"*30 + "\n")
                    break
                else:
                    selected_path = all_logs[choice_idx]['path']
                    if selected_path.lower().endswith('.csv'):
                        open_in_libreoffice(selected_path)
                    else:
                        view_file(selected_path)
        else:
            # If no logs found, ask what to do
            retry = input("Search again? (y/n): ").strip().lower()
            if retry == 'y':
                sn = None
                pn = None
                continue
            else:
                sys.exit(0)

if __name__ == "__main__":
    main()
