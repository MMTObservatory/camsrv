"""
MMTO Rotator Aligment Telescope interface
"""

import os
import socket
import time

from pathlib import Path

import tornado

import logging
import logging.handlers

from indiclient.indicam import SimCam, RATCam

from .camsrv import CAMsrv

logger = logging.getLogger("")
logger.setLevel(logging.INFO)
log = logging.getLogger('tornado.application')
log.setLevel(logging.INFO)

RATCAMPORT = 8789


class RATsrv(CAMsrv):

    def connect_camera(self):
        # check the actual camera
        self.camera = None
        try:
            self.camera = RATCam(host=self.camhost, port=self.camport)
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

    def __init__(self, camhost="192.168.2.4", camport=7624, connect=True):
        super(RATsrv, self).__init__(camhost=camhost, camport=camport, connect=connect)

        self.home_template = "ratcam.html"

        if 'MATCAMROOT' in os.environ:
            self.datadir = Path(os.environ['MATCAMROOT'])
        else:
            self.datadir = Path("/mmt/matcam/latest")

        self.latest_image = None


def main(port=RATCAMPORT):
    application = RATsrv()

    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(port)

    print(f"RATcam server running at http://127.0.0.1:{port}/")
    print("Press Ctrl+C to quit")

    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main(port=RATCAMPORT)
