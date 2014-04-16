# -*- coding: utf-8 -*-
'''
    Tracker groups connections and events into channels.
'''
import logging

from channel import Channel
from events import *

from .active_events import active_events

logger = logging.getLogger('serverpush')


class Tracker(object):

    def generate_id(self):
        ids = 1
        while 1:
            yield ids
            ids += 1

    def __init__(self):

        # mapa: event -> user_id -> connection
        self.channels = {}
        # mapa: user_id -> lista eventow
        self.users = {}

        self.id_gen = self.generate_id()
        #historia
        self.history = {}
        self.shared = {}
        for ev in store_history:
            self.history[ev] = EventHistory(ev, active_events[ev]._event_type)

        for ev in active_events:
            self.channels[ev] = Channel(ev, tracker=self,
                                        history=self.history.get(ev, None))

    def connect(self, conn):
        '''
            Nawiazywanie polaczenia, inicjalizujace eventy
        '''
        #jesli uzytkonik zalogowany id -> pk usera
        #if conn.request.user.is_authenticated():
        #    conn.id = conn.request.user.pk

        conn.id = self.id_gen.next()
        user_id = conn.get_user_id()

        logger.debug("New connection; user %s; path %s; conn_id %s " % (user_id,
                conn.request.path_info, conn.id))

        if user_id not in self.users:
            self.users[user_id] = {}

        #tworzymy kanaly dla wspieranych eventow i doklejamy zdarzenia
        for event in conn.events:
            if active_events.has_key(event):
                #niezalogowani uzytkownicy moga odbierac tylko broadcasty
                if active_events[event].is_init_event():
                    Channel.init_event(conn, event, shared=self.shared)

                if self.history.has_key(event):
                    self.history[event].send_history(conn)

                if not (active_events[event].is_broadcast_event() or
                        conn.request.user.is_authenticated()):
                    continue

                #XXX: nadmiarowe, w konstruktorze wszystkie kanaly sa inicjalizowane
                if not self.channels.has_key(event):
                    logger.error('Brak kanalu %s, to niepowinno miec miejsca' % event)
                    self.channels[event] = Channel(event, tracker=self,
                                        history=self.history.get(event, None))

                if not self.users[user_id].has_key(event):
                    self.users[user_id][event] = True

                self.channels[event].new_connection(conn)

    def disconnect(self, conn):
        '''
            Czyszczenie kolekcji po utracie polaczenia
        '''
        user_id = conn.get_user_id()

        if not self.users.has_key(user_id):
            #nie powinno sie zdarzyc, ale 'just in case'
            return

        #uwzglednia anonimowe polaczenia
        #XXX: moze sprawdzac czy mapowanie istnieje,
        #teoretycznie wieksza szansa ze beda nadmiarowe dane, niz ich nie bedzie
        for event in self.users[user_id].keys():
            try:
                del self.channels[event].connections[user_id][conn.id]
                logger.debug("Disconnect: user %s; conn_id %s; event %s" % (
                    user_id, conn.id, event
                ))
                if not self.channels[event].connections[user_id]:
                    del self.channels[event].connections[user_id]
            except AttributeError:
                continue
            except KeyError:
                continue

    # Caled by notify.py as a callback via server.py on a new event
    # notifies other connections and returns success status
    def event(self, event, gen_timestamp, user=None, **kwargs):
        '''
            Odpalany przez notifier po otrzymaniu requesta
        '''
        if user:
            user = int(user)

        if event == ServerPushEvent.SOCKETIO_LOGOUT:
            self.logout_event(user)
            return

        channel = self.channels.get(event, None)

        if channel:
            if channel.event.is_broadcast_event():
                channel.broadcast_event(gen_timestamp, **kwargs)

            elif channel.event.is_user_event():
                channel.user_event(user, **kwargs)

    def logout_event(self, user):
        '''
            Zdarzenie wylogowania -> przeladowuje wszystkie
            strony aktualnie zalogowanego uzytkownika
        '''
        logger.debug("Logout: user %s" % user)
        #wysylamy conajwyzej jeden komunikat do polaczenia
        connections_notified = {}
        if user is not None:
            if not self.users.has_key(user):
                return

            for event in self.users[user].keys():
                self.channels[event].logout_event(user, connections_notified)

        for con_id, con in connections_notified.items():
            self.disconnect(con)
