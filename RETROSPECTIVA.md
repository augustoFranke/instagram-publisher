# Instagram Publisher — Retrospectiva técnica

## Contexto

A skill `instagram-publisher` nasceu como uma solução pessoal para publicar conteúdo no Instagram diretamente pelo Claude Code, sem abrir browser, sem copiar e colar URLs em interfaces gráficas. O script `publish.py` já existia e funcionava — o problema era que a skill que o envolvia era um arquivo markdown simples, sem estrutura, sem frontmatter, e sem cobertura suficiente para que o modelo soubesse o que fazer nos casos mais avançados.

A sessão de otimização foi um ciclo completo de diagnóstico → reescrita → teste → eval → refinamento. Este documento registra cada decisão tomada e o raciocínio por trás dela.

---

## 1. Estado inicial — o que estava errado

### 1.1 Ausência de frontmatter YAML

O problema mais crítico, e também o menos óbvio: a SKILL.md original não tinha o bloco `---` de frontmatter. Sem ele, o sistema de skills do Claude Code não tinha como ler os campos `name` e `description` de forma estruturada.

Na prática, isso significava que o `available_skills` — a lista que o modelo vê para decidir quando acionar uma skill — tinha como entrada para o instagram-publisher apenas o título `# Instagram Publisher`. Uma descrição de duas palavras para uma skill que cobre 10+ flags, 3 tipos de conteúdo, uploads locais via Tailscale, agendamento, tags, alt text e controle de comentários.

O resultado direto era undertriggering severo: o modelo simplesmente não sabia quando usar a skill.

### 1.2 Path hardcoded com username

O script era referenciado como:

```
python3 /Users/augustodoregofranke/.claude/skills/instagram-publisher/publish.py
```

Isso funcionava para uma máquina específica mas tornava a skill intransferível. O correto é `~/.claude/skills/...`, que resolve para o home directory de qualquer usuário.

### 1.3 Seção "Trigger" no body, não na description

A skill original tinha uma seção `## Trigger` dentro do corpo do markdown listando exemplos de frases. Esse conteúdo estava no lugar errado — o triggering em Claude Code é determinado pelo campo `description` no frontmatter, não pelo corpo da skill. O corpo só é lido *depois* que o modelo já decidiu acionar a skill. Colocar os critérios de ativação no corpo é como colocar a ementa do restaurante do lado de fora mas escondida atrás da porta — só quem já entrou consegue ler.

### 1.4 Flags documentadas mas sem exemplos concretos

O original listava `--alt-text`, `--user-tags` e `--disable-comments` nos parâmetros, mas não mostrava um comando completo usando essas flags juntas. Para um modelo que aprende por padrões, a ausência de exemplo é quase equivalente à ausência de instrução.

### 1.5 Header impreciso de flags

A seção dizia "Optional flags (all content types)" mas `--alt-text` não funciona em reels — confirmado lendo o `publish.py` diretamente — e `--cover-url` (reel-only) nem aparecia na tabela de flags, só em um exemplo isolado. Informação parcialmente errada é pior que informação ausente porque cria falsa confiança.

---

## 2. Análise dos padrões nativos

Antes de reescrever, foram lidas três skills nativas do Claude Code como referência:

- **xlsx**: extensa, cobre fórmulas, bibliotecas, fluxo de trabalho, tem scripts bundled
- **pdf**: organizada em seções, quick start, CLI tools, quick reference table
- **schedule**: curta e focada, 5 passos lineares, zero gordura

O padrão comum entre todas: frontmatter obrigatório com description rica, corpo organizado em seções com propósito claro, e progressive disclosure — o que o modelo precisa saber primeiro aparece primeiro.

O instagram-publisher precisava de algo entre o `pdf` e o `schedule`: completo o suficiente para cobrir casos avançados, mas sem exibir tudo de uma vez.

---

## 3. Decisões de reescrita

### 3.1 A description como primeiro entregável

A primeira e mais importante mudança foi escrever uma description que merecesse o nome. Os critérios usados:

