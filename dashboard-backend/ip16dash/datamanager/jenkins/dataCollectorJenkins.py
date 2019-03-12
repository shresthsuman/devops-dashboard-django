#!/usr/bin/env python

import argparse
import configparser
import json
import logging
import os
import re
import requests
import sys
import tempfile
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataLogger       import initLog
from pprint           import pprint
from bleach           import clean
from connectorJenkins import ConnectorJenkins
from connectorJenkinsDjangoSQL import ConnectorJenkinsDjangoSQL

####################################################
############ GLOBAL VARIABLES ######################
####################################################
DMCONF = '/app/ip16dash/datamanager/jenkins/dm.conf'

config = configparser.ConfigParser()
config.read(DMCONF)

LOGNAME  = config.get('config','LOGNAME_JENKINS_CL').replace("'","")
LOGLEVEL = config.get('config','LOGLEVEL_JENKINS_CL').replace("'","")
LOGFILE  = config.get('config','LOGFILE_JENKINS_CL').replace("'","")
LOGDIR   = config.get('config','LOGDIR').replace("'","")

PIPEBASE = config.get('config','PIPEBASE').replace("'","")
PIPESFX  = config.get('config','PIPESFX').replace("'","")
PIPEWFAPI= config.get('config','PIPEWFAPI').replace("'","")
PIPENODE = config.get('config','PIPENODE').replace("'","")
PIPELOG  = config.get('config','PIPELOG').replace("'","")
PIPEPEND = config.get('config','PIPEPEND').replace("'","")
PIPETEXT = config.get('config','PIPETEXT').replace("'","")

################################################
############### UTILILY FUNCTIONS ##############
################################################

def parseParams():

    parser = argparse.ArgumentParser()

    parser.add_argument('-u', '--url',      help='Jenkins server url', required=True)
    parser.add_argument('-j', '--juser',    help='Jenkins username',   required=True)
    parser.add_argument('-J', '--jpass',    help='Jenkins password',   required=True)
    parser.add_argument('-P', '--pipeline', help='Jenkins pipeline',   required=True)
    parser.add_argument('-p', '--pattern' , help='Jenkins comments pattern')

    args = parser.parse_args()

    if args.juser == '':
        args.juser=None

    if args.jpass == '':
        args.jpass=None

    if not args.pattern:
        args.pattern = ''

    return args.url,args.juser,args.jpass,args.pipeline,args.pattern

