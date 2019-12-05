"""stand up a simple HTTP server
"""

import pattern

import collections.abc as abc
from dataclasses import dataclass
import http.server
import traceback
import typing


def serve(binding, generic_handler=None,
          GET=None, HEAD=None, POST=None, PUT=None, DELETE=None, CONNECT=None,
          OPTIONS=None, TRACE=None, PATCH=None):
    """Serve HTTP requests from the specified `binding` (address, port).
    Use the optionally specified `generic_handler` to process `Request`s.
    Use the optionally specified command-specific handlers to process
    requests of the relevant command (e.g. GET, POST).  Return when SIGTERM
    is sent to the thread invoking this function.
    """

    class RequestHandler(_RequestHandler):
        def do_GET(self):
            return self.handle_command('GET', GET or generic_handler)
        def do_HEAD(self):
            return self.handle_command('HEAD', HEAD or generic_handler)
        def do_POST(self):
            return self.handle_command('POST', POST or generic_handler)
        def do_PUT(self):
            return self.handle_command('PUT', PUT or generic_handler)
        def do_DELETE(self):
            return self.handle_command('DELETE', DELETE or generic_handler)
        def do_CONNECT(self):
            return self.handle_command('CONNECT', CONNECT or generic_handler)
        def do_OPTIONS(self):
            return self.handle_command('OPTIONS', OPTIONS or generic_handler)
        def do_TRACE(self):
            return self.handle_command('TRACE', TRACE or generic_handler)

    server = http.server.HTTPServer(binding, RequestHandler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass  # SIGTERM: time to clean up
    finally:
        server.server_close()


@dataclass
class Request:
    """A `Request` instance is what is passed to the handler(s) in `serve`."""

    client: typing.Tuple[str, int]  # (host, port)
    command: str
    path: str
    headers: dict
    body: typing.Optional[bytes]


class _RequestHandler(http.server.BaseHTTPRequestHandler):
    def handle_command(self, command, handler):
        try:
            return self._do_handle_command(command, handler)
        except Exception:
            traceback.print_exc()
            INTERNAL_SERVER_ERROR = 500
            self.send_error(INTERNAL_SERVER_ERROR)

    def _do_handle_command(self, command, handler):
        OK = 200
        NOT_IMPLEMENTED = 501

        def is_error(status):
            return 400 <= status <= 599

        if handler is None:
            self.send_error(
                NOT_IMPLEMENTED,
                explain=f'{command} is not implemented for this service.')
            return
        
        request = Request(self.client_address,
                          command,
                          self.path,
                          dict(self.headers),
                          None)

        body_length = self.headers.get('Content-Length')
        if body_length is not None:
            body_length = int(body_length)
            request.body = self.rfile.read(body_length)

        response = handler(request)
        match, (status, content_type, body) = pattern.Matcher(3)

        # `handler` could have returned any of the following:
        #
        # - None: 200 status code with no message body.
        # - <int>: status/error code, with canned explanation in body if error.
        # - <bytes>: 200 status code with the specified message body as
        #   text/html
        # - (<int>, <bytes>): specified status code with the specified message
        #   body as text/html
        # - {<str>: <bytes>}: 200 status code with the specified Content-Type
        #   with the specified message body.
        # - (<int>, {<str>: <bytes>}): specified status/error code with the
        #   specified Content-Type with the specified message body.
        #
        if response is None:
            self.send_response(OK)
        elif match(status[int], response):
            status = status.value
            if is_error(status):
                self.send_error(status)
            else:
                self.send_response(status)
        elif match(body[bytes], response):
            body = body.value
            self.send_response(OK)
        elif match((status[int], body[bytes]), response):
            status, body = status.value, body.value
            self.send_response(status)
        elif match({content_type[str]: body[bytes]}, response):
            content_type, body = content_type.value, body.value
            self.send_header('Content-Type', content_type)
            self.send_response(OK)
        else:
            match((status[int], {content_type[str]: body[bytes]}), response)
            assert match
            status, content_type, body = match.values()
            self.send_header('Content-Type', content_type)
            self.send_response(status)
        
        if type(body) is not pattern.Variable:
            assert isinstance(body, bytes)
            self.send_header('Content-Length', len(body))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.end_headers()