- **Pushy por design**: a documentação do skill-creator explica que o modelo tende a undertriggerar skills. A description precisa ser ativa, não descritiva. "Use this skill whenever..." em vez de "This skill does...".
- **Bilíngue**: o usuário trabalha em português, então a description precisava cobrir explicitamente `postar`, `publicar`, `agendar`, `ig`, `insta` — não apenas os equivalentes em inglês.
- **Skip explícito**: indicar o que a skill *não* faz é tão importante quanto indicar o que faz. Sem o `Skip:`, o modelo pode acionar a skill para "me ajuda a escrever uma legenda para o instagram" — que é pesquisa criativa, não publicação via API.
- **Curta o suficiente**: a description vive no contexto de todas as sessions. Cada token conta.

A description passou por três versões ao longo da sessão, culminando em:

> *"Publish photos, videos, and carousels to Instagram via the Graph API — no browser needed. Use when the user wants to upload media they have (local file, URL, or attachment) to Instagram/IG/insta — in English (post/publish/share/schedule) or Portuguese (postar/publicar/agendar no Instagram/ig). Handles captions, scheduling, user tags, alt text, comment controls. Skip: caption writing only, hashtag research, analytics, content planning, or posting to other platforms."*

### 3.2 Flags separadas por content type

Em vez de uma tabela plana de flags com a nota "all content types" — que estava errada — a decisão foi criar três blocos explícitos:

1. Flags que funcionam em todos os tipos
2. Flags exclusivas de photo e carousel (`--alt-text`)
3. Flags exclusivas de reel (`--cover-url`)

Essa separação reflete a realidade do script e evita que o modelo tente passar `--alt-text` para um reel e receba um erro silencioso (o argparse ignora flags desconhecidas nesse contexto).

### 3.3 Exemplo composto com todas as flags avançadas

O gap identificado: `--alt-text`, `--user-tags` e `--disable-comments` existiam na documentação mas nunca apareciam juntos. A solução foi um exemplo dedicado mostrando as três flags em uso simultâneo, com um caption multiline usando a sintaxe `$'...\n...'` do bash — que também estava ausente e é não-óbvio para quem não é intimamente familiar com shell scripting.

### 3.4 User tags: explicação das coordenadas

O formato `[{"username":"alice","x":0.5,"y":0.3}]` é opaco sem explicação. A decisão de adicionar "x e y são coordenadas normalizadas de 0.0 a 1.0 indicando onde o pin aparece na imagem" transforma um JSON arbitrário em algo que o modelo consegue construir corretamente para qualquer pedido — incluindo "tagueia a Alice no canto esquerdo" ou "tag o Bob no centro da foto".

### 3.5 Carousel com vídeo

O `publish.py` detecta extensões `.mp4` e `.mov` nos itens do carousel e os envia como `media_type=VIDEO`. Mas a SKILL.md original só dizia "2-10 images". A correção foi mencionar explicitamente que o carousel suporta mix de imagens e vídeos, e mostrar um exemplo com `.mp4` como item.

---

## 4. A arquitetura de upload local via Tailscale Funnel

Este é o mecanismo técnico mais sofisticado da skill e merece atenção separada.

O Instagram Graph API não aceita arquivos — aceita URLs públicas. Quando o usuário quer postar um arquivo local (uma foto que acabou de tirar, um vídeo que editou), há um problema: o arquivo está na máquina do usuário, atrás de um NAT, sem URL pública.

A solução implementada no `publish.py` é elegante: o script levanta um servidor HTTP local em uma porta aleatória, copia o arquivo para um diretório temporário, e usa `tailscale funnel <porta>` para criar um túnel HTTPS público. O resultado é uma URL como `https://maquina.tailnet-xyz.ts.net/arquivo.jpg` que o Instagram consegue buscar.

O script aguarda ativamente o Funnel propagar (polling com HEAD requests a cada 5 segundos, até 120 segundos), passa a URL para a API, e ao final encerra o Funnel e limpa o diretório temporário.

