import re
import os
import shutil
import sys
from PIL import Image, ImageOps
import glob
import markdown
from datetime import datetime
import tempfile
import json
import argparse

# --- Pre-compiled Regular Expressions for Performance and Readability ---

# Matches YAML front matter
FRONT_MATTER_RE = re.compile(r'^---\n(.*?)\n---\n', re.DOTALL)

# Extracts title from front matter
TITLE_RE = re.compile(r'^title:\s*(.*)', re.MULTILINE)

# Extracts preview_image from front matter
PREVIEW_IMAGE_RE = re.compile(r'^preview_image:\s*(.*)', re.MULTILINE)

# Finds the first Markdown image (for summaries)
FIRST_IMAGE_RE = re.compile(r'!\[.*?\]\((.*?)\)')

# Finds the first paragraph tag in HTML
FIRST_PARAGRAPH_RE = re.compile(r'<p>(.*?)</p>', re.DOTALL)

# Finds Markdown image/video tags for asset processing
ASSET_RE = re.compile(r'(!\[.*?\]\((.*?)\)|<video.*?src="(.*?)".*?>)', re.IGNORECASE)

# Finds alt text in a Markdown image tag
ALT_TEXT_RE = re.compile(r'!\((.*?)\)]')

# Finds internal Markdown links (.md)
MD_LINK_RE = re.compile(r'(\[.*?\]\((?!http|#|mailto|tel)(.*?\.md)\))')

# Finds YouTube URLs for embedding
YOUTUBE_URL_RE = re.compile(r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})(?:\S+)?')

# Finds Twitter/X URLs for embedding
TWITTER_URL_RE = re.compile(r'(?:https?:\/\/)?(?:www\.)?(?:twitter\.com|x\.com)\/\w+\/status\/([0-9]+)(?:\S+)?')


