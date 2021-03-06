# -*- coding=utf-8 -*-

import logging
import logging.config
import time

from xqueue_api import XQueueSession

from scilab_server.plugins import load_plugins
from scilab_server.settings import *


logger = logging.getLogger(__name__)


def cleanup(cwd):
    cwd.rmtree_p()


def main():

    setup_logging()

    logger.info("Starting server...")
    logger.info("CONFIG_ROOT = %s" % CONFIG_ROOT)
    logger.info("CONFIG_FILE = %s" % CONFIG_FILE)
    logger.info("Opening env file: %s" % (CONFIG_ROOT / CONFIG_FILE))
    logger.info("xqueue url = %s" % XQUEUE_INTERFACE['url'])

    plugins = load_plugins()

    # Начинаем работу сервера
    while True:
        xsession = XQueueSession(base_url=XQUEUE_INTERFACE['url'],
                                 username=XQUEUE_INTERFACE['login'],
                                 password=XQUEUE_INTERFACE['password'],
                                 queue=XQUEUE_INTERFACE['queue'],
                                 autoconnect=True)

        length_result, length = xsession.get_len()
        if length_result and length:

            logger.info("Non zero length, retrieve submission")

            xobject_result, xobject = xsession.get_xobject()
            if xobject_result:

                body = json.loads(xobject.body)
                try:
                    # TODO: Temporary compatibility: default plugin is scilab
                    active_plugin = plugins[body.get('submission_sender', 'ifmo_xblock_scilab')]
                    method = body.get('method')
                except KeyError or ValueError:
                    logger.error('Unknown plugin, or plugin not loaded: %s' % body.get('submission_sender'))
                    continue

                logger.info('Active plugin: %s' % active_plugin.__class__.__name__)
                logger.info('Received method: {method}'.format(method=method))

                result = active_plugin.handle(method, xobject=xobject)

                xsession.put_xresult(result)
                logger.info("put_xresult completed")

            # decrease length size
            length -= 1

        elif not length_result:

            # In case of error length will contain detailed requests error message
            logger.error(length)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
