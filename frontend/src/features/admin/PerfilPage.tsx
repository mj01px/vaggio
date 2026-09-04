import { useState, type ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FileText, Save, SlidersHorizontal } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { StateMessage } from '@/components/ui/StateMessage'
import { Seguranca } from '@/features/admin/Seguranca'
import { usePode } from '@/hooks/useSessao'
import { apiErrorMessage } from '@/lib/api'
import { fetchPerfil, updatePerfil } from '@/services/session.service'
import type { Perfil } from '@/types/api'

/** Abaixo disso a geração da apresentação recusa: o backend usa o mesmo numero. */
const MINIMO_DOSSIE = 400

const MICRO = 'text-[10.5px] font-semibold tracking-[0.09em] text-muted uppercase'

const AREA =
  'w-full rounded-lg border border-field bg-card px-3.5 py-2.5 font-mono text-[12.5px] ' +
  'leading-relaxed text-ink outline-none focus:border-ink disabled:cursor-not-allowed ' +
  'disabled:border-line disabled:bg-surface disabled:text-muted'

export function PerfilPage() {
  const perfil = useQuery({ queryKey: ['perfil'], queryFn: fetchPerfil })

  if (perfil.isPending) return <StateMessage>Carregando o perfil...</StateMessage>
  if (perfil.isError) {
    return (
      <StateMessage tone="bad">
        {apiErrorMessage(perfil.error, 'Nao deu para carregar o perfil.')}
      </StateMessage>
    )
  }

  // A `key` remonta o formulario quando o perfil muda no servidor, e e o que
  // deixa o estado nascer ja preenchido em vez de ser sincronizado por efeito.
  return <Formulario key={perfil.data.updated_at} dados={perfil.data} />
}

/** Rotulo da secao com a regua ao lado, fora do card. */
function Secao({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-4">
        <span className={MICRO}>{titulo}</span>
        <div className="h-px flex-1 bg-line" />
      </div>
      {children}
    </div>
  )
}

function Card({ children }: { children: ReactNode }) {
  return <div className="rounded-[10px] border border-line bg-card p-4 lg:p-5">{children}</div>
}

/**
 * Cabecalho de bloco: ladrilho de icone, titulo e explicacao.
 *
 * O `acao` vai para a direita, na mesma linha, que e o formato de linha de
 * acao: o controle fica colado na frase que explica o que ele faz.
 */
function Bloco({
  icone,
  titulo,
  descricao,
  acao,
}: {
  icone: ReactNode
  titulo: string
  descricao: string
  acao?: ReactNode
}) {
  return (
    <div className="flex items-center gap-3.5">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-surface text-muted">
        {icone}
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-[14px] font-semibold">{titulo}</p>
        <p className="mt-0.5 text-[12.5px] text-muted">{descricao}</p>
      </div>
      {acao}
    </div>
  )
}

/**
 * Campo que nao se edita aqui.
 *
 * Mesma forma do campo editavel, com a borda fraca e o fundo lavado que o app
 * ja usa em input desabilitado: e o par que diz "isto e um campo, mas nao e
 * seu para mexer".
 */
function Travado({ rotulo, valor }: { rotulo: string; valor: ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className={MICRO}>{rotulo}</span>
      <div className="flex h-9 items-center truncate rounded-lg border border-line bg-surface px-3 text-[13.5px]">
        {valor}
      </div>
    </div>
  )
}

