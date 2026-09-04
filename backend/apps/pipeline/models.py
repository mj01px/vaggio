from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel
from apps.jobs.models import Job


class ApplicationStatus(models.TextChoices):
    INTEREST = "interest", "Quero aplicar"
    APPLIED = "applied", "Aplicada"
    SCREENING = "screening", "Em triagem"
    CHALLENGE = "challenge", "Teste / desafio"
    INTERVIEW = "interview", "Entrevista"
    OFFER = "offer", "Proposta"
    REJECTED = "rejected", "Rejeitada"
    WITHDRAWN = "withdrawn", "Desisti"


# Colunas do board, na ordem. Rejeitada e Desisti ficam fora do fluxo ativo.
ACTIVE_STATUSES: list[str] = [
    ApplicationStatus.INTEREST,
    ApplicationStatus.APPLIED,
    ApplicationStatus.SCREENING,
    ApplicationStatus.CHALLENGE,
    ApplicationStatus.INTERVIEW,
    ApplicationStatus.OFFER,
]

CLOSED_STATUSES: list[str] = [
    ApplicationStatus.REJECTED,
    ApplicationStatus.WITHDRAWN,
]


class ApplicationQuerySet(models.QuerySet):
    def active(self):
        return self.exclude(status__in=CLOSED_STATUSES)

    def closed(self):
        return self.filter(status__in=CLOSED_STATUSES)

    def overdue(self):
        """Proximo passo vencido e ainda no funil ativo."""
        return self.active().filter(next_step_on__lt=timezone.localdate())


class Application(TimeStampedModel):
    """O acompanhamento de uma vaga: onde ela esta no funil e o que fazer a seguir."""

    job = models.OneToOneField(Job, on_delete=models.CASCADE, related_name="application")
    status = models.CharField(
        "Status",
        max_length=20,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.INTEREST,
        db_index=True,
    )
    priority = models.PositiveSmallIntegerField(
        "Prioridade",
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="1 = maior prioridade, 5 = menor",
    )

    applied_on = models.DateField("Aplicada em", null=True, blank=True)
    next_step = models.CharField("Próximo passo", max_length=300, blank=True)
    next_step_on = models.DateField("Data do próximo passo", null=True, blank=True, db_index=True)

    contact = models.CharField(
        "Contato", max_length=200, blank=True,
        help_text="Recrutador, indicação, quem te respondeu",
    )
    has_referral = models.BooleanField("Tem indicação", default=False)
    notes = models.TextField("Notas", blank=True)

    objects = ApplicationQuerySet.as_manager()

    class Meta:
        db_table = "pipeline_application"
        verbose_name = "candidatura"
        verbose_name_plural = "candidaturas"
        ordering = ["priority", "-updated_at"]
        indexes = [models.Index(fields=["status", "priority"], name="application_status_prio_idx")]

    def __str__(self) -> str:
        return f"{self.job.title} [{self.get_status_display()}]"

    @property
    def is_overdue(self) -> bool:
        """Proximo passo com data vencida e ainda no funil ativo."""
        if not self.next_step_on or self.status in CLOSED_STATUSES:
            return False
        return self.next_step_on < timezone.localdate()

    @property
    def days_idle(self) -> int:
        return (timezone.now() - self.updated_at).days


class Interaction(TimeStampedModel):
    """Linha do tempo da candidatura: cada e-mail, teste, entrevista e resposta."""

    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, related_name="interactions"
    )
    date = models.DateField("Data", default=timezone.localdate)
    title = models.CharField("Título", max_length=200)
    detail = models.TextField("Detalhe", blank=True)

    class Meta:
        db_table = "pipeline_interaction"
        verbose_name = "interação"
        verbose_name_plural = "interações"
        ordering = ["-date", "-id"]
        indexes = [models.Index(fields=["application", "-date"], name="interaction_app_date_idx")]

    def __str__(self) -> str:
        return f"{self.date} {self.title}"
