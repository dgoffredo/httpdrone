<img src="drone.jpg" height="300"/>

httpdrone
=========
A mindless HTTP server in Python.

Why
---
I need a simple Python web server sitting behind an [nginx][1] [proxy_pass][2].
If only I could write a function, `handle_request`, and be done. You can
almost get there with Python's [http.server][3], but there's still some
annoying boilerplate. `httpdrone` hides the boilerplate.

What
----
`httpdrone` is a Python package that allows you to do this:

```python
import httpdrone
import json
import os
import sqlite3


def handle_post(request):
    if request.path != '/puzzle_complete':
        return 404

    fields = json.loads(request.body)
    db = sqlite3.connect(os.environ['DATABASE'])

    db.execute("""
        insert into Wins(Puzzle, Difficulty, Begin, End, ActiveMilliseconds)
        values(:puzzle, :difficulty, :begin, :end, :activeMilliseconds);""",
        fields)


if __name__ == '__main__':
    # send SIGTERM when you want to quit
    httpdrone.serve(('localhost', int(os.environ['PORT'])), POST=handle_post)
```

How
---
It's just one Python package, `httpdrone/`.  Copy it into your project.  You
need Python 3.7 or later.

More
----
```console
>>> import httpdrone
>>> help(httpdrone)
```

Keep in mind that `httpdrone` expects to be behind a clever reverse proxy like
nginx, so it makes no attempt to validate requests, to handle requests
concurrently, to mitigate slowloris, etc.  It's just the simplest thing I could
come up with given the tools in the Python standard library.

[1]: https://www.nginx.com
[2]: https://docs.nginx.com/nginx/admin-guide/web-server/reverse-proxy/
[3]: https://docs.python.org/3.7/library/http.server.html
