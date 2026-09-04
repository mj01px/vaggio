"""Regras do funil que nao pertencem a uma view.

Entrar no funil e mudar de status gravam interacao. Deixar isso na view faria
o admin e o comando repetirem a regra (ou esquecerem dela).
"""

from django.db import transaction
from django.utils import timezone

from apps.jobs.models import Job

from .models import Application, ApplicationStatus, Interaction


@transaction.atomic
def enter_pipeline(job: Job) -> tuple[Application, bool]:
    """Coloca a vaga no funil. Devolve (candidatura, criada agora?)."""
    application, created = Application.objects.get_or_create(
        job=job, defaults={"status": ApplicationStatus.INTEREST}
    )
    if created:
        Interaction.objects.create(application=application, title="Entrou no funil")
    return application, created


@transaction.atomic
def change_status(application: Application, previous_status: str) -> Application:
    """Aplica os efeitos de uma mudanca de status ja gravada no objeto.

    Carimba a data de aplicacao na primeira vez que a candidatura chega em
    "Aplicada" e registra a transicao na linha do tempo.
    """
    if application.status == previous_status:
        return application

    if application.status == ApplicationStatus.APPLIED and not application.applied_on:
        application.applied_on = timezone.localdate()
        application.save(update_fields=["applied_on", "updated_at"])

    Interaction.objects.create(
        application=application,
        title=f"{ApplicationStatus(previous_status).label} -> {application.get_status_display()}",
    )
    return application
