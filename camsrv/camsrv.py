"""
Base classes for MMTO camera interface systems
"""

import os
import io
import socket
import json
import time
import pkg_resources

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

from sbigclient.sbigcam import MATCam, SimCam

from .header import update_header

log = logging.getLogger('tornado.application')
log.setLevel(logging.INFO)


class CAMsrv(tornado.web.Application):
    class HomeHandler(tornado.web.RequestHandler):
        """
        Serves the main HTML page.
        """
        def get(self):
            args = {
                'filter': "N/A",
                'filters': ["N/A"],
                'frame_types': ["N/A"],
                'cooling': "Off",
                'temperature': "N/A",
                'cooling_power': "N/A",
                'requested_temp': self.application.requested_temp,
                'status': False,
            }
            try:
                args = {
                    'filter': self.application.camera.filter,
                    'filters': self.application.camera.filters,
                    'frame_types': self.application.camera.frame_types,
                    'cooling': self.application.camera.cooler,
                    'temperature': self.application.camera.temperature,
                    'cooling_power': self.application.camera.cooling_power,
                    'requested_temp': self.application.requested_temp,
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
            exptime = self.get_argument('exptime', default=1.0)

            if cam is not None:
                if filt is not None and filt in cam.filters:
                    cam.filter = filt

                if exptype not in cam.frame_types:
                    exptype = "Light"

                hdulist = cam.expose(exptime=float(exptime), exptype=exptype)
                if hdulist is not None:
                    hdulist = update_header(hdulist)
                    self.application.latest_image = hdulist[0]
                    self.application.save_latest()
                else:
                    log.error("Exposure failed.")
            else:
                log.warning("Camera not connected.")

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

    class ResetHandler(tornado.web.RequestHandler):
        """
        Reset or start up the connection to the camera's INDI server.
        """
        def get(self):
            cam = self.application.camera
            if cam is None:
                log.info("Attemping to connect to camera...")
                self.application.connect_camera()
            else:
                try:
                    log.info("Disconnecting camera...")
                    cam.disconnect()
                except Exception as e:
                    log.error("Error resetting camera connection: %s" % e)
                    cam = None
                finally:
                    self.application.connect_camera()

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
                else:
                    log.info("Cooling on, turning off...")
                    cam.cooling_off()

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
                    connected = cam.connected
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
                except:
                    cooling_power = "N/A"

                status = {
                    'cooling': cam.cooler,
                    'cooling_power': cooling_power,
                    'temperature': "%.1f" % cam.temperature,
                    'requested_temp': self.application.requested_temp,
                    'status': True,
                }
            self.write(json.dumps(status))

    def connect_camera(self):
        # check the actual camera
        self.camera = None
        try:
            self.camera = SimCam(host="localhost", port=7624)
            self.camera.driver = "CCD Simulator"
        except (ConnectionRefusedError, socket.gaierror):
            log.warning("Can't connect to INDI CCD Simulator...")

    def save_latest(self):
        pass

    def __init__(self):
        parent = Path(pkg_resources.resource_filename(__name__, "web_resources"))
        template_path = parent / "templates"
        static_path = parent / "static"
        js9_path = parent / "js9"
        bootstrap_path = parent / "bootstrap"

        self.parent = parent
        self.home_template = "sim.html"

        self.camera = None

        self.connect_camera()

        self.latest_image = None
        self.requested_temp = -15.0

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

        if hasattr(self, extra_handlers):
            self.handlers.append(self.extra_handlers)

        super(CAMsrv, self).__init__(self.handlers, **self.settings)
