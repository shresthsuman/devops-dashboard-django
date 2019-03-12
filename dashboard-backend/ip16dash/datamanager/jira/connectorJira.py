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

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pprint        import pprint
from requests.auth import HTTPBasicAuth
from dataLogger    import initLog

from connectorJiraDjangoSQL import ConnectorJiraDjangoSQL

###############################################
############## GLOBAL VARIABLES ###############
###############################################

config = configparser.ConfigParser()
config.read("/app/ip16dash/datamanager/jira/dm.conf")

LOGNAME  = config.get('config','LOGNAME_JIRA_CN').replace("'","")
LOGLEVEL = config.get('config','LOGLEVEL_JIRA_CN').replace("'","")
LOGFILE  = config.get('config','LOGFILE_JIRA_CN').replace("'","")
LOGDIR   = config.get('config','LOGDIR').replace("'","")

headers={'Content-Type': 'application/json'}
URL_S  = 'rest/auth/latest/session'
URL_J  = 'rest/api/2'
HEADER = {'Content-Type': 'application/json'}

MAX_RESULTS = 10000

################################################
############### UTILILY FUNCTIONS ##############
################################################

def parseParams():

    parser = argparse.ArgumentParser()

    parser.add_argument('-r','--ruser',help='Proxy user',          default=None)
    parser.add_argument('-R','--rpass',help='Proxy password',      default=None)
    parser.add_argument('-p','--proxy',help='Proxy server',        default='')
    parser.add_argument('-j','--juser',help='Jira user',           required=True)
    parser.add_argument('-J','--jpass',help='Jira password',       required=True)
    parser.add_argument('-u','--url',  help='Jira server url',     required=True)
    parser.add_argument('-b','--base', help='Jira base url',       default='')
    parser.add_argument('-n','--name', help='Issue/Project name',  required=True)

    parser.add_argument('-a', '--auth',help='Authorisation type',  default='BasicAuth',
                        choices=['BasicAuth', 'BasicAuthProxy'])

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-P', '--project',help='Project to retreive data for', action='store_true')
    group.add_argument('-I', '--issue',  help='Issue to retreive data for',   action='store_true')

    args = parser.parse_args()

    if args.auth == 'BasicAuthProxy' and ( args.ruser == None or args.rpass == None):
        raise ValueError('Proxy setting mismatch!!! Missing proxy Username/password !!!')

    if args.auth == 'BasicAuth' and (args.ruser or args.rpass):
        raise ValueError('Proxy setting mismatch!!! Use reverse proxy credentials with BasicAuthProxy setting ...')

    return args.ruser,args.rpass,args.juser,args.jpass,args.url,args.auth,args.proxy,args.base,args.issue,args.project,args.name

################################################
############ CLASS DEFINITIONS #################
################################################
class JIRAConnector():

    ######################################################################
    def __init__(self,url,juser,jpass,authtype,ruser=None,rpass=None,proxy='',base='jira',logdir=LOGDIR,logfile=LOGFILE,loglevel=LOGLEVEL,logname=LOGNAME):

        '''Jira connector constructor :
            - url      - server to connect
            - juser    - jira user to use
            - jpass    - jira pass to use
            - ruser    - proxy user to use [Default - None]
            - rpass    - proxy pass to use [Default - None]
            - authtype - Athorization type [Default - BasicAuth]
            - proxy    - Proxy server name if exists [Default - '']
            - base     - REST API base url [Default - 'jira']
        '''

        loglevel = eval('logging.' + os.getenv('LOGLEVEL', loglevel))

        self.log      = initLog(logdir, logfile, loglevel, logname)
        self.s_url    = "%s/%s/%s" % (url,base,URL_S)
        self.j_url    = "%s/%s/%s" % (url,base,URL_J)
        self.juser    = juser
        self.jpass    = jpass
        self.ruser    = ruser
        self.rpass    = rpass
        self.authtype = authtype
        self.headers  = HEADER
        self.proxy    = proxy

        self.sql = ConnectorJiraDjangoSQL()

        # Set noproxy setting
        ips_no_proxy = self.sql.getNoProxyIPsLst()

        if ips_no_proxy:
            ips_no_proxy_str = ','.join(ips_no_proxy)
            os.environ['NO_PROXY'] = "%s;%s" % (os.environ['NO_PROXY'], ips_no_proxy_str)

        if self.authtype == 'BasicAuthProxy':
            self.auth     = HTTPBasicAuth(self.ruser, self.rpass)
        else:
            self.auth = ''

        self.authdata = json.dumps(
            {
                'username': self.juser,
                'password': self.jpass,
            }
        )

        #Get connection session
        self.session = self.getSession()

    #########################################################################
    def getSession(self):

        try:
            session = requests.session()

        except Exception as e:
            self.log.error("Failed in session establishing with error : [%s]",e)
            raise

        if self.authtype == 'BasicAuthProxy':
            res = session.post(
                url     = self.s_url,
                auth    = self.auth,
                proxies = self.proxy,
                headers = self.headers,
                data    = self.authdata
            )
        else:
            session.auth=(self.juser,self.jpass)
            res = session.get(
                url     = self.s_url,
                #headers = self.headers,
                proxies = self.proxy,
                #data    = self.authdata
            )

        if res.status_code != 200:
            raise ValueError("Failed to connect to [%s] url with rc [%s] and reason [%s]" % (self.s_url, res.status_code, res.reason))

        return session

    #########################################################################
    def getIssueByName(self,issueName):

        #url = "%s/issue/%s" % (self.j_url,issueName)
        url = "%s/search?jql=issue=%s&expand=renderedFields" % (self.j_url, issueName)
        req = self.fetchData(url)
        return json.loads(req.text)

    ##########################################################################
    def getIssuesAllFromProject(self,projName):

        url = "%s/search?jql=project=%s&maxResults=%s&expand=renderedFields&validateQuery=True" % (self.j_url,projName,MAX_RESULTS)
        req = self.fetchData(url)

        return json.loads(req.text)

    ########################################################################
    def fetchData(self,url):

        try:
            req = self.session.get(
                url=url,
                #auth=self.auth,
                headers=HEADER
            )

        except Exception as e:
            self.log.error("Failed in fetch data command [%s] with error : [%s]" % (url,e))
            raise

        return req

#################################################
################ MAIN PART ######################
#################################################
if __name__ == "__main__":

    #Parse CLI arguments
    (ruser,rpass,juser,jpass,url,auth,proxy,base,issue,project,name) = parseParams()

    #Initialise JIRA connector
    jira = JIRAConnector(url,juser,jpass,auth,ruser,rpass,proxy,base)

    #Based on supplied options perform requested issue/project data pull
    if project:
        res = jira.getIssuesAllFromProject(name)
    else:
        res = jira.getIssueByName(name)

    pprint(res)
