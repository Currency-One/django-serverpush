# -*- coding: utf-8 -*-
import logging

from devlib.serverpush.active_events import active_events


logger = logging.getLogger('serverpush')


class Channel(object):

    def __init__(self, name, tracker, history=None):
        self.tracker = tracker
        self.name = name
        self.event = active_events[name]
        self.history = history
        self.connections = {}

    def new_connection(self, conn):
        '''
            Rejestrowanie nowego polaczenia
        '''
        key = conn.get_user_id()

        if not self.connections.has_key(key):
            self.connections[key] = {}
        self.connections[key][conn.id] =  conn

    @staticmethod
    def init_event(conn, event_name, **kwargs):
        '''
            Wysyla event na polaczenie
        '''
        buffer = SendBuffer()

        buffer.append(conn, {
            'name' : event_name,
            'payload' : active_events[event_name].execute(conn.request, **kwargs),
        })
        buffer.send()

    # Called by Tracker on new event
    def user_event(self, user_id, **kwargs):
        '''
            Wiadomosc do zalogowanego usera
        '''
        user_connections = self.connections.get(int(user_id), None)
        if not user_connections:
            return False

        buffer = SendBuffer()

        if not kwargs.has_key('shared'):
            if kwargs:
                kwargs['shared'] = self.tracker.shared
            else:
                kwargs = {"shared": self.tracker.shared}

        user = None
        for con in user_connections.values():
            if not user:
                user = con.request.user
            buffer.append(con, self.generate_message(user, **kwargs))

        buffer.send()
        logger.debug("User event: user %s ; event %s" % (user_id, self.name))

        return True

    def broadcast_event(self, event_timestamp, **kwargs):
        '''
            Broadcast do wszystkich userow (i anonimowych)
        '''
        buffer = SendBuffer()

        if not kwargs.has_key('shared'):
            if kwargs:
                kwargs['shared'] = self.tracker.shared
            else:
                kwargs = {"shared": self.tracker.shared}

        broadcast_msg = self.generate_message(**kwargs)
        if not broadcast_msg['payload']:
            return

        if self.history:
            self.history.append(broadcast_msg, event_timestamp  )

        for user_connections in self.connections.values():
            for con in user_connections.values():
                buffer.append(con, broadcast_msg)

        buffer.send()
        logger.debug("Broadcast event: event %s" % ( self.name))


        return True

    def logout_event(self, user_id, connections_notified):
        user_connections = self.connections.get(int(user_id), None)

        if not user_connections:
            return False

        msg = {"name": "socketio_logout", "payload": ""}
        buffer = SendBuffer()
        for con in user_connections.values():
            if not connections_notified.has_key(con.id):
                buffer.append(con, msg)
                connections_notified[con.id] = con

        buffer.send()
        return True

    def generate_message(self, user=None, **kwargs):
        '''
            Generowanie wiadomosci do wyslania,
        '''
        if self.event.is_broadcast_event():
            msg = self.event.execute(**kwargs)
        else:
            msg = self.event.execute(user, **kwargs)

        return {
            "name": self.name,
            "payload": msg,
        }

class SendBuffer():
    def __init__(self):
        self.buffer = []

    def append(self, conn, data):
        self.buffer.append([conn, data])

    def send(self):
        for package in self.buffer:
            package[0].send(package[1])

# Default serializer for data from database
def extract(request, object, fields):
    data = {}
    for field in fields:
        data[field] = eval(fields[field])
    return data
