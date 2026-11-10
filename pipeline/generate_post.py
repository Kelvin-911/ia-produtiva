"""
Gera o(s) próximo(s) artigo(s) pendente(s) do backlog, insere o link de afiliado
correto e grava em content/posts/. Roda sozinho via .github/workflows/publish.yml.

Uso:
  python pipeline/generate_post.py                 # gera até MAX_POSTS_PER_DIA posts
  python pipeline/generate_post.py --dry-run        # gera 1 post em content/_preview/
                                                     # sem tocar no backlog (p/ revisão)
"""
import datetime
import os
import sys
import time
from pathlib import Path

import yaml

from llm_client import generate, LLMError
from post_utils import write_post
import quality_check

ROOT = Path(__file__).resolve().parent.parent
BACKLOG_FILE = Path(__file__).resolve().parent / "topics_backlog.yaml"
AFFILIATES_FILE = Path(__file__).resolve().parent / "affiliates.yaml"
PREVIEW_DIR = ROOT / "content" / "_preview"
POSTS_DIR = ROOT / "content" / "posts"


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8")) or []


def save_backlog(topics):
    BACKLOG_FILE.write_text(
        yaml.safe_dump(topics, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


def build_prompt(topic: dict, affiliate: dict | None) -> str:
    tool_block = ""
    if affiliate:
        tool_block = (
            f"\nA ferramenta em destaque é '{affiliate['nome']}' ({affiliate['url']}). "
            "Inclua uma recomendação natural dela ao longo do texto e, obrigatoriamente, "
            "um parágrafo claro informando que o post contém link de afiliado e que pode "
            "gerar comissão sem custo extra para o leitor."
        )
    return f"""Você é um redator especialista em IA e produtividade escrevendo em
português do Brasil para um blog. Escreva um artigo completo sobre:

Título: {topic['title']}

Estrutura obrigatória da resposta:
1. Primeira linha: "DESCRIPTION: " seguido de uma meta description de até 155 caracteres.
2. Depois uma linha só com "---".
3. Depois o artigo em Markdown, com introdução, 3 a 5 seções usando "## ", uma seção de
   prós e contras quando fizer sentido, e uma conclusão com recomendação prática.
   O artigo deve ter pelo menos 700 palavras, tom direto e útil, sem enrolação,
   sem inventar dados estatísticos específicos. NÃO repita o título como um "# " no
   início do artigo (o título já é exibido pela página); comece direto pela introdução.
   Não use linhas só com "---" dentro do corpo do artigo.
{tool_block}
"""


def _strip_leading_h1(body: str) -> str:
    # Rede de segurança: se o modelo ignorar a instrução e repetir o título como
    # "# ..." na primeira linha, remove — a página já renderiza o título sozinha.
    lines = body.split("\n", 1)
    if lines[0].strip().startswith("# "):
        return lines[1].strip() if len(lines) > 1 else ""
    return body


def parse_llm_output(raw: str) -> tuple[str, str]:
    if not raw.startswith("DESCRIPTION:"):
        # fallback: sem description explícita, usa as primeiras palavras do corpo
        body = _strip_leading_h1(raw.strip())
        description = " ".join(body.split()[:25])
        return description[:155], body
    first_line, _, rest = raw.partition("\n")
    description = first_line.replace("DESCRIPTION:", "").strip()[:155]
    body = _strip_leading_h1(rest.split("---", 1)[-1].strip())
    return description, body


def generate_one(topic: dict, affiliates: dict, dry_run: bool) -> str:
    """Retorna "ok", "quality_fail" (problema só deste tópico, vale tentar o
    próximo) ou "api_fail" (a API/rede está com problema — tentar outro tópico
    na sequência só gastaria mais cota do tier gratuito à toa)."""
    affiliate = affiliates.get(topic.get("tool")) if topic.get("tool") else None
    prompt = build_prompt(topic, affiliate)
    try:
        raw = generate(prompt)
    except LLMError as exc:
        print(f"[ERRO] Falha ao gerar '{topic['id']}': {exc}")
        return "api_fail"

    description, body = parse_llm_output(raw)
    frontmatter = {
        "title": topic["title"],
        "date": datetime.date.today().isoformat(),
        "description": description,
        "slug": topic["id"],
        "tool": topic.get("tool"),
        "tags": ["ia", "produtividade"] + ([topic["tool"]] if topic.get("tool") else []),
    }

    target_dir = PREVIEW_DIR if dry_run else POSTS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    out_path = target_dir / f"{topic['id']}.md"
    write_post(out_path, frontmatter, body)

    errors = quality_check.check_post(out_path)
    if errors:
        print(f"[REPROVADO] {topic['id']}:")
        for e in errors:
            print(f"  - {e}")
        if not dry_run:
            out_path.unlink(missing_ok=True)
        return "quality_fail"

    print(f"[OK] Gerado: {out_path.relative_to(ROOT)}")
    return "ok"


def main():
    dry_run = "--dry-run" in sys.argv
    # "or" em vez do default do .get(): no GitHub Actions uma secret não configurada
    # chega como string vazia, não ausente, o que quebraria o int() com o .get() puro.
    max_posts = 1 if dry_run else int(os.environ.get("MAX_POSTS_PER_DIA") or "1")

    topics = load_yaml(BACKLOG_FILE)
    affiliates = load_yaml(AFFILIATES_FILE)

    pending = [t for t in topics if t.get("status") == "pending"]
    if not pending:
        print("Nenhum tópico pendente no backlog. Rode discover_topics.py.")
        return

    done_count = 0
    api_failed = False
    for i, topic in enumerate(pending):
        if done_count >= max_posts:
            break
        if i > 0:
            # Tier gratuito do Gemini limita ~5 requisições/minuto.
            time.sleep(15)
        result = generate_one(topic, affiliates, dry_run)
        if result == "ok":
            done_count += 1
            if not dry_run:
                topic["status"] = "done"
        elif result == "api_fail":
            # A API/rede está com problema agora — tentar o próximo tópico só
            # gastaria mais cota do tier gratuito sem chance real de dar certo.
            api_failed = True
            break
        # "quality_fail": tenta o próximo tópico, o problema é só deste.

    if not dry_run and done_count:
        save_backlog(topics)
    print(f"Concluído: {done_count} post(s) gerado(s).")

    if not dry_run and done_count == 0:
        # Sinaliza falha pro GitHub Actions (ex: chave de API ausente/expirada,
        # ou a API fora do ar) em vez de "funcionar silenciosamente" sem publicar nada.
        sys.exit(1)
    if api_failed and done_count < max_posts:
        print("Aviso: parou cedo por falha da API; o cron de amanhã tenta de novo.")


if __name__ == "__main__":
    main()
