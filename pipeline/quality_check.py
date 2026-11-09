"""
Guardrail de qualidade. Bloqueia a publicação de um post se:
- faltar campo obrigatório no frontmatter (title, date, description, slug)
- o corpo do artigo for curto demais (post fino/raso não ajuda SEO nem o leitor)
- faltar o aviso de link de afiliado quando o post referencia uma ferramenta
- o slug já existir em outro post (duplicidade)

Uso: python pipeline/quality_check.py content/posts/arquivo.md
Saída: exit 0 se passou, exit 1 se falhou (imprime os motivos).
"""
import sys
from pathlib import Path

import yaml

from post_utils import read_post, all_posts

REQUIRED_FIELDS = ["title", "date", "description", "slug"]
MIN_WORDS = 500
DISCLOSURE_MARKERS = ["link de afiliado", "links de afiliado", "comissão"]

AFFILIATES_FILE = Path(__file__).resolve().parent / "affiliates.yaml"


def _load_affiliate_keys():
    data = yaml.safe_load(AFFILIATES_FILE.read_text(encoding="utf-8")) or {}
    return set(data.keys())


def check_post(path: Path):
    errors = []
    try:
        frontmatter, body = read_post(path)
    except Exception as exc:  # noqa: BLE001 - queremos capturar qualquer erro de parsing
        return [f"Não foi possível ler o post: {exc}"]

    for field in REQUIRED_FIELDS:
        if not frontmatter.get(field):
            errors.append(f"Campo obrigatório ausente no frontmatter: '{field}'")

    word_count = len(body.split())
    if word_count < MIN_WORDS:
        errors.append(f"Corpo do artigo tem só {word_count} palavras (mínimo {MIN_WORDS}).")

    tool = frontmatter.get("tool")
    if tool:
        known_tools = _load_affiliate_keys()
        if tool not in known_tools:
            errors.append(f"tool '{tool}' não existe em affiliates.yaml.")
        has_disclosure = any(marker in body.lower() for marker in DISCLOSURE_MARKERS)
        if not has_disclosure:
            errors.append(
                "Post referencia uma ferramenta de afiliado mas não contém o aviso "
                "de link de afiliado no corpo (exigido pelo CDC/Procon no Brasil)."
            )

    slug = frontmatter.get("slug")
    if slug:
        duplicates = []
        resolved_path = path.resolve()
        for other in all_posts():
            if other.resolve() == resolved_path:
                continue
            other_fm, _ = read_post(other)
            if other_fm.get("slug") == slug:
                duplicates.append(other.name)
        if duplicates:
            errors.append(f"Slug '{slug}' duplicado em: {', '.join(duplicates)}")

    return errors


def main():
    if len(sys.argv) != 2:
        print("Uso: python pipeline/quality_check.py content/posts/arquivo.md")
        sys.exit(2)
    path = Path(sys.argv[1])
    errors = check_post(path)
    if errors:
        print(f"REPROVADO: {path.name}")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print(f"OK: {path.name}")
    sys.exit(0)


if __name__ == "__main__":
    main()
