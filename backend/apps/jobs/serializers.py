"""Serializers da Vaga: leitura da fila de triagem e cadastro manual."""

from rest_framework import serializers

from .models import Job, JobSource, Pitch
from .pitch import MAX_CHARS_PADRAO
from .scoring import classify


class JobSerializer(serializers.ModelSerializer):
    """Cartao da fila de triagem.

    Sem a descricao de proposito: ela e longa, nao aparece na lista, e em 120
    vagas por pagina seria a maior parte do payload.
    """

    source_display = serializers.CharField(source="get_source_display", read_only=True)
    seniority_display = serializers.CharField(source="get_seniority_display", read_only=True)
    work_mode_display = serializers.CharField(source="get_work_mode_display", read_only=True)
    has_application = serializers.BooleanField(read_only=True)

    class Meta:
        model = Job
        fields = [
            "id",
            "title",
            "company",
            "location",
            "url",
            "source",
            "source_display",
            "seniority",
            "seniority_display",
            "work_mode",
            "work_mode_display",
            "score",
            "tags",
            "discarded",
            "has_application",
            "published_at",
            "created_at",
        ]
        read_only_fields = fields


class JobDetailSerializer(JobSerializer):
    class Meta(JobSerializer.Meta):
        fields = [*JobSerializer.Meta.fields, "description", "source_id", "updated_at"]
        read_only_fields = fields


class JobCreateSerializer(serializers.ModelSerializer):
    """Cadastro manual: e por aqui que uma vaga do LinkedIn entra no radar."""

    class Meta:
        model = Job
        fields = ["title", "company", "location", "url", "description"]

    def validate_url(self, value):
        if Job.objects.filter(key=Job.build_key(value)).exists():
            raise serializers.ValidationError("Essa vaga ja esta no radar.")
        return value

    def create(self, validated_data):
        result = classify(
            validated_data["title"],
            validated_data.get("description", ""),
            validated_data.get("company", ""),
            validated_data.get("location", ""),
        )
        return Job.objects.create(
            source=JobSource.MANUAL, **validated_data, **result.as_dict()
        )

    def to_representation(self, instance):
        return JobSerializer(instance, context=self.context).data


class JobUpdateSerializer(serializers.ModelSerializer):
    """Correcao de vaga por quem tem `vagas.gerenciar`.

    A coleta erra: titulo truncado, empresa vazia, senioridade lida errado no
    texto. Antes a unica saida era o admin do Django, que nao existe mais.

    Fora daqui ficam `source`, `source_id` e `key`: sao a procedencia da vaga,
    nao conteudo. `discarded` tambem, porque ja tem acao propria.
    """

    tags = serializers.ListField(
        child=serializers.CharField(max_length=50, allow_blank=False),
        required=False,
        max_length=20,
    )
    # O score do classificador nao tem teto fixo e chega a ser negativo quando a
    # vaga pede anos demais. A faixa aqui so barra digito a mais.
    score = serializers.IntegerField(required=False, min_value=-100, max_value=100)

    class Meta:
        model = Job
        fields = [
            "title",
            "company",
            "location",
            "url",
            "description",
            "seniority",
            "work_mode",
            "tags",
            "score",
            "published_at",
        ]

    def validate_url(self, value):
        """A URL e a identidade da vaga para a deduplicacao.

        Trocar a URL troca a `key`, e uma key repetida faria a coleta tratar
        duas vagas como a mesma. Recusar aqui e melhor do que gravar e deixar a
        proxima coleta decidir qual das duas sobrevive.
        """
        chave = Job.build_key(value)
        if Job.objects.filter(key=chave).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("Ja existe outra vaga com essa URL.")
        return value

    def validate_tags(self, value):
        """Minusculas e sem repetir, do mesmo jeito que o classificador grava.

        A tela filtra por tag comparando string crua: "Python" e "python" viram
        dois filtros diferentes se a normalizacao ficar so na coleta.
        """
        limpas: list[str] = []
        for tag in value:
            tag = tag.strip().lower()
            if tag and tag not in limpas:
                limpas.append(tag)
        return limpas

    def update(self, instance, validated_data):
        if validated_data.get("url", instance.url) != instance.url:
            # `save` so calcula a key quando ela esta vazia, entao trocar a URL
            # sem limpar deixaria a vaga guardada sob a identidade antiga e a
            # proxima coleta a traria de novo como se fosse outra vaga.
            instance.key = ""
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        # A tela troca a vaga na lista pela resposta do PATCH, e a lista mostra
        # campos que este serializer nao aceita (score_label, has_application).
        return JobSerializer(instance, context=self.context).data


class PitchSerializer(serializers.ModelSerializer):
    """Uma versao gerada do "Apresente-se"."""

    caracteres = serializers.IntegerField(read_only=True)

    class Meta:
        model = Pitch
        fields = [
            "id",
            "texto",
            "caracteres",
            "modelo",
            "instrucao",
            "max_chars",
            "tokens_entrada",
            "tokens_saida",
            "tokens_pensamento",
            "created_at",
        ]
        read_only_fields = fields


class PitchCreateSerializer(serializers.Serializer):
    """Parametros do pedido de geracao."""

    max_chars = serializers.IntegerField(
        required=False, default=MAX_CHARS_PADRAO, min_value=200, max_value=5000
    )
    instrucao = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=300
    )
