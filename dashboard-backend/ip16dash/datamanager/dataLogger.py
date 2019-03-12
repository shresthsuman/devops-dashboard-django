import logging
import os
import sys

from logging.handlers import RotatingFileHandler
from logging import handlers

###########################################
LOG_LEVELS_LIST = ['ERROR','WARN','INFO','DEBUG']
LOGLEVEL = logging.INFO
if 'LOGLEVEL' in os.environ:
    LOGLEVEL = os.environ['LOGLEVEL']

    if not LOGLEVEL in LOG_LEVELS_LIST:
        print("ERROR : Unrecognized [%s] loglevel" % LOGLEVEL)
        sys.exit()

###########################################

def initLog(logdir,logname,loglevel,loggername='collector'):

    #Create logdir in case it is missing
    if not os.path.exists(logdir):
        os.makedirs(logdir)

    #Define logfile path
    logfile = os.path.join(logdir,logname)

    log = logging.getLogger(loggername)
    log.setLevel(loglevel)

    frmt = logging.Formatter('[%(name)s] # [%(levelname)-5.5s] # [%(asctime)s] # %(message)s')

    out_hdlr = logging.StreamHandler(sys.stdout)
    out_hdlr.setFormatter(frmt)
    out_hdlr.setLevel(loglevel)

    log.addHandler(out_hdlr)

    f_hdlr = handlers.RotatingFileHandler(logfile, maxBytes=(1048576*5), backupCount=7)
    f_hdlr.setFormatter(frmt)
    log.addHandler(f_hdlr)

    return log
