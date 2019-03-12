from rest_framework.serializers import (
    CharField,
    ModelSerializer,
    ValidationError,
    JSONField
)

from ip16dash.models import (
    Projects,
)

from django.core.management.base import CommandError

class projSerializer(ModelSerializer):
    data = JSONField()
    class Meta:
        model = Projects
        fields = '__all__'