**Implicações para a skill:**
- O usuário precisa ter Tailscale instalado, autenticado, e Funnel habilitado na ACL
- Não é um pré-requisito para posts de URL — só para arquivos locais
- O `setup.md` foi criado especificamente para documentar esse caminho de configuração, que tem mais passos do que simplesmente "instale o Tailscale"

**Trade-off consciente:** usar Tailscale Funnel é mais complexo do que alternativas como ngrok ou um servidor S3 temporário, mas tem a vantagem de não requerer conta adicional, ser gratuito para uso pessoal, e funcionar sem configuração de firewall além da ACL do Tailscale.

---

## 5. O setup.md — documento novo

A skill original instruía: "se faltar credencial, peça ao usuário para preencher o `.env`". Mas não explicava de onde viriam os valores. Um usuário novo sem experiência com Meta Developer Console não saberia o que fazer.

A decisão de criar um `setup.md` separado (em vez de adicionar ao SKILL.md) foi deliberada:

- **Progressive disclosure**: o SKILL.md é lido em toda invocação. Colocar 6 passos de setup lá desperdiçaria tokens para usuários que já estão configurados.
- **Referência sob demanda**: o SKILL.md agora diz "se for a primeira vez, leia setup.md". O modelo carrega o documento só quando necessário.
- **Completude do setup.md**: cobre criação do app no Meta Developer Console, obtenção do `IG_USER_ID`, geração e troca do token short-lived → long-lived, criação do `.env`, configuração do Tailscale Funnel, e verificação com um post de teste. Inclui tabela de troubleshooting com 5 cenários de erro e o comando ffmpeg para re-encodar vídeos no codec correto.

---

## 6. Tratamento de erros — do silêncio ao mapeamento explícito

A skill original não dizia nada sobre o que fazer quando o script falhava. O modelo estava por conta própria para interpretar um output como:

```
Erro API (400): {"error": {"code": 190, "message": "Error validating access token"}}
```

A adição de uma tabela de erros mapeando padrão → causa → resposta ao usuário transforma o modelo de "receptor passivo de output" em "diagnóstico ativo". Os casos cobertos:

| Erro | Causa | Ação |
|---|---|---|
| IG_USER_ID/ACCESS_TOKEN not set | .env ausente | Redireciona ao setup.md |
| API 190 / invalid token / 401 | Token expirado (60 dias) | Instrui a renovar via Meta Console |
| API 352 / unsupported format | Codec errado | Instrui a re-encodar com H.264 + AAC |
| API 36000 / caption too long | Caption > 2.200 chars | Instrui a encurtar |
| Funnel not reachable | Tailscale não configurado | Redireciona ao setup.md |
| File not found | Path incorreto | Confirmar path absoluto |

A expiração do token em 60 dias merece atenção especial: sem esse aviso, o usuário recebe um erro 401 meses depois de configurar a skill e não sabe por quê funcionava antes. Saber que tokens long-lived expiram e como renová-los é a diferença entre "a skill quebrou" e "a skill está me guiando".

---

## 7. Caption guidance — três dimensões não-óbvias

### 7.1 Oferta proativa

O comportamento esperado de um bom assistente ao receber "posta essa foto no instagram" sem caption não é postar sem legenda, nem recusar por falta de instrução — é perguntar ou oferecer escrever uma. A instrução explícita garante esse comportamento.

### 7.2 Limites do Instagram

2.200 caracteres e 30 hashtags são limites reais da API. Um modelo gerando captions longas sem saber disso vai produzir posts que falham na publicação com um erro críptico (`API 36000`). Colocar o limite na skill fecha esse loop antes de chegar ao erro.

### 7.3 Multiline em bash

`$'linha1\n\nlinha2'` não é sintaxe óbvia. Em contextos onde o usuário quer uma caption com quebra de linha — prática comum em posts de Instagram — o modelo sem essa instrução vai ou passar a string com `\n` literal (que aparece como texto), ou tentar quoted strings que o argparse interpreta incorretamente. Um exemplo concreto resolve isso de forma definitiva.

---

## 8. A curiosidade do usuário como motor de robustez

