"""
MMTO F/9 WFS camera interface
"""

import os
import socket
import time
import pkg_resources

import tornado
import tornado.web
import tornado.httpserver
import tornado.ioloop
import tornado.websocket
from tornado.log import enable_pretty_logging

from pathlib import Path

import logging
import logging.handlers

from astropy.io import fits

from indiclient.indicam import SimCam, F9WFSCam

from .camsrv import CAMsrv

enable_pretty_logging()
logger = logging.getLogger("")
logger.setLevel(logging.INFO)
log = logging.getLogger('tornado.application')
log.setLevel(logging.INFO)

F9WFSPORT = 8787

__all__ = ['F9WFSsrv', 'main']


class F9WFSsrv(CAMsrv):
    class WFSModeHandler(tornado.web.RequestHandler):
        """
        Configure CCD to be in WFS mode, square with 3x3 binnind
        """
        def get(self):
            cam = self.application.camera
            log.info("Configuring f/9 WFS camera for WFS observations...")
            cam.wfs_config()

    class DefaultModeHandler(tornado.web.RequestHandler):
        """
        Configure CCD to be in WFS mode, square with 3x3 binnind
        """
        def get(self):
            cam = self.application.camera
            log.info("Setting f/9 WFS camera to its default configuration, full-frame with 1x1 binning...")
            cam.default_config()

    def connect_camera(self):
        # check the actual camera
        self.camera = None
        try:
            self.camera = F9WFSCam(host=self.camhost, port=self.camport)
            self.camera.driver = "SBIG CCD"
        except (ConnectionRefusedError, socket.gaierror):
            log.warning("Can't connect to f9wfs camera host. Falling back to test server...")

        # fall back to the test simulator server
        if self.camera is None:
            try:
                self.camera = SimCam(host="localhost", port=self.camport)
            except (ConnectionRefusedError, socket.gaierror):
                log.error("Connection refused to local test server as well...")

    def save_latest(self):
        if self.latest_image is not None:
            filename = self.datadir / Path("f9wfs_" + time.strftime("%Y%m%d-%H%M%S") + ".fits")
            self.latest_image.writeto(filename)

    def __init__(self, camhost='f9indi', camport=7624, connect=True):
        self.extra_handlers = [
            (r"/wfs_config", self.WFSModeHandler),
            (r"/default_config", self.DefaultModeHandler),
        ]

        super(F9WFSsrv, self).__init__(camhost=camhost, camport=camport, connect=connect)

        self.home_template = "f9wfs.html"

        if 'WFSROOT' in os.environ:
            self.datadir = Path(os.environ['WFSROOT'])
        elif 'HOME' in os.environ:
            self.datadir = Path(os.environ['HOME']) / "wfsdat"
        else:
            self.datadir = Path("wfsdat")

        self.latest_image = None
        self.requested_temp = -25.0
        self.default_exptime = 10.0

        bp_file = pkg_resources.resource_filename(__name__, os.path.join("data", "f9_mask.fits"))
        with fits.open(bp_file) as hdulist:
            self.bad_pixel_mask = hdulist[0].data.astype(bool)


def main(port=F9WFSPORT):
    application = F9WFSsrv()

    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(port)

    print(f"F/9 WFS camera server running at http://127.0.0.1:{port}/")
    print("Press Ctrl+C to quit")

    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main(port=F9WFSPORT)
