"""
MMTO F/5 WFS camera interface
"""

import os
import time
import asyncio
import pkg_resources
import tornado
import tornado.web
import tornado.httpserver
import tornado.ioloop
import tornado.websocket
from tornado.log import enable_pretty_logging
from scipy.ndimage import median_filter
from pathlib import Path
import logging
import logging.handlers
from astropy.io import fits
import io
import json
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
    F5WFSPORT = 8988  # F5WFSPORT
else:
    F5WFSPORT = 8989

__all__ = ['F5WFSsrv', 'main']


class F5WFSsrv(CAMsrv):

    class WFSModeHandler(tornado.web.RequestHandler):
        """
        Deprecated and should be deleted in future commits.

        Configure CCD to be in WFS mode, square with 3x3 binnind
        """
        def get(self):
            cam = self.application.camera
            log.info("Configuring f/5 WFS camera for WFS observations...")
            cam.wfs_config()

    class DefaultModeHandler(tornado.web.RequestHandler):
        """
        Deprecated and should be deleted in future commits.
        Configure CCD to be in WFS mode, square with 3x3 binnind
        """
        def get(self):
            cam = self.application.camera
            log.info("Setting f/5 WFS camera to its\
                 default configuration, full-frame with 1x1 binning...")
            cam.default_config()

    class ResetDriverHandler(tornado.web.RequestHandler):

        async def get(self):
            """
            Restart the INDI driver running on ops2.
            The indiserver/driver is running in a python
            script that starts indiserver and opens a
            named pipe to dynamically start and stop
            drivers. We can connect to the python
            program to send restart commands to the driver.
            """
            driver = self.get_argument("NAME", "F/5 WFS")
            INDIHOST = os.environ.get(
                "INDIF5WFSHOST",
                "ops2.mmto.arizona.edu")
            INDIPORT = os.environ.get(
                "INDIF5WFSPORT",
                "7625")

            reader, writer = await asyncio.open_connection(
                INDIHOST, INDIPORT)
            json_data = dict(
                action="restart_drivers",
                args=[driver]
            )

            writer.write(json.dumps(json_data).encode() + b'\n')

            resp = await reader.readline()
            try:
                self.finish(json.loads(resp))
            except Exception:
                self.finish(f"not json data: {resp}")

            await writer.drain()
            writer.close()
            await writer.wait_closed()

    class ImagePathHandler(tornado.web.RequestHandler):
        """
        Change the image path.
        This is here in case we need to change the
        image path at run time. I think we won't need
        it and it can probably be deleted in future
        commits.
        """

        def get(self):
            path = self.get_argument("path", None)
            if path is not None:
                datadir = Path(path)
                if not datadir.exists():
                    raise ValueError("path does not exist {datadir}")
                self.application.datadir = datadir

            self.finish(str(self.application.datadir))

    class PyindiPanelHandler(tornado.web.RequestHandler):

        def get(self):

            self.render("pyindi-panel.html")

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
        """
        Camera connection to indidriver
        is done by javascript
        """
        return

    def save_latest(self):
        log.info("Saving latest")
        if self.latest_image is not None:
            imagename = Path(
                "f5wfs_" + time.strftime("%Y%m%d-%H%M%S") + ".fits"
            )
            filename = self.datadir / imagename
            self.last_filename = filename
            log.info(f"saving to {filename}")
            self.latest_image.writeto(filename)

    def __init__(self, camhost='badname', camport=7624, connect=False):
        self.extra_handlers = [
            (r"/wfs_config", self.WFSModeHandler),
            (r"/default_config", self.DefaultModeHandler),
            (r"/restart_indidriver", self.ResetDriverHandler),
            (r"/image_path", self.ImagePathHandler),
            (r"/latest_image_name", self.LatestImageNameHandler),
            (r"/pyindi-panel.html", self.PyindiPanelHandler)
        ]

        iwa = INDIWebApp(
            handle_blob=self.new_image,
            indihost="ops2.mmto.arizona.edu",
            indiport=7624
        )

        self.extra_handlers.extend(iwa.indi_handlers())
        self.indiargs = {"device_name": ["*"], "DEFAULT_TEMP": -10.0}

        super(F5WFSsrv, self).__init__(
            camhost=camhost,
            camport=camport,
            connect=connect
        )

        self.home_template = "f5wfs.html"

        if 'WFSROOT' in os.environ:
            self.datadir = Path(os.environ['WFSROOT'])
        elif 'HOME' in os.environ:
            self.datadir = Path(os.environ['HOME']) / "wfsdat"
        else:
            self.datadir = Path("wfsdat")

        self.latest_image = None
        self.requested_temp = -10.0
        self.default_exptime = 10.0

        # We have to make one for f5
        bp_file = pkg_resources.resource_filename(
            __name__,
            os.path.join("data", "f5_mask.fits")
        )
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


def main(port=F5WFSPORT):
    application = F5WFSsrv()

    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(port)

    print(f"F/5 WFS camera server running at http://127.0.0.1:{port}/")
    print("Press Ctrl+C to quit")

    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
