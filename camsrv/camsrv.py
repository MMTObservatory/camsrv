"""
Base classes for MMTO camera interface systems
"""

import io
import socket
import json
import pkg_resources

from scipy.ndimage import median_filter

import tracemalloc

import logging
import logging.handlers

import tornado
import tornado.web
import tornado.httpserver
import tornado.ioloop
import tornado.websocket
from tornado.log import enable_pretty_logging

from pathlib import Path

from indiclient.indicam import SimCam

from .header import update_header

tracemalloc.start(25)

enable_pretty_logging()

logger = logging.getLogger("")
logger.setLevel(logging.INFO)
log = logging.getLogger('tornado.application')
log.setLevel(logging.INFO)

SIMSRVPORT = 8788


class CAMsrv(tornado.web.Application):
    class HomeHandler(tornado.web.RequestHandler):
        """
        Serves the main HTML page.
        """
        def get(self):
            if self.application.camera is None:
                args = {
                    'filter': "N/A",
                    'filters': ["N/A"],
                    'frame_types': ["N/A"],
                    'cooling': "Off",
                    'temperature': "N/A",
                    'cooling_power': "N/A",
                    'requested_temp': self.application.requested_temp,
                    'binning': {'X': 1, 'Y': 1},
                    'frame': {'X': 0, 'Y': 0, "width": 1280, "height": 1024},
                    'ccdinfo': {'CCD_MAX_X': 1280, 'CCD_MAX_Y': 1024},
                    'status': False,
                }
            else:
                try:
                    args = {
                        'filter': self.application.camera.filter,
                        'filters': self.application.camera.filters,
                        'frame_types': self.application.camera.frame_types,
                        'cooling': self.application.camera.cooler,
                        'temperature': self.application.camera.temperature,
                        'cooling_power': self.application.camera.cooling_power,
                        'requested_temp': self.application.requested_temp,
                        'binning': self.application.camera.binning,
                        'frame': self.application.camera.frame,
                        'ccdinfo': self.application.camera.ccd_info,
                        'status': True,
                    }
                except Exception as e:
                    log.error("Can't load configuration from camera: %s" % e)

            self.render(self.application.home_template, args=args)

    class ExposureHandler(tornado.web.RequestHandler):
        """
        Takes an exposure
        """
        def get(self):
            cam = self.application.camera
            exptype = self.get_argument('exptype', default="Light")
            filt = self.get_argument('filt', default=None)
            exptime = self.get_argument('exptime', default=self.application.default_exptime)

            if cam is not None:
                if filt is not None and filt in cam.filters:
                    cam.filter = filt

                if exptype not in cam.frame_types:
                    exptype = "Light"

                hdulist = cam.expose(exptime=float(exptime), exptype=exptype)
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
                    log.error("Exposure failed.")
            else:
                log.warning("Camera not connected.")

            self.finish()

    class LatestHandler(tornado.web.RequestHandler):
        """
        Serve up the latest image
        """
        def get(self):
            if self.application.latest_image is not None:
                # use io.BytesIO to convert the FITS data structure into a byte stream
                binout = io.BytesIO()
                self.application.latest_image.writeto(binout)
                self.write(binout.getvalue())
                binout.close()
            self.finish()

    class ResetHandler(tornado.web.RequestHandler):
        """
        Reset or start up the connection to the camera's INDI server.
        """
        def get(self):
            cam = self.application.camera
            if cam is None:
                log.info("Attemping to connect to camera...")
                self.application.connect_camera()
                self.finish()
            else:
                try:
                    log.info("Disconnecting camera...")
                    cam.disconnect()
                except Exception as e:
                    log.error("Error resetting camera connection: %s" % e)
                    cam = None
                finally:
                    self.application.connect_camera()
                    self.finish()

    class CoolingHandler(tornado.web.RequestHandler):
        """
        Toggle CCD cooler on/off
        """
        def get(self):
            cam = self.application.camera
            if cam is not None:
                if cam.cooler == "Off":
                    log.info("Cooling off, turning on...")
                    cam.cooling_on()
                    log.info("Setting set-point temperature to %f" % self.application.requested_temp)
                    cam.temperature = self.application.requested_temp
                else:
                    log.info("Cooling on, turning off...")
                    cam.cooling_off()
            self.finish()

    class TemperatureHandler(tornado.web.RequestHandler):
        """
        Set the set-point temperature of the CCD cooler
        """
        def get(self):
            cam = self.application.camera
            temp = self.get_argument('temp', None)
            if temp is not None and cam is not None:
                t = float(temp)
                log.info("Setting set-point temperature to %f" % t)
                self.application.requested_temp = t
                cam.temperature = t
            else:
                log.warning("Unable to set camera temperature to %s" % temp)
            self.finish()

    class CCDHandler(tornado.web.RequestHandler):
        """
        Configure the CCD readout region and binning
        """
        def get(self):
            cam = self.application.camera
            if cam is not None:
                curr_frame = cam.frame
                curr_bin = cam.binning
                framedict = {
                    'X': int(self.get_argument('frame_x', curr_frame['X'])),
                    'Y': int(self.get_argument('frame_y', curr_frame['Y'])),
                    'width': int(self.get_argument('frame_w', curr_frame['width'])),
                    'height': int(self.get_argument('frame_h', curr_frame['height'])),
                }
                bindict = {
                    'X': int(self.get_argument('x_bin', curr_bin['X'])),
                    'Y': int(self.get_argument('y_bin', curr_bin['Y'])),
                }
                cam.binning = bindict
                cam.frame = framedict
            self.finish()

    class StatusHandler(tornado.web.RequestHandler):
        """
        Send JSON dict of status information
        """
        def get(self):
            cam = self.application.camera
            status = {
                'cooling': "Off",
                'cooling_power': "N/A",
                'temperature': "N/A",
                'requested_temp': self.application.requested_temp,
                'status': False,
            }

            if cam is None:
                return status

            # make sure we can connect to camera and bail early if we can't
            if cam is not None:
                try:
                    cam.connected
                except Exception as e:
                    log.error("Error checking camera connection: %s" % e)
                    cam = None
                    self.write(json.dumps(status))
                    return

            # we can check the connection and if we're connected, then query camera and fill in the status
            if cam.connected:
                # don't always get the cooling power
                try:
                    cooling_power = "%.1f" % cam.cooling_power
                except Exception:
                    log.warning("Camera cooling power not available.")
                    cooling_power = "N/A"

                status = {
                    'cooling': cam.cooler,
                    'cooling_power': cooling_power,
                    'temperature': "%.1f" % cam.temperature,
                    'requested_temp': self.application.requested_temp,
                    'binning': cam.binning,
                    'frame': cam.frame,
                    'status': True,
                }
            self.write(json.dumps(status))
            self.finish()

    class MallocHandler(tornado.web.RequestHandler):
        """
        Grab a snapshot of tracemalloc statistics
        """
        def get(self):
            nlines = int(self.get_argument('lines', default=10))
            snapshot = tracemalloc.take_snapshot()
            stats = snapshot.statistics('lineno')
            top_stats = f"Top {nlines} lines of memory usage:\n"
            for s in stats[:nlines]:
                top_stats += f"\t{s}\n"
            self.write(top_stats)
            self.finish()

    class MemHogHandler(tornado.web.RequestHandler):
        """
        Grab a snapshot of tracemalloc traceback for the biggest memory hog
        """
        def get(self):
            snaptype = self.get_argument("snaptype", default="lineno")
            n = int(self.get_argument("n", default=0))
            snapshot = tracemalloc.take_snapshot()
            try:
                stats = snapshot.statistics(snaptype)
                hog_stats = stats[n]
            except Exception as e:
                err = f"Error getting tracemalloc snapshot for snaptype={snaptype} and n={n}: {e}"
                log.error(err)
                self.write(err)
                self.finish()
            top_stats = f"Top memory usage of {hog_stats.count} blocks: {hog_stats.size/1024} KiB\n"
            for ll in hog_stats.traceback.format():
                top_stats += f"\t{ll}\n"
            self.write(top_stats)
            self.finish()

    def connect_camera(self):
        # check the actual camera
        self.camera = None
        try:
            self.camera = SimCam(host=self.camhost, port=self.camport)
            self.camera.driver = "CCD Simulator"
        except (ConnectionRefusedError, socket.gaierror):
            log.warning("Can't connect to INDI CCD Simulator...")

    def save_latest(self):
        pass

    def __init__(self, camhost="localhost", camport=7624, connect=True):
        parent = Path(pkg_resources.resource_filename(__name__, "web_resources"))
        template_path = parent / "templates"
        static_path = parent / "static"
        js9_path = parent / "js9"
        bootstrap_path = parent / "bootstrap"

        self.camhost = camhost
        self.camport = camport

        self.parent = parent
        self.home_template = "sim.html"

        self.camera = None

        if connect:
            self.connect_camera()

        self.latest_image = None
        self.requested_temp = -15.0
        self.default_exptime = 1.0

        self.bad_pixel_mask = None

        self.settings = dict(
            template_path=template_path,
            static_path=static_path,
            debug=True
        )

        self.handlers = [
            (r"/", self.HomeHandler),
            (r"/expose", self.ExposureHandler),
            (r"/latest", self.LatestHandler),
            (r"/cooling", self.CoolingHandler),
            (r"/reset", self.ResetHandler),
            (r"/status", self.StatusHandler),
            (r"/temperature", self.TemperatureHandler),
            (r"/ccdconf", self.CCDHandler),
            (r"/profiler", self.MallocHandler),
            (r"/memhog", self.MemHogHandler),
            (r"/js9/(.*)", tornado.web.StaticFileHandler, dict(path=js9_path)),
            (r"/bootstrap/(.*)", tornado.web.StaticFileHandler, dict(path=bootstrap_path)),
            (r"/js9Prefs\.json(.*)", tornado.web.StaticFileHandler, dict(path=js9_path / "js9Prefs.json")),
            (r"/js9\.min\.js(.*)", tornado.web.StaticFileHandler, dict(path=js9_path / "js9.min.js")),
            (r"/js9worker\.js(.*)", tornado.web.StaticFileHandler, dict(path=js9_path / "js9worker.js")),
            (r"/images/(.*)", tornado.web.StaticFileHandler, dict(path=js9_path / "images")),
            (r"/help/(.*)", tornado.web.StaticFileHandler, dict(path=js9_path / "help")),
            (r"/plugins/(.*)", tornado.web.StaticFileHandler, dict(path=js9_path / "plugins")),
            (r"/params/(.*)", tornado.web.StaticFileHandler, dict(path=js9_path / "params")),
            (r"/analysis-plugins/(.*)", tornado.web.StaticFileHandler, dict(path=js9_path / "analysis-plugins")),
            (r"/fits/(.*)", tornado.web.StaticFileHandler, dict(path=parent / "fitsdata")),
        ]

        if hasattr(self, "extra_handlers"):
            self.handlers.extend(self.extra_handlers)

        super(CAMsrv, self).__init__(self.handlers, **self.settings)


def main(port=SIMSRVPORT):
    application = CAMsrv()

    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(port)

    print(f"Simulator server running at http://127.0.0.1:{port}/")
    print("Press Ctrl+C to quit")

    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main(port=SIMSRVPORT)
