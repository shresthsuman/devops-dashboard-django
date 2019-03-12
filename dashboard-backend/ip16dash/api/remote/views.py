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

from rest_framework import permissions
from rest_framework.response   import Response
from rest_framework.status     import HTTP_200_OK, HTTP_400_BAD_REQUEST
#from rest_framework.views     import APIView

from rest_framework.response   import Response
from rest_framework.decorators import api_view
from rest_framework.parsers    import JSONParser
from rest_framework.renderers  import JSONRenderer
from django.db                 import connection

from .serializers import (
    RemoteSerializer,
    RemoteDetailSerializer,
    RemoteEditSerializer,
    RemoteSerializerRun,
)

from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAdminUser,
    IsAuthenticatedOrReadOnly,
)

from ip16dash.models import (
    Remote,
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

########################################################
############## API CLASSES #############################
########################################################

############################################
class RemoteCollectorRun(RetrieveAPIView):

    queryset = Remote.objects.all()
    serializer_class = RemoteSerializerRun

    def get(self,request,pk,**kwargs):

        types = Remote.objects.values_list('type').get(id=pk)[0]
        logdir_jira    = '/app/ip16dash/datamanager/jira'
        logdir_jenkins = '/app/ip16dash/datamanager/jenkins'

        if re.match('[Jj]ira',types):
             obj = DataManagerJira(pk,logdir_jira)
             obj.dataProcessJiraData() 
        elif re.match('[Jj]enkins',types):
             obj = DataManagerJenkins(pk,True,logdir_jenkins)
             obj.dataProcessJenkinsData()
        else:
             print("ERROR : Unrecognized remote")
             sys.exit()
  
        return self.retrieve(request, pk, **kwargs)

#################################
#### REMOTE Collectors view #####
#################################

###########################################
#Remote collector show all data
class RemoteCollectorList(ListAPIView):
    queryset = Remote.objects.all()
    serializer_class = RemoteSerializer

###########################################
class RemoteCollectorCreate(CreateAPIView):
    queryset = Remote.objects.all()
    serializer_class = RemoteEditSerializer

############################################
class RemoteCollectorDetail(RetrieveAPIView):
    queryset = Remote.objects.all()
    serializer_class = RemoteDetailSerializer

############################################
class RemoteCollectorDelete(DestroyAPIView):
    queryset = Remote.objects.all()
    serializer_class = RemoteDetailSerializer

############################################
class RemoteCollectorUpdate(UpdateAPIView):
    queryset = Remote.objects.all()
    serializer_class = RemoteEditSerializer
