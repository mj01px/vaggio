import hashlib

from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class JobSource(models.TextChoices):
    GITHUB = "github", "GitHub Issues"
    GUPY = "gupy", "Gupy"
    MANUAL = "manual", "Cadastro manual"


class WorkMode(models.TextChoices):
    REMOTE = "remote", "Remoto"
    HYBRID = "hybrid", "Híbrido"
    ONSITE = "onsite", "Presencial"
    UNKNOWN = "unknown", "Não informado"


class Seniority(models.TextChoices):
    INTERNSHIP = "internship", "Estágio"
    JUNIOR = "junior", "Júnior"
    MID = "mid", "Pleno"
    SENIOR = "senior", "Sênior"
    UNKNOWN = "unknown", "Não informado"


class JobQuerySet(models.QuerySet):
    def triage(self):
        """Fila de triagem: nao descartada e ainda sem candidatura."""
        return self.filter(discarded=False, application__isnull=True)

    def discarded(self):
        return self.filter(discarded=True)


class Job(TimeStampedModel):
    """Vaga coletada de uma fonte externa ou cadastrada na mao.

    `key` e o hash de deduplicacao: coletar a mesma vaga duas vezes, inclusive
    de fontes diferentes, nao cria duplicata.
    """

    title = models.CharField("Título", max_length=300)
    company = models.CharField("Empresa", max_length=200, blank=True)
    location = models.CharField("Local", max_length=200, blank=True)
    work_mode = models.CharField(
        "Modalidade", max_length=20, choices=WorkMode.choices, default=WorkMode.UNKNOWN
    )
    seniority = models.CharField(
        "Senioridade", max_length=20, choices=Seniority.choices, default=Seniority.UNKNOWN
    )
    description = models.TextField("Descrição", blank=True)
    url = models.URLField(max_length=1000)

    source = models.CharField("Fonte", max_length=20, choices=JobSource.choices, db_index=True)
    source_id = models.CharField("ID na fonte", max_length=200, blank=True)
    key = models.CharField(max_length=64, unique=True, editable=False)

    score = models.IntegerField(default=0, db_index=True)
    tags = models.JSONField(default=list, blank=True)

    # Indexado porque a fila filtra por janela de recencia
    # (`?published_within=7`), que e o corte usado em toda visita ao Radar.
    published_at = models.DateTimeField("Publicada em", null=True, blank=True, db_index=True)
    discarded = models.BooleanField("Descartada", default=False, db_index=True)

    objects = JobQuerySet.as_manager()

    class Meta:
        db_table = "jobs_job"
        verbose_name = "vaga"
        verbose_name_plural = "vagas"
        # created_at e o momento da coleta: e o que a fila de triagem desempata.
        ordering = ["-score", "-created_at"]
        indexes = [
            models.Index(fields=["discarded", "-score"], name="job_discarded_score_idx"),
            models.Index(fields=["source", "-created_at"], name="job_source_created_idx"),
            models.Index(fields=["discarded", "-published_at"], name="job_discarded_pub_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.title} @ {self.company or 'sem empresa'}"

    @staticmethod
    def build_key(url: str, title: str = "", company: str = "") -> str:
        """Hash estavel para deduplicacao.

        Usa a URL quando ela existe (e o identificador mais confiavel) e cai
        para titulo+empresa normalizados quando nao existe.
        """
        base = url.strip().lower() or f"{title.strip().lower()}|{company.strip().lower()}"
        return hashlib.sha256(base.encode("utf-8")).hexdigest()

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.build_key(self.url, self.title, self.company)
        super().save(*args, **kwargs)

    @property
    def has_application(self) -> bool:
        return hasattr(self, "application")


class Pitch(TimeStampedModel):
    """O "Apresente-se" gerado para uma vaga.

    Uma versao por vaga: gerar de novo substitui a anterior, e quem faz isso e a
    rota de geracao, depois de o texto novo existir. A tabela continua com uma
    linha por vaga, e nao um historico, porque comparar versoes antigas nunca
    virou uso real: o que se faz e gerar, ler, ajustar e gerar de novo.
    """

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="pitches")
    # Quem pediu. O texto sai do dossie dessa pessoa (historico, projetos, as
    # vezes salario), entao ele nao e da vaga: e dela. Sem esta coluna, quem
    # tivesse `apresentacao.gerar` lia o dossie dos outros pela vaga.
    #
    # Nulo para as linhas que existiam antes desta coluna, que nao tem como
    # saber de quem eram; so o superusuario ve essas.
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pitches",
        null=True,
        blank=True,
        verbose_name="Autor",
    )
    texto = models.TextField("Texto")

    modelo = models.CharField("Modelo", max_length=80)
    instrucao = models.CharField("Ajuste pedido", max_length=300, blank=True)
    max_chars = models.PositiveIntegerField("Tamanho alvo")

    tokens_entrada = models.PositiveIntegerField(default=0)
    tokens_saida = models.PositiveIntegerField(default=0)
    tokens_pensamento = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "jobs_pitch"
        verbose_name = "apresentação"
        verbose_name_plural = "apresentações"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["job", "-created_at"], name="pitch_job_created_idx"),
            models.Index(fields=["autor", "-created_at"], name="pitch_autor_created_idx"),
        ]

    def __str__(self) -> str:
        return f"Apresentação para {self.job.title[:40]} ({self.created_at:%d/%m %H:%M})"

    @property
    def caracteres(self) -> int:
        return len(self.texto)
