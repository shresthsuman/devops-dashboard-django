import datetime
import json
import re
import os
import sys
import requests

from pprint                  import pprint
from django.http             import HttpResponse
from rest_framework.response import Response
from rest_framework          import status
from rest_framework.views    import APIView
from rest_framework.generics import (
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

from .serializers import (
    projSerializer,
)

from ip16dash.models import (
    Projects,
)

########################################################
############## API CLASSES #############################
########################################################

###############################################
class ProjectsList(ListAPIView):
    queryset = Projects.objects.all()
    serializer_class = projSerializer

###############################################
class ProjectsCreate(CreateAPIView):
    queryset = Projects.objects.all()
    serializer_class = projSerializer

    # def post(self,request,*args,**kwargs):
    #     pprint(requests.data)
    #     return HttpResponse("Helloo")

###############################################
class ProjectsUpdate(UpdateAPIView):
    queryset = Projects.objects.all()
    serializer_class = projSerializer

###############################################
class ProjectsDelete(DestroyAPIView):
    queryset = Projects.objects.all()
    serializer_class = projSerializer