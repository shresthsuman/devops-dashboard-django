#!/usr/bin/env python

#####################################################
import argparse
import configparser
import datetime
import django
import json
import logging
import pytz
import os
import re
import time
import sys
import textwrap

from pprint         import pprint
from dataCollectorJira import JiraDataCollector
from dataLogger        import initLog
from connectorJiraDjangoSQL import ConnectorJiraDjangoSQL
from datetime import timezone
from django.utils import timezone

from django.db import transaction, IntegrityError

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
    Remote,
)

###################################################
CTYPE='[Jj]ira'
DMCONF = '/app/ip16dash/datamanager/jira/dm.conf'

config = configparser.ConfigParser()
config.read(DMCONF)

####################################################
############### LOGGING DEFENITIONS ################
####################################################

LOGNAME  = config.get('config','LOGNAME_JIRA_DM').replace("'","")
LOGLEVEL = config.get('config','LOGLEVEL_JIRA_DM').replace("'","")
LOGFILE  = config.get('config','LOGFILE_JIRA_DM').replace("'","")
LOGDIR   = config.get('config','LOGDIR').replace("'","")

###########################################################
################ UTILI FUNCTIONS ##########################
###########################################################

#################################################
def parseParams() :

    '''Externaly suppllied parameter processor'''

    # Data can be read from database based on collectorID parameter or by supplying
    # relevant data from command line

    parser = argparse.ArgumentParser()

    #Mandatory parameter for database query
    parser.add_argument('-c', '--collectorID', help="Remote collector id to use", required=True)
    args = parser.parse_args()

    return args.collectorID

