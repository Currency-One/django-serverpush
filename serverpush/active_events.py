# -*- coding: utf-8 -*-
from django.conf import settings
from .events import (
    ServerPushEvent
)

events_module = __import__(settings.SERVEREVENTS_MODULE)
active_events = getattr(events_module, 'ACTIVE_EVENTS')
incoming_messages = getattr(events_module, 'ACTIVE_EMITS')
active_events[ServerPushEvent.SOCKETIO_LOGOUT] = lambda x: {}
