"""
MMTO Mount Aligment Telescope interface
"""

import os
import io

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

from sbigclient.sbigcam import CCDCam

log = logging.getLogger('tornado.application')
log.setLevel(logging.INFO)


class MATServ(tornado.web.Application):
    class HomeHandler(tornado.web.RequestHandler):
        """
        Serves the main HTML page.
        """
        def get(self):
            args = {
                'filter': self.application.camera.filter,
                'filters': self.application.camera.filters,
                'frame_types': self.application.camera.frame_types,
            }
            self.render("matcam.html", args=args)

    class ExposureHandler(tornado.web.RequestHandler):
        """
        Takes an exposure
        """
        def get(self):
            cam = self.application.camera
            exptype = self.get_argument('exptype', default="Light")
            filt = self.get_argument('filt', default=None)
            exptime = self.get_argument('exptime', default=1.0)

            if filt is not None and filt in cam.filters:
                cam.filter = filt

            if exptype not in cam.frame_types:
                exptype = "Light"

            self.application.latest_image = cam.expose(exptime=float(exptime), exptype=exptype)[0]

    class LatestHandler(tornado.web.RequestHandler):
        """
        Serve up the latest image
        """
        def get(self):
            if self.application.latest_image is not None:
                binout = io.BytesIO()
                self.application.latest_image.writeto(binout)
                self.write(binout.getvalue())
                binout.close()

    def __init__(self):
        parent = Path(__file__).parent / ".."
        template_path = parent / "templates"
        static_path = parent / "static"
        js9_path = parent / "js9"
        bootstrap_path = parent / "bootstrap"

        self.camera = CCDCam(host="localhost", port=7624)
        self.latest_image = None

        settings = dict(
            template_path=template_path,
            static_path=static_path,
            debug=True
        )

        handlers = [
            (r"/", self.HomeHandler),
            (r"/expose", self.ExposureHandler),
            (r"/latest", self.LatestHandler),
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
            (r"/fits/(.*)", tornado.web.StaticFileHandler, dict(path=parent / "fitsdata")),
        ]

        super(MATServ, self).__init__(handlers, **settings)


if __name__ == "__main__":
    application = MATServ()

    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(8786)

    print("http://127.0.0.1:8786/")
    print("Press Ctrl+C to quit")

    tornado.ioloop.IOLoop.instance().start()
