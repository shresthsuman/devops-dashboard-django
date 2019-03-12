#!/usr/bin/env python

import argparse
import configparser
import json
import logging
import re
import os
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pprint import pprint
from dataLogger    import initLog
from pprint        import pprint
from connectorJira import JIRAConnector

####################################################
########### GLOBAL VARIABLES DEFENITIONS ###########
####################################################
DMCONF = '/app/ip16dash/datamanager/jira/dm.conf'
config = configparser.ConfigParser()
config.read(DMCONF)

LOGNAME  = config.get('config','LOGNAME_JIRA_CL').replace("'","")
LOGLEVEL = config.get('config','LOGLEVEL_JIRA_CL').replace("'","")
LOGFILE  = config.get('config','LOGFILE_JIRA_CL').replace("'","")
LOGDIR   = config.get('config','LOGDIR').replace("'","")

TMP      = '/tmp/ip16dash/jira'
MAXRESULTS = 100000

#####################################################
############## UTILITY FUNCTIONS ####################
#####################################################

####################################
def parseParams() :

    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--Hostname', help="Jira server to connect", required=True)
    parser.add_argument('-j', '--username', help="Jira user to use",       required=True)
    parser.add_argument('-J', '--password', help="Jira pass to use",       required=True)

    parser.add_argument('-r', '--ruser',    help='Reverse proxy user',     default=None)
    parser.add_argument('-R', '--rpass',    help='Reverse proxy password', default=None)
    parser.add_argument('-o', '--proxy',    help='Corporation proxy url',  default='')
    parser.add_argument('-b', '--base',     help='Jira base url',          default='')

    parser.add_argument('-a', '--auth', help='Authorisation type', default='BasicAuth',
                        choices=['BasicAuth', 'BasicAuthProxy'])

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-P', '--project', help="Jira project to access")
    group.add_argument('-I', '--issue',   help="Jira issue to access")

    args = parser.parse_args()

    #Set missing param to None
    try:
        args.project
    except NameError:
        args.project = None

    try:
        args.issue
    except NameError:
        args.issue = None

    return args.Hostname,args.username,args.password,args.project,args.issue,args.ruser,args.rpass,args.proxy,args.auth,args.base

