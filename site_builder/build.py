"""
Builda o site estático a partir de content/posts/*.md -> docs/ (servido pelo GitHub Pages).

Uso: python site_builder/build.py
"""
import datetime
import os
import re
import shutil
import stat
import sys
from pathlib import Path

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
from post_utils import all_posts, read_post  # noqa: E402

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
STATIC_DIR = Path(__file__).resolve().parent / "static"
OUT_DIR = ROOT / "docs"
SITE_CONFIG_FILE = ROOT / "site.yaml"
AFFILIATES_FILE = ROOT / "pipeline" / "affiliates.yaml"
PAGES_DIR = ROOT / "content" / "pages"


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def load_posts():
    posts = []
    for path in all_posts():
        frontmatter, body = read_post(path)
        html_body = markdown.markdown(body, extensions=["extra"])
        posts.append({"frontmatter": frontmatter, "html_body": html_body})
    posts.sort(key=lambda p: p["frontmatter"].get("date", ""), reverse=True)
    return posts


def load_pages():
    pages = []
    for path in sorted(PAGES_DIR.glob("*.md")):
        frontmatter, body = read_post(path)
        html_body = markdown.markdown(body, extensions=["extra"])
        pages.append({"frontmatter": frontmatter, "html_body": html_body})
    return pages


def group_by_tag(posts):
    tags = {}
    for post in posts:
        for tag in post["frontmatter"].get("tags") or []:
            tags.setdefault(slugify(tag), []).append(post)
    return dict(sorted(tags.items()))


def build():
    site = yaml.safe_load(SITE_CONFIG_FILE.read_text(encoding="utf-8"))
    affiliates = yaml.safe_load(AFFILIATES_FILE.read_text(encoding="utf-8")) or {}
    posts = load_posts()
    pages = load_pages()
    tags = group_by_tag(posts)

    if OUT_DIR.exists():
        # Pastas sincronizadas pelo OneDrive ficam read-only; limpa o atributo
        # antes de remover em vez de falhar com PermissionError.
        def _force_remove(func, path, exc):
            os.chmod(path, stat.S_IWRITE)
            func(path)

        shutil.rmtree(OUT_DIR, onexc=_force_remove)
    OUT_DIR.mkdir(parents=True)
    shutil.copytree(STATIC_DIR, OUT_DIR, dirs_exist_ok=True)

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    env.filters["slugify"] = slugify
    year = datetime.date.today().year

    index_tpl = env.get_template("index.html")
    (OUT_DIR / "index.html").write_text(
        index_tpl.render(site=site, posts=posts, root="", year=year, path=""),
        encoding="utf-8",
    )

    post_tpl = env.get_template("post.html")
    for post in posts:
        slug = post["frontmatter"]["slug"]
        post_dir = OUT_DIR / "posts" / slug
        post_dir.mkdir(parents=True, exist_ok=True)
        tool_key = post["frontmatter"].get("tool")
        affiliate = affiliates.get(tool_key) if tool_key else None
        (post_dir / "index.html").write_text(
            post_tpl.render(
                site=site, post=post, affiliate=affiliate, root="../../", year=year,
                path=f"posts/{slug}/",
            ),
            encoding="utf-8",
        )

    page_tpl = env.get_template("page.html")
    for page in pages:
        slug = page["frontmatter"]["slug"]
        page_dir = OUT_DIR / slug
        page_dir.mkdir(parents=True, exist_ok=True)
        (page_dir / "index.html").write_text(
            page_tpl.render(site=site, page=page, root="../", year=year, path=f"{slug}/"),
            encoding="utf-8",
        )

    tags_index_tpl = env.get_template("tags_index.html")
    (OUT_DIR / "tags").mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "tags" / "index.html").write_text(
        tags_index_tpl.render(site=site, tags=tags, root="../", year=year, path="tags/"),
        encoding="utf-8",
    )

    tag_tpl = env.get_template("tag.html")
    for tag_slug, tag_posts in tags.items():
        tag_dir = OUT_DIR / "tags" / tag_slug
        tag_dir.mkdir(parents=True, exist_ok=True)
        (tag_dir / "index.html").write_text(
            tag_tpl.render(
                site=site, tag_name=tag_slug, posts=tag_posts, root="../../", year=year,
                path=f"tags/{tag_slug}/",
            ),
            encoding="utf-8",
        )

    _write_rss(site, posts)
    _write_sitemap(site, posts)
    (OUT_DIR / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {site['base_url'].rstrip('/')}/sitemap.xml\n",
        encoding="utf-8",
    )
    (OUT_DIR / ".nojekyll").write_text("", encoding="utf-8")
    print(
        f"Site gerado em {OUT_DIR} com {len(posts)} post(s), {len(pages)} página(s) "
        f"e {len(tags)} categoria(s)."
    )


def _write_rss(site, posts):
    from xml.sax.saxutils import escape

    base = site["base_url"].rstrip("/")
    items = []
    for p in posts:
        fm = p["frontmatter"]
        link = f"{base}/posts/{fm['slug']}/"
        items.append(
            "  <item>\n"
            f"    <title>{escape(fm['title'])}</title>\n"
            f"    <link>{escape(link)}</link>\n"
            f"    <guid>{escape(link)}</guid>\n"
            f"    <description>{escape(fm.get('description', ''))}</description>\n"
            f"    <pubDate>{fm.get('date', '')}</pubDate>\n"
            "  </item>"
        )
    body = "\n".join(items)
    (OUT_DIR / "rss.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0"><channel>\n'
        f"  <title>{escape(site['nome'])}</title>\n"
        f"  <link>{escape(base)}/</link>\n"
        f"  <description>{escape(site['descricao'])}</description>\n"
        f"{body}\n"
        "</channel></rss>\n",
        encoding="utf-8",
    )


def _write_sitemap(site, posts):
    base = site["base_url"].rstrip("/")
    urls = [f"{base}/"] + [f"{base}/posts/{p['frontmatter']['slug']}/" for p in posts]
    body = "\n".join(f"  <url><loc>{u}</loc></url>" for u in urls)
    (OUT_DIR / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{body}\n</urlset>\n',
        encoding="utf-8",
    )


if __name__ == "__main__":
    build()