def load_config(config_path='config.json'):
    """Loads the configuration file."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Hata: Yapılandırma dosyası bulunamadı: {config_path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Hata: Yapılandırma dosyasında JSON format hatası: {config_path}", file=sys.stderr)
        sys.exit(1)

def generate_nav_html(config):
    """Generates the navigation HTML from config."""
    nav_links = config.get('navigation_links', [])
    site_url = config.get('site_url', '/')
    nav_html = '<nav><ul>'
    for link in nav_links:
        text = link.get('text')
        url = link.get('url')
        if text and url:
            absolute_url = os.path.join(site_url, url)
            nav_html += f'<li><a href="{absolute_url}">{text}</a></li>'
    nav_html += '</ul></nav>'
    return nav_html

def get_post_summary(config, md_file_path):
    """Generates a summary for a given blog post."""
    try:
        with open(md_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Uyarı: Yazı dosyası bulunamadı, atlanıyor: {md_file_path}", file=sys.stderr)
        return ""
        
    front_matter_match = FRONT_MATTER_RE.search(content)
    title = "Başlıksız"
    preview_image_path = None
    is_external_image = False

    if front_matter_match:
        front_matter = front_matter_match.group(1)
        title_match = TITLE_RE.search(front_matter)
        if title_match:
            title = title_match.group(1).strip().strip('"')
            
        preview_image_match = PREVIEW_IMAGE_RE.search(front_matter)
        if preview_image_match:
            preview_image_path = preview_image_match.group(1).strip()

    content_without_frontmatter = FRONT_MATTER_RE.sub('', content)

    if not preview_image_path:
        image_match = FIRST_IMAGE_RE.search(content_without_frontmatter)
        if image_match:
            image_url = image_match.group(1)
            if image_url.startswith('http'):
                preview_image_path = image_url
                is_external_image = True
            else:
                image_filename = os.path.basename(image_url)
                preview_image_path = os.path.join('assets', image_filename)

    processed_for_links = process_markdown_content(config, content_without_frontmatter, md_file_path)
    html = markdown.markdown(processed_for_links)
    summary_match = FIRST_PARAGRAPH_RE.search(html)
    summary = summary_match.group(1) if summary_match else ""
    
    site_url = config.get('site_url', '/')
    post_filename = os.path.basename(md_file_path).replace('.md', '.html')
    post_link = os.path.join(site_url, post_filename)

    preview_image_html = ''
    if preview_image_path:
        if is_external_image:
            absolute_image_url = preview_image_path
        else:
            absolute_image_url = os.path.join(site_url, preview_image_path.lstrip('/'))
        preview_image_html = f'<img src="{absolute_image_url}" alt="{title}" class="preview-image">'

    html_parts = [
        '<li class="post-list-item">',
        preview_image_html,
        '<div class="summary-content">',
        f'<h2><a href="{post_link}">{title}</a></h2>',
        f'<p>{summary}</p>',
        '</div>',
        '</li>'
    ]
    return '\n'.join(html_parts)

def generate_homepage(config):
    """Generates the main index.html page."""
    content_dir = config.get('content_folder', 'content')
    output_dir = config.get('output_folder', 'public')
    template_path = 'templates/homepage.html'
    output_path = os.path.join(output_dir, 'index.html')
    index_md_path = os.path.join(content_dir, 'index.md')

    try:
        with open('templates/_footer.html', 'r', encoding='utf-8') as f: footer_content = f.read()
        with open(index_md_path, 'r', encoding='utf-8') as f: index_md_content = f.read()
        with open(template_path, 'r', encoding='utf-8') as f: template_content = f.read()
    except FileNotFoundError as e:
        print(f"Hata: Gerekli bir şablon veya içerik dosyası bulunamadı: {e.filename}", file=sys.stderr)
        sys.exit(1)

    nav_content = generate_nav_html(config)
    current_year = str(datetime.now().year)

    index_title_match = TITLE_RE.search(index_md_content)
    index_title = index_title_match.group(1).strip().strip('"') if index_title_match else config.get("site_title", "Blog")

    index_content_without_frontmatter = FRONT_MATTER_RE.sub('', index_md_content)
    index_html_content = markdown.markdown(process_markdown_content(config, index_content_without_frontmatter, index_md_path))

    post_files = glob.glob(os.path.join(content_dir, '*.md'))
    post_files = [f for f in post_files if os.path.basename(f) != 'index.md']
    post_files.sort(key=lambda f: os.path.getmtime(f), reverse=True)

    summaries = [get_post_summary(config, f) for f in post_files]
    posts_html = '<ul class="post-list">\n' + '\n'.join(summaries) + '\n</ul>'

    final_html = template_content.replace('<!-- INDEX_CONTENT_PLACEHOLDER -->', index_html_content)
    final_html = final_html.replace('<!-- POSTS_PLACEHOLDER -->', posts_html)
    final_html = final_html.replace('$site_title$', index_title)
    final_html = final_html.replace('$site_description$', config.get("site_description", ""))
    final_html = final_html.replace('<!-- NAV_PLACEHOLDER -->', nav_content)
    final_html = final_html.replace('<!-- FOOTER_PLACEHOLDER -->', footer_content.replace('__CURRENT_YEAR__', current_year))

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_html)
    print(f"Homepage generated at {output_path}", file=sys.stderr)

def optimize_image(image_path, output_path, quality=85):
    """Optimizes an image file."""
    try:
        with Image.open(image_path) as img:
            img = ImageOps.exif_transpose(img)
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            img.save(output_path, quality=quality, optimize=True)
            print(f"Optimized {os.path.basename(image_path)} and saved to {output_path}", file=sys.stderr)
            return True
    except Exception as e:
        print(f"Error optimizing {os.path.basename(image_path)}: {e}", file=sys.stderr)
        return False

def prepare_post_template(config):
    """Prepares a temporary post template file with shared components."""
    try:
        with open('templates/_footer.html', 'r', encoding='utf-8') as f: footer_content = f.read()
        with open('templates/post.html', 'r', encoding='utf-8') as f: template_content = f.read()
    except FileNotFoundError as e:
        print(f"Hata: Gerekli bir şablon dosyası bulunamadı: {e.filename}", file=sys.stderr)
        sys.exit(1)

    nav_content = generate_nav_html(config)
    current_year = str(datetime.now().year)

    processed_template = template_content.replace('<!-- NAV_PLACEHOLDER -->', nav_content)
    processed_template = processed_template.replace('<!-- FOOTER_PLACEHOLDER -->', footer_content.replace('__CURRENT_YEAR__', current_year))
    processed_template = processed_template.replace('$site_title$', config.get("site_title", "Blog"))
    processed_template = processed_template.replace('$site_description$', config.get("site_description", ""))
    processed_template = processed_template.replace('$author$', config.get("author", ""))

    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8', suffix='.html')
    temp_file.write(processed_template)
    temp_file.close()
    return temp_file.name

def process_markdown_content(config, markdown_content, markdown_file_path):
    """Processes markdown content to handle asset paths, links, and embeds."""
    project_root = os.getcwd()
    markdown_dir = os.path.dirname(markdown_file_path)
    output_dir = config.get('output_folder', 'public')
    site_url = config.get('site_url', '/')

    def replace_path(match):
        original_path = match.group(2) if match.group(2) else match.group(3)
        if not original_path or original_path.startswith(('http://', 'https://', '//', 'mailto:', 'tel:')):
            return match.group(0)
        if os.path.isabs(original_path):
            source_abs_path = os.path.join(project_root, original_path.lstrip('/'))
        else:
            source_abs_path = os.path.abspath(os.path.join(markdown_dir, original_path))
        
        assets_dir = os.path.join(project_root, output_dir, 'assets')
        os.makedirs(assets_dir, exist_ok=True)
        filename = os.path.basename(source_abs_path)
        destination_abs_path = os.path.join(assets_dir, filename)
        
        new_absolute_path = f"{site_url.rstrip('/')}/assets/{filename}"

        if match.group(2) and filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
            if os.path.exists(source_abs_path):
                if not os.path.exists(destination_abs_path) or os.path.getmtime(source_abs_path) > os.path.getmtime(destination_abs_path):
                    if not optimize_image(source_abs_path, destination_abs_path):
                        print(f"Falling back to simple copy for {filename}", file=sys.stderr)
                        shutil.copy2(source_abs_path, destination_abs_path)
            else:
                print(f"Warning: Source image file not found: {source_abs_path}", file=sys.stderr)
        elif os.path.exists(source_abs_path):
            if not os.path.exists(destination_abs_path) or os.path.getmtime(source_abs_path) > os.path.getmtime(destination_abs_path):
                try:
                    shutil.copy2(source_abs_path, destination_abs_path)
                except Exception as e:
                    print(f"Error copying file {source_abs_path}: {e}", file=sys.stderr)
                    return match.group(0)
        elif not os.path.exists(source_abs_path):
            print(f"Warning: Source file not found: {source_abs_path}", file=sys.stderr)
            return match.group(0)
        
        if match.group(2):
            alt_text_match = ALT_TEXT_RE.search(match.group(0))
            alt_text = alt_text_match.group(1) if alt_text_match else ''
            return f'![{alt_text}]({new_absolute_path})'
        elif match.group(3):
            return match.group(0).replace(original_path, new_absolute_path)
        return match.group(0)

    processed_content = ASSET_RE.sub(replace_path, markdown_content)

    def replace_md_link(match):
        original_link_text = match.group(1)
        md_path = match.group(2)
        html_filename = os.path.basename(md_path).replace('.md', '.html')
        
        absolute_html_path = f"{site_url.rstrip('/')}/{html_filename}"
        return original_link_text.replace(md_path, absolute_html_path)

    processed_content = MD_LINK_RE.sub(replace_md_link, processed_content)
    
    processed_content = YOUTUBE_URL_RE.sub(
        r'<div class="video-container"><iframe src="https://www.youtube.com/embed/\1" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe></div>',
        processed_content
    )
    
    twitter_embed_found = False
    def twitter_replacer(match):
        nonlocal twitter_embed_found
        twitter_embed_found = True
        tweet_id = match.group(1)
        return f'<blockquote class="twitter-tweet"><a href="https://twitter.com/user/status/{tweet_id}"></a></blockquote>'

    processed_content = TWITTER_URL_RE.sub(twitter_replacer, processed_content)
    if twitter_embed_found:
        processed_content += '\n<script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>'
        
    return processed_content

def main():
    parser = argparse.ArgumentParser(description="Process markdown files for PanBlog.")
    parser.add_argument('input_file', nargs='?', default=None, help="The path to the markdown file to process. Reads from stdin if not provided.")
    parser.add_argument('--generate-homepage', action='store_true', help="Generate the homepage.")
    parser.add_argument('--prepare-post-template', action='store_true', help="Prepare the post template and print the path.")
    parser.add_argument('--site-url', help="Override the site_url from config.json.")

    args = parser.parse_args()
    config = load_config()

    if args.site_url:
        config['site_url'] = args.site_url

    if args.generate_homepage:
        generate_homepage(config)
    elif args.prepare_post_template:
        temp_file_path = prepare_post_template(config)
        print(temp_file_path)
    elif args.input_file:
        try:
            with open(args.input_file, 'r', encoding='utf-8') as f:
                markdown_input = f.read()
            output_content = process_markdown_content(config, markdown_input, args.input_file)
            sys.stdout.write(output_content)
        except FileNotFoundError:
            print(f"Hata: Girdi dosyası bulunamadı: {args.input_file}", file=sys.stderr)
            sys.exit(1)
    else: # stdin
        markdown_input = sys.stdin.read()
        output_content = process_markdown_content(config, markdown_input, "stdin.md")
        sys.stdout.write(output_content)


if __name__ == "__main__":
    main()
