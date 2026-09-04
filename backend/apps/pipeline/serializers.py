"""Serializers do funil: cartao do board, escrita e linha do tempo."""

from rest_framework import serializers

from apps.jobs.models import Job
from apps.jobs.serializers import JobSerializer

from .models import Application, Interaction


class InteractionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interaction
        fields = ["id", "date", "title", "detail", "created_at"]
        read_only_fields = ["id", "created_at"]


class ApplicationSerializer(serializers.ModelSerializer):
    job = JobSerializer(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    days_idle = serializers.IntegerField(read_only=True)

    class Meta:
        model = Application
        fields = [
            "id",
            "job",
            "status",
            "status_display",
            "priority",
            "applied_on",
            "next_step",
            "next_step_on",
            "contact",
            "has_referral",
            "notes",
            "is_overdue",
            "days_idle",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ApplicationCreateSerializer(serializers.Serializer):
    """Entrada no funil: so precisa dizer qual vaga."""

    job = serializers.PrimaryKeyRelatedField(queryset=Job.objects.all())


class ApplicationUpdateSerializer(serializers.ModelSerializer):
    """Tudo que se edita numa candidatura, incluindo o status pelo board."""

    class Meta:
        model = Application
        fields = [
            "status",
            "priority",
            "applied_on",
            "next_step",
            "next_step_on",
            "contact",
            "has_referral",
            "notes",
        ]

    def to_representation(self, instance):
        return ApplicationSerializer(instance, context=self.context).data
