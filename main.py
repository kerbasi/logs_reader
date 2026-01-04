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

    sn = args.sn
    if not sn:
        sn = input("Enter Serial Number (SN): ").strip()
        if not sn:
            print_error("SN is required.")
            sys.exit(1)

    pn = args.pn
    if not pn:
        # Resolve SN -> PN
        print(f"Resolving Product Number for SN: {sn}...")
        resolver = ProductResolver()
        pn = resolver.get_product_pn(sn)
        
        if not pn:
            print_error("Could not resolve PN. Please specify manually with --pn")
            # For testing/dev, if resolver fails, we might want to let user continue?
            # Original script logic exited if path construction failed implicitly.
            
            # Allow fallback manual entry
            pn = input("Enter Product Number (PN) manually: ").strip()
            if not pn:
                sys.exit(1)
        else:
            print(f"Resolved PN: {pn}")

    # Prepare search paths
    search_paths = args.path if args.path else DEFAULT_PATHS
    
    print(f"Searching in: {len(search_paths)} directories...")
    searcher = LogSearcher(search_paths)
    logs = searcher.search(pn, sn)
    
    display_results(logs)
    
    if logs:
        choice_idx = select_log(logs)
        if choice_idx >= 0:
            view_file(logs[choice_idx]['path'])

if __name__ == "__main__":
    main()
