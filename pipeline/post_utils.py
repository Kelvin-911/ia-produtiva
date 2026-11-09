"""Leitura/escrita de posts em Markdown com frontmatter YAML.

Compartilhado por generate_post.py, quality_check.py e site_builder/build.py
para não duplicar o parsing em três lugares.
"""
from pathlib import Path
import yaml

POSTS_DIR = Path(__file__).resolve().parent.parent / "content" / "posts"


def read_post(path: Path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError(f"{path} não tem frontmatter YAML (---).")
    _, raw_fm, body = text.split("---", 2)
    frontmatter = yaml.safe_load(raw_fm) or {}
    return frontmatter, body.strip()


def write_post(path: Path, frontmatter: dict, body: str) -> None:
    raw_fm = yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False)
    path.write_text(f"---\n{raw_fm}---\n\n{body.strip()}\n", encoding="utf-8")


def all_posts():
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(POSTS_DIR.glob("*.md"))


def existing_slugs() -> set:
    slugs = set()
    for p in all_posts():
        fm, _ = read_post(p)
        if fm.get("slug"):
            slugs.add(fm["slug"])
    return slugs
