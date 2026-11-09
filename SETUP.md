# Setup — passos que só você pode fazer

Tudo que é código já está pronto e automatizado. O que falta são contas e chaves que
exigem sua identidade/pagamento — por segurança, isso nunca deve ser feito por uma IA
sozinha. São ~20 minutos, feitos uma única vez.

## 1. Criar o repositório no GitHub

1. Crie uma conta em github.com, se ainda não tiver.
2. Crie um repositório novo, **público** (necessário para GitHub Pages grátis), com o
   nome que quiser (ex.: `ia-produtiva`).
3. No terminal, dentro desta pasta:
   ```
   git remote add origin https://github.com/SEU-USUARIO/NOME-DO-REPO.git
   git add -A
   git commit -m "Primeiro commit do projeto"
   git push -u origin main
   ```

## 2. Ativar o GitHub Pages

No repositório: **Settings → Pages → Build and deployment → Source: "Deploy from a
branch"** → Branch: `main`, pasta `/docs` → Save. Depois de alguns minutos o site fica
em `https://SEU-USUARIO.github.io/NOME-DO-REPO/`.

## 3. Pegar uma API key gratuita do Gemini

1. Acesse https://aistudio.google.com/app/apikey com uma conta Google.
2. Clique em "Create API key" e copie a chave gerada. O tier gratuito é suficiente para
   1-3 posts/dia sem custo.

## 4. Guardar a chave no repositório (GitHub Secrets)

**Settings → Secrets and variables → Actions → New repository secret**:
- Nome: `GEMINI_API_KEY` → Valor: a chave que você copiou no passo 3.

(Opcional) Você também pode criar o secret `MAX_POSTS_PER_DIA` com um número (padrão é
`1` se não criar).

## 5. Atualizar a URL do site

Edite `site.yaml` e troque `base_url` pela URL real do passo 2
(`https://SEU-USUARIO.github.io/NOME-DO-REPO/`). Sem isso o `sitemap.xml` fica com a
URL de placeholder.

## 6. Testar antes de deixar rodando sozinho

Na aba **Actions** do repositório, rode manualmente o workflow **"Publicar novo post"**
(botão "Run workflow") e confira se ele termina com sucesso e se o site atualizado
aparece no GitHub Pages. Depois disso, o cron diário assume sem precisar de você.

## 7. Cadastro em programas de afiliados (monetização real)

Enquanto você não fizer isso, os posts linkam para o site oficial de cada ferramenta
sem gerar comissão — o site funciona, só não monetiza ainda.

- **Amazon Associates Brasil:** https://associados.amazon.com.br/
- **Hostinger Affiliate Program:** procure "Hostinger affiliate program" no site oficial.
- **Notion, Jasper, Perplexity, Canva, ElevenLabs:** procure "affiliate program" no
  rodapé do site oficial de cada uma — a maioria tem programa próprio ou usa
  PartnerStack/Rewardful/Impact.

Depois de aprovado em cada programa, edite `pipeline/affiliates.yaml` e troque o campo
`url` de cada ferramenta pelo seu link de afiliado real, depois:
```
git add pipeline/affiliates.yaml
git commit -m "Atualiza links de afiliado"
git push
```

## 8. Opcional, só depois que o site tiver tráfego

- **Google Search Console** (grátis): confirma indexação e mostra por quais termos as
  pessoas acham o site.
- **Google Analytics / Plausible**: métricas de tráfego.
- **Google AdSense**: renda extra por anúncio, normalmente só aprova depois de algum
  tempo com conteúdo publicado.
- **Domínio próprio**: trocar `SEU-USUARIO.github.io/NOME-DO-REPO` por um domínio
  comprado (~R$ 40/ano), configurando em Settings → Pages → Custom domain.

## Importante: impostos e aspectos legais

Comissão de afiliado e renda de anúncio são renda real — a partir de um certo volume,
você precisa declarar no Imposto de Renda (e dependendo do volume, considerar abrir MEI).
Isso é uma decisão pessoal/financeira que a automação não toma por você.

## Trocar para a API da Anthropic (Claude) mais tarde

Quando o projeto já estiver gerando receita, crie os secrets `LLM_PROVIDER=anthropic`
e `ANTHROPIC_API_KEY=<sua chave>` para que os novos posts passem a ser gerados com
Claude em vez do Gemini, sem precisar tocar em nenhum código.
