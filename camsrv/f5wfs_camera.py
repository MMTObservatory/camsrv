"""
MSG-based Interface to the F/5-hecto WFS camera
"""
import io
import asyncio
import logging
from enum import Enum, auto

from astropy.io import fits

from saomsg.client import MSGClient

logger = logging.getLogger("")
logger.setLevel(logging.INFO)


class CamState(Enum):
    """
    Enumerate possible camera states
    """
    Idle = auto()
    Exposing = auto()
    Read = auto()
    Reading = auto()
    Exposed = auto()


class Cooler(Enum):
    """
    Enumerate possible camera cooler states
    """
    off = 0
    on = 1


class ExpType(Enum):
    """
    Enumerate possible exposure types
    """
    light = "light"
    dark = "dark"


class F5WFS_Cam(MSGClient):
    def __init__(self, host="localhost", port=6868):
        super(F5WFS_Cam, self).__init__(host=host, port=port)
        self.observer = "F5/Hecto Shack-Hartmann Wavefront Sensor"
        self.object = "N/A"

    @property
    def ccd_info(self):
        """
        Get basic info about the CCD
        """
        info = {
            'CCD_MAX_X': 512,
            'CCD_MAX_Y': 512,
            'CCD_PIXEL_SIZE': 20,
            'CCD_BITSPERPIXEL': 16
        }
        return info

    @property
    def connected(self):
        """
        Query connection status
        """
        return self.running

    @property
    def observer(self):
        """
        Get observer string
        """
        return self.observer

    @observer.setter
    def observer(self, obsstring):
        """
        Set observer string
        """
        self.observer = obsstring

    @property
    def object(self):
        """
        Get object string
        """
        return self.object

    @object.setter
    def object(self, objstring):
        """
        Set object string
        """
        self.object = objstring

    @property
    async def temperature(self):
        """
        Read camera temperature from MSG server
        """
        temp = await self.get("temp")
        return float(temp)

    @property
    async def setpoint(self):
        """
        Read camera cooler setpoint from MSG server
        """
        setp = await self.get("setp")
        return int(setp)

    @property
    async def state(self):
        """
        Read camera state from the MSG server
        """
        state = await self.get("state")
        return CamState[state]

    @property
    async def timer(self):
        """
        Read camera timer from the MSG server
        """"
        timer = await self.get("timer")
        return int(timer)

    async def cooler(self, state):
        """
        Toggle cooler on/off using a state of type Cooler
        """
        status = await self.run("cooler", state.value)
        return status

    async def idle(self):
        """
        Set camera to idle mode
        """
        status = await self.run("idle")
        return status

    async def readout(self):
        """
        Read out last image
        """
        status = await self.run("readout")
        return status

    async def abort(self):
        """
        Abort current exposure
        """
        logging.debug("Sending abort command...")
        status = await self.run("abort")
        if status:
            while True:
                if await self.state == CamState.Idle:
                    logging.debug("Camera idle. Abort complete.")
                    break
                await asyncio.sleep(0.5)
        else:
            logging.error("Problem sending abort command.")
        return status

    async def expose(self, exptype, exptime, nbytes=1322240):
        """
        Acquire an exposure, read it out, and return a FITS object
        """
        logging.debug(f"Taking a {exptime} second {exptype.value} exposure...")
        status = await self.run("expose", 0, exptype.value, exptime)
        if status:
            while True:
                if await self.state == CamState.Exposed:
                    break
                await asyncio.sleep(0.5)
        else:
            logging.error("Exposure command failed")
            return

        logging.debug("Exposure complete. Beginning readout...")
        status = await selt.run("readout")
        if status:
            while True:
                if await self.state == CamState.Read:
                    break
                await asyncio.sleep(0.5)
        else:
            logging.error("Readout command failed")
            return

        logging.debug("Readout complete. Transferring FITS data...")
        status = await self.run("fits", 0, nbytes)
        if status:
            rawreply = await self.reader.readline()
            reply_data = rawreply.decode().split()
            if reply_data[1] == 'blk' and reply_data[2] == nbytes:
                logging.debug(f"Ready to transfer {nbytes} of FITS data")
                fits_blob = await self.reader.read(nbytes)
                hdulist = fits.open(io.BytesIO(fits_blob))
                return hdulist
            else:
                logging.error(f"Failed reply to fits command: {reply_data}")
                return
        else:
            logging.error("FITS command failed")
            return
