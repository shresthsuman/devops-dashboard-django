import json
import datetime
import re
import os
import sys

from django.http               import HttpResponse
from django.core.exceptions    import ObjectDoesNotExist
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
    End2EndSerializer,
    MultiView,
)

from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAdminUser,
    IsAuthenticatedOrReadOnly,
)

from ip16dash.models           import (
    #We need Jira tables for data aggregation
    Build,
    BuildJob,
    Remote,
    Multi,
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

########################################################
################ UTILITY FUNCTIONS #####################
########################################################

################################################
def fetchall2Dict(cursor):
    "Returns all rows from a cursor as a dict"
    desc = cursor.description
    return [dict(zip([col[0] for col in desc], row)) for row in cursor.fetchall()]

#################################################
def runQuery(sql):
    cursor = connection.cursor()
    cursor.execute(sql)
    return fetchall2Dict(cursor)

########################################################
############## API CLASSES #############################
########################################################

##################################################
#Main page view
class MainView(APIView):

    def get(self,request):

        colid = Build.objects

        sql1 = 'SELECT c.name as "Collector", \
                    a.CID, \
                    a.Pipeline, \
                    a.FullName, \
                    a.Started, \
                    a.id, \
                    a.Sequence, \
                    a.Delta, \
                    a.Status \
                    FROM (\
                        SELECT p.collector_id as CID, \
                        p.name as "Pipeline", \
                        b.fullname as "FullName", \
                        b.id as id, \
                        b.started as "Started", \
                        max(b.name) as "Sequence", \
                        (b.duration / b.estimate) as "Delta", \
                        b.result as "Status" \
                        FROM ip16dash_buildjob as p \
                        JOIN  ip16dash_build as b \
                        ON p.id = b.job_id \
                        GROUP BY p.name \
                        ORDER BY b.started ASC)a \
                    JOIN ip16dash_remote as c \
                    WHERE a.CID = c.id \
                    ORDER by a.Status;'

        results = {'broken_pipes': runQuery(sql1)}

        sql2 = 'SELECT c.name as "Collector", \
                    a.CID, \
                    a.Pipeline, \
                    a.FullName, \
                    a.Started, \
                    a.id, \
                    a.Sequence, \
                    a.Delta, \
                    a.Status \
                    FROM (\
                        SELECT p.collector_id as CID, \
                        p.name as "Pipeline", \
                        b.fullname as "FullName", \
                        b.id as id, \
                        b.started as "Started", \
                        max(b.name) as "Sequence", \
                        (b.duration / b.estimate) as "Delta", \
                        b.result as "Status" \
                        FROM ip16dash_buildjob as p \
                        JOIN ip16dash_build as b \
                        ON p.id = b.job_id \
                        GROUP BY p.id \
                        ORDER BY b.duration DESC)a \
                    JOIN ip16dash_remote as c \
                    WHERE a.CID = c.id \
                    AND Status LIKE "success" \
                    ORDER BY Delta DESC;'

        results['delta_pipes'] = runQuery(sql2)

        return Response(results)

##################################################
#Pipelines page view
class PipelinesView(APIView):

    def get(self, request, *args, **kwargs):

        name = kwargs.get('name')

        sql = 'SELECT a.Pipeline, \
                a.Started, \
                a.id, \
                a.Sequence, \
                a.Delta, \
                a.Status \
                FROM (\
                        SELECT p.collector_id as CID, \
                        p.name as "Pipeline", \
                        b.id as id, \
                        max(b.started) as "Started", \
                        b.name as "Sequence", \
                        (b.duration / b.estimate) as "Delta", \
                        b.result as "Status" \
                        FROM ip16dash_buildjob as p \
                        JOIN ip16dash_build as b \
                        ON p.id = b.job_id \
                        GROUP BY p.id \
                        ORDER BY b.duration DESC)a \
                JOIN ip16dash_remote as c \
                WHERE a.CID = c.id \
                AND c.name = "' + name + '";'

        results = {'pipes': runQuery(sql)}

        return Response(results)

################################################################
#JenkinsReleases page view
class JenkinsReleasesView(APIView):

    def get(self, request, *args, **kwargs):

        name = kwargs.get('name')

        sql = 'SELECT b.id as id, \
        			b.name as name, \
        			b.started as started, \
        			b.result as result, \
                    b.fullname, \
        			j.id as jid, \
        			j.name as job \
        			FROM ip16dash_build as b \
        			JOIN ip16dash_buildjob as j \
        			WHERE j.id = b.job_id \
        			AND j.name = "' + name + '" \
        			ORDER BY b.started DESC;'

        results = {'pipes': runQuery(sql)}
        return Response(results)

################################################################
class JenkinsReleasesMultiView(APIView):

    def get(self, request, *args, **kwargs):

        pname = kwargs.get('name')
        bname = kwargs.get('bname')

        name = "%s:%s" % (pname,bname)

        sql = 'SELECT b.id as id, \
        			b.name as name, \
        			b.started as started, \
        			b.result as result, \
                    b.fullname, \
        			j.id as jid, \
        			j.name as job \
        			FROM ip16dash_build as b \
        			JOIN ip16dash_buildjob as j \
        			WHERE j.id = b.job_id \
        			AND j.name = "' + name + '" \
        			ORDER BY b.started DESC;'

        results = {'pipes': runQuery(sql)}
        return Response(results)

################################################################
class End2EndView(APIView):

    ###############################################
    def datetime_handler(self,x):
        if isinstance(x, datetime.datetime):
            return x.isoformat()
        raise TypeError("Unknown type")

    ###############################################
    def generateObj(self,id):

        h = dict()

        bd = Build.objects.get(id=id)

        # Building build level of hash
        h['name'] = bd.name
        h['fullname'] = bd.fullname
        h['duration'] = bd.duration
        h['started'] = bd.started
        h['result'] = bd.result
        h['comments'] = bd.comments
        h['ptype'] = bd.ptype
        h['parent_pipe'] = bd.parent_pipe

        if bd.depdirect:
            h['depdirect']   = bd.depdirect
            h['depinst']     = bd.depinst
            h['deplocation'] = bd.deplocation

        # Builind build_state level of hash
        h['stage'] = list()
        for stage in bd.buildstage_set.all():
            hs = dict()
            hs['name'] = stage.name
            hs['duration'] = stage.duration
            hs['result'] = stage.result

            # Building build node level of hash
            hs['node'] = list()

            for node in stage.buildnode_set.all():
                hn = dict()

                hn['descrpt'] = node.descrpt
                hn['duration'] = node.duration
                hn['progress'] = node.progress
                hn['result'] = node.result

                hs['node'].append(hn)

            h['stage'].append(hs)

        return h

    ###############################################
    def get(self, request, *args, **kwargs):

        id = kwargs.get('id')

        #Get pipelinen instance data
        h = self.generateObj(id)

        #See if we have dependent trigers and add them to result
        if 'depdirect' in h:
            if h['depdirect'] == 'downstream':
                try:
                    pid = Build.objects.get(fullname=h['depinst']).id
                    h2 = self.generateObj(pid)
                    results = {'pipes': h, 'dpipe': h2}

                except ObjectDoesNotExist:
                    results = {'pipes': h, 'dpipe': None}

            elif h['depdirect'] == 'upstream':
                try:
                    pid = Build.objects.get(fullname=h['depinst']).id
                    h2 = self.generateObj(pid)
                    results = {'pipes': h2, 'dpipe': h}
                except ObjectDoesNotExist:
                    results = {'pipes': h, 'dpipe': None}
        else:
            #This is a non triggered case
            results = {'pipes': h,'depnd': None}

        return Response(results)

##################################################
class MultiList(ListAPIView):
    queryset = Multi.objects.all()
    serializer_class = MultiView

##################################################
class MultiDetail(RetrieveAPIView):
    queryset = Multi.objects.all()
    serializer_class = MultiView
    lookup_field = 'name'
