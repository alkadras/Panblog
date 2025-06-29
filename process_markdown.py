import re
import os
import shutil
import sys
from PIL import Image, ImageOps
import glob
import markdown
from datetime import datetime
import tempfile
import atexit

def get_post_summary(md_file_path):
    with open(md_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        # Extract title from YAML front matter
        title_match = re.search(r'^---\n.*?title:\s*([^\n]*?)\n.*?---\n', content, re.DOTALL | re.MULTILINE)
        title = title_match.group(1) if title_match else "Başlıksız"
        
        # Remove front matter for summary
        content_without_frontmatter = re.sub(r'^---.*?---\n', '', content, flags=re.DOTALL)
        
        # Convert to HTML to get a clean summary
        html = markdown.markdown(process_markdown_content(content_without_frontmatter, md_file_path))
        
        # Extract the first paragraph as summary
        summary_match = re.search(r'<p>(.*?)</p>', html, re.DOTALL)
        summary = summary_match.group(1) if summary_match else ""
        
        # Create a link to the post
        post_link = '/' + os.path.basename(md_file_path).replace('.md', '.html')
        
        return f'<h2><a href="{post_link}">{title}</a></h2>\n<p>{summary}</p>'

def generate_homepage():
    content_dir = 'content'
    template_path = 'templates/homepage.html'
    output_path = 'public/index.html'
    index_md_path = os.path.join(content_dir, 'index.md')

    # Read partials
    with open('templates/_nav.html', 'r', encoding='utf-8') as f: nav_content = f.read()
    with open('templates/_footer.html', 'r', encoding='utf-8') as f: footer_content = f.read()
    current_year = str(datetime.now().year)

    # Read index.md content
    with open(index_md_path, 'r', encoding='utf-8') as f:
        index_md_content = f.read()

    # Extract title from index.md YAML front matter
    index_title_match = re.search(r'^---\n.*?title:\s*"(.*?)"\n---\n', index_md_content, re.DOTALL | re.MULTILINE)
    index_title = index_title_match.group(1) if index_title_match else "Blog Ana Sayfası"

    # Remove front matter from index.md content for HTML conversion
    index_content_without_frontmatter = re.sub(r'^---.*?---\n', '', index_md_content, flags=re.DOTALL)
    index_html_content = markdown.markdown(process_markdown_content(index_content_without_frontmatter, index_md_path))

    # Get all markdown files except index.md
    post_files = glob.glob(os.path.join(content_dir, '*.md'))
    post_files = [f for f in post_files if os.path.basename(f) != 'index.md']

    # Sort posts by modification time (newest first)
    post_files.sort(key=lambda f: os.path.getmtime(f), reverse=True)

    # Generate summaries
    summaries = [get_post_summary(f) for f in post_files]
    posts_html = '\n'.join(summaries)

    # Read homepage template
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()

    # Replace placeholders
    final_html = template_content.replace('<!-- INDEX_CONTENT_PLACEHOLDER -->', index_html_content)
    final_html = final_html.replace('<!-- POSTS_PLACEHOLDER -->', posts_html)
    final_html = final_html.replace('<title>Blog Ana Sayfası</title>', f'<title>{index_title}</title>')
    final_html = final_html.replace('<!-- NAV_PLACEHOLDER -->', nav_content)
    final_html = final_html.replace('<!-- FOOTER_PLACEHOLDER -->', footer_content.replace('__CURRENT_YEAR__', current_year))

    # Write the final index.html
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_html)
    print(f"Homepage generated at {output_path}", file=sys.stderr)

def optimize_image(image_path, output_path, quality=85):
    try:
        with Image.open(image_path) as img:
            # Apply EXIF orientation if present
            img = ImageOps.exif_transpose(img)

            # Convert to RGB if not already (e.g., for PNGs with alpha channel)
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')

            # Save with optimized quality, preserving original dimensions
            img.save(output_path, quality=quality, optimize=True)
            print(f"Optimized {os.path.basename(image_path)} and saved to {output_path}", file=sys.stderr)
            return True
    except Exception as e:
        print(f"Error optimizing {os.path.basename(image_path)}: {e}", file=sys.stderr)
        return False

def prepare_post_template():
    # Read partials
    with open('templates/_nav.html', 'r', encoding='utf-8') as f: nav_content = f.read()
    with open('templates/_footer.html', 'r', encoding='utf-8') as f: footer_content = f.read()
    current_year = str(datetime.now().year)

    # Read post template
    with open('templates/post.html', 'r', encoding='utf-8') as f:
        template_content = f.read()

    # Replace placeholders
    processed_template = template_content.replace('<!-- NAV_PLACEHOLDER -->', nav_content)
    processed_template = processed_template.replace('<!-- FOOTER_PLACEHOLDER -->', footer_content.replace('__CURRENT_YEAR__', current_year))

    # Create a temporary file
    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8', suffix='.html')
    temp_file.write(processed_template)
    temp_file.close()

    return temp_file.name

