import json
import datetime
import re
import os
import sys

from django.http import HttpResponse
from rest_framework            import status
from rest_framework.views      import APIView
from rest_framework.generics   import (
   ListAPIView,
   CreateAPIView,
   DestroyAPIView,
   RetrieveAPIView,
   UpdateAPIView,
)

from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAdminUser,
    IsAuthenticatedOrReadOnly,
)

from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.status   import HTTP_200_OK, HTTP_400_BAD_REQUEST
#from rest_framework.views    import APIView

from rest_framework.response   import Response
from rest_framework.decorators import api_view
from rest_framework.parsers    import JSONParser
from rest_framework.renderers  import JSONRenderer
from django.db                 import connection

from .serializers              import (
    JiraSerializer,
)

from ip16dash.models           import (
    Build,
    BuildJob,
    Remote,
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

from pprint import pprint
from django.contrib.auth import get_user_model
User = get_user_model()

import django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append('/app/ip16dash/datamanager/jira')
sys.path.append('/app/ip16dash/datamanager/jenkins')

from ip16dash.datamanager.jira.dataManagerJira    import DataManagerJira
from ip16dash.datamanager.jenkins.dataManagerJenkins import DataManagerJenkins

##############################
#### JIRA Collecotr views ####
##############################

#################################################
class JiraCollectorList(ListAPIView):
    queryset = JiraIssue.objects.all().select_related("aggregate").select_related("assigne").select_related("components").select_related("creator").select_related("epic").select_related("parent").select_related("project").select_related("sprint").select_related("creator")
    serializer_class = JiraSerializer

##################################################
class JiraCollectorIssue(APIView):

    serializer_class = JiraSerializer

    #############################################
    def get(self,request,*args,**kwargs):

        issue  = kwargs['issue']
        record = JiraIssue.objects.filter(issue_key=issue).select_related("aggregate").select_related("assigne").select_related("components").select_related("creator").select_related("epic").select_related("parent").select_related("project").select_related("sprint").select_related("creator")

        serializer = JiraSerializer(record[0])
        return Response(serializer.data)

###################################################
class JiraAggregations(APIView):

    serializer_class = JiraSerializer

    def get(self,request,*args,**kwargs):
        serializer = JiraSerializer
        issue = kwargs['issue']
        res = {'pipeid' : None}
        bdobj = Build.objects.all()
        for iss in bdobj:
            if iss.comments:
                if issue in iss.comments:
                   res['pipeid'] = iss.id
                   break
        return Response(res)

###################################################
class JiraAggregationsList(APIView):

    serializer_class = JiraSerializer

    def get(self,request,*args,**kwargs):
        serializer = JiraSerializer
        res = dict()
        bdobj = Build.objects.all()
        for iss in bdobj:
            if iss.comments:
                res[iss.id] = iss.comments

        return Response(res)
