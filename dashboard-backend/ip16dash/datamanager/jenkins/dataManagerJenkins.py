#!/usr/bin/env python

#####################################################
import argparse
import configparser
import datetime
import json
import logging
import os
import re
import pytz
import time
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append('../../../')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dashboard.settings")
django.setup()

from pprint                    import pprint
from django.db                 import transaction, IntegrityError
from dataCollectorJenkins      import JenkinsDataCollector
from connectorJenkinsDjangoSQL import ConnectorJenkinsDjangoSQL
from datetime import timezone
from django.utils import timezone

from dataLogger      import initLog
from ip16dash.models import (
    Build,
    BuildJob,
    BuildNode,
    BuildStage,
    Multi,
    Remote
)

########################################################
TMP    = '/app/ip16dash/datamanager/jenkins/tmp'
DMCONF = '/app/ip16dash/datamanager/jenkins/dm.conf'

config = configparser.ConfigParser()
config.read(DMCONF)

########################################################
############ JENKINS API PARAMETER #####################
########################################################
LOGNAME  = config.get('config','LOGNAME_JENKINS_DM').replace("'","")
LOGLEVEL = config.get('config','LOGLEVEL_JENKINS_DM').replace("'","")
LOGFILE  = config.get('config','LOGFILE_JENKINS_DM').replace("'","")
LOGDIR   = config.get('config','LOGDIR').replace("'","")

PIPEBASE = config.get('config','PIPEBASE').replace("'","")
PIPESFX  = config.get('config','PIPESFX').replace("'","")
PIPEWFAPI= config.get('config','PIPEWFAPI').replace("'","")
PIPENODE = config.get('config','PIPENODE').replace("'","")
PIPELOG  = config.get('config','PIPELOG').replace("'","")

########################################################
############### JENKINS TABLES #########################
########################################################
TBL_BUILD       = config.get('config','TBL_BUILD').replace("'","")
TBL_BUILD_STAGE = config.get('config','TBL_BUILD_STAGE').replace("'","")
TBL_BUILD_NODE  = config.get('config','TBL_BUILD_NODE').replace("'","")
TBL_REMOTE      = config.get('config','TBL_REMOTE').replace("'","")
TBL_BUILD_JOB   = config.get('config','TBL_BUILD_JOB').replace("'","")

########################################################
################# LOGGING DEFENITIONS ##################
########################################################
LOGNAME  = config.get('config','LOGNAME_JENKINS_DM').replace("'","")
LOGLEVEL = config.get('config','LOGLEVEL_JENKINS_DM').replace("'","")
LOGFILE  = config.get('config','LOGFILE_JENKINS_DM').replace("'","")
LOGDIR   = config.get('config','LOGDIR').replace("'","")

###########################################################
################ UTILI FUNCTIONS ##########################
###########################################################

#################################################
def parseParams() :

    '''Externaly suppllied parameter processor'''

    parser = argparse.ArgumentParser()

    # Mandatory parameter for database query
    parser.add_argument('-c', '--collectorID', help="Remote collector id to use", required=True)
    parser.add_argument('-d', '--depth', help="Depth of data pulls", action='store_true')
    args = parser.parse_args()

    depth = False
    if args.depth:
        depth = True

    return args.collectorID,depth

