#!/bin/bash

# --- Configuration ---
# Exit immediately if a command exits with a non-zero status.
set -e

# --- Pre-flight Checks ---
echo "🚀 Starting PanBlog build process..."

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo "❌ Error: jq is not installed. Please install it to continue." >&2
    exit 1
fi

# Check if pandoc is installed
if ! command -v pandoc &> /dev/null; then
    echo "❌ Error: pandoc is not installed. Please install it to continue." >&2
    exit 1
fi

# --- Load Configuration ---
CONFIG_FILE="config.json"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Error: Configuration file not found at '$CONFIG_FILE'." >&2
    exit 1
fi

OUTPUT_DIR=$(jq -r '.output_folder' "$CONFIG_FILE")
CONTENT_DIR=$(jq -r '.content_folder' "$CONFIG_FILE")
SITE_URL=$(jq -r '.site_url' "$CONFIG_FILE")

# --- Build Steps ---
echo "1. Preparing environment..."
# Clean up old HTML files from the output directory
echo "   - Cleaning old build artifacts..."
rm -f "$OUTPUT_DIR"/*.html
# Ensure assets directory exists
mkdir -p "$OUTPUT_DIR/assets"

echo "2. Preparing post template..."
# Prepare the post template using the script and store its path
# The script creates a temporary file and prints its path.
PROCESSED_POST_TEMPLATE=$(python3 process_markdown.py --prepare-post-template --site-url "$SITE_URL")

# Ensure the temporary template is cleaned up on script exit (even on error)
trap 'rm -f "$PROCESSED_POST_TEMPLATE"' EXIT

echo "3. Processing Markdown posts..."
# Process individual markdown posts
for file in "$CONTENT_DIR"/*.md; do
  # Skip index.md for individual processing, it's handled by the homepage generation
  if [ "$(basename "$file")" = "index.md" ]; then
    continue
  fi

  output_file="$OUTPUT_DIR/$(basename "$file" .md).html"
  
  echo "   - Compiling $(basename "$file") -> $(basename "$output_file")"
  
  # Process markdown for assets and links, then pipe to pandoc for HTML conversion
  python3 process_markdown.py "$file" --site-url "$SITE_URL" | \
pandoc -o "$output_file" --template="$PROCESSED_POST_TEMPLATE" --standalone --from markdown+yaml_metadata_block --to html
done

echo "4. Generating homepage..."
python3 process_markdown.py --generate-homepage --site-url "$SITE_URL"

echo "5. Cleaning up unused assets..."
python3 cleanup_assets.py

# The 'trap' command will handle the removal of the temp file.

echo "✅ Site build successful!"