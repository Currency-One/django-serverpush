# -*- coding: utf-8 -*-
'''
    Client functions (for django application).
'''
import urllib
import time
import logging
import inspect

from django.conf import settings
from django.contrib.auth.models import User

from .events import (
    ServerPushEventException,
    ServerPushEvent
)
from .active_events import active_events

from celery.task import task

logger = logging.getLogger('serverpush')


class PingNotifierException(Exception):
    pass


def ping_notifier(event, user=None, celery_task=True,  **kwargs):
    '''
        Sygnalizuje zdarzenie @event, dla uzytkownika @user (instancja / pk) , @kwargs sa przekazywane do handlera
    '''
    if settings.IS_TEST:  # SKip dla testow
        return False

    force_celery_task = getattr(settings, 'SERVERPUSH_NOTIFIER_CELERY_TASK', None)
    tm = time.time()  # timestamp zlecenia powiadomienia

    logger.info(inspect.getouterframes(inspect.currentframe())[1][1:])

    try:
        if (force_celery_task is None and celery_task) or force_celery_task:
            ping_notifier_task.delay(event, gen_timestamp=tm, user=user, **kwargs)
        else:
            ping_notifier_task(event, gen_timestamp=tm, user=user, **kwargs)
    except:
        raise PingNotifierException


def signal_logout(user, celery_task=True):
    ping_notifier(event=ServerPushEvent.SOCKETIO_LOGOUT, user=user, celery_task=celery_task)


@task(name='serverpush-ping-notifier')
def ping_notifier_task(event, gen_timestamp, user=None, **kwargs):
    try:
        if not active_events.has_key(event):
            raise ServerPushEventException('Niezarejestrowany event: %s' % event)

        if not user and not active_events[event].is_broadcast_event():
            raise ServerPushEventException(
                'Brak id usera a zdarzenie nie jest broadcastem: %s' % event)

        data = {
            'event': event,
            'user': user.pk if isinstance(user, User) else user,
            'gen_timestamp': gen_timestamp,
        }
        if not user:
            del data['user']

        data.update(kwargs)

        url = 'http://%s:%d/notify' % (settings.SERVERPUSH_NOTIFIER_HOST,
                                       settings.SERVERPUSH_NOTIFIER_PORT)
        urllib.urlopen(url, urllib.urlencode(data))

    except Exception as e:
        logger.error(e)