########################################################
#################### CLASS PART ########################
########################################################
class DataManagerJenkins:

    #############################################################
    def __init__(self,collector_id,depth=None,logdir=LOGDIR,logfile=LOGFILE,loglevel=LOGLEVEL,logname=LOGNAME):

        '''Constructor : Initialising Jenkins MYSQL collector
            - collector_id - id of collector holding Jenkins access data
            - depth        - depth of data pull
            - logdir       - directory to store log data
            - logfile      - name of log file
            - loglevel     - verbose level of logged data
            - logname      - string indefying this log enteries. Used to destinguish between different self.logs
        '''

        self.collector_id = collector_id
        self.depth        = depth

        # If loglevel is supplied on environment level overwrite program supplied
        # value with environment
        self.logdir   = logdir
        self.logfile  = logfile
        self.loglevel = loglevel
        self.logname  = logname
        self.colid    = collector_id

        loglevel = eval('logging.' + os.getenv('LOGLEVEL', loglevel))
        self.log = initLog(logdir,logfile,loglevel,logname)

        self.sql = ConnectorJenkinsDjangoSQL()

        #Get connector data based on supplied connector id
        (self.hostname, self.project, ctype, self.username, self.password,self.pattern) = self.sql.getConnectorConfig(self.collector_id)

        #Check for right collector type - we deal here with Jenkins collectors only
        if not re.match('[Jj]enkins',ctype):
            raise ValueError("Wrong collector type : Collector record with id [%s] is of type [%s] instead of [Jenkins]" % (collector_id,ctype))

        # Initialize tmp directory to store tmp files with collected data sets
        if not os.path.exists(TMP):
            os.makedirs(TMP)

        # Initialise jenkins data collector
        self.jen_data_collector = JenkinsDataCollector(self.hostname,
                                                       self.username,
                                                       self.password,
                                                       self.project,
                                                       self.pattern,
                                                       PIPEBASE, PIPESFX, PIPEWFAPI, PIPENODE, PIPELOG)

    ################################################################
    def buildsategetbl(self,stage):

        '''All possible build stage defenitions'''

        if stage == 'progress':
            return 'In Work'
        if stage == 'pending':
            return 'Waiting for Approval'
        if stage == 'success':
            return 'Successful'
        if stage == 'aborted':
            return 'Aborted'
        if stage == 'failure':
            return 'Failed'
        if stage == 'other':
            return 'Other'

        self.log.warn('Unrecognized [%s] stage status.... Setting status as Unknown' % stage)
        return 'Unknown'

    ###########################################################
    def buildnodetbl(self, node):

            '''All possible build node defenitions'''

            if node == 'input':
                return 'User Approval'
            if node == 'build':
                return 'Build'
            if node == 'unit':
                return 'Unit Tests'
            if node == 'analysis':
                return 'Code Analysis'
            if node == 'security':
                return 'Security Tests'
            if node == 'deployment':
                return 'Deployment'
            if node == 'packaging':
                return 'Packaging'
            if node == 'other':
                return 'Other'

            self.log.warning('Unrecognized [%s] node status.... Setting status as Unknown' % node)
            return 'Unknown'

    ############################################################
    def generateBuildObject(self,data,job_id):

        #####################################################
        #Additional calculations are needed for some fields.#
        #####################################################

        self.log.info("Generating build object - [%s]" % data['id'])

        #In case of multipipeline we will not have this settings
        if data['started'] == None:
            self.log.debug("Multiple pipeline : setting default values")

            bld_obj = dict()

            bld_obj['bld_id']   = 0
            bld_obj['name']     = data['name']
            bld_obj['job_id']   = job_id
            bld_obj['progress'] = 0
            bld_obj['ptype']    = data['ptype']

            return bld_obj

        # Convert miliseconds format into human redable format that could be uploaded to database : '%Y-%m-%d %H:%M:%S
        started = datetime.datetime.fromtimestamp(data['started'] / 1000,pytz.utc)

        # Generate progress estimation
        progress = 0
        if data['duration'] / data['estimate'] > 1:
            progress = 1

        # Deployed stage
        deployed = None
        if data['result'] == 'success':
            deployed = datetime.datetime.fromtimestamp((data['started'] + data['duration']) / 1000,pytz.utc)

        # Coverage estimation
        if 'coverage' in data:
            coverage = data['coverage']
        else:
            coverage = 'Null'

        #################################
        #Build final object dictionary  #
        #################################
        bld_obj = dict()

        #Originaly intact fields (as they come from Jenkins server)
        bld_obj['bld_id']   = data['id']
        bld_obj['name']     = data['name']
        bld_obj["fullname"] = data['fullDisplayName']
        bld_obj['duration'] = data['duration']
        bld_obj['result']   = data['result']
        bld_obj['estimate'] = data['estimate']
        bld_obj['cause']    = data['causes']
        bld_obj['job_id']   = job_id
        bld_obj['comments'] = data['comments']

        #Additionaly calculated fields
        bld_obj['deployed'] = deployed
        bld_obj['progress'] = progress
        bld_obj['started']  = started

        #Triggered dependent pipelines
        if 'depdirect' in data:
            bld_obj['depinst']     = data['depinst']
            bld_obj['depdirect']   = data['depdirect']
            if 'deplocation' in data:
                bld_obj['deplocation'] = data['deplocation']

        # As build state we store the last stage object name
        #bld_obj['stage'] = data['stagelst'][-1]['name']

        bld_obj['ptype']       = data['ptype']

        if 'parent_pipe' in data:
            bld_obj['parent_pipe'] = data['parent_pipe']

        return bld_obj

    ############################################################
    def upload2Multi(self,data,job_id):

        '''Upload multi data to relevant DB table'''

        self.log.info("Processing Multi data for id [%s]" % job_id)

        # Create parameters dict which will be used for previous record existance verification
        check_dict = {'name': data['name']}

        # Upload build data to Multi table with django API
        self.sql.uploadData2Table(Multi,data,check_dict)

    ############################################################
    def upload2Build(self,data,job_id):

        '''Upload build data to relevant DB table
            - data   - data object filled with data pulled from Jenkins source
            - job_id - job id for this build object
            Returns : record build id
        '''

        self.log.info("Processing Build data for job id [%s]" % job_id)

        # Generate build data object to be feed into django upload into DB function
        bld_obj = self.generateBuildObject(data,job_id)

        # Create parameters dict which will be used for previous record existence verification
        check_dict = {'name':bld_obj['name'], 'job_id':job_id}

        # Upload build data to Build table with django API
        # NOTE : Build in function is Model table object !!!!!!!
        bid = self.sql.uploadData2Table(Build,bld_obj,check_dict)

        return bid

    ############################################################
    def generateNodeObject(self,node,stage_id):

        '''Generate Node object based on supplied data'''
        self.log.debug("Generating node object - [%s] " % (node['id']))

        obj = dict()
        obj['stageid_id'] = stage_id
        obj['nd_id']      = node['id']
        obj['build']      = node["build"]
        obj['stage']      = node["stage"]
        obj['duration']   = node['duration']
        obj['progress']   = node["progress"]
        obj['result']     = self.buildsategetbl(node['result'])
        obj['descrpt']    = node['desc']
        obj['type']       = self.buildnodetbl(node['type'])

        # Convert miliseconds to human readable format
        obj['started'] = datetime.datetime.fromtimestamp(node['started'] / 1000,pytz.utc)

        return obj

    ############################################################
    def upload2BuildNode(self,nodesobj,stage_id):

        '''Upload build node data to relevant DB table
            - data     - data object filled with data pulled from Jenkins source
            - stage_id - stage id for this node object
        '''

        self.log.info("Processing Node data for [%s] stage id" % stage_id)

        for node in nodesobj:

            if type(node) is str:
                self.log.warning("Wrong node type  ... Skiping to next node")
                continue

            # Generate node object from supplied data to feed into django DB upload function
            node_obj = self.generateNodeObject(node,stage_id)

            #Create parameters dict which will be used for previous record existance verification
            check_dict = {'nd_id':node_obj['nd_id'],'stageid_id':stage_id}

            # Upload build data to Build table with django API
            self.sql.uploadData2Table(BuildNode, node_obj, check_dict)

    ############################################################
    def generateStageObject(self,stage,build_id):

        '''Geberate stage object from pulled data'''

        self.log.debug("Generating stage object - [%s] " % (stage['name']))

        obj = dict()
        obj['buildid_id'] = build_id
        obj['stg_id']     = stage['id']
        obj['build']      = stage["build"]
        obj['name']       = stage['name']
        obj['result']     = self.buildsategetbl(stage['result'])
        obj['duration']   = stage['duration']

        # Convert miliseconds to human readable format
        obj['started'] = datetime.datetime.fromtimestamp(stage['started'] / 1000,pytz.utc)

        return obj

    ############################################################
    def upload2BuildStage(self,data,build_id):

        '''Upload build stage data to relevant DB table
            - data     - data object filled with data pulled from Jenkins source
            - build_id - build id for this stage object
        '''

        self.log.info("Processing Stage data for [%s] build id" % build_id)

        # Pass over stage data and send generated SQL code for upload
        for stage in data['stagelst']:

            self.log.debug("Processing stage - [%s] - [%s]" % (stage['id'],stage['name']))

            #Generate stage data object that we will feed into upload table function
            stage_obj = self.generateStageObject(stage,build_id)

            # Create parameters dict which will be used for previous record existance verification
            check_dict = {'name':stage_obj['name'] ,'buildid_id':build_id}

            # Upload build data to Build table
            stage_id = self.sql.uploadData2Table(BuildStage,stage_obj,check_dict)

            # Upload Nodes data related to this stage
            self.upload2BuildNode(stage['nodeslst'], stage_id)

    ############################################################
    @transaction.atomic
    def upload2DB(self,data,job_id,iname):

        # Fill up build data into table
        build_id = self.upload2Build(data, job_id)

        # Fill up stages data into table
        self.upload2BuildStage(data, build_id)

        # Update processed instances table
        status = data['result']
        self.sql.setInstanceState(iname,job_id,status)

    #####################################################
    def generateCMDObj(self,obj):

        '''Generates dictionary Remote CMD data object. Scrap excesive data'''

        #We need only lines with 'Url' string since this holds Jeson URL calls
        robj          = dict()
        robj['cmd']   = list()
        robj['id']    = obj[0]['id']
        robj['inputs']= obj[0]['inputs']

        #Save commands without URL suffix and also skip redirectApprovalUrl setting
        for key,val in obj[0].items():
            if re.search('Url',key):
                if key == 'redirectApprovalUrl':
                    continue
                cmd = re.sub('Url','',key)
                robj['cmd'].append(cmd)

        return robj

    ###################################################
    def isExistsAndStable(self,iname,job_id):

        '''Detect insance existing and state'''

        # See if we previously have this instance stored in our DB
        # if it was stored with status Success or Failre do not
        # process it again

        # Get instance status based on Job id
        status = self.sql.getInstanceState(iname, job_id)

        if status == "success" or status == "aborted" or status == "failed":
            # Instance already in DB and it is stable. No need to re-process
            # it any further

            self.log.debug("Instance [%s] already in DB and stable... Skipping re-processing it" % iname)
            return True

        self.log.debug("Should process instance [%s]" % iname)
        return False

    #####################################################
    def generateJenDataStages(self,url,build,iname,job_id):

        '''Process instance stages data generation'''

        # Get stages urls list
        stageobj = self.jen_data_collector.getStagesList(url)

        for stageref in stageobj['stages']:

            # Generate Stage object
            stage = self.jen_data_collector.generateStageObj(url, build, stageref)

            # Get nodes list
            nodeobj = self.jen_data_collector.getNodeList(url, stageref['id'])

            for noderef in nodeobj['stageFlowNodes']:
                self.log.debug("Processing nodes data for [%s] stage" % stageref['name'])
                node = self.jen_data_collector.generateNodeObj(nodeobj, noderef, build, stage, url)

                # Add newly created node object to stage data, nodelst list
                stage["nodeslst"].append(node)

            # Add newly created stage object to build data, stagelst list
            build["stagelst"].append(stage)

        # Upload build object into DB
        self.upload2DB(build, job_id, iname)

    ###########################################
    def processPendingInput(self, build):

        '''Processing possible user pending input'''

        # Process possible user input pending command
        if 'rcmd' in build:
            self.log.debug("Processing user input pending command [%s]" % build['rcmd']['id'])

            # Generate pending record object
            cmdobj = self.generateCMDObj(build['rcmd']['cmdobj_full'])

            # Upload prepared record into DB but only if cmdobj was created.
            # meaning we recognized defined commands
            if cmdobj:
                self.sql.uploadNewRemoteCMD(build['rcmd']['id'], cmdobj, self.colid)
            else:
                self.log.warn("Pending user input exists but commands format was not recognized")

        # We want to see if user input pending was previously stored for this build but
        # was removed due to user iput on Jenkins side. In such case we need to clear
        # remotes comands table from entery for this build since it is alraedy procesed
        else:

            if self.sql.isRemCMDExists(build['id']):
                # RCMD record exists but no pending input anymore.
                # Remove RCMD record for this build
                self.log.info("Cleaning up pending input stalled record for build [%s]" % build['id'])
                self.sql.deleteRCMDrecord(build['id'])

    ##############################################
    def generateJenDataObjDo(self,jobobj,ptype,job_id,pname=None):

        '''Generate Jenkins data object for a single pipeline.'''

        # Single pipelines could be as stand alone as well as part of multipieline
        for buildref in jobobj['builds']:

            self.log.debug("Processing [%s] instance data" % buildref['number'])

            # Get instance REST API url
            url = buildref['url']

            # Generate build object from Jenkins data
            build = self.jen_data_collector.generateBuildObj(url)
            build['ptype'] = ptype
            if pname:
                build['parent_pipe'] = pname

            # Set possible triggers list and dependency direction but only if
            # data is presented
            trgiers = self.jen_data_collector.triggeredList(build['id'])

            if trgiers:
                build['depinst'] = trgiers
                build['depdirect'] = 'downstream'
                self.log.debug("saving downstream triggered data [%s]" % build['depinst'])
            else:
                self.log.debug("No downstream triggered data")

            # See if we need to further process current instance
            iname = str(build['name'])
            iname = iname.lstrip('#')

            if self.isExistsAndStable(iname,job_id):
                # This instance is already in DB and it's state did not change.
                # No need to further process such instance
                self.log.info("Instance [%s] is already in DB and stable..." % iname)
                continue

            # This is a new instance or has unstable state
            self.log.info("Processing [%s] instance " % iname)

            # Process instance stages data
            self.generateJenDataStages(url,build,iname,job_id)

            # Process possible user pending input
            self.processPendingInput(build)

            # Release used resources
            del build

    ##############################################
    def generateJenDataObjMulti(self,buildobj,job_id):

        '''Generate Jenkins data object for a multiple pipeline.'''

        #The multi pipeline format is differnt from standart
        self.log.debug("Generating Jenkins data object for multiple pipeline")

        #This is a build data object similar but more simple to standart
        #pipeline strucuture
        build = dict()
        build["stagelst"] = list()
        build["id"]       = 0
        build["name"]     = buildobj['displayName']
        build["started"]  = None
        build["duration"] = None
        build["estimate"] = None
        build["progress"] = None
        build["result"]   = "None"
        build['causes']   = None
        build["coverage"] = None
        build['comments'] = ''
        build['ptype'] = 'multi'

        #This is the multi pipleine object which holds multi pipe name as well
        #as it's child pipelines names
        plst = list()
        [ plst.append(pp['name']) for pp in buildobj['jobs'] if pp['color'] != 'disabled']

        multi = dict()
        multi['name']        = build["name"]
        multi['childs_list'] = plst

        # Upload multi object to DB
        self.upload2Multi(multi,job_id)

        # Upload build object into DB
        self.upload2DB(build,job_id,build["name"])

        # Release used resources
        del build

    ############################################################
    def dataProcessJenkinsData(self):

        '''Processing Jenkins data and upload MYSQL upload data flow'''

        self.log.info("Starting Jenkins MYSQL data upload process")

        #Run collector to pull data from Jenkins. We now run collector in sequences
        #each sequence pulls data for one pipeline instance. After each sequence we
        #push data into DB. Also prior to push we check state of instance. Currently
        #instances in SUCCESFULL and FAILED state which already exists in DB are not
        #being pulled again

        # Create instances to pull url
        url = "%s/%s/%s/%s" % (self.hostname,PIPEBASE,self.project,PIPESFX)

        #Get instances list for current pipeline
        jobobj =  self.jen_data_collector.getInstancesList(url)

        # Get this job id from BuildJobs table. If need create new record
        job_id = self.sql.getJobID(self.project, self.collector_id)

        # Here we store resulting jenkins data object. In case of standard
        # pipeline there will be only one entry. In case of Multi the resulting
        # list will include several data objects
        if 'jobs' in jobobj:
            # This is a multipipeline case
            self.log.info("Detected pipeline type : Multiple")

            # Generate data object for multiple pipeline and add to objects todo list
            self.generateJenDataObjMulti(jobobj,job_id)

            # Get list of mulitpipelines child pipelines urls
            pipelst = self.jen_data_collector.getPipeChildren(jobobj)
            parname = jobobj['displayName']

            # We have a list of single pipeline urls
            for url in pipelst:
                url = "%s/%s" % (url,PIPESFX)

                self.log.debug("Multiple : Processing child url - %s" % url)

                # get data specific for this url
                childobj = self.jen_data_collector.getInstancesList(url)

                # Now see how we were called. If we need to get full data set
                if self.depth:    # This means we want to pull data for all builds
                    self.log.info("Running max depth request")

                    url="%s?%s" % (url,'tree=allBuilds[url,number]')
                    urlsobj = self.jen_data_collector.getInstancesList(url)

                    #Owerwrite restricted builds section
                    childobj['builds'] = urlsobj['allBuilds']
                else:
                    self.log.info("Running standart depth request")

                # Get this job id from BuildJobs table. If need create new record
                job_id = self.sql.getJobID(childobj['displayName'],self.collector_id,parname)

                # generate data object for single pipeline which is child to
                # multiple pipeline parent
                self.generateJenDataObjDo(childobj, 'single', job_id, parname)
        else:
            #This is a single pipeline case.
            #Now generate data object and add it to list as single entry
            self.log.info("Detected pipeline type : Standart")
            self.generateJenDataObjDo(jobobj, 'single', job_id)

################################################################
################### MAIN TESTING PART ##########################
################################################################
if __name__ == '__main__':

    (jcolid,depth) = parseParams()
    jenObj = DataManagerJenkins(jcolid,depth)
    jenObj.dataProcessJenkinsData()

