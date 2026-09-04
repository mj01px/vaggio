"""Operacoes de vaga que passam por varios registros de uma vez."""

from .models import Job
from .scoring import classify


def rescore_all(batch_size: int = 200) -> tuple[int, int]:
    """Repontua todas as vagas com as regras atuais.

    Devolve (quantas foram avaliadas, quantas mudaram). Um bulk_update so, em
    vez de um UPDATE por vaga.
    """
    jobs = list(Job.objects.all())
    changed = 0

    for job in jobs:
        result = classify(job.title, job.description, job.company, job.location)
        if (
            job.score != result.score
            or job.seniority != result.seniority
            or job.work_mode != result.work_mode
        ):
            changed += 1
        job.score = result.score
        job.tags = result.tags
        job.seniority = result.seniority
        job.work_mode = result.work_mode

    Job.objects.bulk_update(
        jobs, ["score", "tags", "seniority", "work_mode"], batch_size=batch_size
    )
    return len(jobs), changed
