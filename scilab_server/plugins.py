import pkg_resources
from .settings import *


def load_plugins():

    plugins = {}
    for ep in pkg_resources.iter_entry_points(group='ifmo_xbserver.v1'):
        plugin = ep.plugin.load()
        if hasattr(plugin, 'configuration_section'):
            plugin.configuration = PLUGIN_CONFIGURATION.get(plugin.configuration_section, {})
        plugins.update({ep.name: plugin})
    return plugins
