# -*- coding: utf-8 -*-
import importlib

from django.conf import settings

from serverpush.events import (
    ServerPushEvent
)

events_module = importlib.import_module(settings.SERVEREVENTS_MODULE)
active_events = getattr(events_module, 'ACTIVE_EVENTS', {})
incoming_messages = getattr(events_module, 'ACTIVE_EMITS', {})
active_events[ServerPushEvent.SOCKETIO_LOGOUT] = lambda x: {}