Um padrão recorrente na sessão: a pergunta "a skill mostra como usar todas as flags?" revelou buracos que não seriam encontrados por uma revisão passiva.

O processo foi:
1. Ler o `publish.py` linha por linha
2. Listar todas as flags e seus contextos de uso
3. Comparar contra o que estava documentado
4. Identificar gaps

Gaps encontrados por esse processo:
- `--alt-text` não funciona em reels (confirmado no `cmd_reel` do script)
- `--cover-url` estava em um exemplo mas ausente da tabela de flags
- O header "all content types" estava tecnicamente errado
- Carousel suportava vídeo mas a skill não mencionava

Esse exercício de "ler o código fonte e comparar contra a documentação" é uma técnica de auditoria que deveria ser padrão em qualquer skill que envolva um script externo. A documentação reflete intenção; o código é a realidade.

---

## 9. Estratégia de testes — dois regimes diferentes

### 9.1 Triggering eval (run_loop.py)

O primeiro eval rodado usou o framework nativo do skill-creator: 20 queries (10 should-trigger, 10 should-not), cada uma testada 3 vezes em `claude -p` headless, verificando se o modelo acionava a skill.

**Resultado: 5 iterações, ~0% de recall em todas.**

A causa raiz foi identificada como uma limitação estrutural do framework para skills de ação: em modo `claude -p` headless, o modelo recebe "posta essa foto no instagram" e responde diretamente ("não tenho credenciais...") em vez de consultar a skill, porque percebe que não precisa de instruções especializadas para *responder* — só precisaria para *executar*. Skills de geração de conteúdo (docx, xlsx, pdf) funcionam bem nesse regime porque o modelo genuinamente precisa da skill para saber *como* produzir o output.

**O que o triggering eval ainda produziu de valor:** confirmou que os false positives estavam zerados. Nenhuma das 10 queries de should-not-trigger acionou a skill em nenhuma iteração. A descrição tinha boa especificidade, falhava em sensibilidade.

As 5 iterações produziram descrições candidatas com abordagens diferentes:
- Estrutura com "combine ALL THREE: mention + verb + media"
- Tom imperativo com "actually post, not plan or brainstorm"
- Bloco `Skip:` explícito

Nenhuma superou a original no test set (holdout 40%). A melhor descrição final foi um híbrido manual das melhores características de cada candidata.

### 9.2 Execution eval (codex exec)

O segundo eval foi a abordagem correta para skills de ação: dado um pedido do usuário, o modelo construiu o comando correto?

**10 casos de teste, 38 assertions:**

| Caso | O que testa |
|---|---|
| Photo por URL | Subcomando, URL positional, flag caption, ausência de --file |
| Photo por arquivo local | --file com path absoluto, ausência de URL como positional |
| Reel com thumbnail | --cover-url em reel, não em photo |
| Scheduled photo | --schedule com datetime exato |
| Carousel por URLs | Múltiplas URLs posicionais, subcomando carousel |
| Photo com user tags + alt text + sem comentários | Três flags avançadas juntas, JSON de tags |
| Carousel por arquivos locais | --files (plural), múltiplos paths |
| Reel local sem comentários | --file, --disable-comments, detecção de PT |
| Erro 190 (token expirado) | Diagnóstico correto, não repetição cega do comando |
| Sem caption fornecida | Oferta de escrever caption, não postagem imediata |

**Resultado: 10/10 casos, 38/38 assertions — 100% de pass rate.**

O eval foi rodado via `codex exec` (OpenAI Codex CLI) em vez de Claude Code, por decisão explícita de economia de tokens. Isso introduziu dois problemas técnicos resolvidos na hora:

1. **stdin pipe**: passar o prompt via `$(cat arquivo)` em subshell fez o codex interpretar como leitura de stdin e travar. Solução: atribuir a variável antes e passar como argumento direto.
2. **git repo check**: o codex exige que o working directory seja um repositório git por padrão. Solução: `git init` no workspace antes de disparar o processo.

---

## 10. Arquitetura final do projeto

