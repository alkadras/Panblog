import os
import re
import glob

def cleanup_assets():
    project_root = os.getcwd()
    public_assets_dir = os.path.join(project_root, 'public', 'assets')
    content_dir = os.path.join(project_root, 'content')

    # Get all current asset files in public/assets
    current_assets = set()
    if os.path.exists(public_assets_dir):
        for filename in os.listdir(public_assets_dir):
            if os.path.isfile(os.path.join(public_assets_dir, filename)):
                current_assets.add(filename)

    # Collect all referenced asset filenames from markdown files
    referenced_assets = set()
    markdown_files = glob.glob(os.path.join(content_dir, '*.md'))

    # Regex to find image and video links in Markdown
    # This covers ![alt](path) and <video src="path">
    # It tries to capture the path itself.
    asset_pattern = re.compile(r'(!\[.*?\]\((.*?)\)|<video.*?src="(.*?)".*?>)', re.IGNORECASE)

    for md_file_path in markdown_files:
        with open(md_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            matches = asset_pattern.findall(content)
            for match in matches:
                # Determine which group contains the path (group 2 for ![...](path), group 3 for <video src="path">)
                original_path = match[1] if match[1] else match[2]
                
                if not original_path:
                    continue # Should not happen if regex is correct

                # Skip external URLs
                if original_path.startswith(('http://', 'https://', '//')):
                    continue
                
                # Extract just the filename from the path
                filename = os.path.basename(original_path)
                referenced_assets.add(filename)

    # Determine which assets to delete
    assets_to_delete = current_assets - referenced_assets

    # Delete unreferenced assets
    for asset_filename in assets_to_delete:
        asset_full_path = os.path.join(public_assets_dir, asset_filename)
        if os.path.exists(asset_full_path):
            try:
                os.remove(asset_full_path)
                print(f"Deleted unreferenced asset: {asset_full_path}")
            except Exception as e:
                print(f"Error deleting asset {asset_full_path}: {e}")

if __name__ == "__main__":
    cleanup_assets()
