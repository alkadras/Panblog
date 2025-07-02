import os
import re
import glob
import json
import argparse
import sys

# --- Pre-compiled Regular Expressions (Consistent with process_markdown.py) ---
# This regex is designed to find asset paths in various contexts.
# It captures paths from:
# - Markdown images: ![alt text](path/to/image.jpg)
# - HTML tags (like <img>, <video>, <source>): src="path/to/asset.mp4"
# - CSS properties: url('path/to/font.woff') or url("path/to/image.png")
ASSET_PATH_RE = re.compile(
    r'(!\[.*?\]\((?P<md_img>.*?)\)|'          # Group 'md_img' for Markdown images
    r'<[a-zA-Z0-9]+\s+[^>]*?src\s*=\s*["\\](?P<html_src>.*?)["\\][^>]*?>|' # Group 'html_src' for src attributes
    r'url\s*\(\s*["\\]?(?P<css_url>.*?)["\\]?\s*\))', # Group 'css_url' for CSS url()
    re.IGNORECASE
)

def load_config(config_path='config.json'):
    """Loads the configuration file with error handling."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: Configuration file not found: {config_path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"❌ Error: JSON format error in configuration file: {config_path}", file=sys.stderr)
        sys.exit(1)

def find_all_referenced_assets(config):
    """Scans all relevant project files to find which assets are in use."""
    content_dir = config.get('content_folder', 'content')
    output_dir = config.get('output_folder', 'public')
    templates_dir = 'templates'
    
    # Define which file types to scan for asset references
    scan_patterns = [
        os.path.join(content_dir, '**', '*.*'),
        os.path.join(output_dir, '**', '*.html'),
        os.path.join(output_dir, '**', '*.css'),
        os.path.join(templates_dir, '**', '*.html'),
    ]
    
    referenced_assets = set()
    
    print("   - Scanning for asset references in project files...")
    for pattern in scan_patterns:
        # recursive=True is needed for '**' to work correctly
        for file_path in glob.glob(pattern, recursive=True):
            if os.path.isfile(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        matches = ASSET_PATH_RE.finditer(content)
                        for match in matches:
                            # Find the path from the correct capture group
                            path = match.group('md_img') or match.group('html_src') or match.group('css_url')
                            if path and not path.startswith(('http://', 'https://', '//', 'data:')):
                                # Extract just the filename from the path
                                filename = os.path.basename(path)
                                referenced_assets.add(filename)
                except Exception as e:
                    print(f"   - Warning: Could not read or process file {file_path}: {e}", file=sys.stderr)
                    
    print(f"   - Found {len(referenced_assets)} unique referenced assets.")
    return referenced_assets

def cleanup_assets(dry_run):
    """Deletes unused assets from the public assets directory."""
    print("🧹 Starting asset cleanup...")
    config = load_config()
    project_root = os.getcwd()
    output_dir = config.get('output_folder', 'public')
    public_assets_dir = os.path.join(project_root, output_dir, 'assets')

    if not os.path.exists(public_assets_dir):
        print("   - Assets directory does not exist. Nothing to clean up.")
        return

    # 1. Get all assets currently in the public/assets directory
    current_assets = {f for f in os.listdir(public_assets_dir) if os.path.isfile(os.path.join(public_assets_dir, f))}
    print(f"   - Found {len(current_assets)} files in the public assets directory.")

    # 2. Find all assets that are actually referenced in the project
    referenced_assets = find_all_referenced_assets(config)

    # 3. Determine which assets are unreferenced and should be deleted
    assets_to_delete = current_assets - referenced_assets

    if not assets_to_delete:
        print("✨ All assets are in use. No cleanup needed.")
        return

    print(f"   - Found {len(assets_to_delete)} unreferenced assets to delete.")

    if dry_run:
        print("\n[DRY RUN] The following assets would be deleted:")
        for asset_filename in sorted(list(assets_to_delete)):
            print(f"  - {asset_filename}")
        print("\n[DRY RUN] No files were actually deleted.")
    else:
        print("\nDeleting unreferenced assets...")
        deleted_count = 0
        for asset_filename in assets_to_delete:
            asset_full_path = os.path.join(public_assets_dir, asset_filename)
            try:
                os.remove(asset_full_path)
                print(f"  - Deleted: {asset_filename}")
                deleted_count += 1
            except Exception as e:
                print(f"  - ❌ Error deleting {asset_filename}: {e}", file=sys.stderr)
        print(f"\n✅ Cleanup complete. Deleted {deleted_count} asset(s).")

def main():
    parser = argparse.ArgumentParser(
        description="Cleans up unused assets from the public/assets directory.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help="""Perform a 'dry run' without deleting any files.
This will list all the assets that are considered unreferenced
and would be deleted if run normally."""
    )
    args = parser.parse_args()

    cleanup_assets(dry_run=args.dry_run)

if __name__ == "__main__":
    main()