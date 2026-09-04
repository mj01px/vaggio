"""Serializers de sessao e perfil."""

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from .models import Cargo, Perfil, Permissao
from .permissoes import GERENCIAR_USUARIOS

User = get_user_model()


def username_para(email: str) -> str:
    """O identificador interno da conta nova, a partir do e-mail.

    O `auth.User` exige um username unico e nao nulo, mas ele nao aparece mais
    em lugar nenhum: quem entra digita o e-mail. Usar o proprio e-mail como
    username mantem a coluna legivel no admin sem inventar um segundo nome para
    a pessoa decorar. O sufixo so entra quando um username antigo, de antes do
    login por e-mail, ja ocupava o texto.
    """
    base = email.strip().lower()[:150]
    if not User.objects.filter(username__iexact=base).exists():
        return base
    for n in range(2, 100):
        sufixo = f"-{n}"
        tentativa = f"{base[: 150 - len(sufixo)]}{sufixo}"
        if not User.objects.filter(username__iexact=tentativa).exists():
            return tentativa
    raise serializers.ValidationError("Nao consegui gerar um identificador para esta conta.")


def email_esta_livre(email: str, ignorando=None) -> bool:
    """Ninguem mais pode estar com esse e-mail: ele e a credencial de login."""
    qs = User.objects.filter(email__iexact=email.strip())
    if ignorando is not None:
        qs = qs.exclude(pk=ignorando.pk)
    return not qs.exists()


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    # Default True mantem o que a API sempre fez: cookie persistente. Cliente
    # antigo, que nao manda o campo, continua entrando do mesmo jeito.
    lembrar = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs):
        usuario = authenticate(
            request=self.context.get("request"),
            username=attrs["email"],
            password=attrs["password"],
        )
        if not usuario:
            # Mensagem unica de proposito: dizer "esse e-mail nao existe"
            # entrega quais contas existem para quem estiver tentando adivinhar.
            raise serializers.ValidationError("E-mail ou senha inválidos.")
        if not usuario.is_active:
            raise serializers.ValidationError("Esta conta está desativada.")
        attrs["user"] = usuario
        return attrs


class CargoSerializer(serializers.ModelSerializer):
    permissoes = serializers.SlugRelatedField(slug_field="slug", many=True, read_only=True)

    class Meta:
        model = Cargo
        fields = ["id", "slug", "nome", "descricao", "permissoes"]
        read_only_fields = fields


class PerfilSerializer(serializers.ModelSerializer):
    """O perfil de quem esta logado, com o que a tela precisa para se montar."""

    email = serializers.EmailField(source="user.email", read_only=True)
    cargo = CargoSerializer(read_only=True)
    permissoes = serializers.ListField(child=serializers.CharField(), read_only=True)
    tem_dossie = serializers.SerializerMethodField()

    class Meta:
        model = Perfil
        fields = [
            "id",
            "email",
            "nome",
            "cargo",
            "permissoes",
            "dossie",
            "tem_dossie",
            "termos",
            "pitch_max_chars",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "email", "cargo", "permissoes", "created_at", "updated_at"]

    def get_tem_dossie(self, obj) -> bool:
        return len(obj.dossie.strip()) >= 400


