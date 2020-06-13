"""
MMTO Mount Aligment Telescope interface
"""

import os
import socket
import time

from pathlib import Path

import tornado

import logging
import logging.handlers

from indiclient.indicam import SimCam, MATCam

from .camsrv import CAMsrv

logger = logging.getLogger("")
logger.setLevel(logging.INFO)
log = logging.getLogger('tornado.application')
log.setLevel(logging.INFO)

MATCAMPORT = 8786


class MATsrv(CAMsrv):

    def connect_camera(self):
        # check the actual camera
        self.camera = None
        try:
            self.camera = MATCam(host=self.camhost, port=self.camport)
            self.camera.driver = "SBIG CCD"
        except (ConnectionRefusedError, socket.gaierror):
            log.warning("Can't connect to matcam host. Falling back to test server...")

        # fall back to the test simulator server
        if self.camera is None:
            try:
                self.camera = SimCam(host="localhost", port=self.camport)
            except (ConnectionRefusedError, socket.gaierror):
                log.error("Connection refused to local test server as well...")

    def save_latest(self):
        if self.latest_image is not None:
            filename = self.datadir / Path("matcam_" + time.strftime("%Y%m%d-%H%M%S") + ".fits")
            self.latest_image.writeto(filename)

    def __init__(self, camhost="matcam", camport=7624, connect=True):
        super(MATsrv, self).__init__(camhost=camhost, camport=camport, connect=connect)

        self.home_template = "matcam.html"

        if 'MATCAMROOT' in os.environ:
            self.datadir = Path(os.environ['MATCAMROOT'])
        else:
            self.datadir = Path("/mmt/matcam/latest")

        self.latest_image = None
        self.requested_temp = -15.0


def main(port=MATCAMPORT):
    application = MATsrv()

    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(port)

    print(f"MATcam server running at http://127.0.0.1:{port}/")
    print("Press Ctrl+C to quit")

    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main(port=MATCAMPORT)