function Formulario({ dados }: { dados: Perfil }) {
  const queryClient = useQueryClient()
  const podeEditar = usePode('perfil.editar')

  const [nome, setNome] = useState(dados.nome)
  const [dossie, setDossie] = useState(dados.dossie)
  const [termos, setTermos] = useState(JSON.stringify(dados.termos ?? {}, null, 2))
  const [erroTermos, setErroTermos] = useState('')
  const [aviso, setAviso] = useState('')
  const [error, setError] = useState('')

  const salvar = useMutation({
    mutationFn: () => {
      const texto = termos.trim()
      // `pitch_max_chars` fica de fora: o PATCH e parcial, entao o valor
      // guardado sobrevive. A tela deixou de oferecer o campo, nao o apagou.
      return updatePerfil({
        nome,
        dossie,
        // Parse aqui dentro de proposito: um JSON quebrado vira erro da
        // mutation e cai no mesmo lugar que o erro da API.
        termos: texto ? JSON.parse(texto) : {},
      })
    },
    onMutate: () => {
      setError('')
      setAviso('')
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['perfil'] })
      // A sessao carrega o mesmo perfil: o nome novo aparece na topbar sem
      // precisar recarregar a pagina.
      void queryClient.invalidateQueries({ queryKey: ['sessao'] })
      setAviso('Perfil salvo.')
    },
    onError: (err) =>
      setError(
        err instanceof SyntaxError
          ? 'Os termos precisam ser JSON valido.'
          : apiErrorMessage(err, 'Nao deu para salvar o perfil.'),
      ),
  })

  function conferirTermos(texto: string) {
    setTermos(texto)
    if (!texto.trim()) return setErroTermos('')
    try {
      JSON.parse(texto)
      setErroTermos('')
    } catch {
      setErroTermos('JSON inválido')
    }
  }

  const tamanho = dossie.trim().length
  const curto = tamanho < MINIMO_DOSSIE
  const inicial = (dados.nome || dados.email).trim().charAt(0).toUpperCase()
  const mudou =
    nome !== dados.nome ||
    dossie !== dados.dossie ||
    termos.trim() !== JSON.stringify(dados.termos ?? {}, null, 2)

  return (
    <div className="flex flex-col gap-5">
      {aviso && (
        <div className="rounded-lg border border-line bg-card px-3.5 py-2.5 text-sm">{aviso}</div>
      )}
      {error && (
        <div className="rounded-lg border border-bad bg-card px-3.5 py-2.5 text-sm text-bad">
          {error}
        </div>
      )}

      <Secao titulo="Identidade">
        <Card>
          <div className="flex flex-col gap-5">
            <div className="flex min-w-0 items-center gap-3.5">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-[10px] bg-accent text-[18px] font-semibold text-white">
                {inicial}
              </div>
              <div className="min-w-0">
                <p className="truncate text-[15px] font-semibold">{dados.nome || dados.email}</p>
                <p className="mt-0.5 text-[12.5px] text-muted">{dados.cargo?.nome ?? 'sem cargo'}</p>
              </div>
            </div>

            <div className="flex flex-col gap-1.5">
              <label className={MICRO} htmlFor="perfil-nome">
                Nome
              </label>
              <input
                id="perfil-nome"
                value={nome}
                disabled={!podeEditar}
                onChange={(event) => setNome(event.target.value)}
                className="h-9 w-full rounded-lg border border-field bg-card px-3 text-[13.5px] text-ink outline-none focus:border-ink disabled:cursor-not-allowed disabled:border-line disabled:bg-surface disabled:text-muted"
              />
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <Travado rotulo="E-mail" valor={dados.email} />
              <Travado
                rotulo="Cargo"
                valor={dados.cargo?.nome ?? <span className="text-muted">sem cargo</span>}
              />
            </div>
          </div>
        </Card>
      </Secao>

      <Secao titulo="Dossiê">
        <Card>
          <div className="flex flex-col gap-4">
            <Bloco
              icone={<FileText size={20} />}
              titulo="Sobre você"
              descricao="É a única coisa que o Apresente-se sabe sobre você. O que não estiver aqui não entra no texto."
            />

            <textarea
              aria-label="Dossiê"
              value={dossie}
              disabled={!podeEditar}
              rows={14}
              onChange={(event) => setDossie(event.target.value)}
              className={AREA}
            />

            <div className="flex items-center justify-between gap-3">
              <span className={`text-[12px] ${curto ? 'text-warn' : 'text-muted'}`}>
                {curto
                  ? `Abaixo de ${MINIMO_DOSSIE} caracteres a geração recusa.`
                  : 'Quanto mais concreto, melhor o texto gerado.'}
              </span>
              <span
                className={`text-[12.5px] font-semibold tabular-nums ${
                  curto ? 'text-warn' : 'text-muted'
                }`}
              >
                {curto ? `${tamanho} / ${MINIMO_DOSSIE}` : `${tamanho} caracteres`}
              </span>
            </div>
          </div>
        </Card>
      </Secao>

      <Secao titulo="Segurança">
        <Seguranca email={dados.email} />
      </Secao>

      <Secao titulo="Preferências">
        <Card>
          <div className="flex flex-col gap-4">
            <Bloco
              icone={<SlidersHorizontal size={20} />}
              titulo="Termos de scoring"
              descricao="Muda o que conta ponto no Radar. Vazio usa o perfil padrão do projeto."
            />

            <textarea
              aria-label="Termos de scoring"
              value={termos}
              disabled={!podeEditar}
              rows={8}
              spellCheck={false}
              onChange={(event) => conferirTermos(event.target.value)}
              className={AREA}
            />

            <div className="flex flex-col gap-1">
              <span className={`text-[12px] ${erroTermos ? 'text-bad' : 'text-muted'}`}>
                {erroTermos ||
                  'formato: { "core": { "weight": 12, "terms": ["python", "django"] } }'}
              </span>
              {/* Score ja gravado nao muda sozinho: quem reaplica e o rescore. */}
              <span className="text-[12px] text-muted">
                Vale nas próximas coletas. Para reaplicar nas vagas que já estão na fila, rode{' '}
                <code className="rounded bg-surface px-1">manage.py rescore</code>.
              </span>
            </div>
          </div>
        </Card>
      </Secao>

      {/* A barra so aparece depois de mexer em alguma coisa: botao sempre
          visivel e sempre desabilitado nao diz o que falta para habilitar. */}
      {podeEditar && mudou && (
        <div className="flex justify-end">
          <Button
            variant="primary"
            disabled={salvar.isPending || Boolean(erroTermos)}
            onClick={() => salvar.mutate()}
          >
            <Save size={16} />
            {salvar.isPending ? 'salvando...' : 'salvar alterações'}
          </Button>
        </div>
      )}

      {!podeEditar && (
        <p className="text-[12.5px] text-muted">Seu cargo não permite editar o perfil.</p>
      )}
    </div>
  )
}
