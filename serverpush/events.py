# -*- coding: utf-8 -*-
import time
from collections import deque

from django.conf import settings


class ServerPushEventException(Exception):
    pass


class EventHistory(object):
    HISTORY_LENGTH = 10

    def __init__(self, event_name, event_type):
        if event_type != ServerPushEvent.BROADCAST_EVENT:
            raise NotImplementedError()
        self.event_queue = deque(maxlen=self.HISTORY_LENGTH)

    def append(self, data, timestamp=None):
        self.event_queue.append({
            'timestamp': timestamp or time.time(),
            'data': data,
        })

    def get_missed_events(self, gen_timestamp):
        return [data['data'] for data in self.event_queue if float(data['timestamp']) >
                float(gen_timestamp)]

    def send_history(self, conn):
        if conn is None or conn.timestamp is None:
            return
        for payload in self.get_missed_events(conn.timestamp):
            conn.send(payload)


class ServerPushEvent(object):

    '''
        Zdarzenia
    '''
    INIT_EVENT = 0
    USER_EVENT = 10
    BROADCAST_EVENT = 100

    EVENTS = (
        INIT_EVENT,
        USER_EVENT,
        BROADCAST_EVENT,
    )

    # domyslnie oprogramowane eventy
    SOCKETIO_LOGOUT = 'socketio_logout'

    ACTIVE_EVENTS = {}

    def __init__(self, event=None, event_type=None, shared=False):
        self._event = event

        if event_type not in ServerPushEvent.EVENTS:
            raise Exception('Niepoprawny typ zdarzenia')

        self._event_type = event_type
        self._shared = shared

    @staticmethod
    def register_event(event, type):
        pass

    def is_user_event(self):
        return self._event_type == ServerPushEvent.USER_EVENT

    def is_init_event(self):
        return self._event_type == ServerPushEvent.INIT_EVENT

    def is_broadcast_event(self):
        return self._event_type == ServerPushEvent.BROADCAST_EVENT

    def execute(self, *args, **kwargs):
        if self._event:
            return self._event(*args, **kwargs)
        else:
            raise Exception('Zdarzenie nie jest zaimplementowane')


def serverpush_init(user, **kwargs):
    return {'init': 'aasfas'}


def serverpush_broadcast(**kwargs):
    return {'broadcast': 'b'}


def serverpush_userevent(user, a=None, **kwargs):
    return {'hello': 'world' if a is None else a}


incoming_messages = {
}
events_module = __import__(settings.SERVEREVENTS_MODULE)
store_history = getattr(events_module, 'STORE_HISTORY', [])
