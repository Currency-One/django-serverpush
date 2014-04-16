# -*- coding: utf-8 -*-
'''
    Event notifier.
'''
import tornado.web

from exceptions import catch_exceptions


class Notifier(tornado.web.RequestHandler):

    def post(self):
        event = self.get_argument('event', None)
        user = self.get_argument('user', None)
        tm = self.get_argument('gen_timestamp', None)
        #pozostale parametry
        kwargs = dict((key, val[0] if val and isinstance(val, list) else val) for \
                key,val in self.request.arguments.items() if \
                key not in ['event', 'user', 'gen_timestamp'])
        try:
            self._handle(event, user, gen_timestamp=tm, **kwargs)
            pass
        except Exception as ex:
            self.write('fail')
            raise ex

    @catch_exceptions
    def _handle(self, event=None, user=None, channel=None, gen_timestamp=None, **kwargs):
        if not event and channel:
            event = channel
        if event is None:
            raise Exception('request nie zawiera zdarzenia')
        self.tracker.event(event, gen_timestamp, user, **kwargs)
