import { useState, type FormEvent } from 'react'
import { ListFilter, Plus, RefreshCw, Search, X } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { DateSelect } from '@/components/ui/DateSelect'
import { Select } from '@/components/ui/Select'
import { SOURCES, type RadarFilterValues } from './constants'

interface Props {
  filters: RadarFilterValues
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
  onClear: () => void
  onRemover: (chave: keyof RadarFilterValues) => void
  podeColetar: boolean
  coletando: boolean
  onColetar: () => void
  /** Falso esconde cadastrar: quem so ve a fila nao acrescenta vaga. */
  podeTriar: boolean
  onCadastrar: () => void
}

const rotulo =
  'mb-1.5 block text-[10.5px] font-semibold tracking-[0.09em] text-muted uppercase'

/** Data ISO em dd/mm/aa, so para a pilula. */
function curto(valor: string): string {
  const [a, m, d] = valor.split('-')
  return `${d}/${m}/${a.slice(2)}`
}

/** O que esta ligado agora, em pilulas removiveis uma a uma. */
function ativos(filters: RadarFilterValues) {
  const lista: { chave: keyof RadarFilterValues; texto: string }[] = []
  if (filters.q) lista.push({ chave: 'q', texto: `"${filters.q}"` })
  if (filters.published_after) {
    lista.push({ chave: 'published_after', texto: `de ${curto(filters.published_after)}` })
  }
  if (filters.published_before) {
    lista.push({ chave: 'published_before', texto: `até ${curto(filters.published_before)}` })
  }
  if (filters.source) {
    const fonte = SOURCES.find((s) => s.value === filters.source)
    lista.push({ chave: 'source', texto: fonte?.label ?? filters.source })
  }
  if (filters.min_score) lista.push({ chave: 'min_score', texto: `score ≥ ${filters.min_score}` })
  return lista
}

/**
 * A barra da fila: busca sempre visivel, o resto atras do botao.
 *
 * Os filtros saíram da coluna lateral e vieram para o topo. Isso devolve
 * 264px de largura para a lista, que e o que faz o cartao de vaga caber
 * inteiro numa linha em vez de espremer titulo e empresa.
 *
 * As pilulas do que esta ligado existem porque filtro escondido corta a lista
 * em silencio: sem elas, com o painel fechado, nao da para saber por que a
 * fila encolheu nem o que desligar para ela voltar.
 */
