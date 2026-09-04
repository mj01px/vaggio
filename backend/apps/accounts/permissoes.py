"""Catalogo de permissoes e a classe que o DRF usa para checar.

Os slugs sao a fonte de verdade do que existe. A migration de dados semeia a
tabela a partir daqui, e `manage.py sync_permissoes` reaplica quando a lista
crescer, para acrescentar acao nao virar migration nova.
"""

from rest_framework.permissions import BasePermission

VER_VAGAS = "vagas.ver"
TRIAR_VAGAS = "vagas.triar"
GERENCIAR_VAGAS = "vagas.gerenciar"
VER_FUNIL = "funil.ver"
GERENCIAR_FUNIL = "funil.gerenciar"
VER_COLETA = "coleta.ver"
RODAR_COLETA = "coleta.rodar"
GERAR_APRESENTACAO = "apresentacao.gerar"
EDITAR_PERFIL = "perfil.editar"
VER_USUARIOS = "usuarios.ver"
GERENCIAR_USUARIOS = "usuarios.gerenciar"
VER_CARGOS = "cargos.ver"
GERENCIAR_CARGOS = "cargos.gerenciar"

PERMISSOES_PADRAO: list[tuple[str, str, str]] = [
    (VER_VAGAS, "Ver vagas", "Abrir o Radar e a fila de triagem."),
    (TRIAR_VAGAS, "Triar vagas", "Descartar, devolver para a fila e cadastrar vaga na mão."),
    (
        GERENCIAR_VAGAS,
        "Editar vagas",
        "Corrigir título, empresa, local, descrição e score de uma vaga coletada.",
    ),
    (VER_FUNIL, "Ver o funil", "Abrir o Board e a linha do tempo das candidaturas."),
    (GERENCIAR_FUNIL, "Gerenciar o funil", "Criar candidatura e mover de status."),
    (VER_COLETA, "Ver o histórico de coleta", "Consultar as execuções já feitas."),
    (RODAR_COLETA, "Rodar a coleta", "Disparar uma busca nova nas fontes."),
    (GERAR_APRESENTACAO, "Gerar apresentação", 'Escrever o "Apresente-se" de uma vaga.'),
    (EDITAR_PERFIL, "Editar o próprio perfil", "Mudar dossiê, termos e preferências."),
    (VER_USUARIOS, "Ver usuários", "Listar quem tem acesso ao Vaggio."),
    (GERENCIAR_USUARIOS, "Gerenciar usuários", "Criar conta, trocar cargo, ativar e desativar."),
    (VER_CARGOS, "Ver cargos", "Consultar os cargos e o que cada um libera."),
    (GERENCIAR_CARGOS, "Gerenciar cargos", "Criar cargo e mudar as permissões dele."),
]

# Cargo semeado. Acesso total nao precisa de cargo: o superusuario ja passa por
# cima da checagem, e um cargo "pode tudo" so criava um segundo lugar para dar
# acesso total, que envelhecia toda vez que uma permissao nova entrava aqui.
CARGOS_PADRAO: dict[str, tuple[str, str, list[str]]] = {
    "leitura": (
        "Somente leitura",
        "Enxerga o radar e o funil, sem mexer em nada.",
        [VER_VAGAS, VER_FUNIL, VER_COLETA],
    ),
}


class TemPermissao(BasePermission):
    """Exige a permissao declarada em `permissao_exigida` na view.

    A view pode declarar um slug so, ou um dicionario por acao quando ler e
    escrever tem exigencias diferentes, que e o caso comum aqui.
    """

    message = "Seu cargo não tem permissão para esta ação."

    def has_permission(self, request, view) -> bool:
        exigida = self._exigida(view, request)
        if exigida is None:
            return True

        usuario = request.user
        if not usuario or not usuario.is_authenticated:
            return False
        if usuario.is_superuser:
            return True

        perfil = getattr(usuario, "perfil", None)
        if perfil is None:
            # Usuario sem perfil e conta pela metade: nega em vez de assumir
            # que pode, que e o jeito seguro de errar.
            return False
        return perfil.pode(exigida)

    @staticmethod
    def _exigida(view, request) -> str | None:
        exigida = getattr(view, "permissao_exigida", None)
        if not isinstance(exigida, dict):
            return exigida

        acao = getattr(view, "action", None)
        # Uma acao que serve GET e POST na mesma URL precisa de exigencias
        # diferentes por metodo: ler a linha do tempo nao e escrever nela.
        # `acao:post` vence `acao`, que vence `default`.
        return (
            exigida.get(f"{acao}:{request.method.lower()}")
            or exigida.get(acao)
            or exigida.get("default")
        )
