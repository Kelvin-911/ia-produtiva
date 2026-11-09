# IA Produtiva — blog autônomo de IA & produtividade

Blog estático em português sobre ferramentas de IA e produtividade, com conteúdo gerado
e publicado automaticamente via GitHub Actions, e monetizado por links de afiliado.

Veja **SETUP.md** para os passos manuais necessários (contas, chaves, afiliados) antes
de deixar a automação rodando sozinha, e `C:\Users\kelvi\.claude\plans\parsed-sleeping-moonbeam.md`
para o plano completo de arquitetura e fases do projeto.

## Estrutura

- `content/posts/` — artigos em Markdown (frontmatter + corpo).
- `pipeline/` — scripts Python que geram, validam e descobrem pautas automaticamente.
- `site_builder/` — gera o site estático (`docs/`) a partir dos posts.
- `docs/` — saída gerada, servida pelo GitHub Pages. Não editar manualmente.
- `.github/workflows/` — automação: `publish.yml` (diário) e `discover.yml` (semanal).

## Comandos locais

```bash
pip install -r requirements.txt

# gerar o site a partir dos posts existentes
python site_builder/build.py

# testar a geração de 1 post sem publicar (grava em content/_preview/)
cd pipeline && python generate_post.py --dry-run

# validar um post manualmente
python pipeline/quality_check.py content/posts/arquivo.md

# ver o site localmente
python -m http.server --directory docs 8000
```

## Como o ciclo autônomo funciona

1. `discover_topics.py` (semanal) usa o LLM para sugerir pautas novas e evita repetir
   temas já publicados.
2. `generate_post.py` (diário) escreve o próximo artigo pendente, insere o link de
   afiliado certo e só publica se passar por `quality_check.py`.
3. `site_builder/build.py` reconstrói o site e o GitHub Actions commita tudo.

Todo o histórico fica em commits do Git — qualquer post pode ser revertido com
`git revert` se algo saír errado.