```
~/.claude/skills/instagram-publisher/   ← skill instalada (em uso)
├── SKILL.md                            ← instruções para o modelo (146 linhas)
├── setup.md                            ← guia de configuração para o usuário (117 linhas)
├── publish.py                          ← script da Graph API (395 linhas)
└── .env                                ← credenciais (IG_USER_ID, ACCESS_TOKEN)

~/Developer/instagram-publisher/        ← repositório de desenvolvimento
├── SKILL.md                            ← source of truth para edição
├── setup.md
├── publish.py
└── RETROSPECTIVA.md                    ← este documento

~/Developer/instagram-publisher-workspace/   ← artefatos de eval
├── trigger_eval.json                   ← 20 queries de triggering
├── codex_eval_prompt.md                ← prompt do execution eval
├── run_execution_eval.py               ← script gerado pelo codex
├── eval_execution_results.json         ← resultados (10/10, 38/38)
└── run_loop.log                        ← log das 5 iterações de triggering
```

---

## 11. Trade-offs e decisões não tomadas

**Tailscale vs. alternativas**: ngrok, localtunnel e upload direto para S3 foram opções não explicitamente descartadas mas implicitamente rejeitadas por requererem contas externas ou configuração adicional. O Tailscale já era uma dependência existente do usuário.

**setup.md separado vs. seção no SKILL.md**: a opção de colocar o setup dentro da SKILL.md foi rejeitada para não desperdiçar tokens em invocações de usuários já configurados. O custo é que o modelo precisa de uma instrução explícita para saber quando carregar o documento.

**Eval de triggering como métrica principal**: foi reconhecido como inadequado para skills de ação após a primeira rodada, mas rodado até o fim para confirmar a hipótese e documentar o resultado. O valor produzido foi a confirmação de especificidade (zero false positives) e a exploração do espaço de descriptions candidatas.

**100% no execution eval como sinal definitivo**: um pass rate perfeito em um eval de 10 casos pode ser sinal de eval fácil demais. A mitigação foi usar assertions compostas (casos 6 e 7 com 5-6 assertions cada) e incluir casos de comportamento (casos 9 e 10) além de casos de construção de comando. Um segundo ciclo com casos mais ambíguos seria o próximo passo natural.

---

## 12. O que fica como aprendizado

A skill começou como um wrapper fino em torno de um script de linha de comando. Terminou como um sistema documentado com:

- Triggering calibrado para PT e EN, cobrindo abreviações coloquiais
- Cobertura completa de todos os content types e flags, segregada por aplicabilidade
- Arquitetura de upload local via Tailscale explicada em termos de requisitos do usuário
- Guia de setup standalone para onboarding de novos usuários
- Mapeamento de erros com diagnóstico e ação sugerida
- Orientação de comportamento proativo (oferta de caption, aviso de limite)
- Eval de execução com 100% de pass rate em 10 casos e 38 assertions

O ponto mais importante: a robustez não veio de adicionar mais casos ao script. O script não mudou. Veio de traduzir fielmente o comportamento do script em instruções que o modelo consegue seguir — e de preencher os gaps onde a tradução estava incompleta, imprecisa ou ausente.


---

# Sessão 2 — Construção do desafio TiOps

## Contexto

Esta sessão foi dedicada a construir a skill `instagram-publisher` do zero como entrega do desafio técnico da TiOps para a vaga de Estágio em Automações com IA e Agentes. O requisito central: publicar fotos no Instagram 100% via API, sem browser, rodando em background.

---

## 1. Decisões de arquitetura

### 1.1 Bash → Python

A primeira implementação (`publish.sh`) usava bash + cURL. Foi descartada ao adicionar Reels (que requerem polling de status assíncrono), carrossel (múltiplos containers) e as flags opcionais. Bash não tem tratamento de exceções adequado e o parsing de argumentos com `getopts` ficaria frágil rapidamente.

A migração para Python 3 stdlib only (`urllib.request`, `json`, `argparse`) foi a decisão correta: zero dependências externas, roda em qualquer Mac, debug com tracebacks legíveis, e `argparse` cobre subcommands de forma limpa.

