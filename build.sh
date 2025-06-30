#!/bin/bash

# Exit on error
set -e

# Check if jq is installed
if ! command -v jq &> /dev/null
then
    echo "jq could not be found, please install it to continue."
    exit 1
fi

# Load config values
CONFIG_FILE="config.json"
OUTPUT_DIR=$(jq -r '.output_folder' "$CONFIG_FILE")
CONTENT_DIR=$(jq -r '.content_folder' "$CONFIG_FILE")
SITE_URL=$(jq -r '.site_url' "$CONFIG_FILE")

# Clean up old files
find "$OUTPUT_DIR/" -maxdepth 1 -type f -name "*.html" -delete

# Ensure assets directory exists
mkdir -p "$OUTPUT_DIR/assets"

# Prepare the post template using process_markdown.py
PROCESSED_POST_TEMPLATE=$(python3 process_markdown.py --prepare-post-template --site-url "$SITE_URL")
cp "$PROCESSED_POST_TEMPLATE" templates/post_processed.html

# Process individual markdown posts
for file in "$CONTENT_DIR"/*.md; do
  # Skip index.md for individual processing
  if [ "$(basename "$file")" = "index.md" ]; then
    continue
  fi

  output_file="$OUTPUT_DIR/$(basename "$file" .md).html"
  template="templates/post_processed.html"

  echo "Processing $file -> $output_file"
  
  # Process markdown, then pipe to pandoc
  python3 process_markdown.py "$file" --site-url "$SITE_URL" | pandoc -o "$output_file" --template="$template" --standalone --from markdown+yaml_metadata_block --to html
done

# Generate the homepage
echo "Generating homepage..."
python3 process_markdown.py --generate-homepage --site-url "$SITE_URL"


# Cleanup unused assets
python3 cleanup_assets.py

# Remove temporary processed template
rm templates/post_processed.html
rm "$PROCESSED_POST_TEMPLATE"

echo "Site build successful!"
