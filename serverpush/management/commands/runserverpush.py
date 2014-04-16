# -*- coding: utf-8 -*-
from os import path as op

import tornado.web
import tornadio2
import tornadio2.router
import tornadio2.server

from django.conf import settings
from django.core.management.base import BaseCommand

from .cache import patch
from .connection import Connection
from .notifier import Notifier
from .tracker import Tracker


class Command(BaseCommand):
    def handle(self, *args, **options):
        # set tracker object
        Connection.tracker = Notifier.tracker = Tracker()

        # use the routes classmethod to build the correct resource
        router = tornadio2.router.TornadioRouter(Connection,
            dict(websocket_check=False,
                enabled_protocols=[
                'websocket',
                #'flashsocket',
                'xhr-polling',
                'jsonp-polling',
                'htmlfile',
                ]
            )
        )

        r = router.apply_routes([
             #(r"/WebSocketMain.swf", WebSocketFileHandler),
        ])
        # configure the Tornado application
        application = tornado.web.Application(r,
            socket_io_port=settings.SERVERPUSH_PORT,
            flash_policy_port=getattr(settings, 'SERVERPUSH_FLASH_PORT', 10843),
            flash_policy_file=op.join(settings.ROOT_PATH, "flashpolicy.xml"),
        )

        notifier = tornado.web.Application(
            [(r"/notify", Notifier)],
        )
        notifier.listen(settings.SERVERPUSH_NOTIFIER_PORT, '0.0.0.0')

        #logger.setLevel(logging.INFO if getattr(settings, "PRODUCTION", False) else logging.DEBUG)

        # patch django orm
        patch()

        ssl_options = None
        if getattr(settings, "SERVERPUSH_PROTOCOL", "HTTP") == "HTTPS":
            cert = getattr(settings, "SSL_CERT", None)
            cert_key = getattr(settings, "SSL_CERT_KEY", None)
            if cert and cert_key and op.exists(cert) and op.exists(cert_key):
                ssl_options = {
                    "certfile": cert,
                    "keyfile": cert_key,
                }
        try:
            tornadio2.server.SocketServer(application, ssl_options=ssl_options)

        except KeyboardInterrupt:
            print "Ctr+C pressed; Exiting."
