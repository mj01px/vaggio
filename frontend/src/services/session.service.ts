import { api } from '@/lib/api'
import type { Entrada, Perfil, Sessao } from '@/types/api'

/**
 * Quem esta logado.
 *
 * Tambem e o que planta o cookie de CSRF: o backend responde este GET com
 * `ensure_csrf_cookie`, e sem ele o proprio POST de login seria recusado.
 */
export async function fetchSessao(): Promise<Sessao> {
  const { data } = await api.get<Sessao>('/sessao/')
  return data
}

/**
 * Entra.
 *
 * A credencial e o e-mail: o username do Django continua existindo, mas so
 * como identificador interno da conta.
 *
 * `lembrar` decide a vida do cookie: com ele a sessao dura o padrao do Django,
 * sem ele o cookie morre quando o navegador fecha. Quem omite recebe `true`,
 * que e o que a API sempre fez.
 */
export async function login(
  email: string,
  password: string,
  lembrar = true,
): Promise<Entrada> {
  const { data } = await api.post<Entrada>('/sessao/', { email, password, lembrar })
  return data
}

/** Segundo passo da entrada, quando a conta tem segundo fator. */
export async function entrarComCodigo(codigo: string): Promise<Sessao> {
  const { data } = await api.post<Sessao>('/sessao/codigo/', { codigo })
  return data
}

export async function logout(): Promise<void> {
  await api.delete('/sessao/')
}

export async function fetchPerfil(): Promise<Perfil> {
  const { data } = await api.get<Perfil>('/perfil/')
  return data
}

export async function updatePerfil(changes: Partial<Perfil>): Promise<Perfil> {
  const { data } = await api.patch<Perfil>('/perfil/', changes)
  return data
}


// ── Senha, e-mail e segundo fator ───────────────────────────────────────────

export async function trocarSenha(senha_atual: string, nova: string): Promise<void> {
  await api.post('/perfil/senha/', { senha_atual, nova })
}

/** Publica. Responde igual exista ou nao a conta, de proposito. */
export async function pedirRecuperacao(email: string): Promise<string> {
  const { data } = await api.post<{ detail: string }>('/senha/esqueci/', { email })
  return data.detail
}

/** Publica. Serve para o link de recuperacao e para o do convite. */
export async function redefinirSenha(
  uid: string,
  token: string,
  nova: string,
): Promise<void> {
  await api.post('/senha/redefinir/', { uid, token, nova })
}

/** Publica. Diz se o link ainda vale antes de a pessoa digitar a senha. */
export async function conferirLink(
  uid: string,
  token: string,
): Promise<{ valido: boolean; email: string }> {
  const { data } = await api.post<{ valido: boolean; email: string }>(
    '/senha/conferir-link/',
    { uid, token },
  )
  return data
}

/** Pede a troca. O e-mail so muda quando o link chegar e for aberto. */
export async function pedirTrocaDeEmail(senha_atual: string, email: string): Promise<string> {
  const { data } = await api.post<{ detail: string }>('/perfil/email/', {
    senha_atual,
    email,
  })
  return data.detail
}

/** Publica. Aplica a troca que o link autoriza. */
export async function confirmarEmail(codigo: string): Promise<string> {
  const { data } = await api.post<{ detail: string }>('/email/confirmar/', { codigo })
  return data.detail
}

export interface EstadoDoisFatores {
  ativo: boolean
  codigos_restantes: number
}

export async function fetchDoisFatores(): Promise<EstadoDoisFatores> {
  const { data } = await api.get<EstadoDoisFatores>('/perfil/2fa/')
  return data
}

/** Prepara a ativacao: gera o segredo e o QR. Nao liga nada ainda. */
export async function prepararDoisFatores(): Promise<{ qr: string; segredo: string }> {
  const { data } = await api.post<{ qr: string; segredo: string }>('/perfil/2fa/')
  return data
}

/** Liga, depois de o aplicativo provar que funciona. Devolve os de reserva. */
export async function confirmarDoisFatores(codigo: string): Promise<string[]> {
  const { data } = await api.post<{ codigos: string[] }>('/perfil/2fa/confirmar/', { codigo })
  return data.codigos
}

export async function desativarDoisFatores(senha_atual: string): Promise<void> {
  await api.post('/perfil/2fa/desativar/', { senha_atual })
}

export async function novosCodigosDeReserva(senha_atual: string): Promise<string[]> {
  const { data } = await api.post<{ codigos: string[] }>('/perfil/2fa/codigos/', {
    senha_atual,
  })
  return data.codigos
}
