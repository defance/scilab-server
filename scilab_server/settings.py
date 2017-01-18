import logging
import logging.config
import json
import os

from path import path

from xbserver_plugin import IfmoXBServerPlugin

from .env.common import *


PROJECT_ROOT = path(__file__).abspath().dirname()
REPO_ROOT = PROJECT_ROOT.dirname()
ENV_ROOT = REPO_ROOT.dirname()
CONFIG_ROOT = path(os.environ.get('CONFIG_ROOT', REPO_ROOT / "config"))
CONFIG_FILE = path(os.environ.get('SCILAB_ENV', "default.env.json"))

with open(CONFIG_ROOT / CONFIG_FILE) as env_file:
    ENV_TOKENS = json.load(env_file)

# SCILAB_EXEC = ENV_TOKENS.get('SCILAB_EXEC', SCILAB_EXEC)
# SCILAB_HOME = ENV_TOKENS.get('SCILAB_HOME', SCILAB_HOME)

XQUEUE_INTERFACE = ENV_TOKENS.get('XQUEUE_INTERFACE', XQUEUE_INTERFACE)

LOGGING_DEFAULT_PATH = path(REPO_ROOT / 'config' / 'logging.json')
LOGGING_DEFAULT_LEVEL = logging.INFO
LOGGING_ENV_KEY = 'LOG_CFG'

SERVER_ID = ENV_TOKENS.get('SERVER_ID', SERVER_ID)

ENABLE_SILENCE_MODE = ENV_TOKENS.get('ENABLE_SILENCE_MODE', ENABLE_SILENCE_MODE)
SILENCE_MODE = ENV_TOKENS.get('SILENCE_MODE', SILENCE_MODE)

ENABLED_PLUGINS = ENV_TOKENS.get('ENABLED_PLUGINS', ENABLED_PLUGINS)
PLUGIN_CONFIGURATION = ENV_TOKENS.get('PLUGIN_CONFIGURATION', PLUGIN_CONFIGURATION)


def setup_logging(
    default_path=LOGGING_DEFAULT_PATH,
    default_level=LOGGING_DEFAULT_LEVEL,
    env_key=LOGGING_ENV_KEY
):
    """
    Setup logging configuration
    """
    config_path = default_path
    value = os.getenv(env_key, None)
    if value:
        config_path = path(value)
    if config_path.exists():
        with open(config_path, 'rt') as f:
            config = json.load(f)
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=default_level)


def get_plugin_configuration(plugin=None):
    """
    If "plugin" is class -> reference retrieved from its "configuration_section"
    attribute.

    :param plugin:
    :return:
    """
    plugin_display_name = plugin
    if issubclass(plugin, IfmoXBServerPlugin):
        plugin = IfmoXBServerPlugin.configuration_section
        plugin_display_name = plugin.__name__

    configuration = {
        "GRADER_ID": "%s::%s" % (SERVER_ID, plugin_display_name)
    }

    configuration.update(PLUGIN_CONFIGURATION.get(plugin, {}))
    return configuration
