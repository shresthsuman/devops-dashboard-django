#!/usr/bin/env python

#####################################################
import configparser
import django
import logging
import re
import os
import pytz
import time
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append('../../')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dashboard.settings")
django.setup()

sys.path.append('jenkins')
sys.path.append('jira')

from pprint import pprint
from datetime              import datetime
from django.utils          import timezone
from django.utils.timezone import utc
from dataLogger            import initLog
from dataManagerJenkins    import DataManagerJenkins
from dataManagerJira       import DataManagerJira


from ip16dash.models import (
    Remote,
)

###############################################
############## GLOBAL VARIABLES ###############
###############################################

config = configparser.ConfigParser()
config.read("dm.conf")

LOGNAME  = config.get('config','LOGNAME_DM').replace("'","")
LOGLEVEL = config.get('config','LOGLEVEL_DM').replace("'","")
LOGFILE  = config.get('config','LOGFILE_DM').replace("'","")
LOGDIR   = config.get('config','LOGDIR').replace("'","")

#####################################################
############### CLASS DEFENITION ####################
#####################################################

class DataManager():

        ###########################################
        def __init__(self,logdir=LOGDIR,logfile=LOGFILE,loglevel=LOGLEVEL,logname=LOGNAME):

                '''Initialising DataManager object'''

                loglevel = eval('logging.' + os.getenv('LOGLEVEL', loglevel))
                self.log = initLog(logdir, logfile, loglevel, logname)

        ###########################################
        def getRemotesList(self):

            '''
                Get enabled collectors list. Skip disabled
            '''

            coll_list = Remote.objects.values('id','name','type','last_run','next_run').filter(enabled=True)
            return coll_list

        ###########################################
        def ready2Run(self,lastrun,nextrun,id):

            '''
                Detect if need to run this collector at this iteration
            '''

            currun  = datetime.utcnow().replace(tzinfo=utc)
            delta = (currun - lastrun).total_seconds()

            if  delta < nextrun:
                #Not enough time passed since last run
                self.log.debug("Not reached [%s] threshold for [%s] remote" % (nextrun,id))
                return False

            #This is time to run collector
            self.log.debug("Reached [%s] threshold for [%s] remote" % (nextrun, id))
            return True

        ###########################################
        def updateRemoteTS(self,cid):

            '''Update last_run filed of supplied collector with new now timestamp'''

            self.log.debug("Updating last_run field for [%s] remote" % id)

            tnow = timezone.now()
            Remote.objects.filter(id=cid).update(last_run=tnow)

        ###########################################
        def runRemotes(self):

            '''Runs remote collectors'''

            # Get list of collecotrs to run
            coll_list = self.getRemotesList()

            # For each collector get time to run parameters
            for rec in coll_list:

                #If no data for lastrun and nextrun continue to next collector
                if rec['last_run'] == None or rec['next_run'] == None:
                    self.log.warn("Skipping [%s] collector ... last/next run parameters are not set" % rec['name'])
                    continue

                # Check if time had come to run current collector.
                # Otherwise go to next collector.
                if not self.ready2Run(rec['last_run'],rec['next_run'],rec['id']):
                    self.log.info("Skipping [%s] collector ... last/next run delta is not reached" % rec['name'])
                    continue

                # Run this collector
                if re.match('[Jj]ira', rec['type']):
                    self.log.info("Processing [%s] %s collector" % (rec['name'],rec['type']))
                    obj = DataManagerJira(rec['id'])
                    obj.dataProcessJiraData()

                elif re.match('[Jj]enkins', rec['type']):
                    self.log.info("Processing [%s] %s collector" % (rec['name'], rec['type']))
                    obj = DataManagerJenkins(rec['id'])
                    obj.dataProcessJenkinsData()

                else:
                    #If we are here then not supported collector type
                    self.log.error("Unsupported [%s] collector type" % rec['type'])
                    raise ValueError("Unsupported [%s] collector type" % rec['type'])

                #Update last_run setting for current remote
                self.updateRemoteTS(rec['id'])

        ###########################################
        def run(self):

                '''Running DataManager instance'''

                self.log.info("Executing DataManager run ....")

                #Run remote collectors
                self.runRemotes()

#####################################################
################ MAIN PART ##########################
#####################################################
if __name__ == '__main__':
       dm_obj = DataManager()
       dm_obj.run()
