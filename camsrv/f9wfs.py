"""
MMTO F/9 WFS camera interface
"""

import os
import io
import socket
import json
import time
import pkg_resources

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

import logging
import logging.handlers
logger = logging.getLogger("")
logger.setLevel(logging.INFO)
log = logging.getLogger('tornado.application')
log.setLevel(logging.INFO)

from sbigclient.sbigcam import SimCam, F9WFSCam

from .header import update_header
from .camsrv import CAMsrv


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
            self.camera = F9WFSCam(host="f9indi", port=7624)
            self.camera.driver = "SBIG CCD"
        except (ConnectionRefusedError, socket.gaierror):
            log.warning("Can't connect to f9wfs camera host. Falling back to test server...")

        # fall back to the test simulator server
        if self.camera is None:
            try:
                self.camera = SimCam(host="localhost", port=7624)
            except (ConnectionRefusedError, socket.gaierror):
                log.error("Connection refused to local test server as well...")

    def save_latest(self):
        if self.latest_image is not None:
            filename = self.savedir / Path("f9wfs_" + time.strftime("%Y%m%d-%H%M%S") + ".fits")
            self.latest_image.writeto(filename)

    def __init__(self):
        self.extra_handlers = [
            (r"/wfs_config", self.WFSModeHandler),
            (r"/default_config", self.DefaultModeHandler),
        ]

        super(F9WFSsrv, self).__init__()

        self.home_template = "f9wfs.html"

        if 'WFSROOT' in os.environ:
            self.savedir = Path(os.environ['WFSROOT'])
        else:
            self.savedir = Path("/mmt/shwfs/datadir")

        self.camera = None

        self.connect_camera()

        self.latest_image = None
        self.requested_temp = -25.0
