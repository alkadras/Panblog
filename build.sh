#!/bin/bash

# Exit on error
set -e

# Clean up old files
find public/ -maxdepth 1 -type f -name "*.html" -delete

# Ensure assets directory exists
mkdir -p public/assets

# Prepare the post template using process_markdown.py
PROCESSED_POST_TEMPLATE=$(python3 -c "from process_markdown import prepare_post_template; print(prepare_post_template())")
cp "$PROCESSED_POST_TEMPLATE" templates/post_processed.html

# Process individual markdown posts
for file in content/*.md; do
  # Skip index.md for individual processing
  if [ "$(basename "$file")" = "index.md" ]; then
    continue
  fi

  output_file="public/$(basename "$file" .md).html"
  template="templates/post_processed.html"

  echo "Processing $file -> $output_file"
  
  # Process markdown, then pipe to pandoc
  cat "$file" | python3 process_markdown.py "$file" | pandoc -o "$output_file" --template="$template" --standalone --from markdown+yaml_metadata_block --to html
done

# Generate the homepage
echo "Generating homepage..."
python3 process_markdown.py --generate-homepage


# Cleanup unused assets
python3 cleanup_assets.py

# Remove temporary processed template
rm templates/post_processed.html
rm "$PROCESSED_POST_TEMPLATE"

echo "Site build successful!"