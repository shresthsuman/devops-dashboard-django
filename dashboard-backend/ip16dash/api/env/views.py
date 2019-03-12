import json
import datetime
import re
import os
import socket
import sys

from pprint                  import pprint
from django.http             import HttpResponse
from rest_framework.response import Response
from rest_framework.status   import HTTP_200_OK, HTTP_400_BAD_REQUEST
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
    ipSerializer,
)

from ip16dash.models import (
    NoProxy,
)

########################################################
############## API CLASSES #############################
########################################################

######################################################
class IPList(ListAPIView):
    queryset           = NoProxy.objects.all()
    serializer_class   = ipSerializer

######################################################
class IPCreate(CreateAPIView):

    serializer_class   = ipSerializer

    #############################################
    def isValidHostname(self,name):
        if len(name) > 255:
            return False
        allowed = re.compile("(?!-)[A-Z\d\-\_]{1,63}(?<!-)$", re.IGNORECASE)
        name = name.rstrip(".")
        return all(allowed.match(x) for x in name.split("."))

    ##############################################
    def post(self,request,*args,**kwargs):

        hname = request.data['name']
        ip    = request.data['ip']

        # Check if we already have such entry
        res = NoProxy.objects.filter(name=hname).first()
        if res:
            content = {'Results':'Record already exists'}
            return Response(content,status=HTTP_200_OK)

        # Validate hostname format
        if not self.isValidHostname(hname):
            content = {'Results': 'Not valid hostname [%s]' % hname}
            return Response(content,status=HTTP_400_BAD_REQUEST)

        # Do not permit for both ip and name be empty at the same time
        if not ip and not ip:
            content = {'Results': 'Empty ip and hostname'}
            return Response(content, status=HTTP_400_BAD_REQUEST)

        # Store Hostname:ip pair into no_poxy table
        rec = NoProxy(name=hname, ip=ip)
        rec.save()
        content = {'Results': 'Operation sucessfull'}
        return Response(content,status=HTTP_200_OK)

######################################################
class IPDelete(DestroyAPIView):
    queryset           = NoProxy.objects.all()
    serializer_class   = ipSerializer
