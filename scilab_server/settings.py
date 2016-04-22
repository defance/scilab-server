import logging
import json
import os

from path import path

from .env.common import *


PROJECT_ROOT = path(__file__).abspath().dirname()
REPO_ROOT = PROJECT_ROOT.dirname()
ENV_ROOT = REPO_ROOT.dirname()
CONFIG_ROOT = path(os.environ.get('CONFIG_ROOT', REPO_ROOT / "config"))
CONFIG_FILE = path(os.environ.get('SCILAB_ENV', "default.env.json"))

with open(CONFIG_ROOT / CONFIG_FILE) as env_file:
    ENV_TOKENS = json.load(env_file)

SCILAB_EXEC = ENV_TOKENS.get('SCILAB_EXEC', SCILAB_EXEC)
SCILAB_HOME = ENV_TOKENS.get('SCILAB_HOME', SCILAB_HOME)

XQUEUE_INTERFACE = ENV_TOKENS.get('XQUEUE_INTERFACE', XQUEUE_INTERFACE)

LOGGING_DEFAULT_PATH = path(PROJECT_ROOT / 'config' / 'logging.json')
LOGGING_DEFAULT_LEVEL = logging.INFO
LOGGING_ENV_KEY = 'LOG_CFG'

GRADER_ID = ENV_TOKENS.get('GRADER_ID', GRADER_ID)
