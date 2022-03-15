"""
MMTO F/5 WFS camera interface
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
import io

from indiclient.indicam import SimCam, F9WFSCam

from .sbig import SBIGClient
from pyindi.webclient import INDIWebApp
import base64

from .camsrv import CAMsrv

enable_pretty_logging()
logger = logging.getLogger("")
logger.setLevel(logging.INFO)
log = logging.getLogger('tornado.application')
import asyncio
log.setLevel(logging.INFO)


from .header import update_header

F9WFSPORT = 8787

__all__ = ['F5WFSsrv', 'main']




class F5WFSsrv(CAMsrv):
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

    def connect_camera_old(self):
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
                self.camera = SimCam(host="indiserver", port=self.camport)
            except (ConnectionRefusedError, socket.gaierror):
                log.error("Connection refused to local test server as well...")

    def connect_camera(self):
        return
        self.que.put_nowait(
                self.sbig.setSimulation(True)
                )

        self.que.put_nowait(
                    self.sbig.connect(True)
                )

    def save_latest(self):
        if self.latest_image is not None:
            filename = self.datadir / Path("f9wfs_" + time.strftime("%Y%m%d-%H%M%S") + ".fits")
            self.latest_image.writeto(filename)

    def __init__(self, camhost='badname', camport=7624, connect=False):
        self.extra_handlers = [
            (r"/wfs_config", self.WFSModeHandler),
            (r"/default_config", self.DefaultModeHandler),
        ]

        iwa = INDIWebApp(handle_blob=self.new_image, indihost="indiserver", indiport=7624)
        self.extra_handlers.extend(iwa.indi_handlers())
        self.indiargs = {"device_name":["*"]}

        super(F5WFSsrv, self).__init__(camhost=camhost, camport=camport, connect=connect)

        self.home_template = "f5wfs.html"

        if 'WFSROOT' in os.environ:
            self.datadir = Path(os.environ['WFSROOT'])
        elif 'HOME' in os.environ:
            self.datadir = Path(os.environ['HOME']) / "wfsdat"
        else:
            self.datadir = Path("wfsdat")

        self.latest_image = None
        self.requested_temp = -25.0
        self.default_exptime = 10.0

        # We have to make one for f5
        bp_file = pkg_resources.resource_filename(__name__, os.path.join("data", "f9_mask.fits"))
        with fits.open(bp_file) as hdulist:
            self.bad_pixel_mask = hdulist[0].data.astype(bool)
    
    def new_image(self, blob):
        buff = io.BytesIO(blob['data'])
        hdulist = fits.open(buff)
        if hdulist is not None:
            hdulist = update_header(hdulist)
            if self.application.bad_pixel_mask is not None:
                im = hdulist[0].data
                if im.shape != self.application.bad_pixel_mask.shape:
                    log.warning("Wrong readout configuration for making bad pixel corrections...")
                else:
                    blurred = median_filter(im, size=5)
                    im[self.application.bad_pixel_mask] = blurred[self.application.bad_pixel_mask]

            self.application.latest_image = hdulist[0]
            self.application.save_latest()

        else:
            log.error("Exposure Failed")




def main(port=F9WFSPORT):
    application = F5WFSsrv()

    
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(port)

    print(f"F/9 WFS camera server running at http://127.0.0.1:{port}/")
    print("Press Ctrl+C to quit")

    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
