"""Bases compartilhadas por todos os apps de dominio."""

from django.db import models


class TimeStampedModel(models.Model):
    """Carimbo de criacao e atualizacao, no banco, para todo modelo do projeto."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
