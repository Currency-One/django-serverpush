import logging
import urllib
import json

from paste import urlmap
import eventlet
import eventlet.wsgi
import eventlet.websocket
from csp_eventlet import Listener
import rtjp_eventlet

from protocol import HookboxConn
from notify import HookboxNotify
from error import ExpectedException

from demo.serverpush.handlers import EventTracker

eventlet.monkey_patch(all = False, socket = True, select = True)

logger = logging.getLogger('hookbox')
access_logger = logging.getLogger('access')

class HookboxServer(object):

	def __init__(self):	
		self._rtjp_server = rtjp_eventlet.RTJPServer()
		
		self.eventTracker = EventTracker()
		
		#comet and websocket
		self._root_wsgi_app = urlmap.URLMap()
		self.csp = Listener()
		self._root_wsgi_app['/csp'] = self.csp
		self._root_wsgi_app['/ws'] = self._ws_wrapper
		self._ws_wsgi_app = eventlet.websocket.WebSocketWSGI(self._ws_wsgi_app)
		
		#notifications
		self._notify_wsgi_app = urlmap.URLMap()
		self._notify_wsgi_app['/'] = HookboxNotify(self.eventTracker.event)

	def _ws_wrapper(self, environ, start_response):
		environ['PATH_INFO'] = environ['SCRIPT_NAME'] + environ['PATH_INFO']
		environ['SCRIPT_NAME'] = ''
		return self._ws_wsgi_app(environ, start_response)

	def _ws_wsgi_app(self, ws):
		access_logger.info("Incoming WebSocket connection\t%s\t%s", ws.environ.get('REMOTE_ADDR', ''), ws.environ.get('HTTP_HOST'))
		sock = SockWebSocketWrapper(ws)
		rtjp_conn = rtjp_eventlet.RTJPConnection(sock=sock)
		self._accept(rtjp_conn)

	def run(self):
		self._bound_socket = eventlet.listen(('0.0.0.0', 8013)) #TODO: read from config
		self._bound_notify_socket = eventlet.listen(('127.0.0.1', 8014))
		
		eventlet.spawn(eventlet.wsgi.server, self._bound_socket, self._root_wsgi_app, log=EmptyLogShim())
		eventlet.spawn(eventlet.wsgi.server, self._bound_notify_socket, self._notify_wsgi_app, log=EmptyLogShim())
		
		main_host, main_port = self._bound_socket.getsockname()
		logger.info("Listening to hookbox on http://%s:%s", main_host, main_port)
		
		ev = eventlet.event.Event()
		self._rtjp_server.listen(sock=self.csp)
		eventlet.spawn(self._run, ev)
		return ev

	def _run(self, ev):
		while True:
			try:
				rtjp_conn = self._rtjp_server.accept().wait()
				if not rtjp_conn:
					continue
				access_logger.info("Incoming CSP connection\t%s\t%s", rtjp_conn._sock.environ.get('HTTP_X_FORWARDED_FOR', rtjp_conn._sock.environ.get('REMOTE_ADDR', '')),  rtjp_conn._sock.environ.get('HTTP_HOST'))
				eventlet.spawn(self._accept, rtjp_conn)
			except:
				logger.exception("Unknown Exception occurred at top level")
		logger.info("Hookbox Daemon Stopped")

	def __call__(self, environ, start_response):
		return self._root_wsgi_app(environ, start_response)

	def _accept(self, rtjp_conn):
		conn = HookboxConn(self, rtjp_conn, rtjp_conn._sock.environ.get('HTTP_X_FORWARDED_FOR', ''))
		conn.run()

	def connect(self, conn):
		self.eventTracker.connect(conn)

	def disconnect(self, conn):
		self.eventTracker.disconnect(conn)

class SockWebSocketWrapper(object):
	def __init__(self, ws):
		self._ws = ws

	def recv(self, num):
		# not quite right (ignore num)... but close enough for our use.
		data = self._ws.wait()
		if data:
			data = data.encode('utf-8')
		return data

	def send(self, data):
		self._ws.send(data)
		return len(data)

	def sendall(self, data):
		self.send(data)

	def __getattr__(self, key):
		return getattr(self._ws, key)

class EmptyLogShim(object):
	def write(self, *args, **kwargs):
		return
