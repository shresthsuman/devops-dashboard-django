from rest_framework.serializers import (
    CharField,
    ModelSerializer,
    ValidationError
)

from django.contrib.auth import get_user_model
User = get_user_model()

from ip16dash.models import (
    JiraRemote,
    JiraIssue,
    JiraAggregate,
    JiraComponents,
    JiraEpic,
    JiraParent,
    JiraPerson,
    JiraProject,
    JiraSprint,
    JiraStatus,
)

######################################################
class JiraAggregateSerializer(ModelSerializer):
    class Meta:
        model = JiraAggregate
        fields = '__all__'

######################################################
class JiraAssigneSerializer(ModelSerializer):
    class Meta:
        model = JiraPerson
        fields = '__all__'

######################################################
class JiraComponentSerializer(ModelSerializer):
    class Meta:
        model = JiraComponents
        fields = '__all__'

######################################################
class JiraCreatorSerializer(ModelSerializer):
    class Meta:
        model = JiraPerson
        fields = '__all__'

######################################################
class JiraEpicSerializer(ModelSerializer):
    class Meta:
        model = JiraEpic
        fields = '__all__'

######################################################
class JiraParentSerializer(ModelSerializer):
    class Meta:
        model = JiraParent
        fields = '__all__'

######################################################
class JiraProjectSerializer(ModelSerializer):
    class Meta:
        model = JiraProject
        fields = '__all__'

######################################################
class JiraSprintSerializer(ModelSerializer):
    class Meta:
        model = JiraSprint
        fields = '__all__'

######################################################
class JiraStatusSerializer(ModelSerializer):
    class Meta:
        model = JiraStatus
        fields = '__all__'

######################################################
class JiraSerializer(ModelSerializer):

    aggr    = JiraAggregateSerializer(read_only=True)
    assigne = JiraAssigneSerializer(read_only=True)
    compnt  = JiraComponentSerializer(read_only=True)
    creator = JiraCreatorSerializer(read_only=True)
    epic    = JiraEpicSerializer(read_only=True)
    parent  = JiraParentSerializer(read_only=True)
    project = JiraProjectSerializer(read_only=True)
    sprint  = JiraSprintSerializer(read_only=True)
    status  = JiraStatusSerializer(read_only=True)

    class Meta:
        model = JiraIssue
        fields = [
           'issue_id',
           'issue_key',
           'issue_description',
           'issue_priority',
           'issue_progress',
           'issue_subtsks',
           'issue_summary',
           'issue_types',
           'issue_created',
           'issue_resdate',
           'issue_url',
           'aggr',
           'assigne',
           'compnt',
           'creator',
           'epic',
           'parent',
           'project',
           'sprint',
           'status'
        ]
