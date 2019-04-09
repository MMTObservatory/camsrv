"""
MMTO Rotator Aligment Telescope interface
"""

import os
import io
import socket
import json
import time
import pkg_resources

from pathlib import Path

import logging
import logging.handlers
logger = logging.getLogger("")
logger.setLevel(logging.INFO)
log = logging.getLogger('tornado.application')
log.setLevel(logging.INFO)

from indiclient.indicam import SimCam, RATCam

from .header import update_header
from .camsrv import CAMsrv


class RATsrv(CAMsrv):

    def connect_camera(self):
        # check the actual camera
        self.camera = None
        try:
            self.camera = RATCam(host="192.168.2.4", port=7624)
            self.camera.driver = "SBIG ST-I"
        except (ConnectionRefusedError, socket.gaierror):
            log.warning("Can't connect to ratcam host. Falling back to test server...")

        # fall back to the test simulator server
        if self.camera is None:
            try:
                self.camera = SimCam(host="localhost", port=7624)
            except (ConnectionRefusedError, socket.gaierror):
                log.error("Connection refused to local test server as well...")

    def save_latest(self):
        if self.latest_image is not None:
            filename = self.datadir / Path("ratcam_" + time.strftime("%Y%m%d-%H%M%S") + ".fits")
            self.latest_image.writeto(filename)

    def __init__(self):
        super(RATsrv, self).__init__()

        self.home_template = "ratcam.html"

        if 'MATCAMROOT' in os.environ:
            self.datadir = Path(os.environ['MATCAMROOT'])
        else:
            self.datadir = Path("/mmt/matcam/latest")

        self.camera = None

        self.connect_camera()

        self.latest_image = None