###########################################################
#################### CLASS PART ###########################
###########################################################
class DataManagerJira:

    #############################################################
    def __init__(self,collector_id,logdir=LOGDIR,logfile=LOGFILE,loglevel=LOGLEVEL,logname=LOGNAME):
        '''Constructor : Initialising Jenkins MYSQL collector
            - logdir       - directory to store log data
            - logfile      - name of log file
            - loglevel     - verbose level of logged data
            - logname      - string indefying this log enteries. Used to destinguish between different loggers
        '''

        # If loglevel is supplied on environment level overwrite program supplied
        # value with environmen
        self.logdir   = logdir
        self.logfile  = logfile
        self.loglevel = loglevel
        self.logname  = logname

        self.collector_id = collector_id

        loglevel = eval('logging.' + os.getenv('LOGLEVEL', loglevel))
        self.log = initLog(logdir,logfile,loglevel,logname)

        # Initiate Django SQL connector
        self.sql = ConnectorJiraDjangoSQL()

        # collector ID is set then get data from Database
        (self.hostname,self.project,self.types,self.username,self.password,self.rproxyuser, self.rproxypass,self.proxy, self.auth, self.apibase) = self.sql.getConnectorConfig(self.collector_id)

        if self.apibase == None:
            self.apibase = ''

        # Check for right collector type - we deal here with Jenkins collectors only
        if not re.match(CTYPE,self.types):
            raise ValueError("Wrong collector type : Collector record with id [%s] is of type [%s] instead of [Jenkins]" % (collector_id, ctype))

        # Now specific issue data colelction in case of database read
        self.issue = None

        # In case wrong collector_id was supplied abort execution
        if self.hostname == None or self.project == None:
            self.log.error("Wrong collector id - [%s] ... Aborting ..." %collector_id)
            sys.exit(1)

    ############################################################
    def generateIssueObject(self,jdata,remid):

        '''
            Generate Issue object to be pushed into appropriate tables
            Return list of dictionaries related to appropriate tables
        '''

        self.log.debug("Generating [%s] issue data structure" % jdata['key'])

        ###########################################
        # Covert dictionary into tables parameters #
        ###########################################

        # Loading ip16dash_jirraissue table params
        iss = dict()
        iss['issue_id']          = jdata['id']
        iss['issue_key']         = jdata['key']
        iss['issue_description'] = jdata['description']
        iss['issue_priority']    = jdata['priority']
        iss['issue_progress']    = jdata['progress']
        iss['issue_summary']     = jdata['summary']
        iss['issue_types']       = jdata['type']
        iss['issue_url']         = jdata['url']
        iss['issue_created']     = jdata['created']
        iss['issue_resdate']     = jdata['resolutiondate']
        iss['remote']            = remid

        # Prepare to store list of subtasks id's
        if jdata['subtasks']:
            iss['issue_subtsks'] = 'None'
        else:
            sublst = list()
            for task in jdata['subtasks']:
                sublst.append(task['id'])
            iss['issue_subtsks'] = ':'.join(sublst)

        # Do some description text cleanup from possible inserted quat's and backline and other staff
        if iss['issue_description'] != None:
            iss['issue_description'] = iss['issue_description'].replace("\r", "")
            iss['issue_description'] = iss['issue_description'].replace("\n", " ")

        # Do some summury text cleanup from possible inserted quat's and backline and other staff
        if iss['issue_summary'] != None:
            iss['issue_summary'] = iss['issue_summary'].replace("\r", "")
            iss['issue_summary'] = iss['issue_summary'].replace("\n", " ")

        # Loading ip16dash_jiraaggregate table params
        agg = dict()
        agg['progress'] = jdata['aggregate']['progress']
        agg['timeestimate'] = jdata['aggregate']['timeestimate']
        agg['timeoriginalestimate'] = jdata['aggregate']['timeoriginalestimate']
        agg['timespent'] = jdata['aggregate']['timespent']

        # Loading ip16dash_jiraperson table params for assignee
        # NOTE : If assigne is not set keys name will be different from set case
        ass = dict()
        if 'key' in jdata['assignee']:
            ass['pe_dname'] = jdata['assignee']['key']
            ass['pe_rname'] = jdata['assignee']['name']
        else:
            ass['pe_dname'] = jdata['assignee']['name']
            ass['pe_rname'] = jdata['assignee']['rname']
        ass['pe_email'] = jdata['assignee']['email']

        # Loading ip16dash_jiracomponents table params
        comp = dict()
        comp['name'] = jdata['components']['name']
        comp['description'] = jdata['components']['description']

        # Loading ip16dash_jiraperson table params for creator
        crt = dict()
        crt['pe_dname'] = jdata['creator']['dname']
        crt['pe_email'] = jdata['creator']['email'][0]
        crt['pe_rname'] = jdata['creator']['rname']

        # Loading ip16dash_jiraepic table params
        epc = dict()
        epc['name'] = jdata['epic']

        # Loading ip16dash_jiraparent table params
        pa = dict()
        pa['pa_key'] = jdata['parent']['key']
        pa['pa_url'] = jdata['parent']['url']

        # Loading ip16dash_jiraproject table params
        pr = dict()
        pr['pr_key']  = jdata['project']['key']
        pr['pr_name'] = jdata['project']['name']
        pr['pr_url']  = jdata['project']['url']

        # Loading ip16dash_jirasprint table params
        sp = dict()
        sp['state']        = jdata['sprint']['state']
        sp['name']         = jdata['sprint']['name']
        sp['startDate']    = jdata['sprint']['startDate']
        sp['endDate']      = jdata['sprint']['endDate']
        sp['completeDate'] = jdata['sprint']['completeDate']

        for i in ('completeDate','endDate','completeDate'):
            if sp[i] == '<null>':
                self.log.debug("In sprint field [%s] change null to None" % i)
                sp[i] = None

        # Loading ip16dash_jirastatus table params
        st = dict()
        st['name'] = jdata['status']['name']
        st['description'] = jdata['status']['description']

        return iss,agg,ass,comp,epc,crt,pa,pr,sp,st

    ############################################################
    @transaction.atomic
    def uploadIssue2DBdo(self,iss,agg,ass,comp,epc,crt,pa,pr,sp,st,fks):

        '''
            Upload prepared data into related tables. Based on existence of fks
            variable we choosed between create new and update existing issue records
        '''

        self.log.debug("Uploading [%s] issue data objects into appropriate tables" % iss['issue_key'])

        # 1. Update ip16dash_jiraaggregate table and store created record id in issue dictionary
        assid = self.sql.uploadIssue2Tbl(JiraAggregate,agg,fks['aggregate_id'],'JiraAggregate')
        iss['aggregate_id'] = assid

        # 2. Update ip16dash_jiracomponents table and store created record id in issue dictionary
        comid = self.sql.uploadIssue2Tbl(JiraComponents, comp, fks['components_id'], 'JiraComponents')
        iss['components_id'] = comid

        # 3. Update ip16dash_jiraepic table and store created record id in issue dictionary
        epid = self.sql.uploadIssue2Tbl(JiraEpic, epc, fks['epic_id'], 'JiraEpic')
        iss['epic_id'] = epid

        # 4. Update ip16dash_jiraparent table and store created record id in issue dictionary
        paid = self.sql.uploadIssue2Tbl(JiraParent, pa, fks['parent_id'], 'JiraParent')
        iss['parent_id'] = paid

        # 5. Update ip16dash_jiraproject table and store created record id in issue dictionary
        prid = self.sql.uploadIssue2Tbl(JiraProject, pr, fks['project_id'], 'JiraProject')
        iss['project_id'] = prid

        # 6. Update ip16dash_jirasprint table and store created record id in issue dictionary
        sprid = self.sql.uploadIssue2Tbl(JiraSprint, sp, fks['sprint_id'], 'JiraSprint')
        iss['sprint_id'] = sprid

        # 7. Update ip16dash_jirastatus table and store created record id in issue dictionary
        stid = self.sql.uploadIssue2Tbl(JiraStatus, st, fks['status_id'], 'JiraStatus')
        iss['status_id'] = stid

        # 8. Update ip16dash_jiraperson table and store created record id in issue dictionary
        assid = self.sql.uploadPerson2Tbl(JiraPerson, ass,'assigne')
        iss['assigne_id'] = assid

        # 9. Update ip16dash_jiraperson table and store created record id in issue dictionary
        crid = self.sql.uploadPerson2Tbl(JiraPerson, crt,'creator')
        iss['creator_id'] = crid

        # 10. Update previous recorded issue main table. No need to capture record id here
        self.sql.uploadIssue2Tbl(JiraIssue, iss, fks['id'], 'JiraIssue')

    ############################################################
    def uploadIssue2DB(self,jdata,remid):

        '''Upload JIRA data to DB'''

        self.log.info("Starting [%s] issue upload process" % jdata['key'])

        #Generate tables related dictionaries
        (iss,agg,ass,comp,epc,crt,pa,pr,sp,st) = self.generateIssueObject(jdata,remid)

        #Check if previous issue record exists. We destinguish between create new
        #and update previous data.
        fks_dct = self.sql.getIssueFK(jdata['key'])

        #Upload prepared dictionaries into related tables with FK restriction
        self.uploadIssue2DBdo(iss,agg,ass,comp,epc,crt,pa,pr,sp,st,fks_dct)

        return

    ############################################################
    def dataProcessJiraData(self):

        '''Processing JIRA MYSQL upload data flow'''

        self.log.info("Starting JIRA MYSQL data collection and upload operation")

        #Initialize and run JIRA data collection process upon completetion a path to tmp
        #JSON file will be returned
        jira_data_collector = JiraDataCollector(
                self.hostname,
                self.username,
                self.password,
                self.project,
                self.issue,
                self.proxy,
                self.rproxyuser,
                self.rproxypass,
                self.auth,
                self.apibase,
                self.logdir,
                self.logfile,
                self.loglevel
        )

        jira_data_file = jira_data_collector.generateJiraDataObj()

        #Get exisiting jira remote id or create new record if missing
        remid = self.sql.getRemoteID(self.project, self.collector_id)

        #Read tmp JIRA data file. In each iteration data for single issue is read
        with open(jira_data_file) as f:

            for issue in f:
                #Each iteration pulls one issue data in JSON format
                self.log.debug("Processing issue line ....")
                issue = issue.rstrip('\n')

                #Convert JSON string to dictionary
                jdata = json.loads(issue)

                #Send issue data for DB upload
                self.uploadIssue2DB(jdata,remid)

        #Remove tm JIRA data file
        self.log.info("Removing [%s] processed tmp data file" % jira_data_file)
        os.remove(jira_data_file)

################################################################
################### MAIN TESTING PART ##########################
################################################################
if __name__ == '__main__':

    jcolid = parseParams()
    jiraObj = DataManagerJira(jcolid)
    jiraObj.dataProcessJiraData()

