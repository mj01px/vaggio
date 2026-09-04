"""Serializer do historico de coletas (somente leitura)."""

from rest_framework import serializers

from .models import CollectionRun


class CollectionRunSerializer(serializers.ModelSerializer):
    source_display = serializers.CharField(source="get_source_display", read_only=True)
    duration_seconds = serializers.FloatField(read_only=True)

    class Meta:
        model = CollectionRun
        fields = [
            "id",
            "source",
            "source_display",
            "started_at",
            "finished_at",
            "duration_seconds",
            "found_count",
            "new_count",
            "error",
        ]
        read_only_fields = fields
