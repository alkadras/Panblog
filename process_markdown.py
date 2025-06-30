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

def load_config(config_path='config.json'):
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def generate_nav_html(config):
    nav_links = config.get('navigation_links', [])
    site_url = config.get('site_url', '/')
    nav_html = '<nav><ul>'
    for link in nav_links:
        text = link.get('text')
        url = link.get('url')
        if text and url:
            # site_url'nin sonunda zaten / varsa, os.path.join onu doğru bir şekilde işler
            absolute_url = os.path.join(site_url, url).replace('\\', '/')
            nav_html += f'<li><a href="{absolute_url}">{text}</a></li>'
    nav_html += '</ul></nav>'
    return nav_html

def get_post_summary(config, md_file_path):
    with open(md_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        title_match = re.search(r'^---\n.*?title:\s*([^\n]*?)\n.*?---\n', content, re.DOTALL | re.MULTILINE)
        title = title_match.group(1).strip() if title_match else "Başlıksız"
        content_without_frontmatter = re.sub(r'^---.*?---\n', '', content, flags=re.DOTALL)
        # Önce .md linklerini dönüştür, sonra markdown'a çevir
        processed_for_links = process_markdown_content(config, content_without_frontmatter, md_file_path)
        html = markdown.markdown(processed_for_links)
        summary_match = re.search(r'<p>(.*?)</p>', html, re.DOTALL)
        summary = summary_match.group(1) if summary_match else ""
        site_url = config.get('site_url', '/')
        post_filename = os.path.basename(md_file_path).replace('.md', '.html')
        post_link = os.path.join(site_url, post_filename).replace('\\', '/')
        return f'<h2><a href="{post_link}">{title}</a></h2>\n<p>{summary}</p>'


def generate_homepage(config):
    content_dir = config.get('content_folder', 'content')
    output_dir = config.get('output_folder', 'public')
    template_path = 'templates/homepage.html'
    output_path = os.path.join(output_dir, 'index.html')
    index_md_path = os.path.join(content_dir, 'index.md')

    nav_content = generate_nav_html(config)
    with open('templates/_footer.html', 'r', encoding='utf-8') as f: footer_content = f.read()
    current_year = str(datetime.now().year)

    with open(index_md_path, 'r', encoding='utf-8') as f:
        index_md_content = f.read()

    index_title_match = re.search(r'^---\n.*?title:\s*"(.*?)"\n---\n', index_md_content, re.DOTALL | re.MULTILINE)
    index_title = index_title_match.group(1) if index_title_match else config.get("site_title", "Blog")

    index_content_without_frontmatter = re.sub(r'^---.*?---\n', '', index_md_content, flags=re.DOTALL)
    index_html_content = markdown.markdown(process_markdown_content(config, index_content_without_frontmatter, index_md_path))

    post_files = glob.glob(os.path.join(content_dir, '*.md'))
    post_files = [f for f in post_files if os.path.basename(f) != 'index.md']
    post_files.sort(key=lambda f: os.path.getmtime(f), reverse=True)

    summaries = [get_post_summary(config, f) for f in post_files]
    posts_html = '\n'.join(summaries)

    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()

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
    nav_content = generate_nav_html(config)
    with open('templates/_footer.html', 'r', encoding='utf-8') as f: footer_content = f.read()
    current_year = str(datetime.now().year)

    with open('templates/post.html', 'r', encoding='utf-8') as f:
        template_content = f.read()

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
    pattern = re.compile(r'(!\[.*?\]\((.*?)\)|<video.*?src="(.*?)".*?>)', re.IGNORECASE)
    project_root = os.getcwd()
    markdown_dir = os.path.dirname(markdown_file_path)
    output_dir = config.get('output_folder', 'public')
    site_url = config.get('site_url', '/')

    def replace_path(match):
        original_path = match.group(2) if match.group(2) else match.group(3)
        if not original_path or original_path.startswith(('http://', 'https://', '//', 'mailto:', 'tel:')):
            return match.group(0)
        if os.path.isabs(original_path):
            # Eğer yol zaten mutlaksa, proje kökünden itibaren olduğunu varsayalım
            source_abs_path = os.path.join(project_root, original_path.lstrip('/'))
        else:
            source_abs_path = os.path.abspath(os.path.join(markdown_dir, original_path))
        
        assets_dir = os.path.join(project_root, output_dir, 'assets')
        os.makedirs(assets_dir, exist_ok=True)
        filename = os.path.basename(source_abs_path)
        destination_abs_path = os.path.join(assets_dir, filename)
        
        # site_url'nin sonunda / olup olmadığını kontrol et
        if site_url.endswith('/'):
            new_absolute_path = f"{site_url}assets/{filename}"
        else:
            new_absolute_path = f"{site_url}/assets/{filename}"
        
        new_absolute_path = new_absolute_path.replace('\\', '/')

        if match.group(2) and filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
            if os.path.exists(source_abs_path):
                if not os.path.exists(destination_abs_path) or os.path.getmtime(source_abs_path) > os.path.getmtime(destination_abs_path):
                    if not optimize_image(source_abs_path, destination_abs_path):
                        print(f"Falling back to simple copy for {filename}", file=sys.stderr)
                        shutil.copy2(source_abs_path, destination_abs_path)
                else:
                    # print(f"Skipping optimization for {filename} (already optimized or source is older)", file=sys.stderr)
                    pass
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
        
        if match.group(2): # Markdown image ![]()
            alt_text = re.search(r'!\[(.*?)\]', match.group(0)).group(1)
            return f'![{alt_text}]({new_absolute_path})'
        elif match.group(3): # Video tag <video src="">
            return match.group(0).replace(original_path, new_absolute_path)
        return match.group(0)

    processed_content = pattern.sub(replace_path, markdown_content)
    link_pattern = re.compile(r'(\[.*?\]\((?!http|#|mailto|tel)(.*?\.md)\))')

    def replace_md_link(match):
        original_link_text = match.group(1)
        md_path = match.group(2)
        html_filename = os.path.basename(md_path).replace('.md', '.html')
        
        if site_url.endswith('/'):
             absolute_html_path = f"{site_url}{html_filename}"
        else:
             absolute_html_path = f"{site_url}/{html_filename}"

        absolute_html_path = absolute_html_path.replace('\\', '/')
        return original_link_text.replace(md_path, absolute_html_path)

    processed_content = link_pattern.sub(replace_md_link, processed_content)
    youtube_url_pattern = re.compile(r'(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})(?:\S+)?')
    processed_content = youtube_url_pattern.sub(
        r'<div class="video-container"><iframe src="https://www.youtube.com/embed/\1" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe></div>',
        processed_content
    )
    twitter_embed_found = False
    def twitter_replacer(match):
        nonlocal twitter_embed_found
        twitter_embed_found = True
        tweet_id = match.group(1)
        return f'<blockquote class="twitter-tweet"><a href="https://twitter.com/user/status/{tweet_id}"></a></blockquote>'

    twitter_url_pattern = re.compile(r'(?:https?://)?(?:www\.)?(?:twitter\.com|x\.com)/\w+/status/([0-9]+)(?:\S+)?')
    processed_content = twitter_url_pattern.sub(twitter_replacer, processed_content)
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
        config['site_url'] = args.site_url.rstrip('/')

    if args.generate_homepage:
        generate_homepage(config)
    elif args.prepare_post_template:
        temp_file_path = prepare_post_template(config)
        print(temp_file_path)
    elif args.input_file:
        with open(args.input_file, 'r', encoding='utf-8') as f:
            markdown_input = f.read()
        output_content = process_markdown_content(config, markdown_input, args.input_file)
        sys.stdout.write(output_content)
    else: # stdin
        markdown_input = sys.stdin.read()
        # Stdin'den okurken dosya yolu belirsiz olduğu için göreceli yollar sorun olabilir.
        # Bu yüzden geçici bir dosya adı kullanıyoruz.
        output_content = process_markdown_content(config, markdown_input, "stdin.md")
        sys.stdout.write(output_content)


if __name__ == "__main__":
    main()