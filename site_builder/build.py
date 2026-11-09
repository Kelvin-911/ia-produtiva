"""
Builda o site estático a partir de content/posts/*.md -> docs/ (servido pelo GitHub Pages).

Uso: python site_builder/build.py
"""
import datetime
import os
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


def load_posts():
    posts = []
    for path in all_posts():
        frontmatter, body = read_post(path)
        html_body = markdown.markdown(body, extensions=["extra"])
        posts.append({"frontmatter": frontmatter, "html_body": html_body})
    posts.sort(key=lambda p: p["frontmatter"].get("date", ""), reverse=True)
    return posts


def build():
    site = yaml.safe_load(SITE_CONFIG_FILE.read_text(encoding="utf-8"))
    affiliates = yaml.safe_load(AFFILIATES_FILE.read_text(encoding="utf-8")) or {}
    posts = load_posts()

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
    year = datetime.date.today().year

    index_tpl = env.get_template("index.html")
    (OUT_DIR / "index.html").write_text(
        index_tpl.render(site=site, posts=posts, root="", year=year),
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
                site=site, post=post, affiliate=affiliate, root="../../", year=year
            ),
            encoding="utf-8",
        )

    _write_sitemap(site, posts)
    (OUT_DIR / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {site['base_url'].rstrip('/')}/sitemap.xml\n",
        encoding="utf-8",
    )
    (OUT_DIR / ".nojekyll").write_text("", encoding="utf-8")
    print(f"Site gerado em {OUT_DIR} com {len(posts)} post(s).")


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
