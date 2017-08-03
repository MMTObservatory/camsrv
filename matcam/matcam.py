"""
MMTO Mount Aligment Telescope interface
"""

import os

import logging
import logging.handlers
logger = logging.getLogger("")
logger.setLevel(logging.INFO)

try:
    import tornado
except ImportError:
    raise RuntimeError("This server requires tornado.")
import tornado.web
import tornado.httpserver
import tornado.ioloop
import tornado.websocket
from tornado.log import enable_pretty_logging
enable_pretty_logging()

from pathlib import Path

log = logging.getLogger('tornado.application')
log.setLevel(logging.INFO)


class MATServ(tornado.web.Application):
    class HomeHandler(tornado.web.RequestHandler):
        """
        Serves the main HTML page.
        """
        def get(self):
            self.render("js9.html")

    def __init__(self):
        parent = Path(__file__).parent / ".."
        template_path = parent / "templates"
        static_path = parent / "static"
        js9_path = parent / "js9"
        bootstrap_path = parent / "bootstrap"

        settings = dict(
            template_path=template_path,
            static_path=static_path,
            debug=True
        )

        handlers = [
            (r"/", self.HomeHandler),
            (r"/js9/(.*)", tornado.web.StaticFileHandler, dict(path=js9_path)),
            (r"/bootstrap/(.*)", tornado.web.StaticFileHandler, dict(path=bootstrap_path)),
            (r"/js9Prefs\.json(.*)", tornado.web.StaticFileHandler, dict(path=js9_path / "js9Prefs.json")),
            (r"/js9\.min\.js", tornado.web.StaticFileHandler, dict(path=js9_path / "js9.min.js")),
            (r"/js9worker\.js", tornado.web.StaticFileHandler, dict(path=js9_path / "js9worker.js")),
            (r"/images/(.*)", tornado.web.StaticFileHandler, dict(path=js9_path / "images")),
            (r"/help/(.*)", tornado.web.StaticFileHandler, dict(path=js9_path / "help")),
            (r"/plugins/(.*)", tornado.web.StaticFileHandler, dict(path=js9_path / "plugins")),
            (r"/params/(.*)", tornado.web.StaticFileHandler, dict(path=js9_path / "params")),
            (r"/analysis-plugins/(.*)", tornado.web.StaticFileHandler, dict(path=js9_path / "analysis-plugins")),
        ]

        super(MATServ, self).__init__(handlers, **settings)


if __name__ == "__main__":
    application = MATServ()

    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(8786)

    print("http://127.0.0.1:8786/")
    print("Press Ctrl+C to quit")

    tornado.ioloop.IOLoop.instance().start()
