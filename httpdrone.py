"""stand up a simple HTTP server
"""

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
    """A `Request` is what is passed to the handler(s) in `serve`."""

    client: typing.Tuple[str, int]  # (host, port)
    command: str
    path: str
    headers: dict
    body: typing.Optional[bytes] = None


@dataclass
class Response:
    """A `Response` is what is returned by the handler(s) in `serve`."""

    status: typing.Optional[int] = 200
    content_type: typing.Optional[str] = 'text/html'
    body: typing.Optional[bytes] = None


class _RequestHandler(http.server.BaseHTTPRequestHandler):
    def handle_command(self, command, handler):
        try:
            return self._do_handle_command(command, handler)
        except Exception:
            traceback.print_exc()
            INTERNAL_SERVER_ERROR = 500
            self.send_error(INTERNAL_SERVER_ERROR)

    def _do_handle_command(self, command, handler):
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

        if is_error(response.status):
            self.send_error(response.status)
        else:
            self.send_response(response.status)

        if response.body is not None:
            self.send_header('Content-Type', response.content_type)
            self.send_header('Content-Length', len(response.body))
            self.end_headers()
            self.wfile.write(response.body)
        else:
            self.end_headers()