####################################################
############### CLASS DEFENITIONS ##################
####################################################
class JiraDataCollector() :

    ########################################################################
    def __init__(self,url=None,juser=None,jpass=None,project=None,issue=None,proxy='',rproxyuser=None,rproxypass='',authtype=None,apibase='',logdir=LOGDIR,logfile=LOGFILE,loglevel=LOGLEVEL,logname=LOGNAME):

        """Jira collector construcor"""

        self.url     = url
        self.juser   = juser
        self.jpass   = jpass
        self.project = project
        self.issue   = issue

        #Jira connection additional settings
        self.proxy    = proxy         # Possible corporation proxy URL
        self.ruser    = rproxyuser    # Reverse proxy user
        self.rpass    = rproxypass    # Reverse proxy password
        self.rauth    = authtype      # BasicAuth | BacicAuthProxy | ...
        self.apibase  = apibase

        #If loglevel is supplied on environment level overwrite program supplied
        #value with environment
        loglevel = eval('logging.' + os.getenv('LOGLEVEL',loglevel))
        self.log = initLog(logdir,logfile,loglevel,logname)

        #Initialize tmp directory to store tmp files with collected data sets
        if not os.path.exists(TMP):
            os.makedirs(TMP)

        #Initialize JIRA connector object
        self.jira = JIRAConnector(self.url,self.juser,self.jpass,self.rauth,self.ruser,self.rpass,self.proxy,self.apibase)

        #Initialize tmp file to store results
        self.tfile = tempfile.NamedTemporaryFile(dir=TMP,mode='a',delete=False,prefix='jira')

    ########################################################################
    def storeInFile(self,jobj):

        # append issue data to tmp file
        self.log.info("Writing [%s] issue data into [%s] file" % (jobj['key'], self.tfile.name))
        json.dump(jobj, self.tfile)
        self.tfile.write(os.linesep)

    ########################################################################
    def generateObj(self,issue):

        """Generate data object from supplied Jira data"""

        h = dict()

        #pprint(issue)
        #print("-------------------------------")
        #pprint(issue['fields']['created'])
        #pprint(issue['fields']['resolutiondate'])
        #sys.exit()

        ###########################################################
        #1. agregates
        #          - progress             <= aggregateprogress
        #          - timeestimate         <= aggregatetimeestimate
        #          - timeoriginalestimate <= aggregatetimeoriginalestimate
        #          - timespent            <= aggregatetimespent
        h['aggregate'] = dict()

        if 'aggregateprogress' in issue['fields']:
            h['aggregate']['progress']             = issue['fields']['aggregateprogress']['progress']
            h['aggregate']['timeestimate']         = issue['fields']['aggregatetimeestimate']
            h['aggregate']['timeoriginalestimate'] = issue['fields']['aggregatetimeoriginalestimate']
            h['aggregate']['timespent']            = issue['fields']['aggregatetimespent']
        else:
            h['aggregate']['progress']             = 0
            h['aggregate']['timeestimate']         = 0
            h['aggregate']['timeoriginalestimate'] = 0
            h['aggregate']['timespent']            = 0

        ###########################################################
        #2. assignee
        h['assignee'] = dict()

        if issue['fields']['assignee'] == None:
            h['assignee']['name']  = None
            h['assignee']['email'] = None
            h['assignee']['key']   = None
        else:
            h['assignee']['name']  = issue['fields']['assignee']['displayName']
            h['assignee']['email'] = issue['fields']['assignee']['emailAddress']
            h['assignee']['rname'] = issue['fields']['assignee']['name']

        ###########################################################
        #3. component - can be empty or have empty subfields

        h['components'] = dict()

        if 'components' in  issue['fields'] and issue['fields']['components']:

            if 'name' in issue['fields']['components'][0]:
                h['components']['name'] = issue['fields']['components'][0]['name']
            else:
                h['components']['name'] = None

            if 'description' in issue['fields']['components'][0]:
                h['components']['description'] = issue['fields']['components'][0]['description']
            else:
                h['components']['description'] = None
        else:
            h['components']['name'] = None
            h['components']['description'] = None

        ###########################################################
        #4. creator
        h['creator'] = dict()
        h['creator']['dname'] = issue['fields']['creator']['displayName']
        h['creator']['email'] = issue['fields']['creator']['emailAddress'],
        h['creator']['rname'] = issue['fields']['creator']['name']

        ############################################################
        #5. description
        h['description'] = issue['fields']['description']

        ############################################################
        #6. epic
        if 'customfield_11953' in issue['fields']:
            h['epic'] = issue['fields']['customfield_11953']
        else:
            h['epic'] = None

        ############################################################
        #7. id
        h['id'] = issue['id']

        ############################################################
        #8 . key
        h['key'] = issue['key']

        ############################################################
        #9. parent
        h['parent'] = dict()
        if 'parenrt' in issue['fields']:
            h['parent']['key'] = issue['fields']['parent']['fields']['issuetype']['key']
            h['parent']['url'] = issue['fields']['parent']['fields']['issuetype']['selg']
        else:
            h['parent']['key'] = None
            h['parent']['url'] = None

        ############################################################
        #10. priority

        if 'priority' in issue['fields'] and issue['fields']['priority'] != None:
            h['priority'] = issue['fields']['priority']['name']
        else:
            h['priority'] = None

            ############################################################
        #11. progress
        if 'progress' in issue['fields']:
            h['progress'] = issue['fields']['progress']['progress']
        else:
            h['progress'] = 0

        ############################################################
        #12. project
        h['project'] = dict()
        h['project']['key']  = issue['fields']['project']['key']
        h['project']['name'] = issue['fields']['project']['name']
        h['project']['id']   = issue['fields']['project']['id']
        h['project']['url']  = issue['fields']['project']['self']

        ############################################################
        #13. sprint - can be None in some cases
        h['sprint'] = dict()
        if not 'customfield_11951' in issue['fields'] or issue['fields']['customfield_11951'] == None:
            h['sprint']['state'] = None
            h['sprint']['name'] = None
            h['sprint']['startDate'] = None
            h['sprint']['endDate'] = None
            h['sprint']['completeDate'] = None
        else:
            if 'customfield_11951' in issue['fields']:

                #This field seems to be a string with parameters being separated by ,
                fs0, fs1, fs2, fs3, fs4 = issue['fields']['customfield_11951'][0].split(',')[2:7]

                h['sprint']['state']        = fs0.split('=')[1]
                h['sprint']['name']         = fs1.split('=')[1]
                h['sprint']['startDate']    = fs2.split('=')[1]
                h['sprint']['endDate']      = fs3.split('=')[1]
                h['sprint']['completeDate'] = fs4.split('=')[1]

                if h['sprint']['startDate'] == '<null>':
                    h['sprint']['startDate'] = None

                if h['sprint']['endDate'] == '<null>':
                    h['sprint']['endDate'] = None
            else:
                h['sprint']['state']        = None
                h['sprint']['name']         = None
                h['sprint']['startDate']    = None
                h['sprint']['endDate']      = None
                h['sprint']['completeDate'] = None

        ############################################################
        #14. subtasks
        h['subtasks'] = issue['fields']['subtasks']

        ############################################################
        #15. status
        h['status'] = dict()
        h['status']['name'] = issue['fields']['status']['name']
        h['status']['description'] = issue['fields']['status']['description']

        ############################################################
        #16. summary
        h['summary'] = issue['fields']['summary']

        ############################################################
        #17. type
        h['type'] = issue['fields']['issuetype']['name']

        ############################################################
        #18. url
        h['url'] = issue['self']

        #19. Create date
        if 'created' in issue['fields']:
            h['created'] = issue['fields']['created']

        #20. Resolution date
        if 'resolutiondate' in issue['fields']:
            h['resolutiondate'] = issue['fields']['resolutiondate']

        return h

    ########################################################################
    def processJiraData(self,issue):

        """Pass over extracted from JIRA issues list and generate JSON objects list"""

        self.log.info("Generating list of JIRA data objects")

        #convert issue data into dict
        jobj  = self.generateObj(issue)

        #append issue data to tmp JSON file
        self.storeInFile(jobj)

        return

    ########################################################################
    def generateJiraDataObj(self):

        """Extract data from Jira data source
            - Establish Jira connection
            - Pulls Jira data for single issue
            - Creates list of Jira objects
        """

        self.log.info("Starting get Data from Jira process")

        #perform project or single issue level data collection
        if self.issue == None:
            # This is a full project pull case
            jdata = self.jira.getIssuesAllFromProject(self.project)

            if not 'issues' in jdata:
                self.log.error(jdata['errorMessages'][0])
            else:
                # This is the list of dict when each dict holds one issue info
                issues_lst = jdata['issues']

                # Pass over issues list
                for issue in issues_lst:
                    self.processJiraData(issue)
        else:
            # This is a single issue pull case
            issue = self.jira.getIssueByName(self.issue)
            issue = issue['issues'][0]
            self.processJiraData(issue)

        # Flush tmp file
        self.tfile.close()

        self.log.info("Completing objects generation process")
        return self.tfile.name

########################################################
############# MAIN PART FOR MODULE TESTING #############
########################################################

if __name__ == '__main__':

    (url,juser,jpass,project,issue,ruser,rpass,proxy,auth,base) = parseParams()
    jiraCollector = JiraDataCollector(url,juser,jpass,project,issue,proxy,ruser,rpass,auth,base)
    tmp_data_file = jiraCollector.generateJiraDataObj()

    print(tmp_data_file)
