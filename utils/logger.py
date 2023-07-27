import logging
from logging.handlers import RotatingFileHandler

logpath = "logs/"
filename = "log.txt"

logging.basicConfig(handlers=[RotatingFileHandler(filename=logpath+filename,
                                                  mode='w', maxBytes=512000, backupCount=4)], level=logging.INFO,
                    format='[%(levelname)s] %(asctime)s: %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p')

logger = logging.getLogger("cSMTP")