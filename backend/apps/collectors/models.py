from django.db import models
from django.utils import timezone

from apps.jobs.models import JobSource


class CollectionRun(models.Model):
    """Log de execucao da coleta, por fonte."""

    source = models.CharField("Fonte", max_length=20, choices=JobSource.choices)
    started_at = models.DateTimeField("Início", default=timezone.now)
    finished_at = models.DateTimeField("Fim", null=True, blank=True)
    found_count = models.IntegerField("Encontradas", default=0)
    new_count = models.IntegerField("Novas", default=0)
    error = models.TextField("Erro", blank=True)

    class Meta:
        db_table = "collectors_run"
        verbose_name = "coleta"
        verbose_name_plural = "coletas"
        ordering = ["-started_at"]
        indexes = [models.Index(fields=["source", "-started_at"], name="run_source_started_idx")]

    def __str__(self) -> str:
        return f"{self.source} {self.started_at:%d/%m %H:%M} ({self.new_count} novas)"

    @property
    def duration_seconds(self) -> float | None:
        if not self.finished_at:
            return None
        return (self.finished_at - self.started_at).total_seconds()
