"""stand up a simple HTTP server
"""


import collections.abc as abc
from dataclasses import dataclass
import http.server
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
        body = None  # response body, to be determined below

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
        elif _matches(int, response):
            if is_error(response):
                self.send_error(response)
            else:
                self.send_response(response)
        elif _matches(bytes, response):
            self.send_response(OK)
            body = response
        elif _matches((int, bytes), response):
            status, body = response
            self.send_response(status)
        elif _matches({str: bytes}, response):
            (content_type, body), = response.items()
            self.send_header('Content-Type', content_type)
            self.send_response(OK)
        else:
            assert _matches((int, {str: bytes}), response)
            status, content = response
            (content_type, body), = content.items()
            self.send_header('Content-Type', content_type)
            self.send_response(status)
        

        if body is not None:
            assert isinstance(body, bytes)
            self.send_header('Content-Length', len(body))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.end_headers()


# What follows is some poor man's pattern matcher.


def _matches(pattern, subject):
    if isinstance(pattern, abc.Sequence):
        return _matches_sequence(pattern, subject)
    elif isinstance(pattern, abc.Mapping):
        return _matches_mapping(pattern, subject)
    elif isinstance(pattern, abc.Set):
        return _matches_set(pattern, subject)
    elif isinstance(pattern, type):
        return isinstance(subject, pattern)
    else:
        return subject == pattern


def _matches_sequence(pattern, subject):
    if not isinstance(subject, abc.Sequence):
        return False

    if len(subject) != len(pattern):
        return False

    return all(_matches(subpattern, subsubject)
               for subpattern, subsubject in zip(pattern, subject))


def _matches_mapping(pattern, subject):
    if not isinstance(subject, abc.Mapping):
        return False

    # Note: quadratic time complexity
    return all(any(_matches(key, k) and _matches(value, v)
                   for k, v in subject.items())
               for key, value in pattern.items())


def _matches_set(pattern, subject):
    if not isinstance(subject, abc.Set):
        return False

    # Note: quadratic time complexity
    return all(any(_matches(subpattern, subsubject)
                   for subsubject in subject)
               for subpattern in pattern)