####################################################
############### CLASS DEFENITIONS ##################
####################################################
class JenkinsDataCollector() :

    ##########################################
    def __init__(self,hostname=None,username=None,password=None,pipeline=None,ptrn=None,pbase=PIPEBASE,psuffix=PIPESFX,wfapi=PIPEWFAPI,pnode=PIPENODE,plog=PIPELOG,pend=PIPEPEND,logdir=LOGDIR,logfile=LOGFILE,loglevel=LOGLEVEL,logname=LOGNAME):
        '''Class constructor'''

        self.hostname = hostname
        self.username = username
        self.password = password
        self.pipeline = pipeline
        self.urlbase  = pbase
        self.urlsfx   = psuffix
        self.urlwfapi = wfapi
        self.urlnode  = pnode
        self.urllog   = plog
        self.urlpend  = pend
        self.ptrn     = ptrn

        # If loglevel is supplied on environment level overwrite program supplied
        # value with environment
        loglevel = eval('logging.' + os.getenv('LOGLEVEL', loglevel))

        self.log = initLog(logdir, logfile, loglevel, logname)
        self.log.info("Initialising Jenkins connector object")

        # Initialising Jenkins collector object
        self.jenkins = ConnectorJenkins(self.hostname, self.username, self.password, self.pipeline, self.urlbase, self.urlsfx, self.urlwfapi, self.urlnode, self.urllog, self.urlpend)

        # Initialising SQL collector object
        self.sql = ConnectorJenkinsDjangoSQL()

    ##################################################################################
    ##################################################################################

    #####################################################
    def storeInFile(self, jobj):
        # append issue data to tmp file
        self.log.info("Writing [%s] pipeline data into [%s] file" % (jobj['build']['name'], self.tfile.name))
        json.dump(jobj, self.tfile)
        self.tfile.write(os.linesep)

    #####################################################
    def getInstancesList(self,url):

        '''Get Pipeline instances list'''
        self.log.debug("Getting Pipelines Instances list")
        jobobj = self.jenkins.getJobsData(url)
        return jobobj

    #####################################################
    def getPatternsList(self,dataobj,ptrn):

        comnt_lst = list()
        chgItems  = dataobj['changeSets'][0]['items']
        comment   = ""

        for item in chgItems:
            comment = comment + ' ' + item['comment']

        # Get list of substrings accordong to provided pattern
        items = re.findall(ptrn,comment)

        # No retrieved patterns add to resulting list
        for ptrn in items:
            comnt_lst.append(ptrn)

        return comnt_lst

    #####################################################
    def generateBuildObj(self,url):

        '''Get current instance build data'''

        self.log.info("Generate build data object")

        ##################################################
        # Get instance comments parsed content.
        buildobj = self.jenkins.getBuildData(url)

        build = dict()
        build["stagelst"]        = list()
        build["id"]              = buildobj['id']
        build["name"]            = buildobj['displayName']
        build["fullDisplayName"] = buildobj['fullDisplayName']
        build["started"]         = buildobj['timestamp']
        build["duration"]        = buildobj['duration']
        build["estimate"]        = buildobj['estimatedDuration']
        build["progress"]        = False

        if not buildobj['building']:
            build["progress"] = True

        if buildobj['result'] == None:
            build["result"] = "None"
        else:
            build["result"] = buildobj['result'].lower()

        for actionobj in buildobj['actions']:

            if 'causes' in actionobj:
                build['causes'] = actionobj['causes'][0]['shortDescription']
            elif 'failCount' in actionobj:
                if actionobj['totalCount'] - actionobj['failCount']:
                    build["coverage"] = (actionobj['totalCount'] - actionobj['skipCount']) / (
                    actionobj['totalCount'] - actionobj['failCount'])
                else:
                    build["coverage"] = 1

        # Save data for possible upstream jobs. Assuming that number of upatream jobs
        # can be bigger than 1 we store a list of uperstream project names and their
        # dependent builds numbers
        stream = list()
        if 'causes' in buildobj['actions'][0]:
            for item in buildobj['actions'][0]['causes']:
                if 'upstreamBuild' in item:
                    stream.append("%s #%s" % (item['upstreamProject'],item['upstreamBuild']))

        #Save only if there is any data
        if stream:
            build['depinst']     = ';'.join(stream)
            build['depdirect']   = 'upstream'
            build['deplocation'] = 'first'

            self.log.debug("saving upstream triggered data [%s]" % build['depinst'])
        else:
            self.log.debug("No upstream triggered data")

        ##########################################################
        # If pattern was provided get and parse pipeline comments
        build['comments'] = ''

        if self.ptrn:
            self.log.debug("Processing [%s] pipeline comments based on [%s] pattern" % (build['id'],self.ptrn))
            coments_obj = self.jenkins.getCommentsData(build['id'],url)
            if coments_obj['changeSets']:
                build['comments'] = ';'.join(self.getPatternsList(coments_obj, self.ptrn))
        else:
            self.log.debug("No pattern set for [%s] pipeline ... Skipping this stage ..." % build['id'])

        ####################################################
        # Process possible user input pending command

        cmdobj_full = self.jenkins.getPendingJobsStatus(build['id'],url)

        # Found input user pending info
        if cmdobj_full:
            self.log.info("Adding pending user command to build [%s]" % build['id'])

            # Add record info to node data
            build['rcmd'] = dict()
            build['rcmd']['id'] = build['id']
            build['rcmd']['cmdobj_full'] = cmdobj_full

        return build

    #####################################################
    def getStagesList(self,url):

        '''Get stages urls list'''
        self.log.debug("Getting [%s] stage data" % url)
        stageobj = self.jenkins.getPipelineData(url)
        return stageobj

    #####################################################
    def generateStageObj(self,url,build,stageref):

        '''Generate stage object'''

        self.log.debug("Processing [%s] stages data" % stageref['name'])

        # Update build duration parameter based on stage data
        d = stageref['durationMillis'] + stageref['pauseDurationMillis']
        if d < 0:
            d = 0
        build['duration'] += d

        # Generate stage data
        stage             = dict()
        stage["id"]       = build["id"] + "-" + stageref['id']
        stage["build"]    = build["id"]
        stage["name"]     = stageref['name']
        stage["result"]   = stageref['status'].lower()
        stage["started"]  = stageref['startTimeMillis']
        stage["duration"] = stageref['durationMillis'] + stageref['pauseDurationMillis']
        stage["nodeslst"] = list()

        return stage

    ####################################################
    def getNodeList(self,url,id):

        '''Get nodes url list'''
        self.log.debug("Getting data for [%s] node" % id)
        nodeobj = self.jenkins.getStageData(url,id)
        return nodeobj

    #####################################################
    def generateNodeObj(self,stageobj, nodeobj,build,stage,url):

        '''Generate Node data object and add this object to build data'''

        self.log.info("Generate Build Node object")

        node = dict()

        node["id"]       = build["id"] + "-" + nodeobj['id']
        node["build"]    = build["id"]
        node["stage"]    = stageobj['name']
        node["started"]  = nodeobj['startTimeMillis']
        node["duration"] = nodeobj['durationMillis'] + nodeobj['pauseDurationMillis']
        node["progress"] = False
        node["result"]   = nodeobj['status'].lower()
        node["desc"]     = False

        if node["duration"] < 0: node["duration"] = 0

        #Next logobj/log parameters are the same for all folowing options
        logobj = self.jenkins.getNodeLogsData(url,nodeobj['id'])

        self.log.debug("LOG TEXT : %s" % logobj['consoleUrl'])

        # Sometimes there is no text setting. In this case skipp to next node
        if not 'text' in logobj:
            log = ''
        else:
            log = logobj['text']
            log = clean(log, tags=[], strip=True, strip_comments=True)
            log = re.sub('#\n?[0-9]{2}:[0-9]{2}:[0-9]{2} #', "\n", log)

        log=str(log)

        # Detect if we have a remote pipe triggered from this node
        res = re.search(r'Remote build URL: (.*)/\n', log)
        if res:

            pipe_inst = os.path.basename(res.group(1))
            pipe_name = os.path.basename(os.path.dirname(res.group(1)))

            build['depdirect']  = 'downstream'
            build['depinst']    = "%s #%s" % (pipe_name,pipe_inst)
            build['deplocation']= "%s:%s:%s" % (build['name'],stage['name'],node['id'])

        if nodeobj['name'] == "Wait for interactive input":

            build['state'] = 'waiting user'

            node["type"]   = "input"
            node["result"] = "warning"

            log = str(log.strip())
            loglines     = log.split('\n')

            node["desc"] = loglines.pop()

            res = node["desc"][0:8]
            if res == "Approved":
                node["result"] = "success"
                return node

            #If build was aborted by user the stage result will be Failed
            if stage['result'] == "failed":
                node["result"] = "failed"
                node["desc"]   = "Aborted"
                return node

        elif nodeobj['name'] == "Shell Script":

            cmdline = "unknown"

            res = re.search(r'^\+ ([^\n]*)$',log)
            if res:
                cmdline = res.group(1)

            info = cmdline
            p = cmdline.split()

            if "deploy:deploy" in cmdline:
                node["type"] = "deployment"

            elif "CheckmarxScanner.java" in log:
                node["type"] = "security"
                if "STATIC SCAN COMPLETED" in log:
                    node["result"] = "danger"

            elif re.search(r'Tests run: ([0-9]*), Failures: ([0-9]*), Errors: ([0-9]*), Skipped: ([0-9]*)',log):
                res = re.search(r'Tests run: ([0-9]*), Failures: ([0-9]*), Errors: ([0-9]*), Skipped: ([0-9]*)',log)
                node["type"] = "unit"
                passed       = int(res.group(1)) - int(res.group(2)) - int(res.group(4))
                node["desc"] = "Passed (" + str(passed) + ") Failed (" + res.group(2) + ")"

            elif re.search(r"TQS Reports", log):
                res = re.search(r"#TQS Reports#", log)
                node["type"] = "analysis"
                for a in buildobj['artifacts']:
                    if re.search(r"TQS_Report",a['fileName']):
                        node['link'] = url + "artifact/" + a['relativePath']
                        break

            elif re.search(r'Building war',log):
                node["type"] = "packaging"

            elif "\n[INFO] BUILD" in log:
                node["type"] = "build"
                if "BUILD SUCCESS" in log:
                    node["result"] = "danger"
                if re.search("Final Memory: ([^ \n]*)", log):
                    res = re.search(r"Final Memory: ([^ \n]*)", log)
                    node["desc"] = "Memory usage " + res.group(1)
            else:
                node["type"] = 'others'
        else:

            node["type"] = 'operation'

            if 'milestone' in nodeobj['name']:
                node["desc"] = 'Milestone'
            elif 'Git' in nodeobj['name']:
                node["desc"] = 'Git'
            elif 'ansible' in nodeobj['name'] or 'Ansible' in nodeobj['name']:
                node["desc"] = 'Ansible'
            else:
                node["desc"] = nodeobj['name']

        return node

    #####################################################
    def getPipeChildren(self,jobobj):

        '''Get list of pipeline childs urls'''

        child_urls_lst = list()

        for item in jobobj['jobs']:
            #Add only active jobs
            if item['color'] != 'disabled':
                child_urls_lst.append(item['url'])
            else:
                self.log.debug("Discarding [%s] disabled job" % item['name'])

        return child_urls_lst

    #####################################################
    def triggeredList(self,id):

        '''Get triggers list'''
        self.log.debug("Getting triggers list for job [%s]" % id)
        url = "%s/%s/%s/%s/%s" % (self.hostname,PIPEBASE,self.pipeline,id,PIPETEXT)

        res = self.jenkins.getTriggersFromConsole(url)
        if res:
            #we have found a trigger line. Now separate pipeline name and instance
            #and safe them in returned dictionary
            res = res.rstrip()
            return res

        return None

    #####################################################
    def generateJenDataObjMulti(self,buildobj):

        '''Generate Jenkins data object for a multiple pipeline.'''

        #The multi pipeline format is differnt from standart
        self.log.debug("Generating Jenkins data object for multiple pipeline")

        build = dict()
        build["stagelst"] = list()
        build["id"]              = None
        build["name"]            = buildobj['displayName']
        build["fullDisplayName"] = buildobj['fullDisplayName']
        build["started"]         = None
        build["duration"]        = None
        build["estimate"]        = None
        build["progress"]        = None
        build["result"]          = "None"
        build['causes']          = None
        build["coverage"]        = None
        build['comments']        = ''
        build['ptype']           = 'multi'

        return build

    #####################################################
    def generateJenDataObjDo(self,jobobj):

        '''Generate Jenkins data object for a single pipeline.'''

        self.log.debug("Generating Jenkins data object")

        for buildref in jobobj['builds']:

            self.log.debug("Processing [%s] instance data" % buildref['number'])

            #This module do not have access to DB so there will be no
            #check for previously stored instances state. This check will be
            #done when run from dataManager module

            #Get instance REST API url
            url = buildref['url']

            #Generate build object
            build = self.generateBuildObj(url)

            #Get stages urls list
            stageobj = self.getStagesList(url)

            for stageref in stageobj['stages']:

                # Generate Stage object
                stage = self.generateStageObj(url,build,stageref)

                # Get nodes list
                nodeobj = self.getNodeList(url,stageref['id'])

                for noderef in nodeobj['stageFlowNodes']:

                    self.log.debug("Processing nodes data for [%s] stage" % stageref['name'])
                    node = self.generateNodeObj(nodeobj,noderef,build,stage,url)

                    # Add newly created node object to stage data, nodelst list
                    stage["nodeslst"].append(node)

                # Add newly created stage object to build data, stagelst list
                build["stagelst"].append(stage)

            build['ptype'] = 'single'

            #Set possible triggers list and dependency direction
            build['depinst']     = self.triggeredList(build['id'])
            if build['depinst']:
                build['depdirect']   = 'downstream'
                build['deplocation'] = 'last'
            else:
                build['depdirect']   = None
                build['deplocation'] = None

        #This is a test collector function
        return build

    #####################################################
    def generateJenDataObj(self):

        '''
            Pull data from Jenkins and create data object
            ---------------------------------------------
            This is test driver function and not used in real process
            The real genrate Jen data object is done from dataManager module
        '''

        #Create instances to pull url
        url = "%s/%s/%s/%s" % (self.hostname, self.urlbase, self.pipeline,self.urlsfx)

        self.log.info("Generate Jenkins object")
        jobobj = self.getInstancesList(url)

        #Here we store resulting jenkins data object. In case of standart
        #pipeline there will be only one entry. In case of Multi the resulting
        #list will include several data objects
        jenobj = list()

        if 'jobs' in jobobj:
            #This is a multipipeline case
            self.log.info("Detected pipeline type : Multiple")

            #Generate data object for multiple pipeline
            jenobj.append(self.generateJenDataObjMulti(jobobj))

            pipelst = self.getPipeChildren(jobobj)

            #We have a list of single pipeline urls
            for url in pipelst:

                url = "%s/%s" % (url,self.urlsfx)

                self.log.debug("Multiple : Processing child url - %s" % url)
                #get data specific for this url
                jobobj = self.getInstancesList(url)

                #generate data object for single pipeline which is child to
                #multiple pipline parent
                jenobj.append(self.generateJenDataObjDo(jobobj))

        else:
            #This is a single pipeline case.
            #Now generate data object and add it to list as single entry
            self.log.info("Detected pipeline type : Standart")
            jenobj.append(self.generateJenDataObjDo(jobobj))

        return jenobj

#####################################################
################# MAIN PART #########################
#####################################################
if __name__ == '__main__':

    (url,juser,jpass,pipeline,ptrn) = parseParams()

    jen_data_collector = JenkinsDataCollector(url,juser,jpass,pipeline,ptrn,PIPEBASE,PIPESFX,PIPEWFAPI,PIPENODE,PIPELOG)
    jenobj = jen_data_collector.generateJenDataObj()
    pprint(jenobj)
