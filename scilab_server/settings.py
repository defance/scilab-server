from path import path
import os
import json

from .env.common import *

PROJECT_ROOT = path(__file__).abspath().dirname()
REPO_ROOT = PROJECT_ROOT.dirname()
ENV_ROOT = REPO_ROOT.dirname()
CONFIG_ROOT = path(os.environ.get('CONFIG_ROOT', ENV_ROOT))

with open(CONFIG_ROOT / "scilab-server.env.json") as env_file:
    ENV_TOKENS = json.load(env_file)

SCLAB_SERVER_URL = ENV_TOKENS.get('SCLAB_SERVER_URL', SCLAB_SERVER_URL)
SCLAB_SERVER_PORT = ENV_TOKENS.get('SCLAB_SERVER_PORT', SCLAB_SERVER_PORT)
SCILAB_EXEC = ENV_TOKENS.get('SCILAB_EXEC', SCILAB_EXEC)
SCILAB_HOME = ENV_TOKENS.get('SCILAB_HOME', SCILAB_HOME)

XQUEUE_INTERFACE = ENV_TOKENS.get('XQUEUE_INTERFACE', XQUEUE_INTERFACE)
