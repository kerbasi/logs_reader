import sys
import argparse
from pathlib import Path

# Add src to path so we can import modules
sys.path.append(str(Path(__file__).parent / "src"))

try:
    from src.core import ProductResolver, LogSearcher
    from src.interface import print_header, print_error, display_results, select_log, view_file
except ImportError  as e:
    # If running directly from src folder or structure is different
    try:
        from core import ProductResolver, LogSearcher
        from interface import print_header, print_error, display_results, select_log, view_file
    except ImportError:
        print(f"Critical Error: Could not import modules: {e}")
        sys.exit(1)


# Default search paths from original script
DEFAULT_PATHS = [
    "/usr/flexfs/lion_cub/log/ft",
    "/usr/flexfs/lion_cub/log",
    "/usr/flexfs/lion_cub/log/customization",
    "/usr/flexfs/lion_cub/dbg/log/ft",
    "/usr/flexfs/lion_cub/dbg/log",
    "/usr/flexfs/lion_cub/dbg/log/customization"
]

def main():
    parser = argparse.ArgumentParser(description="Log Reader for FT/Customization Logs")
    parser.add_argument("sn", nargs='?', help="Serial Number to search for")
    parser.add_argument("--pn", help="Directly specify Product Number (skip lookup)")
    parser.add_argument("--path", action='append', help="Add custom search path")
    
    args = parser.parse_args()
    
    print_header("Log Reader V2")

    # Initial values from args
    sn = args.sn
    pn = args.pn
    search_paths = args.path if args.path else DEFAULT_PATHS

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
        print(f"Searching in: {len(search_paths)} directories...")
        searcher = LogSearcher(search_paths)
        logs = searcher.search(current_pn, sn)
        
        display_results(logs)
        
        # 4. Interact
        if logs:
            while True:
                choice_idx = select_log(logs)
                
                if choice_idx == -1: # Quit
                    sys.exit(0)
                elif choice_idx == -2: # Search Again
                    # Reset parameters for next loop
                    sn = None
                    pn = None # Clear PN to re-resolve or re-ask
                    print("\n" + "-"*30 + "\n")
                    break # Break inner loop, returns to top of while True
                else:
                    # View File
                    view_file(logs[choice_idx]['path'])
                    # Loop continues, allowing viewing another file
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
