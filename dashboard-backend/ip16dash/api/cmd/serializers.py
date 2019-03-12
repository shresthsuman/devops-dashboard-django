from rest_framework.serializers import (
    CharField,
    ModelSerializer,
    ValidationError
)

from ip16dash.models import (
    RemoteCmd,
)

from django.core.management.base import CommandError

class jenlstSerializer(ModelSerializer):

    d = dict()

    class Meta:
        model = RemoteCmd
        fields = '__all__'

        def get(self):
            return HT

class jenexecSerializer(ModelSerializer):

    class Meta:
        model = RemoteCmd
        fields = '__all__'