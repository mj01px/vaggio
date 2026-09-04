import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api/v1',
  headers: { 'Content-Type': 'application/json' },
  // A sessao do Django e cookie: sem isso o navegador nao manda de volta e
  // toda chamada volta 403, mesmo depois de entrar.
  withCredentials: true,
  // O Django espera o token de CSRF em X-CSRFToken lendo o cookie csrftoken.
  // O padrao do axios e XSRF-TOKEN / X-XSRF-TOKEN, que o Django ignora.
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
})

/**
 * Mensagem legivel a partir de um erro da API.
 *
 * O backend responde toda falha com { error: { code, message, details } }
 * (apps/core/exceptions.py). Ler so `detail`, que esta API nunca devolve,
 * transformaria todo erro de campo num generico "tente de novo".
 */
export function apiErrorMessage(err: unknown, fallback: string): string {
  if (!axios.isAxiosError(err)) return fallback
  const data = err.response?.data as
    | { error?: { message?: string; details?: { field: string; message: string }[] } }
    | undefined
  return data?.error?.message ?? data?.error?.details?.[0]?.message ?? fallback
}
