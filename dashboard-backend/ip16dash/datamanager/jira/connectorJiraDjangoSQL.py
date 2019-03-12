#!/usr/bin/env python

#####################################################
import configparser
import django
import logging
import os
import sys

from pprint         import pprint

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append('../../../')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dashboard.settings")
django.setup()

from dataLogger      import initLog
from ip16dash.models import (
    JiraAggregate,
    JiraComponents,
    JiraEpic,
    JiraIssue,
    JiraParent,
    JiraPerson,
    JiraProject,
    JiraRemote,
    JiraSprint,
    JiraStatus,
    NoProxy,
    Remote,
)

####################################################
########### GLOBAL VARIABLES DEFENITIONS ###########
####################################################
DMCONF = '/app/ip16dash/datamanager/jira/dm.conf'

config = configparser.ConfigParser()
config.read(DMCONF)

LOGNAME  = config.get('config','LOGNAME_JIRA_SQL').replace("'","")
LOGLEVEL = config.get('config','LOGLEVEL_JIRA_SQL').replace("'","")
LOGFILE  = config.get('config','LOGFILE_JIRA_SQL').replace("'","")
LOGDIR   = config.get('config','LOGDIR').replace("'","")

######################################################################
################ CLASS DJANGO SQL ####################################
######################################################################

class ConnectorJiraDjangoSQL:

    #############################################################
    def __init__(self,logdir=LOGDIR, logfile=LOGFILE, loglevel=LOGLEVEL, logname=LOGNAME):

        # If loglevel is supplied on environment level overwrite program supplied
        # value with environment
        self.logdir   = logdir
        self.logfile  = logfile
        self.loglevel = loglevel
        self.logname  = logname

        loglevel = eval('logging.' + os.getenv('LOGLEVEL', loglevel))
        self.log = initLog(logdir, logfile, loglevel, logname)

    ##############################################################
    def getConnectorConfig(self,collector_id):

        '''
            Get collector data related to collector id from Remote table
            return collectors data in list format or raise exception if no record was found
        '''

        #Get connector parameters from Remotes table
        res = Remote.objects.values_list('url', 'project', 'type', 'username', 'password','rproxyuser','rproxypass','proxy','auth','apibase').filter(id=collector_id).first()

        #Raise exception if no results was found
        if not res:
            raise ValueError("Wrong collector id!!! No records for [%s] id !!!" % collector_id)

        return res

    ##############################################################
    def getRemoteID(self,job_name,collector_id):

        '''
            Get jira remote ID related to given collector id from JiraRemote table
            If no exising record found then create  new record
            return found/created job id
        '''

        res = JiraRemote.objects.filter(name=job_name).first()

        if not res:
            #No record was found then create new record and return it's id
            rec = JiraRemote(name=job_name,collector_id=collector_id)
            rec.save()
            return rec

        return res

    ##############################################################
    def getNoProxyIPsLst(self):

        ips_lst = list()

        no_proxy_res = NoProxy.objects.values_list('ip')
        for ip in no_proxy_res:
            ips_lst.append(ip[0])

        return ips_lst

    ##############################################################
    def getIssueFkIDs(self,issueid):

        '''Get if exists all foreign keys ids for issue with id'''
        return JiraIssue.objects.values_list('id','aggregate_id','assigne_id','components_id','creator_id','epic_id','parent_id','project_id','sprint_id','status_id').filter(issue_id=issueid).first()

    ###############################################################
    def getIssueFK(self,isskey):

        '''
            Check if issue already exists in database
            Return dictionary of foreign keys to issue sub-tables to know which
            records in what tables we should update
        '''

        # This check we always do against main JiraIssue table
        fk_dict = JiraIssue.objects.values('id','aggregate_id','assigne_id','components_id','creator_id','epic_id','parent_id','project_id','sprint_id','status_id').filter(issue_key=isskey).first()

        self.log.debug("No previous records for issue [%s] was found... Create new record mode" % isskey)

        if not fk_dict:
            fk_dict = {
                'id'           : None,
                'aggregate_id' : None,
                'assigne_id'   : None,
                'components_id': None,
                'creator_id'   : None,
                'epic_id'      : None,
                'parent_id'    : None,
                'project_id'   : None,
                'sprint_id'    : None,
                'status_id'    : None,
            }

        return fk_dict

    ##############################################################
    def uploadPerson2Tbl(self,tbl_obj,data,mode):
        '''
            Updates person table. Persons could be creater or assignee as well as combination of
            these two. Also on person can be asssosiated with many issues in both roles
        '''

        self.log.debug("Updating person table in [%s] mode" % mode)

        #Check if such person already exists and return it's id otherwise create new person
        obj = tbl_obj.objects.get_or_create(**data)
        return obj[0].id

    ###############################################################
    def uploadIssue2Tbl(self,tbl_obj,data,fk,tbl_name):

        '''
            Upload supplied table object with data
            tbl_obj  - django table object
            data     - dictionary(record) data to push into table
            fk       - foreign key from issue table to use if we update record
            tbl_name - current table name. Used for debug message

            return created/updated record id
        '''

        #Need to separate update vs create scenarios. if FK was supplied then the
        #previous issue data had been found and we need to update existing record
        if fk:

            #Previous record found we are in update record scenario
            self.log.debug("Updating record [%s] in [%s] table" % (fk,tbl_name))
            tbl_obj.objects.filter(id=fk).update(**data)
            id = fk
        else:

            #No previous record was found in issue table. we use get_or_create function here
            #to cover for case when this specific record was previously created but was not
            #written in issues main table due to possible crash. Upload operation is not atomic.

            self.log.debug("Creating new record in [%s] table" % (tbl_name))
            rec = tbl_obj(**data)
            rec.save()
            id = rec.id

        return id
