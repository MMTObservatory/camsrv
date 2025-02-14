"""
MMTO F/9 WFS camera interface
"""

import os
import time
import importlib

import tornado
import tornado.web
import tornado.httpserver
import tornado.ioloop
import tornado.websocket
from tornado.log import enable_pretty_logging
import io
from pathlib import Path

from scipy.ndimage import median_filter
import logging
import logging.handlers

from astropy.io import fits


from pyindi.webclient import INDIWebApp

dev = os.environ.get("WFSDEV", False)
if dev:
    from header import update_header
    from camsrv import CAMsrv
else:
    from .header import update_header
    from .camsrv import CAMsrv

enable_pretty_logging()
logger = logging.getLogger("")
logger.setLevel(logging.INFO)
log = logging.getLogger('tornado.application')
log.setLevel(logging.INFO)

if dev:
    F9WFSPORT = 8788
else:
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

    class LatestImageNameHandler(tornado.web.RequestHandler):
        """
        Return the last image filename and path to a get
        request.
        This is used by the webapp to display the latest
        image filename.
        """

        def get(self):
            if hasattr(self.application, "last_filename"):
                if self.application.last_filename is None:
                    self.write("None")
                else:
                    self.write(str(self.application.last_filename))
            else:
                self.write("None")

    def connect_camera(self):
        # No need to do this anymore.
        # Camera connection is done by pyindi
        # we should remove as soon as we are
        # sure this noop is not called anywhere.
        return

    def save_latest(self):
        if self.latest_image is not None:
            filename = self.datadir / Path("f9wfs_" + time.strftime("%Y%m%d-%H%M%S") + ".fits")
            self.latest_image.writeto(filename)
            self.last_filename = filename

    def __init__(self, camhost='f9indi', camport=7624, connect=True):
        self.extra_handlers = [
            (r"/wfs_config", self.WFSModeHandler),
            (r"/default_config", self.DefaultModeHandler),
            (r"/latest_image_name", self.LatestImageNameHandler),
        ]

        iwa = INDIWebApp(
            handle_blob=self.new_image,
            indihost="f9indi.mmto.arizona.edu",
            indiport=7624
        )

        self.extra_handlers.extend(iwa.indi_handlers())
        self.indiargs = {"device_name": ["*"], "DEFAULT_TEMP": -10.0}
        super(F9WFSsrv, self).__init__(camhost="badhost", camport=camport, connect=connect)

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

        bp_file = importlib.resources.files(__name__) / "data" / "f9_mask.fits"

        with fits.open(bp_file) as hdulist:
            self.bad_pixel_mask = hdulist[0].data.astype(bool)

    def new_image(self, blob):
        """
        Pyindi blob callback


        @param blob
        The blob object from the indidriver in this case it is the
        image from the sbig wfs camera.
        """
        buff = io.BytesIO(blob['data'])
        hdulist = fits.open(buff)
        if hdulist is not None:
            hdulist = update_header(hdulist)
            if self.bad_pixel_mask is not None:
                im = hdulist[0].data
                if im.shape != self.bad_pixel_mask.shape:
                    log.warning(
                        "Wrong readout configuration for\
                      making bad pixel corrections..."
                    )
                else:
                    blurred = median_filter(im, size=5)
                    im[self.bad_pixel_mask] = blurred[self.bad_pixel_mask]

            self.latest_image = hdulist[0]
            self.save_latest()

        else:
            log.error("Exposure Failed")


def main(port=F9WFSPORT):
    application = F9WFSsrv()

    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(port)

    print(f"F/9 WFS camera server running at http://127.0.0.1:{port}/")
    print("Press Ctrl+C to quit")

    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main(port=F9WFSPORT)