export function RadarFilters({
  filters,
  onSubmit,
  onClear,
  onRemover,
  podeColetar,
  coletando,
  onColetar,
  podeTriar,
  onCadastrar,
}: Props) {
  const [aberto, setAberto] = useState(false)

  // Data escolhida no calendario, guardada aqui ate o "aplicar": o form e lido
  // por FormData, e o calendario nao e campo nativo.
  const [de, setDe] = useState(filters.published_after)
  const [ate, setAte] = useState(filters.published_before)
  const ligados = ativos(filters)

  // A busca fica na linha de cima, entao o contador do botao conta so o que
  // esta escondido. Contar a busca faria o numero mentir sobre o painel.
  const avancados = ligados.filter((item) => item.chave !== 'q').length

  /**
   * As datas vivem em estado local, entao limpar so a URL nao as apaga.
   *
   * Sem isto o calendario continuava marcado depois do "limpar" e o proximo
   * "aplicar" trazia de volta a faixa que voce acabou de tirar.
   */
  function limpar() {
    setDe('')
    setAte('')
    onClear()
  }

  function remover(chave: keyof RadarFilterValues) {
    if (chave === 'published_after') setDe('')
    if (chave === 'published_before') setAte('')
    onRemover(chave)
  }

  return (
    <div className="rounded-[10px] border border-line bg-card">
      <form onSubmit={onSubmit}>
        <div className="flex flex-col gap-2.5 p-3.5 sm:flex-row sm:items-center">
          <div className="relative min-w-0 flex-1">
            <Search
              size={17}
              className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-muted"
            />
            <Input
              type="search"
              name="q"
              inputSize="sm"
              defaultValue={filters.q}
              key={`q-${filters.q}`}
              placeholder="Buscar por título, empresa ou descrição"
              className="max-sm:h-11 pl-9"
            />
          </div>

          <div className="flex gap-2.5">
            <Button
              type="button"
              size="sm"
              aria-expanded={aberto}
              onClick={() => setAberto((atual) => !atual)}
              className={`max-sm:h-11 max-sm:flex-1 ${
                aberto
                  ? 'border-accent! bg-accent! text-white!'
                  : avancados > 0
                    ? 'border-accent! bg-wash! font-semibold text-accent!'
                    : ''
              }`}
            >
              <ListFilter size={16} />
              Filtros
              {avancados > 0 && (
                <span
                  className={`inline-flex h-[18px] min-w-[18px] items-center justify-center rounded-full px-1.5 text-[10.5px] font-semibold ${
                    aberto ? 'bg-white text-accent' : 'bg-accent text-white'
                  }`}
                >
                  {avancados}
                </span>
              )}
            </Button>

            {podeTriar && (
              <Button
                type="button"
                size="sm"
                onClick={onCadastrar}
                title="Cadastrar uma vaga que a coleta nao traz"
                className="max-sm:h-11"
              >
                <Plus size={16} />
                <span className="max-sm:hidden">Cadastrar vaga</span>
              </Button>
            )}

            {podeColetar && (
              <Button
                type="button"
                variant="primary"
                size="sm"
                disabled={coletando}
                onClick={onColetar}
                title="Roda GitHub e Gupy agora. Leva uns 40 segundos."
                className="max-sm:h-11 max-sm:w-11 max-sm:px-0"
              >
                <RefreshCw size={16} className={coletando ? 'animate-spin' : undefined} />
                <span className="max-sm:hidden">
                  {coletando ? 'Buscando...' : 'Buscar vagas novas'}
                </span>
              </Button>
            )}
          </div>
        </div>

        {aberto && (
          <div className="px-3.5 pb-3.5">
            {/* Campos estreitos e em linha, nao um grid de quatro colunas
                esticadas: periodo e fonte sao rotulo curto, e um campo com o
                triplo da largura do texto so afasta um filtro do outro. */}
            <div className="flex flex-wrap items-start gap-3">
              <div className="w-[216px]">
                <label className={rotulo} htmlFor="radar-de">
                  Publicada de
                </label>
                <input type="hidden" name="published_after" value={de} />
                <DateSelect
                  id="radar-de"
                  aria-label="Publicada a partir de"
                  value={de}
                  onChange={setDe}
                  max={ate || undefined}
                />
              </div>

              <div className="w-[216px]">
                <label className={rotulo} htmlFor="radar-ate">
                  Até
                </label>
                <input type="hidden" name="published_before" value={ate} />
                <DateSelect
                  id="radar-ate"
                  aria-label="Publicada até"
                  value={ate}
                  onChange={setAte}
                  min={de || undefined}
                />
              </div>

              <div className="w-[168px]">
                <label className={rotulo} htmlFor="radar-fonte">
                  Fonte
                </label>
                <Select
                  id="radar-fonte"
                  name="source"
                  inputSize="xs"
                  options={[{ value: '', label: 'Todas as fontes' }, ...SOURCES]}
                  defaultValue={filters.source}
                  key={`source-${filters.source}`}
                />
              </div>

              <div className="w-[186px]">
                <label className={rotulo} htmlFor="radar-score">
                  Score mínimo
                </label>
                <Input
                  id="radar-score"
                  type="number"
                  name="min_score"
                  inputSize="xs"
                  defaultValue={filters.min_score}
                  key={`min-${filters.min_score}`}
                  placeholder="sem mínimo"
                />
                {/* A dica mora colada no campo que ela explica; solta no rodape
                    do painel ela parecia legenda dos tres. */}
                <p className="mt-1 text-[11.5px] text-muted">Procure por scores de 12+.</p>
              </div>

              <div className="ml-auto flex gap-2 self-end">
                <Button type="button" size="sm" onClick={limpar} disabled={ligados.length === 0}>
                  limpar
                </Button>
                <Button type="submit" variant="primary" size="sm">
                  aplicar
                </Button>
              </div>
            </div>
          </div>
        )}
      </form>

      {/* A faixa so existe quando ha filtro ligado: vazia, seria uma tira de
          padding sem conteudo embaixo da busca. */}
      {ligados.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 px-3.5 pb-3.5">
          {ligados.map((item) => (
            <button
              key={item.chave}
              type="button"
              onClick={() => remover(item.chave)}
              title={`Remover ${item.texto}`}
              className="inline-flex cursor-pointer items-center gap-1.5 rounded-full bg-wash px-2.5 py-0.5 text-[11.5px] leading-[17px] font-medium text-accent outline-none hover:bg-accent hover:text-white focus-visible:border focus-visible:border-ink"
            >
              {item.texto}
              <X size={12} strokeWidth={2.6} />
            </button>
          ))}

          <button
            type="button"
            onClick={limpar}
            className="cursor-pointer text-[12.5px] text-muted underline outline-none hover:text-ink focus-visible:text-ink"
          >
            limpar
          </button>
        </div>
      )}
    </div>
  )
}