def process_markdown_content(markdown_content, markdown_file_path):
    # Regex to find image and video links in Markdown
    # This covers ![alt](path) and <video src="path">
    # It also tries to capture the path itself.
    pattern = re.compile(r'(!\[.*?\]\((.*?)\)|<video.*?src="(.*?)".*?>)', re.IGNORECASE)

    # Base directory for resolving relative paths (where build.sh is run)
    project_root = os.getcwd()
    
    # Directory where the current markdown file is located
    markdown_dir = os.path.dirname(markdown_file_path)

    def replace_path(match):
        # Determine which group contains the path (group 2 for ![...](path), group 3 for <video src="path">)
        original_path = match.group(2) if match.group(2) else match.group(3)
        
        if not original_path:
            return match.group(0) # Should not happen if regex is correct

        # Skip if it's an external URL
        if original_path.startswith(('http://', 'https://', '//')):
            return match.group(0)

        # Resolve the absolute path of the source file
        # If path is already absolute, os.path.join will handle it correctly
        # Otherwise, it's relative to the markdown file's directory
        if os.path.isabs(original_path):
            source_abs_path = original_path
        else:
            # All relative paths are resolved relative to the markdown file's directory
            source_abs_path = os.path.abspath(os.path.join(markdown_dir, original_path))

        # Define the destination directory for assets
        assets_dir = os.path.join(project_root, 'public', 'assets')
        os.makedirs(assets_dir, exist_ok=True)

        # Get the filename and create the new path in public/assets
        filename = os.path.basename(source_abs_path)
        destination_abs_path = os.path.join(assets_dir, filename)
        
        # New relative path for the Markdown/HTML
        new_relative_path = os.path.join('assets', filename).replace('\\', '/') # Use forward slashes for web paths

        # Check if it's an image and optimize it
        if match.group(2) and filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
            if os.path.exists(source_abs_path):
                # Only optimize if the destination file doesn't exist or is older than source
                # This prevents re-optimizing already optimized images unnecessarily
                if not os.path.exists(destination_abs_path) or \
                   os.path.getmtime(source_abs_path) > os.path.getmtime(destination_abs_path):
                    if not optimize_image(source_abs_path, destination_abs_path):
                        # If optimization fails, fall back to simple copy
                        print(f"Falling back to simple copy for {filename}", file=sys.stderr)
                        shutil.copy2(source_abs_path, destination_abs_path)
                else:
                    print(f"Skipping optimization for {filename} (already optimized or source is older)", file=sys.stderr)
            else:
                print(f"Warning: Source image file not found: {source_abs_path}", file=sys.stderr)
        # For non-images or if optimization fails, just copy
        elif os.path.exists(source_abs_path) and not os.path.exists(destination_abs_path):
            try:
                shutil.copy2(source_abs_path, destination_abs_path)
                # print(f"Copied: {source_abs_path} to {destination_abs_path}", file=sys.stderr)
            except Exception as e:
                print(f"Error copying file {source_abs_path}: {e}", file=sys.stderr)
                # If copy fails, return original path to avoid broken links
                return match.group(0)
        elif not os.path.exists(source_abs_path):
            print(f"Warning: Source file not found: {source_abs_path}", file=sys.stderr)
            # If source not found, return original path to avoid broken links
            return match.group(0)

        # Replace the original path with the new relative path
        if match.group(2): # Image link
            return f"![{match.group(1).split('](')[0][2:]}]({new_relative_path})"
        elif match.group(3): # Video link
            return match.group(0).replace(original_path, new_relative_path)
        return match.group(0) # Fallback

    # Perform the asset path replacement
    processed_content = pattern.sub(replace_path, markdown_content)

    # Regex to find internal markdown links: [text](path.md)
    # This will run AFTER asset processing, so we only care about .md links
    # that are not assets.
    link_pattern = re.compile(r'(\[.*?\]\((?!http|#)(.*?\.md)\))')

    def replace_md_link(match):
        original_link_text = match.group(1)
        md_path = match.group(2)
        
        # Replace .md with .html
        html_path = md_path.replace('.md', '.html')
        
        # Reconstruct the link
        return original_link_text.replace(md_path, html_path)

    # Perform the markdown link replacement
    processed_content = link_pattern.sub(replace_md_link, processed_content)

    # Regex for YouTube URLs: https://www.youtube.com/watch?v=VIDEO_ID or https://youtu.be/VIDEO_ID
    youtube_url_pattern = re.compile(r'(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})(?:\S+)?')
    processed_content = youtube_url_pattern.sub(
        r'<div class="video-container"><iframe src="https://www.youtube.com/embed/\1" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe></div>',
        processed_content
    )

    # Regex for Twitter URLs: https://twitter.com/user/status/TWEET_ID
    twitter_embed_found = False
    def twitter_replacer(match):
        nonlocal twitter_embed_found
        twitter_embed_found = True
        tweet_id = match.group(1)
        return f'<blockquote class="twitter-tweet"><a href="https://twitter.com.com/user/status/{tweet_id}"></a></blockquote>'

    twitter_url_pattern = re.compile(r'(?:https?://)?(?:www\.)?(?:twitter\.com|x\.com)/\w+/status/([0-9]+)(?:\S+)?')
    processed_content = twitter_url_pattern.sub(twitter_replacer, processed_content)

    # If Twitter embeds were found, append the Twitter widget script
    if twitter_embed_found:
        processed_content += '\n<script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>'
    
    return processed_content

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--generate-homepage':
        generate_homepage()
        sys.exit(0)

    # Read markdown content from stdin
    markdown_input = sys.stdin.read()
    
    # Get the markdown file path from the first command line argument
    # This is crucial for resolving relative paths correctly.
    if len(sys.argv) > 1:
        md_file_path = sys.argv[1]
    else:
        # Fallback if no path is provided, assume current dir for relative paths
        md_file_path = "temp.md" 
        print("Warning: No markdown file path provided to process_markdown.py. Relative paths might be incorrect.", file=sys.stderr)

    output_content = process_markdown_content(markdown_input, md_file_path)
    sys.stdout.write(output_content)