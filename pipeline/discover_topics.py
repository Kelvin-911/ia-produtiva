"""
"Inovação": roda semanalmente (.github/workflows/discover.yml) e usa o LLM para
sugerir novas pautas de IA/produtividade ainda não publicadas, alimentando o backlog
para o generate_post.py consumir nos dias seguintes. Sem automação ainda não há caixa
para pagar uma API de busca paga, então o brainstorm usa o próprio conhecimento do LLM.
"""
import re
from pathlib import Path

import yaml

from llm_client import generate, LLMError

BACKLOG_FILE = Path(__file__).resolve().parent / "topics_backlog.yaml"
AFFILIATES_FILE = Path(__file__).resolve().parent / "affiliates.yaml"
N_NEW_TOPICS = 5


def build_prompt(existing_titles: list[str], tool_keys: list[str]) -> str:
    titles_block = "\n".join(f"- {t}" for t in existing_titles)
    return f"""Você ajuda a planejar pautas para um blog brasileiro sobre ferramentas de
IA e produtividade. Estes títulos já foram publicados ou estão na fila, não repita temas
parecidos:
{titles_block}

Sugira {N_NEW_TOPICS} pautas NOVAS e específicas (nada genérico como "IA no futuro").
Responda SOMENTE com uma lista YAML, sem comentários, neste formato exato:

- id: slug-curto-sem-acento
  title: "Título do artigo"
  tool: null

O campo "tool" só pode ser um destes valores ou null: {', '.join(tool_keys)}.
"""


def extract_yaml(raw: str) -> str:
    match = re.search(r"```(?:yaml)?\s*(.*?)```", raw, re.DOTALL)
    return match.group(1) if match else raw


def main():
    topics = yaml.safe_load(BACKLOG_FILE.read_text(encoding="utf-8")) or []
    affiliates = yaml.safe_load(AFFILIATES_FILE.read_text(encoding="utf-8")) or {}
    tool_keys = list(affiliates.keys())
    existing_ids = {t["id"] for t in topics}
    existing_titles = [t["title"] for t in topics]

    try:
        raw = generate(build_prompt(existing_titles, tool_keys))
    except LLMError as exc:
        print(f"[ERRO] discover_topics: {exc}")
        return

    try:
        new_topics = yaml.safe_load(extract_yaml(raw)) or []
    except yaml.YAMLError as exc:
        print(f"[ERRO] LLM retornou YAML inválido: {exc}\nResposta bruta:\n{raw}")
        return

    added = 0
    for topic in new_topics:
        if not isinstance(topic, dict) or "id" not in topic or "title" not in topic:
            continue
        if topic["id"] in existing_ids:
            continue
        if topic.get("tool") not in (None, *tool_keys):
            topic["tool"] = None
        topic["status"] = "pending"
        topics.append(topic)
        existing_ids.add(topic["id"])
        added += 1

    if added:
        BACKLOG_FILE.write_text(
            yaml.safe_dump(topics, allow_unicode=True, sort_keys=False), encoding="utf-8"
        )
    print(f"Adicionadas {added} nova(s) pauta(s) ao backlog.")


if __name__ == "__main__":
    main()