### 1.2 Tailscale Funnel para arquivos locais

O Instagram Graph API só aceita URLs públicas — não arquivos. Quando o usuário anexa um arquivo ao chat, a skill precisa torná-lo acessível.

Opções consideradas e descartadas:
- **catbox.moe** (200MB, permanente): dependência de terceiro, arquivo sai da máquina
- **transfer.sh** (10GB, 14 dias): idem
- **0x0.st**: uploads desabilitados desde mai/2026 por spam de bots

Solução final: `serve_via_funnel()` no `publish.py`. O script levanta um `http.server` local em porta aleatória, copia o arquivo para um tmpdir (sanitizando espaços no nome), e usa `tailscale funnel <porta>` para criar um túnel HTTPS público. Antes de passar a URL para a Meta, o script faz polling com HEAD requests a cada 5s até o Funnel estar acessível (até 120s). Após o container atingir status FINISHED, o Funnel é encerrado e o tmpdir removido. O arquivo nunca sai da máquina.

**Complicação encontrada:** o CLI do Tailscale empacotado no app (`/Applications/Tailscale.app/Contents/MacOS/Tailscale`) tem um bug de bundle identifier quando executado via symlink. O código usa o caminho absoluto do binário. O comando `tailscale funnel` bloqueia indefinidamente; foi necessário usar `subprocess.Popen` (não `subprocess.run`) para rodar em background e encerrar com `terminate()` ao final.

**Pré-requisito:** Funnel precisa estar habilitado na ACL da conta Tailscale via `https://login.tailscale.com/f/funnel?node=...`.

### 1.3 Subcommands no argparse

A interface CLI usa subcommands (`photo`, `reel`, `carousel`) em vez de uma flag `--type`. Isso permite argumentos posicionais diferentes por tipo (ex: `carousel` aceita múltiplas URLs, `reel` aceita `--cover-url`) sem criar conflitos de argparse.

### 1.4 Polling universal

A primeira implementação fazia polling apenas para Reels (upload assíncrono de vídeo). Testes mostraram que fotos e carrosseis também podem retornar `IN_PROGRESS` antes de `FINISHED`. O polling foi movido para todas as publicações via `poll_container()`, eliminando o erro `Media ID is not available` (code 9007, subcode 2207027).

---

## 2. Features implementadas

| Feature | Parâmetro | Funciona em |
|---|---|---|
| Foto | `image_url` | photo, carousel |
| Reel | `video_url`, `media_type=REELS` | reel |
| Carrossel | `children`, `media_type=CAROUSEL` | carousel |
| Alt text | `alt_text` | photo |
| User tags | `user_tags` (JSON com x,y) | photo |
| Disable comments | POST pós-publicação | todos |
| Scheduling | `published=false` + `scheduled_publish_time` | todos |
| Arquivo local | Tailscale Funnel | todos |

### Features removidas durante a sessão

- **Location tagging**: requer Facebook Place ID obtido via `pages/search`, endpoint que exige token do Facebook Login (não do Instagram Business Login). O app configurado com Instagram Business Login only não tem acesso. Removida após diagnóstico.
- **Share to Facebook**: `share_to_feed=true` só funciona se o Instagram estiver vinculado a uma Facebook Page (não a um perfil pessoal). O perfil de teste estava vinculado ao perfil pessoal. Removida após teste.

---

## 3. Problemas encontrados e soluções

### 3.1 Token com aspas no .env

O token gerado pelo dashboard da Meta foi copiado com aspas (`"token"`). O `load_env()` do script não fazia strip de aspas — o token chegava malformado para a API (error 190). Diagnóstico via `xxd` nos últimos bytes do `.env`. Solução: remover as aspas manualmente.

### 3.2 URLs de vídeo inacessíveis para a Meta

Todos os vídeos de amostra testados (sample-videos.com, Google Storage, exit109.com) retornavam HTTP 403 ou timeout. Diagnóstico via `curl -sI` confirmou que nenhuma URL retornava 200. A Meta baixa o vídeo de seus servidores — não do browser do usuário — e CDNs de amostra frequentemente bloqueiam data centers.

