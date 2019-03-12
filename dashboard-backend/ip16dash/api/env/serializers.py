from rest_framework.serializers import (
    CharField,
    ModelSerializer,
    ValidationError
)

from ip16dash.models import (
    NoProxy,
)

######################################################
class ipSerializer(ModelSerializer):
    class Meta:
        model = NoProxy
        fields = '__all__'
