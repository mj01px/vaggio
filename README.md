# Vaggio

Coleta vagas de desenvolvimento de fontes publicas, pontua cada uma pelo meu
perfil e acompanha as candidaturas num funil. Resolve dois problemas concretos
da busca por emprego: **achar as vagas certas no meio do ruido** e **nao perder
o follow-up** de processo nenhum.

Sucessor do `radar`, com backend e frontend separados.

## Arquitetura

```
frontend/  React 19 + Vite + TypeScript + Tailwind        :5173
   |  HTTP  /api/v1
backend/   Django 5 + DRF                                  :8000
   |
   +-- apps/collectors  fontes (GitHub, Gupy) e log de coleta
   +-- apps/jobs        vaga + scoring por perfil
   +-- apps/pipeline    funil de candidaturas e linha do tempo
   +-- apps/accounts    perfil, cargo e permissao (RBAC)
   +-- apps/core        bases, paginacao, envelope de erro
```

Fluxo: `manage.py collect` busca nas fontes, corta o que e velho, deduplica por
hash e pontua. A tela **Radar** mostra a fila da ultima semana ordenada por
score, paginada de 100 em 100, onde cada vaga vira candidatura ou e descartada.
O seletor de periodo abre a janela para 15 ou 30 dias, ou para tudo.

A fila nao esconde vaga ruim: tudo que foi coletado aparece, e o score so
decide a ordem. Quem quiser cortar usa o campo `score min` da tela. O contador
"na fila inteira" no cabecalho mostra o total sem os filtros, para nunca
sobrar duvida sobre o que o periodo esta cortando. A tela **Board** e o funil: Quero aplicar, Aplicada, Triagem, Teste,
Entrevista, Proposta. Follow-up vencido aparece em vermelho no topo.

## Rodando

Backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements/development.txt
copy .env.example .env
python manage.py migrate
python manage.py createsuperuser   # o e-mail que ele pede e o login
python manage.py runserver 8000
```

Frontend, em outro terminal:

```bash
cd frontend
npm install
npm run dev
```

Abre em <http://localhost:5173/>, que e a tela de login; o app fica em
`/dashboard` e nas outras rotas, quase todas atras de sessao. A API fica em
<http://127.0.0.1:8000/api/v1/> e o Vite ja faz proxy de `/api`, entao nao ha
CORS para configurar em dev.

Para mudar a porta da API, ajuste `BACKEND` em `frontend/vite.config.ts` e o
`runserver` do `scripts/dev.bat` juntos: quem decide para onde o front fala e
o proxy, nao o navegador.

No Windows, `scripts\dev.bat` sobe os dois de uma vez e `scripts\collect.bat`
roda a coleta.

Banco padrao e SQLite, sem configurar nada. Para usar PostgreSQL, preencha
`DB_NAME` e o resto das `DB_*` no `backend/.env`.

## Comandos

| Comando | O que faz |
|---|---|
| `manage.py collect` | Roda todas as fontes (ultimos 30 dias) |
| `manage.py collect --source github` | Roda uma fonte so |
| `manage.py collect --max-age 7` | So o que foi publicado na ultima semana |
| `manage.py collect --max-age 0` | Sem corte de idade |
| `manage.py collect --min-score 20` | Descarta o que pontuar abaixo disso na entrada |
| `manage.py collect --dry-run` | Mostra o que salvaria, sem gravar |
| `manage.py rescore` | Recalcula o score das vagas ja salvas |
| `manage.py pitch` | Lista as vagas do topo da fila, com o id |
| `manage.py pitch <id>` | Gera o "Apresente-se" da Gupy para aquela vaga |

A coleta corta por **idade**, nao por score. Vaga publicada ha mais de 30 dias
nao entra (`--max-age`), e o score serve so para ordenar a fila depois: cortar
por score na entrada joga fora um dado que nao volta sem recoletar, e o
`rescore` pode mudar de ideia sobre ele amanha. Se quiser o corte antigo,
`--min-score` continua ali.

Uma rodada completa leva cerca de 20 segundos e faz ~50 requisicoes. O botao
**buscar vagas novas** no Radar dispara exatamente a mesma coleta, com os mesmos
30 dias de corte, e devolve o resultado na tela. Ela e sincrona de proposito:
esperar 20 segundos e ver "42 novas" vale mais que responder na hora e ficar
perguntando se ja acabou. Duas coletas ao mesmo tempo sao recusadas com 409.

## Apresente-se

A Gupy tem um campo de apresentacao pessoal por vaga. O Vaggio escreve um
rascunho dele, personalizado para a vaga. Nada e enviado a lugar nenhum: voce
le, ajusta e cola voce mesmo.

Pelo **Board**, que e o caminho do dia a dia: o botao `apresente-se` no cartao
da candidatura abre um painel com o tamanho alvo, um campo de ajuste opcional,
o texto gerado e o botao de copiar. Gerar de novo acrescenta uma versao ao
historico em vez de substituir, entao da para comparar.

Pelo terminal, que e onde se experimenta prompt sem encher o banco de rascunho:

```bash
python manage.py pitch                 # lista as vagas com o id
python manage.py pitch 64
python manage.py pitch 64 --max-chars 800
python manage.py pitch 64 --instrucao "puxa mais o lado de dados"
```

Duas pecas fazem funcionar:

- **O dossie**, em `apps/jobs/pitch/dossie.md`, que diz quem voce e. E a unica
  fonte de verdade sobre voce: o que nao estiver escrito ali nao pode aparecer
  no texto. Fica fora do git, junto com o `.env`, porque carrega historico de
  carreira real.
- **A vaga**, com a descricao inteira que a coleta ja guardou, mais as `tags`,
  que sao os pontos onde o seu perfil ja casa com ela segundo o scoring.

O modelo e o Gemini pelo Google AI Studio, no free tier. Preencha
`GEMINI_API_KEY` no `.env`; `GEMINI_MODEL` tem padrao e so precisa ser mexido
para trocar de modelo. Uma geracao gasta cerca de 3200 tokens de entrada e 250
de saida.

## Perfil e acesso

Tudo que o app sabe sobre uma pessoa mora num **Perfil**: o dossie que escreve a
apresentacao, os termos que decidem se uma vaga e boa para ela, e o tamanho
preferido do texto. Antes isso vivia em arquivo, o que so funcionava para uma
pessoa so.

O acesso e RBAC com as permissoes em tabela, nao fixas no codigo: dar ou tirar
acesso e dado, nao deploy. Um **Cargo** junta permissoes, e o Perfil aponta para
um cargo. Dois cargos ja vem prontos:

| Cargo | O que pode |
|---|---|
| `leitura` | Ve o radar, o funil e o historico de coleta, sem mexer em nada |

Nao ha cargo "pode tudo" semeado: acesso total sai do `is_superuser`, que passa
por cima da checagem inteira. Um cargo com todas as permissoes seria um segundo
lugar para dar o mesmo acesso, e envelheceria a cada permissao nova.

As treze permissoes: `vagas.ver`, `vagas.triar`, `vagas.gerenciar`, `funil.ver`,
`funil.gerenciar`, `coleta.ver`, `coleta.rodar`, `apresentacao.gerar`,
`perfil.editar`, `usuarios.ver`, `usuarios.gerenciar`, `cargos.ver`,
`cargos.gerenciar`. Cargos e permissoes se editam na tela `/cargos`.

Superusuario passa por tudo sem depender de cargo. Perfil **sem** cargo nao pode
nada: conta pela metade nao vira acesso.

```bash
python manage.py createsuperuser          # cria a conta; o perfil nasce no 1o login
python manage.py sync_permissoes          # reaplica o catalogo depois de mexer nele
python manage.py importar_dossie --usuario mauro@exemplo.dev   # leva o dossie.md para o perfil
```

As rotas do app, com a administracao entre elas em vez de num painel separado.
So `/` e publica; nas outras, quem chega sem sessao volta para o login e e
devolvido ao lugar certo depois de entrar:

| Rota | O que faz |
|---|---|
| `/` | Login. Quem ja tem sessao cai direto no board |
| `/board` | O funil, que e a home de dentro do app |
| `/radar` | A fila de triagem, ordenada por score |
| `/perfil` | Seu dossie, termos de scoring e tamanho da apresentacao |
| `/usuarios` | Quem tem acesso, cargo, senha, ativar e desativar |
| `/cargos` | Cargos e as caixas de permissao de cada um |
| `/coletas` | Historico das execucoes da coleta |

O login e por **e-mail**: ele e unico entre as contas e e a unica credencial
que entra, inclusive no `/admin`. O username do Django continua existindo, mas
so como identificador interno, derivado do e-mail quando a conta nasce.

Para dar acesso a mais alguem: `/usuarios`, novo usuario, escolha o cargo. O
front esconde o botao e o item de menu que a pessoa nao pode usar, mas quem
decide e o backend, que checa de novo em toda chamada.

Tres travas impedem se trancar para fora: voce nao desativa a propria conta, nao
troca o proprio cargo, e conta nao se apaga (desativa), porque candidatura e
apresentacao ficam penduradas em quem as criou.

O admin do Django foi removido do projeto. Tudo que so dava para fazer por la
tem tela e endpoint proprios, sob as mesmas permissoes de cargo do resto:
usuarios em `/usuarios`, cargos em `/cargos`, historico de coleta em `/coletas`,
edicao de vaga no proprio Radar e detalhes da candidatura no board.

### Senha, e-mail e segundo fator

Nao existe cadastro publico: conta so nasce por convite de quem tem
`usuarios.gerenciar`. O que existe de rota publica sao quatro telas, todas
alcancadas por um link mandado por e-mail.

| Fluxo | Onde comeca | Onde termina |
|---|---|---|
| Convite | admin cria a conta em `/usuarios` | `/definir-senha` |
| Esqueci a senha | link no login | `/redefinir-senha` |
| Trocar o e-mail | `/perfil` | `/confirmar-email` |
| Trocar a senha | `/perfil` | ali mesmo, com a senha atual |

Os tres primeiros usam a mesma maquina, em `apps/accounts/links.py`. Para senha
e o `PasswordResetTokenGenerator` do Django, cujo token e um hash do estado do
usuario: gravar a senha nova ja derruba o link, sem tabela de tokens usados.
Para o e-mail e `signing.dumps`, que carrega o endereco novo dentro do proprio
link assinado.

Duas decisoes que valem saber:

- **o admin nunca sabe a senha de ninguem.** A conta nasce com
  `set_unusable_password()` e a pessoa escolhe a dela pelo convite;
- **o link de troca de e-mail vai para o endereco NOVO**, e nada muda ate ele
  ser aberto. E o unico jeito de provar que aquele endereco existe e e da
  pessoa antes de ele virar a credencial de entrada.

O segundo fator e TOTP (`apps/accounts/dois_fatores.py`), com oito codigos de
reserva gerados junto com a ativacao e guardados com hash. Preparar nao liga
nada: quem abre a tela e desiste no meio nao fica trancado fora. Com 2FA ativo,
a senha certa devolve `precisa_codigo` e **nao** cria sessao — `request.user`
so vira aquela pessoa depois do `POST /sessao/codigo/`.

As rotas publicas e a de codigo tem limite de tentativa (`DEFAULT_THROTTLE_RATES`
em `config/settings/base.py`): 10/min no login, 5/hora na recuperacao, 10/min no
codigo. O `esqueci` responde sempre a mesma frase, exista ou nao a conta.

**E-mail:** sem `EMAIL_HOST` no `.env`, o Django imprime a mensagem no console e
o link aparece no terminal do `runserver`, que basta para desenvolver. Em
producao, alem das credenciais do SMTP, `FRONTEND_URL` precisa ser o endereco
real do front: e a base de todo link mandado por e-mail.

**Uma limitacao consciente:** `score`, `tags`, `seniority` e `work_mode` ainda
sao colunas do `Job`, calculadas por um perfil so. Com dois perfis usando termos
diferentes, a mesma vaga teria dois scores, e isso pede uma tabela de juncao
`(vaga, perfil)`. O `Perfil.termos` ja existe para essa mudanca ser so de
armazenamento quando a hora chegar.

## Ajustando o score

Todo o criterio de "vaga boa pra mim" vive em `apps/jobs/scoring/profile.py`,
que e o ponto de partida de quem nunca mexeu em nada. Um perfil com `termos`
preenchidos sobrescreve esse padrao.
Cada grupo tem um peso e uma lista de termos, e acerto no titulo vale o dobro de
acerto na descricao. Depois de mexer, rode `manage.py rescore`.

## Fontes

**GitHub Issues** le quatro repositorios de vagas da comunidade brasileira pela
API publica: `backend-br/vagas` e `soujava/vagas-java` (ativos), `frontendbr/vagas`
e `react-brasil/vagas` (parados, mas com fila aberta). Sem token o limite e 60
requisicoes/hora; com `GITHUB_TOKEN` no `.env` sobe para 5000.

**Gupy** consome o portal publico onde publica a maior parte das empresas
grandes do Brasil. Sao 26 termos de busca, cada um paginado ate o fim, o que
rende cerca de 2700 resultados brutos por rodada. O endereco e configuravel por
`GUPY_API`.

Duas coisas medidas na API da Gupy que valem lembrar antes de mexer nela:
`limit` tem teto de 100 (200 devolve 400), e o `pagination.total` do envelope
**mente** com `limit` alto, cravando 100 mesmo quando existem 650 resultados.
Por isso a paginacao para na primeira pagina incompleta, e nao pelo `total`.
Ela tambem nao aceita nenhum parametro de ordenacao ou de data, entao recencia
so da para resolver do nosso lado.

**LinkedIn ficou de fora de proposito.** Scraping viola os termos deles e o
risco e perder a conta, que e o ativo mais importante durante uma busca de
emprego. Vaga do LinkedIn entra pelo cadastro manual.

### Adicionando uma fonte

Subclasse `Source` em `apps/collectors/sources/`, implemente `fetch` devolvendo
`RawJob`, e registre em `SOURCES` no `__init__.py`. A fonte nao fala com o banco
e nao pontua nada, entao da para testar sem Django.

## Modelo de dados

- **Job** (`apps/jobs`): a vaga coletada. `key` e o hash de deduplicacao, entao
  coletar a mesma vaga duas vezes, mesmo de fontes diferentes, nao duplica.
  `created_at` e a data da coleta.
- **Application** (`apps/pipeline`): 1:1 com Job. Status no funil, prioridade,
  proximo passo e a data do proximo passo, que e o que alimenta o alerta de
  vencidos.
- **Interaction** (`apps/pipeline`): linha do tempo da candidatura. Toda mudanca
  de status grava uma automaticamente.
- **Pitch** (`apps/jobs`): uma versao gerada do "Apresente-se". Historico, e nao
  um texto por vaga: gerar de novo acrescenta, e comparar as versoes e o que
  ensina a ajustar o dossie.
- **CollectionRun** (`apps/collectors`): log de cada execucao da coleta, por fonte.
- **Perfil / Cargo / Permissao** (`apps/accounts`): quem usa o Vaggio, o que o
  app sabe sobre a pessoa, e o que ela pode fazer.

Vaga nao se apaga, descarta: o historico e o que impede a mesma vaga de voltar
para a fila na proxima coleta. Candidatura tambem nao se apaga, vira Rejeitada
ou Desisti.

## API

Tudo sob `/api/v1/`. Toda falha responde no mesmo envelope
`{ error: { code, message, details } }`.

| Rota | O que faz |
|---|---|
| `GET /jobs/` | Fila de triagem. `?queue=triage\|discarded\|all`, `?q=`, `?source=`, `?min_score=`, `?published_within=7`, `?page=`, `?page_size=` |
| `POST /jobs/` | Cadastro manual (e por aqui que a vaga do LinkedIn entra) |
| `PATCH /jobs/{id}/` | Corrige a vaga: titulo, empresa, local, descricao, score, tags |
| `POST /jobs/{id}/discard/` | Descarta |
| `POST /jobs/{id}/restore/` | Devolve para a fila |
| `GET /jobs/stats/` | Contadores da tela Radar |
| `GET /jobs/{id}/pitch/` | Versoes ja geradas do "Apresente-se" |
| `POST /jobs/{id}/pitch/` | Gera mais uma (`max_chars`, `instrucao`) |
| `GET /applications/board/` | O board inteiro: colunas, atrasadas e contadores |
| `POST /applications/` | Poe a vaga no funil |
| `PATCH /applications/{id}/` | Move de status, muda prioridade, notas, proximo passo |
| `GET /applications/closed/` | As encerradas: rejeitadas e desistidas juntas |
| `DELETE /applications/{id}/` | Apaga, so depois de encerrada |
| `GET /collections/` | Historico das coletas |
| `POST /collections/run/` | Dispara a coleta agora (e o botao "buscar vagas novas" do Radar) |
| `GET /health/` | Ping (unica rota aberta) |
| `GET /sessao/` | Quem esta logado. Tambem planta o cookie de CSRF |
| `POST /sessao/` | Entra (`email`, `password`, `lembrar`). Com 2FA devolve `precisa_codigo` |
| `POST /sessao/codigo/` | Segundo passo da entrada. **Publica** |
| `DELETE /sessao/` | Sai |
| `GET /perfil/` | O proprio perfil, com cargo e permissoes |
| `PATCH /perfil/` | Edita dossie, termos e preferencias |
| `POST /perfil/senha/` | Troca a propria senha (exige a atual) |
| `POST /perfil/email/` | Pede a troca de e-mail; o link vai para o endereco novo |
| `GET/POST /perfil/2fa/` | Estado do segundo fator, e o comeco da ativacao |
| `POST /perfil/2fa/confirmar/` | Liga, e devolve os codigos de reserva |
| `POST /perfil/2fa/desativar/`, `/codigos/` | Desliga, ou so renova os codigos |
| `GET /usuarios/` | Quem tem acesso |
| `POST /usuarios/` | Cria conta e perfil juntos (`email` obrigatorio: e o login) |
| `PATCH /usuarios/{id}/` | Troca cargo, nome, e-mail, ativa e desativa |
| `POST /usuarios/{id}/convite/` | Manda o link para a pessoa escolher a propria senha |
| `GET /cargos/` | Cargos e o que cada um libera |
| `POST /cargos/`, `PATCH`, `DELETE` | Cria, edita e apaga cargo |
| `GET /permissoes/` | Catalogo de permissoes (somente leitura) |
| `POST /senha/esqueci/` | Pede o link de recuperacao. **Publica** |
| `POST /senha/redefinir/` | Fecha o link de recuperacao e o de convite. **Publica** |
| `POST /senha/conferir-link/` | Diz se um link ainda vale. **Publica** |
| `POST /email/confirmar/` | Aplica a troca de e-mail. **Publica** |

Fora `/health/`, que e ping de infraestrutura, as unicas rotas sem sessao sao as
cinco marcadas como publicas, e todas nascem de um link mandado por e-mail. Elas
tem limite de tentativa proprio. O resto exige sessao, e o acesso e por cargo
(veja **Perfil e acesso**).

## Testes

```bash
cd backend
pytest          # 184 testes
ruff check .    # lint
```

```bash
cd frontend
npm run build   # tsc -b + vite build
npm run lint
```

O scoring e funcao pura e roda sem banco. As fontes sao testadas com payload
fixo, sem rede. O resto usa `pytest-django`.
