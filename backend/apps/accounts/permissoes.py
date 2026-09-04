"""Catalogo de permissoes e a classe que o DRF usa para checar.

Os slugs sao a fonte de verdade do que existe. A migration de dados semeia a
tabela a partir daqui, e `manage.py sync_permissoes` reaplica quando a lista
crescer, para acrescentar acao nao virar migration nova.
"""

import logging

from rest_framework.permissions import BasePermission

seguranca = logging.getLogger("apps.seguranca")

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


# Sentinela de "a view nao disse nada". Precisa ser diferente de `None`, que e
# como a view diz "esta rota nao depende de cargo" de proposito. Sem essa
# distincao, esquecer de declarar e abrir a rota davam no mesmo resultado.
NAO_DECLARADO = object()


class TemPermissao(BasePermission):
    """Exige a permissao declarada em `permissao_exigida` na view.

    A view pode declarar um slug so, ou um dicionario por acao quando ler e
    escrever tem exigencias diferentes, que e o caso comum aqui. Quem nao
    depende de cargo declara `None`, e a declaracao e obrigatoria: view que
    esquecer de dizer o que exige nao passa.

    O teste `test_toda_rota_declara_permissao` percorre o roteador e quebra
    antes do deploy; a negacao aqui e a rede embaixo dele, para o esquecimento
    virar 403 e nao acesso liberado.
    """

    message = "Seu cargo não tem permissão para esta ação."

    def has_permission(self, request, view) -> bool:
        exigida = self._exigida(view, request)

        if exigida is NAO_DECLARADO:
            seguranca.error(
                "rbac: %s nao declarou permissao_exigida, acesso negado (acao=%s metodo=%s)",
                view.__class__.__name__,
                getattr(view, "action", None),
                request.method,
            )
            return False

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

        if perfil.pode(exigida):
            return True

        seguranca.info(
            "rbac: %s negado para %s (exigia %s, cargo %s)",
            request.method,
            usuario.email or usuario.get_username(),
            exigida,
            getattr(perfil.cargo, "slug", "sem cargo"),
        )
        return False

    @staticmethod
    def _exigida(view, request):
        exigida = getattr(view, "permissao_exigida", NAO_DECLARADO)
        if not isinstance(exigida, dict):
            return exigida

        acao = getattr(view, "action", None)
        # Uma acao que serve GET e POST na mesma URL precisa de exigencias
        # diferentes por metodo: ler a linha do tempo nao e escrever nela.
        # `acao:post` vence `acao`, que vence `default`.
        #
        # O `default` tambem cai na sentinela: um dicionario que esquece uma
        # acao e nao tem `default` era o mesmo buraco pela porta de tras.
        for chave in (f"{acao}:{request.method.lower()}", acao, "default"):
            if chave in exigida:
                valor = exigida[chave]
                if valor is not None:
                    return valor
                # Chave presente com None e "esta acao nao depende de cargo".
                return None
        return NAO_DECLARADO
