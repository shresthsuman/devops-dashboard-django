from rest_framework.serializers import (
    CharField,
    ModelSerializer,
    ValidationError
)

from django.db.models    import Q
from django.contrib.auth import get_user_model
User = get_user_model()

from ip16dash.models import (
    Build,
    BuildStage,
    BuildNode,
    Multi,
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

#######################################################
class End2EndSerializer(ModelSerializer):
    class Meta:
        model = Build
        fields = '__all__'

#######################################################
class MultiView(ModelSerializer):
    class Meta:
        model = Multi
        fields = '__all__'