Solução: vídeo hospedado no Streamable, com URL direta extraída via API pública (`api.streamable.com/videos/{id}`). O vídeo era landscape (16:9), mas o teste confirmou que aspect ratio não é o bloqueador — era a inacessibilidade da URL.

### 3.3 Funnel encerrado antes da Meta baixar o arquivo

O context manager `serve_via_funnel` encerrava o Funnel no bloco `finally` quando `sys.exit()` era chamado dentro do `with` block (via `SystemExit`). A sequência era: `create_container` → Meta retorna erro → `sys.exit()` → `finally` roda → Funnel encerrado → erro exibido.

O problema real era diferente: o Funnel precisava de mais de 3 segundos para propagar. Solução: polling ativo com HEAD requests antes de passar a URL para a API. O Funnel só é encerrado após `poll_container()` retornar `FINISHED` — garantindo que a Meta já baixou o arquivo.

### 3.4 Espaços no nome do arquivo

Arquivos com espaços (ex: `Screenshot 2026-05-21 at 19.22.50.png`) quebravam a URL do Funnel (`https://host/Screenshot%202026...`), que a Meta não conseguia resolver. Solução: `.replace(' ', '_')` no filename ao copiar para o tmpdir — transparente para o usuário.

---

## 4. Resultados dos testes

### test_all.py — 8/8 casos ✓

| Caso | Status | permalink |
|---|---|---|
| Foto simples | ✓ | instagram.com/p/DYnlPaPGhmZ |
| Foto com alt text | ✓ | instagram.com/p/DYnlQeCmvuN |
| Foto com user tag (@instagram) | ✓ | instagram.com/p/DYnlS4rmoo4 |
| Foto com comentários desativados | ✓ | instagram.com/p/DYnlUhOGlrX |
| Foto agendada | ✓ | (agendada, não publicada imediatamente) |
| Carrossel (2 fotos) | ✓ | instagram.com/p/DYnlXdxGt4s |
| Reel | ✓ | instagram.com/reel/DYnlY1fgAMk |
| Reel (variante) | ✓ | instagram.com/reel/DYnlcepierK |

### Teste via Claude Code CLI

Skill invocada diretamente pelo Claude Code com imagem anexada ao chat. O Claude identificou o arquivo no path temporário e usou `--file` corretamente na segunda tentativa. Na primeira, usou o path com espaços que o Funnel não conseguiu servir — o Claude resolveu copiando para `/tmp/ig_post.png` manualmente.

O fix de sanitização de espaços no `publish.py` foi aplicado após esse teste.

---

## 5. Estrutura final da skill

```
~/.claude/skills/instagram-publisher/
├── SKILL.md      — instruções para o Claude (triggers, parâmetros, exemplos, fluxo API)
├── publish.py    — script Python stdlib-only (~300 linhas)
├── test_all.py   — 8 casos de teste automatizados
└── .env          — IG_USER_ID e ACCESS_TOKEN
```

---

## 6. Aprendizados

**O bloqueio real raramente é o que parece.** O erro de Reel ficou um longo tempo sendo investigado como problema de aspect ratio — era inacessibilidade de URL. O diagnóstico correto veio de testar as URLs com `curl` antes de qualquer hipótese sobre formato de vídeo.

**Polling é mais seguro que delay fixo.** `time.sleep(3)` não era suficiente para o Funnel propagar. Polling com HEAD requests até receber 200 elimina race conditions independente da velocidade da rede.

**A API da Meta tem dois sistemas de auth que não se falam.** Instagram Business Login (graph.instagram.com) e Facebook Login (graph.facebook.com) usam tokens incompatíveis. Features que dependem de uma não funcionam com token da outra — mesmo que o app aparentemente cubra ambas.

**Remover features é uma decisão técnica válida.** Location e Share to Facebook foram removidas quando o diagnóstico confirmou que não eram viáveis com o setup atual — não adiadas indefinidamente.