class PerfilUpdateSerializer(serializers.ModelSerializer):
    """O que o dono do perfil pode mudar. Cargo fica de fora de proposito:
    ninguem se promove editando o proprio perfil."""

    class Meta:
        model = Perfil
        fields = ["nome", "dossie", "termos", "pitch_max_chars"]

    def validate_pitch_max_chars(self, value):
        if not 200 <= value <= 5000:
            raise serializers.ValidationError("Use um valor entre 200 e 5000.")
        return value

    def validate_termos(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Os termos precisam ser um objeto por grupo.")
        for grupo, conteudo in value.items():
            if not isinstance(conteudo, dict):
                raise serializers.ValidationError(f'O grupo "{grupo}" precisa ser um objeto.')
            if not isinstance(conteudo.get("weight"), int):
                raise serializers.ValidationError(f'O grupo "{grupo}" precisa de um peso inteiro.')
            termos = conteudo.get("terms")
            if not isinstance(termos, list) or not all(isinstance(t, str) for t in termos):
                raise serializers.ValidationError(
                    f'O grupo "{grupo}" precisa de uma lista de termos em texto.'
                )
        return value

    def to_representation(self, instance):
        return PerfilSerializer(instance, context=self.context).data


class PermissaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permissao
        fields = ["id", "slug", "nome", "descricao"]
        read_only_fields = fields


class CargoEscritaSerializer(serializers.ModelSerializer):
    """Cria e edita cargo, com as permissoes por slug.

    Slug em vez de id: e o que a tela ja usa e o que aparece no codigo, entao o
    corpo do PATCH fica legivel e nao depende de id de banco.
    """

    permissoes = serializers.SlugRelatedField(
        slug_field="slug", many=True, queryset=Permissao.objects.all(), required=False
    )

    class Meta:
        model = Cargo
        fields = ["id", "slug", "nome", "descricao", "permissoes"]

    def to_representation(self, instance):
        return CargoSerializer(instance, context=self.context).data


class UsuarioSerializer(serializers.ModelSerializer):
    """Uma pessoa com acesso, do jeito que a tela de usuarios mostra.

    O `username` saiu: e identificador interno, a tela nunca mostrou, e mandar
    junto so dava um segundo nome de conta para quem estivesse colecionando.

    `is_superuser` sai para quem so tem `usuarios.ver`. A permissao e descrita
    como "listar quem tem acesso", e dizer de quebra quais contas passam por
    cima de todo controle e entregar a lista de alvos junto com a lista de
    pessoas. Quem gerencia continua vendo, porque a tela precisa: e o campo que
    desabilita o botao de desativar.
    """

    nome = serializers.CharField(source="perfil.nome", read_only=True)
    cargo = CargoSerializer(source="perfil.cargo", read_only=True)
    permissoes = serializers.SerializerMethodField()
    perfil_id = serializers.IntegerField(source="perfil.id", read_only=True)
    tem_dossie = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "nome",
            "cargo",
            "permissoes",
            "perfil_id",
            "tem_dossie",
            "is_active",
            "is_superuser",
            "last_login",
            "date_joined",
        ]
        read_only_fields = fields

    def get_permissoes(self, obj) -> list[str]:
        perfil = getattr(obj, "perfil", None)
        return perfil.permissoes if perfil else []

    def get_tem_dossie(self, obj) -> bool:
        perfil = getattr(obj, "perfil", None)
        return bool(perfil and len(perfil.dossie.strip()) >= 400)

    def to_representation(self, instance):
        dados = super().to_representation(instance)
        if not self._quem_le_gerencia():
            dados.pop("is_superuser", None)
        return dados

    def _quem_le_gerencia(self) -> bool:
        pedido = self.context.get("request")
        usuario = getattr(pedido, "user", None)
        if usuario is None or not usuario.is_authenticated:
            return False
        if usuario.is_superuser:
            return True
        perfil = getattr(usuario, "perfil", None)
        return bool(perfil and perfil.pode(GERENCIAR_USUARIOS))


class UsuarioCreateSerializer(serializers.Serializer):
    """Cria a conta e o perfil junto: conta sem perfil nao consegue fazer nada.

    O e-mail e obrigatorio porque e por ele que a pessoa entra. O username nao
    vem do formulario: ele e derivado do e-mail e so serve por dentro.
    """

    email = serializers.EmailField()
    nome = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    # Sem senha e o caminho normal: a conta nasce sem senha utilizavel e a
    # pessoa escolhe a dela pelo link do convite. Assim ninguem, nem quem
    # cadastrou, chega a saber a senha de outra pessoa. O campo continua
    # aceito para o caso de criar conta sem ter e-mail funcionando.
    password = serializers.CharField(
        write_only=True, required=False, allow_blank=True, style={"input_type": "password"}
    )
    cargo = serializers.SlugRelatedField(
        slug_field="slug", queryset=Cargo.objects.all(), required=False, allow_null=True
    )

    def validate_email(self, value):
        if not email_esta_livre(value):
            raise serializers.ValidationError("Ja existe uma conta com esse e-mail.")
        return value.strip()

    def validate_password(self, value):
        if not value:
            return value
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value

    @transaction.atomic
    def create(self, validated_data):
        email = validated_data["email"]
        senha = validated_data.get("password")
        user = User.objects.create_user(username=username_para(email), email=email)
        if senha:
            user.set_password(senha)
        else:
            # Nao e "senha vazia": e uma senha que nenhum hash pode casar,
            # entao a conta so entra depois de passar pelo convite.
            user.set_unusable_password()
        user.save(update_fields=["password"])

        Perfil.objects.create(
            user=user,
            nome=validated_data.get("nome") or email,
            cargo=validated_data.get("cargo"),
        )
        return user

    def to_representation(self, instance):
        return UsuarioSerializer(instance, context=self.context).data


