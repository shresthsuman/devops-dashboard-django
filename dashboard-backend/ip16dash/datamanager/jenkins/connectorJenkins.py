#!/usr/bin/env python

import argparse
import base64
import configparser
import json
import logging
import os
import re
import requests
import sys

from pprint        import pprint
from requests.auth import HTTPBasicAuth

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dataLogger    import initLog

from connectorJenkinsDjangoSQL import ConnectorJenkinsDjangoSQL

###############################################
############## GLOBAL VARIABLES ###############
###############################################

DMCONF = '/app/ip16dash/datamanager/jenkins/dm.conf'

config = configparser.ConfigParser()
config.read(DMCONF)

LOGNAME  = config.get('config','LOGNAME_JENKINS_CN').replace("'","")
LOGLEVEL = config.get('config','LOGLEVEL_JENKINS_CN').replace("'","")
LOGFILE  = config.get('config','LOGFILE_JENKINS_CN').replace("'","")
LOGDIR   = config.get('config','LOGDIR').replace("'","")

PIPEBASE = config.get('config','PIPEBASE').replace("'","")
PIPESFX  = config.get('config','PIPESFX').replace("'","")
PIPEWFAPI= config.get('config','PIPEWFAPI').replace("'","")
PIPENODE = config.get('config','PIPENODE').replace("'","")
PIPELOG  = config.get('config','PIPELOG').replace("'","")
PIPEPEND = config.get('config','PIPEPEND').replace("'","")

HEADER = {'Content-Type': 'application/json'}

################################################
############### UTILILY FUNCTIONS ##############
################################################

####################################################
def parseParams():

    parser = argparse.ArgumentParser()

    parser.add_argument('-j','--juser',help='Jenkins user',       required=True)
    parser.add_argument('-J','--jpass',help='Jenkins password',   required=True)
    parser.add_argument('-u','--url',  help='Jenkins server url', required=True)

    parser.add_argument('-P','--pipeline',help='Pipeline to retreive data for', required=True)

    args = parser.parse_args()

    return args.juser, args.jpass, args.url, args.pipeline

