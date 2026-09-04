# Por que existe um `vercel.json`

O front fica na Vercel e a API no Render, que são **domínios diferentes**. A
autenticação do Vaggio é cookie de sessão, e cookie de sessão não atravessa
domínio: com `SESSION_COOKIE_SAMESITE = "Strict"` o navegador simplesmente não
manda o cookie, e o login não fecha.

A saída seria afrouxar para `SameSite=None` e ligar `CORS_ALLOW_CREDENTIALS`.
Funciona, e joga fora justamente a proteção que o SameSite dá: o token de CSRF
passaria a ser a única defesa, em vez de a segunda.

O `rewrites` daqui resolve por outro caminho. A Vercel recebe `/api/...` e
repassa para o Render, então **o navegador só enxerga um domínio**. O cookie
volta a ser de primeira parte, o `SameSite=Strict` continua valendo, e nenhuma
requisição cruza origem, o que também dispensa CORS por completo.

É o mesmo desenho que o `vite.config.ts` já usa em desenvolvimento, onde o proxy
do Vite faz esse papel. Produção passou a combinar com dev em vez de divergir.

## As três regras, e por que cada uma existe

### 1. O rewrite do `/api`

Uma linha para ajustar, a primeira `destination`: troque
`TROQUE-PELO-SEU-SERVICO` pelo nome do serviço no Render. O endereço aparece no
painel dele depois do primeiro deploy, no formato `https://<nome>.onrender.com`.

### 2. O `/index.html` para todo o resto

Roteamento do lado do cliente. A Vercel serve os arquivos que existem em disco
antes de olhar os `rewrites`, então `/assets/...` continua vindo do build e só as
rotas do React Router (`/dashboard`, `/radar`, `/perfil`) caem no `index.html`.
Sem essa regra, recarregar a página em qualquer rota que não seja `/` dá 404.

### 3. `x-vercel-enable-rewrite-caching: 0`

Esta é a que não é óbvia, e a que evita um vazamento.

Desde abril de 2026 a Vercel **cacheia respostas de rewrite externo por padrão**,
respeitando o `Cache-Control` que vem de cima. A API do Vaggio é toda
autenticada por cookie e não manda `Cache-Control` nenhum na maioria das rotas,
então o comportamento fica dependendo de heurística de CDN sobre respostas que
contêm dado de uma pessoa específica: dossiê, candidaturas, lista de usuários.

Uma resposta dessas guardada na borda e servida para outra sessão é vazamento de
dado pessoal, e do tipo difícil de perceber, porque só aparece quando duas
pessoas usam o sistema ao mesmo tempo. O cabeçalho desliga o cache para tudo sob
`/api`, que é o comportamento que a API sempre teve por trás do proxy do Vite e
o que ela espera.

Não mexa nisso sem antes fazer o Django mandar `Cache-Control` explícito em cada
rota.

## Configuração do projeto na Vercel

| Campo | Valor |
|---|---|
| Root Directory | `frontend` |
| Framework Preset | Vite (detectado sozinho) |
| Build Command | `npm run build` (o padrão) |
| Output Directory | `dist` (o padrão) |

Não precisa de variável de ambiente: o `VITE_API_BASE_URL` já cai no default
`/api/v1`, que é exatamente o caminho que o rewrite intercepta.
