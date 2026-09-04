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

## O que ajustar

Uma linha, a primeira `destination`: troque `TROQUE-PELO-SEU-SERVICO` pelo nome
do serviço no Render. O endereço aparece no painel dele depois do primeiro
deploy, no formato `https://<nome>.onrender.com`.

A segunda regra é o roteamento do lado do cliente: a Vercel serve os arquivos que
existem em disco antes de olhar os `rewrites`, então `/assets/...` continua vindo
do build e só as rotas do React Router (`/dashboard`, `/radar`, `/perfil`) caem
no `index.html`. Sem ela, recarregar a página em qualquer rota que não seja `/`
devolve 404.

## Configuração do projeto na Vercel

| Campo | Valor |
|---|---|
| Root Directory | `frontend` |
| Framework Preset | Vite |
| Build Command | `npm run build` (o padrão) |
| Output Directory | `dist` (o padrão) |

Não precisa de variável de ambiente: o `VITE_API_BASE_URL` já cai no default
`/api/v1`, que é exatamente o caminho que o rewrite intercepta.
