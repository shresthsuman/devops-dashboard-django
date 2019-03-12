import datetime
import json
import re
import os
import sys
import requests

from pprint import pprint

from django.http             import HttpResponse

from rest_framework.response import Response
from rest_framework import status
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

from .serializers              import (
    jenexecSerializer,
)

import django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ip16dash.models import (
    RemoteCmd,
)

########################################################
############## API CLASSES #############################
########################################################

class JenkinsGetCmdLst(ListAPIView):
    #permission_classes = [AllowAny]
    queryset = RemoteCmd.objects.all()
    serializer_class = jenexecSerializer

#####################################################
class JenkinsExec(APIView):

    #permission_classes = [AllowAny]
    serializer_class = jenexecSerializer

    ################################################
    def runPOSTQuery(self,cmd,recobj):

        #We get appropriate authorative users from record object
        user    = recobj.remote_id.username
        pswd    = recobj.remote_id.password
        url     = recobj.remote_id.url
        proj    = recobj.remote_id.project

        urlpath = "%s/job/%s/%s/input/%s/%s" % (url,proj,cmd['bid'],cmd['id'],cmd['cmd'])
        urlcrum = "%s/crumbIssuer/api/xml?xpath=concat(//crumbRequestField,\":\",//crumb)" % url

        #First we need to get a valid CRUM token to use in command request
        hdrs = {'Connection': 'close'}

        CRUM = requests.get(urlcrum,auth=(user,pswd),headers=hdrs).text
        (hdr_name,hdr_val) = CRUM.split(':')

        #Run url request which will essentialy execute appropariate command supplied in
        #urlpath on Jenkins
        try:
            hdrs[hdr_name] = hdr_val
            response = requests.post(urlpath,auth=(user,pswd),headers=hdrs)
        except requests.ConnectionError as e:
             raise ValueError("Failed to to [%s] url with rc [%s] and reason [%s]" % (urlpath,response.status_code,response.reason))


    ################################################
    def removeCMDRecord(self,bid):

        #Remove executed command relative record from DB. The Jenkins state had changed anyway
        #and we can not re-runc already executed command
        rec = RemoteCmd.objects.filter(build_id=bid)
        if rec:
            rec.delete()

    ################################################
    def post(self,request,*args,**kwargs):

        kwcmd    = kwargs['cmd']
        buildid  = kwargs['buildid']
        record   = RemoteCmd.objects.filter(build_id=buildid)

        # See if supplied parameters are actual and we have related record in DB
        # if no record found means pipeline instance state was changed by user
        if record:
            record = record[0]
        else:
            #No record for supplied nodeid
            content = {'Results': 'No record found for [%s]' % kwcmd}
            return Response(content, status=status.HTTP_404_NOT_FOUND)

        jasoncmd = record.rcmd
        dictcmd  = json.loads(jasoncmd)

        # If supplied command is in commands list
        if not [ x for x in dictcmd['cmd'] if kwcmd in x ]:
            #Unrecofnized command
            content = {'Results': 'Supplied command [%s] is not defined' % kwcmd}
            return Response(content, status=status.HTTP_404_NOT_FOUND)

        #We currently support only abort or proceed options. If inputs parameter
        #holds data then we also do not support such configuration
        if dictcmd['inputs']:
            content = {'Results': 'Not supported operation'}
            return Response(content, status=status.HTTP_200_OK)

        #Ok we are ready to send command URL to jenkins
        if kwcmd == 'proceed':
            kwcmd = 'proceedEmpty'
        cmd_data = {
            'cmd'     : kwcmd,
            'bid'     : buildid,
            'id'      : dictcmd['id'],
        }
        self.runPOSTQuery(cmd_data,record)

        #After sending command URL we need to clear command entry from the database
        #the state of the pipeline is changed upon command execution anyway
        self.removeCMDRecord(buildid)

        content = {'Results': 'Operation completed succesfully'}
        return Response(content, status=status.HTTP_200_OK)
