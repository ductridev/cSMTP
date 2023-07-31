import logging
import logging.handlers

logpath = "logs/"
filename = "logs.txt"

class ColorFormatter(logging.Formatter):
    """Logging Formatter to add colors to log messages"""
    green = "\x1b[32m"
    red = "\x1b[31m"
    reset = "\x1b[0m"

    format = "[%(levelname)s][%(name)s] %(asctime)s: %(message)s"

    def format(self, record):
        log_level_colors = {
            logging.DEBUG: self.green,
            logging.ERROR: self.red
        }

        log_level_color = log_level_colors.get(record.levelno, "")
        log_message = super().format(record)
        formatted_message = f"{log_level_color}{log_message}{self.reset}"
        return formatted_message

# datefmt='%m/%d/%Y %I:%M:%S %p'

# Create a logger and set the level
logger = logging.getLogger("cSMTP")
logger.setLevel(logging.INFO)

# Create a rotating file handler and set the formatter
file_handler = logging.handlers.RotatingFileHandler(filename=logpath+filename, mode='w', maxBytes=512000, backupCount=4)
file_formatter = ColorFormatter()
file_handler.setFormatter(file_formatter)

# Add the file handler to the logger
logger.addHandler(file_handler)