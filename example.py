import httpdrone as httpd
import os
import sys


def handle_get(request):
    if request.path != '/example':
        return httpd.Response(status=404)

    print(request.body, file=sys.stderr)

    return httpd.Response(body=b'<html><body>Here you go!</body></html>')


if __name__ == '__main__':
    # send SIGTERM when you want to quit
    binding = 'localhost', int(os.environ.get('PORT', 1337))
    httpd.serve(binding, GET=handle_get)