class UsuarioUpdateSerializer(serializers.Serializer):
    """O que um administrador muda em outra pessoa.

    Senha fica de fora: ela tem rota propria, para trocar senha nunca acontecer
    de raspao no meio de uma edicao de cadastro.
    """

    # Sem allow_blank: apagar o e-mail hoje seria tirar da pessoa o unico jeito
    # de entrar.
    email = serializers.EmailField(required=False)
    nome = serializers.CharField(max_length=120, required=False, allow_blank=True)
    cargo = serializers.SlugRelatedField(
        slug_field="slug", queryset=Cargo.objects.all(), required=False, allow_null=True
    )
    is_active = serializers.BooleanField(required=False)

    def validate_email(self, value):
        if not email_esta_livre(value, ignorando=self.instance):
            raise serializers.ValidationError("Ja existe uma conta com esse e-mail.")
        return value.strip()

    @transaction.atomic
    def update(self, instance, validated_data):
        if "email" in validated_data:
            instance.email = validated_data["email"]
        if "is_active" in validated_data:
            instance.is_active = validated_data["is_active"]
        instance.save()

        perfil, _ = Perfil.objects.get_or_create(
            user=instance, defaults={"nome": instance.email or instance.username}
        )
        if "nome" in validated_data:
            perfil.nome = validated_data["nome"]
        if "cargo" in validated_data:
            perfil.cargo = validated_data["cargo"]
        perfil.save()

        instance.refresh_from_db()
        return instance

    def to_representation(self, instance):
        return UsuarioSerializer(instance, context=self.context).data


class TrocarSenhaSerializer(serializers.Serializer):
    """Troca da propria senha, estando logado.

    Pede a senha atual mesmo com a sessao valida: sessao esquecida aberta e
    justamente o cenario em que trocar a senha sem provar quem e seria o
    caminho para tomar a conta de alguem.
    """

    senha_atual = serializers.CharField(write_only=True, style={"input_type": "password"})
    nova = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate_senha_atual(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Senha atual incorreta.")
        return value

    def validate_nova(self, value):
        try:
            validate_password(value, self.context["request"].user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value

    def validate(self, attrs):
        if attrs["senha_atual"] == attrs["nova"]:
            raise serializers.ValidationError("A senha nova tem de ser diferente da atual.")
        return attrs


class EsqueciSerializer(serializers.Serializer):
    email = serializers.EmailField()


class RedefinirSerializer(serializers.Serializer):
    """Fecha o fluxo do link: uid e token vieram na URL do e-mail."""

    uid = serializers.CharField()
    token = serializers.CharField()
    nova = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate_nova(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value


class TrocarEmailSerializer(serializers.Serializer):
    """Pede a troca. Nada muda ainda: quem muda e o clique no link."""

    senha_atual = serializers.CharField(write_only=True, style={"input_type": "password"})
    email = serializers.EmailField()

    def validate_senha_atual(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Senha atual incorreta.")
        return value

    def validate_email(self, value):
        usuario = self.context["request"].user
        if value.strip().lower() == usuario.email.lower():
            raise serializers.ValidationError("Esse ja e o seu e-mail.")
        if not email_esta_livre(value, ignorando=usuario):
            raise serializers.ValidationError("Ja existe uma conta com esse e-mail.")
        return value.strip()


class CodigoSerializer(serializers.Serializer):
    """Um codigo de seis digitos do aplicativo, ou um de reserva."""

    codigo = serializers.CharField(max_length=32)


class DesativarDoisFatoresSerializer(serializers.Serializer):
    senha_atual = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate_senha_atual(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Senha atual incorreta.")
        return value
