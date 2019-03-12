#!/usr/bin/env python

import configparser
import django
import json
import logging
import os
import sys

from pprint import pprint

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append('../../../')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dashboard.settings")
django.setup()

from jsonfield       import JSONField
from dataLogger      import initLog
from ip16dash.models import (
    Build,
    BuildJob,
    BuildNode,
    BuildStage,
    Instances,
    NoProxy,
    Remote,
    RemoteCmd,
)

####################################################
########### GLOBAL VARIABLES DEFENITIONS ###########
####################################################
DMCONF = '/app/ip16dash/datamanager/jenkins/dm.conf'

config = configparser.ConfigParser()
config.read(DMCONF)

LOGNAME  = config.get('config','LOGNAME_JENKINS_SQL').replace("'","")
LOGLEVEL = config.get('config','LOGLEVEL_JENKINS_SQL').replace("'","")
LOGFILE  = config.get('config','LOGFILE_JENKINS_SQL').replace("'","")
LOGDIR   = config.get('config','LOGDIR').replace("'","")

######################################################################
################ CLASS DJANGO SQL ####################################
######################################################################

class ConnectorJenkinsDjangoSQL:

    #############################################################
    def __init__(self,logdir=LOGDIR, logfile=LOGFILE, loglevel=LOGLEVEL, logname=LOGNAME):

        # If loglevel is supplied on environment level overwrite program supplied
        # value with environment
        self.logdir = logdir
        self.logfile = logfile
        self.loglevel = loglevel
        self.logname = logname

        loglevel = eval('logging.' + os.getenv('LOGLEVEL', loglevel))
        self.log = initLog(logdir, logfile, loglevel, logname)

    ##############################################################
    def getNoProxyIPsLst(self):

        '''Gets NoProxy IP/Name data'''

        ips_lst = list()

        no_proxy_res = NoProxy.objects.values('name','ip')
        for ip in no_proxy_res:
            ips_lst.append(ip)

        return ips_lst

    ##############################################################
    def deleteRCMDrecord(self,bid):

        '''Deletes pending user input record'''
        inst = RemoteCmd.objects.filter(build_id=bid)
        inst.delete()

    ##############################################################
    def isRemCMDExists(self,bid):

        '''Shows if relevant remote command exists'''
        res = RemoteCmd.objects.filter(build_id=bid)
        if res:
            return True
        return False

    ##############################################################
    def uploadNewRemoteCMD(self,bid,cmd,cid):

        '''
            Creates new Remote CMD record
            Remote CMD data is uploaded as JSON object
        '''

        self.log.debug("Uploading data for [%s] build" % bid)

        #Convert cmd data into JSON object
        jcmd = json.dumps(cmd)

        #Get collector id for this job
        jres = Remote.objects.get(id=cid)

        def_dict = {
            'build_id' : bid,
            'rcmd'     : jcmd,
            'remote_id': jres
        }

        #Create or update prepared data into DB
        res = RemoteCmd.objects.update_or_create(build_id=bid,defaults=def_dict)

    ##############################################################
    def getConnectorConfig(self,collector_id):

        '''
            Get collector data related to collector id from Remote table
            return collectors data in list format or raise exception if no record was found
        '''

        #Get connector parameters from Remotes table
        res = Remote.objects.values_list('url', 'project', 'type', 'username', 'password','pattern').filter(id=collector_id).first()

        #Raise exception if no results was found
        if not res:
            raise ValueError("Wrong collector id!!! No records for [%s] id !!!" % collector_id)

        return res

    ##############################################################
    def setConnectorConfig(self,data):

        '''Sets new collector in the Remotes collecotr table'''
        res = Remote.objects.get_or_create(**data)
        return res[1]

    ##############################################################
    def getInstanceState(self,iname,colid):

        '''Get previously stored instance state'''

        res = Instances.objects.filter(name=iname, job_id=colid).first()
        if not res:
            return None
        return res.status

    ##############################################################
    def setInstanceState(self,iname,colid,status):

        '''Set new/update instance state'''

        res = Instances.objects.filter(name=iname, job_id=colid).first()

        if not res:
            # New instane. Create it.
            rec = Instances(name=iname, job_id=colid, status=status)
            rec.save()
        else:
            # Exisintg instance. Update it
            data = {
                'name'  : iname,
                'job_id': colid,
                'status': status
            }
            Instances.objects.filter(name=iname, job_id=colid).update(**data)

    ##############################################################
    def getJobID(self,job_name,collector_id,par_name=None):

        '''
            Get job ID related to given collector id from BuildJob table
            If no exising record found then create  new record
            return found/created job id
        '''

        if par_name:
            job_name = "%s:%s" % (par_name, job_name)

        res = BuildJob.objects.filter(name=job_name).first()

        if not res:

            #No record was found then create new record and return it's id
            rec = BuildJob(name=job_name,collector_id=collector_id)
            rec.save()
            return rec.id

        return res.id

    ##############################################################
    def uploadData2Table(self,tbl_obj,data,check_dict):

        '''
            Receives : table object and data dictionary
            Results  : if such record do not exitst in related table than create it
                       if such record exists update it with new data
        '''

        #Generate data string to use in debug messages
        jdata =  ' '.join('{}={}'.format(key,val) for key,val in data.items())

        #First see if we already have such record. This wil define whether we create or update
        rec = tbl_obj.objects.filter(**check_dict).first()

        if rec:

            #Previous record exists... Need to update
            id = rec.id
            self.log.debug("Updating existing [%s] record with data [%s]" % (rec.id,jdata))
            tbl_obj.objects.filter(id=rec.id).update(**data)

        else:

            #New record ... Need to create it
            self.log.debug("Creating new record with data [%s]" % jdata)
            obj = tbl_obj.objects.get_or_create(**data)
            id = obj[0].id

        #Return record id
        return id
