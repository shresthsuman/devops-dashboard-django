from rest_framework.serializers import (
    CharField,
    ModelSerializer,
    ValidationError
)

from django.db.models    import Q
from django.contrib.auth import get_user_model
User = get_user_model()

from ip16dash.models import (
    Remote,
)

######################################################
class RemoteSerializerRun(ModelSerializer):
    class Meta:
        model = Remote
        fields = [
		'id',
		'type'
	]

class RemoteSerializer(ModelSerializer):
    class Meta:
        model = Remote
        fields = [
            'id',
            'name',
            'url',
            'type',
            'project',
            'username',
            'next_run',
            'enabled',
            'apibase',
            'isprod'
        ]
class RemoteDetailSerializer(ModelSerializer):
    class Meta:
        model = Remote
        fields = '__all__'

class RemoteEditSerializer(ModelSerializer):
    class Meta:
        model = Remote
        fields = [
            'name',
            'url',
            'type',
            'project',
            'username',
            'password',
            'next_run',
            'rproxyuser',
            'rproxypass',
            'proxy',
            'auth',
            'apibase',
            'enabled',
            'pattern',
            'isprod'
        ]