################################################
############ CLASS DEFINITIONS #################
################################################
class ConnectorJenkins:

    ############################################
    def __init__(self,url=None,juser=None,jpass=None,pipeline=None,pbase=PIPEBASE,psuffix=PIPESFX,wfapi=PIPEWFAPI,pnode=PIPENODE,plog=PIPELOG,pend=PIPEPEND,logdir=LOGDIR,logfile=LOGFILE,loglevel=LOGLEVEL,logname=LOGNAME):

        '''Jenkins connector constructor :
                    - jurl     - jenkins server url
                    - juser    - jenkis user to use
                    - jpass    - jenkins pass to use
                    - pipeline - jenkins pipline to fetch as a test
        '''

        loglevel      = eval('logging.' + os.getenv('LOGLEVEL', loglevel))

        self.log      = initLog(logdir, logfile, loglevel, logname)

        self.jurl     = url
        self.juser    = juser
        self.jpass    = jpass
        self.pipeline = pipeline
        self.urlbase  = pbase + '/' + pipeline
        self.urlsfx   = psuffix
        self.urlwfapi = wfapi
        self.urlnode  = pnode
        self.urllog   = plog
        self.urlpend  = pend

        self.sql = ConnectorJenkinsDjangoSQL()

        #Get existing noproxy setting name/ip
        ips_no_proxy = self.sql.getNoProxyIPsLst()

        #Set noProxy parameter
        self.setNoProxy(ips_no_proxy)

        #Update /etc/hosts file received settings
        self.setEtcHosts(ips_no_proxy)

        #Verify mandatory parameters.
        errors = 0
        if not url:
            self.log.error("Missing mandatory parameter server URL")
            errors = 1

        if not pipeline:
            self.log.error("Missing mandatory parameter pipeline name")
            errors = 1

        if errors:
            #Abort due to unrecoverable errors
            raise

    #############################################
    def setNoProxy(self,no_proxy_lst):

        '''Add supplied ip/name list to no_proxy setttings'''

        self.log.info("Updating no_proxy settings")

        for pair in no_proxy_lst:

            #Check for NOPROY parameter existance
            if "NO_PROXY" in os.environ:

                #Check if we have current ip already in no_proxy parameter
                if pair['ip'] in os.environ['NO_PROXY']:
                    self.log.info("NOPROXY : Found already defined ip [%s]" % pair['ip'])
                    continue
                #Check if we have current name in no proxy parameter
                if pair['name'] in os.environ['NO_PROXY']:
                    self.log.info("NOPROXY : Found already defined name [%s]" % pair['name'])
                    continue

            if pair['ip']:
                # If IP is provided use it to add to list
                self.log.info('Updating no_proxy environment parameter list with ip [%s]' % pair['ip'])
                if "NO_PROXY" in os.environ:
                    os.environ['NO_PROXY'] = "%s,%s" % (os.environ['NO_PROXY'], pair['ip'])
                else:
                    os.environ['NO_PROXY'] = pair['ip']
            elif pair['name']:
                # If name is provided and IP not use name
                self.log.info('Updating no_proxy environment parameter list with name [%s]' % pair['name'])
                if "NO_PROXY" in os.environ:
                    os.environ['NO_PROXY'] = "%s,%s" % (os.environ['NO_PROXY'], pair['name'])
                else:
                    os.environ['NO_PROXY'] = pair['name']
            else:
                raise ValueError("No ip/name parameters in no_proxy setup")

    #############################################
    def setEtcHosts(self,addr_lst):

        '''Add supplied ip/name list to /etc/hosts file'''

        self.log.info("Updating no_proxy settings")

        hostsfile = '/etc/hosts'

        for pair in addr_lst:
            hosts = open(hostsfile).read()
            if pair['ip'] in hosts and pair['name'] in hosts:
                self.log.debug("Ip [%s] already in hosts file ... Skipping ...." % pair['ip'])
                continue

            self.log.debug("Ip [%s] is not in hosts file... adding" % pair['ip'])
            with open(hostsfile,'a') as f:
                f.write("%s\t%s\n" % (pair['ip'],pair['name']))

    #############################################
    def runGETQuery(self,urlpath):

        '''Run REST GET command'''

        self.log.debug("REST API : [runGETQuery] : %s" % urlpath)

        if self.juser:
            # Process connection call with credentials
            try:
                response = requests.get(urlpath,auth=(self.juser, self.jpass),verify=False)
            except requests.ConnectionError as e:
                self.log.error("Failed in Jenkins query with error : [%s]" % e)
                raise ValueError("Failed in Jenkins query")
        else:
            # Process connection call with no credentials
            try:
                response = requests.get(urlpath,verify=False)
            except requests.ConnectionError as e:
                self.log.error("Failed in Jenkins query with error : [%s]" % e)
                raise ValueError("Failed in Jenkins query")

        if response.status_code != 200:
            self.log.error("Failed to connect to [%s] url with rc [%s] and reason [%s]" % (urlpath,response.status_code,response.reason))
            raise ValueError("Failed to connect to Jenkins Data Source")

        res = response.json()
        response.close()

        # Everthing ok we have go our connection
        return res
        response.close()

        # Everthing ok we have go our connection
        return res

    #############################################
    def runGETQuery2(self, urlpath):

        '''Run REST GET command'''

        self.log.debug("REST API : [runGETQuery] : %s" % urlpath)

        if self.juser:
            # Process connection call with credentials
            try:
                response = requests.get(urlpath, auth=(self.juser, self.jpass), verify=False)
            except requests.ConnectionError as e:
                self.log.error("Failed in Jenkins query with error : [%s]" % e)
                raise ValueError("Failed in Jenkins query")
        else:
            # Process connection call with no credentials

            try:
                response = requests.get(urlpath, verify=False)
            except requests.ConnectionError as e:
                self.log.error("Failed in Jenkins query with error : [%s]" % e)
                raise ValueError("Failed in Jenkins query")

        if response.status_code != 200:
            if 'consoleText' in urlpath:
                self.log.warn("No consoleText was found for this job")
            else:
                self.log.error("Failed to connect to [%s] url with rc [%s] and reason [%s]" % (
                urlpath, response.status_code, response.reason))
                raise ValueError("Failed to connect to Jenkins Data Source")

        res = response.text
        response.close()

        # Everthing ok we have go our connection
        return res

    ###########################################
    def getJobsData(self,url):

        '''Get Jenkins job names list'''
        self.log.info("Get jobs config data")
        self.log.debug("REST API : [getJobsData] : %s" % url)
        jobobj = self.runGETQuery(url)

        return jobobj

    ##############################################
    def getBuildData(self,buildurl):

        '''Get build config data'''

        url = "%s/%s" % (buildurl,self.urlsfx)

        self.log.info('Get builds config data')
        self.log.debug("REST API : [getBuildData] : %s " % url)

        buildobj = self.runGETQuery(url)

        return buildobj

    ############################################
    def getMultiPipelineData(self,pipeurl):

        '''Get multipipeline childs pipeline list '''

        #We get only active pipelines list
        url = "%s/%s" % (pipeurl, self.urlwfapi)

        self.log.info("Get pipeline config data")
        self.log.debug("REST API : [getPipelineData] : %s " % url)
        pipeobj = self.runGETQuery(url)

        return pipeobj

    ############################################
    def getTriggersFromConsole(self,url):

        '''Get triggers list fron console output '''

        console_output = self.runGETQuery2(url)

        trigjob = re.search('Triggering a new build of ([\w#-_\s]+)',console_output)

        if trigjob:
            res = re.sub('\nFinished: SUCCESS','',trigjob.group(1))
            return res
        return None

    ############################################
    def getPipelineData(self,pipeurl):

        '''Get pipeline config data'''

        url = "%s/%s" % (pipeurl,self.urlwfapi)

        self.log.info("Get pipeline config data")
        self.log.debug("REST API : [getPipelineData] : %s " % url)
        pipeobj = self.runGETQuery(url)

        return pipeobj

    #############################################
    def getStageData(self,stageurl,stageid):

        '''Get specific pipeline stage config data'''

        url = "%s/%s/%s/%s" % (stageurl,self.urlnode,stageid,self.urlwfapi)

        self.log.info("Get [%s] stage config data" % stageid)
        self.log.debug("REST API : [getStageData] : %s" % url)
        stageobj = self.runGETQuery(url)

        return stageobj

    ##############################################
    def getNodeLogsData(self,nodeurl,nodeid):

        '''Get operation logs for specific node'''

        url = "%s/%s/%s/%s" % (nodeurl,self.urlnode,nodeid,self.urllog)
        self.log.info("Get [%s] node log data" % nodeid)
        self.log.debug("REST API : [getNodeLogsData] : %s" % url)

        logobj = self.runGETQuery(url)
        return logobj

    #############################################
    def getPipelinesList(self):

        '''Get list and state of all pipelines defined in the system'''

        job_sfx = '?tree=jobs[name,color]'

        url = "%s/%s/%s" % (self.jurl,self.urlsfx,job_sfx)
        self.log.debug("REST API : [getNodeLogsData] : %s" % url)

        logobj = self.runGETQuery(url)
        return logobj

    ##############################################
    def getCommentsData(self,bid,url=None):

        '''Get list of comments related to specific pipeline instance'''

        #url = "%s/%s/%s/%s" % (self.jurl,self.urlbase,bid,self.urlsfx)
        url = "%s/%s" % (url,self.urlsfx)
        self.log.debug("REST API : [getCommentsData] : %s" % url)
        inst_obj = self.runGETQuery(url)
        return inst_obj

    ##############################################
    def getPendingJobsStatus(self,bid,url=None):

        '''Get pending jobs expected commands'''

        if url:
            url = "%s/%s/" % (url,self.urlpend)
        else:
            url = "%s/%s/%s/%s" % (self.jurl,self.urlbase,bid,self.urlpend)

        self.log.debug("REST API : [getNodeLogsData] : %s" % url)

        logobj = self.runGETQuery(url)
        return logobj

#################################################
################ MAIN PART ######################
#################################################

if __name__ == "__main__":
    (juser,jpass,jurl,pipeline) = parseParams()

    jenkins = ConnectorJenkins(jurl,juser,jpass,pipeline)

    res = jenkins.getJobsData()
    pprint(res)
