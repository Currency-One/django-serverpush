# -*- encoding: utf-8 -*-
import logging
import tornadio2

from django.http import HttpRequest
from django.conf import settings
from django.contrib.auth.models import (
    User,
    AnonymousUser,
)

# odpowiedni SesisonStore na podstawie konfiguracji
if getattr(settings, 'SESSION_ENGINE') == 'django.contrib.sessions.backends.cache':
    from django.contrib.sessions.backends.cache import SessionStore
elif getattr(settings, 'SESSION_ENGINE') == 'django.contrib.sessions.backends.db':
    from django.contrib.sessions.backends.db import SessionStore
elif getattr(settings, 'SESSION_ENGINE') == 'django.contrib.sessions.backends.cached_db':
    from django.contrib.sessions.backends.cached_db import SessionStore
elif getattr(settings, 'SESSION_ENGINE') == 'redis_sessions.session':
    from redis_sessions.session import SessionStore
else:
    from django.contrib.sessions.backends.db import SessionStore

from .exceptions import catch_exceptions
from .events import incoming_messages

logger = logging.getLogger(__name__)


class Connection(tornadio2.SocketConnection):
    ANONYMOUS = 'anonymous'

    def __init__(self, *args, **kwargs):
        super(Connection, self).__init__(*args, **kwargs)
        self.handshake = True

    def is_anonymous(self):
        try:
            return not self.request.user.is_authenticated()
        except:
            return True

    def get_user_id(self):
        try:
            if not self.request.user.is_authenticated():
                return self.ANONYMOUS
            else:
                return self.request.user.pk
        except:
            return self.ANONYMOUS

    @tornadio2.event('user_message')
    @catch_exceptions
    def user_event(self, **message):
        handler_id = message.get("message_handler_id", None)
        if handler_id and handler_id in incoming_messages:
            incoming_messages[handler_id](self, **message)
        else:
            logger.warning("No handler for id %s at %s" % (handler_id, self.request.path,))

    @tornadio2.event('login')
    @catch_exceptions
    def login(self, **message):
        if self.handshake:
            cookies = self.session.info.cookies
            try:
                self.timestamp = float(message['timestamp'])
            except:
                self.timestamp = None
            self.request = HttpRequest()
            self.request.path = message.get('url', '/')
            # TODO(hamax): path_info is not always full path
            self.request.path_info = self.request.path
            self.request.method = 'GET'
            self.request.GET = parse_params(message.get('GET', ''))
            self.request.COOKIES = parse_cookies(cookies)
            # set to XMLHttpRequest so that request.is_ajax() returns True
            self.request.META['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'
            self.events = message.get('events', [])

            # auth
            #self.request.session = {}
            self.request.user = AnonymousUser()
            session_id = self.request.COOKIES.get(settings.SESSION_COOKIE_NAME)
            if session_id:
                self.request.session = SessionStore(session_key=session_id)
                if '_auth_user_id' in self.request.session:
                    self.request.user = User.objects.get(pk=self.request.session['_auth_user_id'])

            self.handshake = False
            self.tracker.connect(self)

    @catch_exceptions
    def on_close(self):
        self.tracker.disconnect(self)


def parse_params(params):
    try:
        return dict([p.split('=') for p in params[1:].split('&')])
    except:
        return {}


def parse_cookies(cookieString):
    output = {}
    cookieString = unicode(cookieString)
    cookieString = cookieString.replace('Set-Cookie: ', '')
    for m in cookieString.splitlines():
        try:
            k, v = m.split('=', 1)
            output[k] = v
        except:
            continue
    return output
