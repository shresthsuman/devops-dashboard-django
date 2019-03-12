#!/usr/bin/env python

import argparse
import configparser
import django
import getpass
import os
import sys

from pprint import pprint

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append('../../../')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dashboard.settings")
django.setup()

from connectorJenkinsDjangoSQL import ConnectorJenkinsDjangoSQL
from connectorJenkins          import ConnectorJenkins

####################################################
############ GLOBAL VARIABLES ######################
####################################################
DMCONF = '/app/ip16dash/datamanager/jenkins/dm.conf'

config = configparser.ConfigParser()
config.read(DMCONF)

PIPEBASE = config.get('config','PIPEBASE').replace("'","")
PIPESFX  = config.get('config','PIPESFX').replace("'","")
PIPEWFAPI= config.get('config','PIPEWFAPI').replace("'","")
PIPENODE = config.get('config','PIPENODE').replace("'","")
PIPELOG  = config.get('config','PIPELOG').replace("'","")

########################################################
################### UTILILY FUNCTIONS ##################
########################################################

######################################################
def cliParams():

    '''Read params supplied on CLI'''

    parser = argparse.ArgumentParser()

    parser.add_argument('-U', '--url',      default=None, help='URL to connect', )
    parser.add_argument('-u', '--username', default=None, help='Usename')
    parser.add_argument('-p', '--password', default=None, help='Password')
    parser.add_argument('-n', '--num',      default=None, help='Number of pipelines to load')

    args = parser.parse_args()

    return args.url,args.username,args.password,args.num

#######################################################
def readParams(url=None,username=None,password=None):

    '''Read interactively supplied params '''

    if url and username and password:
        #All mandatary params are already set no need to ask
        return url,username,password

    #Ask for url to connect
    if not url:
        url = input("Please provide url to connect : ")

    # Ask for username to connect
    if not username:
        username = input("Please provide username : ")

    # Ask for passowrd to connect
    if not password:
        password = getpass.getpass("Please provide password : ")

    #Test for bad input. Esentially if user just pressed enter
    if url == '' or username == '' or password == '':
        print("ERROR : Parameters url/user/pass cannot be empty string")
        sys.exit()

    return url,username,password

########################################################
#################### CLASS PART ########################
########################################################

######################################################
class RemoteJenkinsLoader():

    #############################################
    def __init__(self,hostname,username,password,num,pbase,psuffix,wfapi,pnode,plog):

        '''Class constructor'''

        if url == None or username == None or password == None:
            print("ERROR : Cannot initialize object with not set url/user/pass paramers")
            sys.exit()

        self.hostname = hostname
        self.username = username
        self.password = password
        self.pipeline = 'test'
        self.urlbase  = pbase
        self.urlsfx   = psuffix
        self.urlwfapi = wfapi
        self.urlnode  = pnode
        self.urllog   = plog
        self.type     = 'Jenkins'
        self.num      = num

        self.sql      = ConnectorJenkinsDjangoSQL()
        self.jenkins = ConnectorJenkins(self.hostname, self.username, self.password, self.pipeline, self.urlbase,self.urlsfx, self.urlwfapi, self.urlnode, self.urllog)
        return

    #############################################
    def getPipelinesList(self):

        '''Get pipelines list defined on Jenkins server'''
        jobobj = self.jenkins.getPipelinesList()
        return jobobj

    ##############################################
    def fillRemotesDB(self,pl_name):

        '''Prepare Remote object and send it for upload'''

        data = dict()
        data['url']      = self.hostname
        data['username'] = self.username
        data['password'] = self.password
        data['project']  = pl_name
        data['type']     = self.type
        data['name']     = pl_name

        self.sql.setConnectorConfig(data)
        return

    ###############################################
    def runOperation(self):

        '''Run pull/load pipelines operation'''

        #Get defined pipelines list from Jenkins server
        pl_lst = self.getPipelinesList()

        #For all retireved pipes excluding ones with status 'notbuilt'
        #send them to upload to remotes table
        for pl in pl_lst['jobs']:
            if pl['color'] == 'notbuilt':
                #Pipeline is not active no need to save it
                continue

            print("Loading [%s] pipleine configuration" % pl['name'])
            self.fillRemotesDB(pl['name'])

##########################################################
#################### MAIN PART ###########################
##########################################################

if __name__ == "__main__":

    (url,username,password,num)   = cliParams()
    (url, username, password) = readParams(url,username,password)
    obj = RemoteJenkinsLoader(url,username,password,num,PIPEBASE,PIPESFX,PIPEWFAPI,PIPENODE,PIPELOG)

    obj.runOperation()
