"""Filtros da fila de triagem: busca textual, fonte, score minimo, nivel, idade."""

from datetime import timedelta

import django_filters
from django.db.models import Q
from django.utils import timezone

from .models import Job


class JobFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(method="filter_search", label="busca")
    min_score = django_filters.NumberFilter(field_name="score", lookup_expr="gte")
    max_score = django_filters.NumberFilter(field_name="score", lookup_expr="lte")
    published_within = django_filters.NumberFilter(
        method="filter_published_within", label="publicada nos ultimos N dias"
    )
    published_after = django_filters.DateFilter(
        method="filter_published_after", label="publicada a partir de"
    )
    published_before = django_filters.DateFilter(
        method="filter_published_before", label="publicada ate"
    )

    class Meta:
        model = Job
        fields = ["source", "seniority", "work_mode"]

    def filter_search(self, queryset, name, value):
        value = value.strip()
        if not value:
            return queryset
        return queryset.filter(
            Q(title__icontains=value)
            | Q(company__icontains=value)
            | Q(description__icontains=value)
        )

    def filter_published_within(self, queryset, name, value):
        """Janela de recencia, em dias.

        Cai para `created_at` quando a vaga nao tem data de publicacao, que e o
        caso do cadastro manual: uma vaga que voce cadastrou hoje precisa
        aparecer no filtro "ultimos 7 dias", e sem esse fallback ela sumiria
        justamente da janela mais usada.
        """
        try:
            dias = int(value)
        except (TypeError, ValueError):
            return queryset
        if dias <= 0:
            return queryset

        limite = timezone.now() - timedelta(days=dias)
        return queryset.filter(
            Q(published_at__gte=limite)
            | Q(published_at__isnull=True, created_at__gte=limite)
        )

    def filter_published_after(self, queryset, name, value):
        """A partir do inicio do dia escolhido.

        Mesmo fallback do `published_within`: vaga sem data de publicacao, como
        a do cadastro manual, e comparada pela data em que entrou.
        """
        if not value:
            return queryset
        return queryset.filter(
            Q(published_at__date__gte=value)
            | Q(published_at__isnull=True, created_at__date__gte=value)
        )

    def filter_published_before(self, queryset, name, value):
        """Ate o fim do dia escolhido.

        `__date__lte` e nao `__lt` no instante: quem escolhe 01/09 espera ver a
        vaga publicada as 18h de 01/09, e nao so as de antes da meia-noite.
        """
        if not value:
            return queryset
        return queryset.filter(
            Q(published_at__date__lte=value)
            | Q(published_at__isnull=True, created_at__date__lte=value)
        )
