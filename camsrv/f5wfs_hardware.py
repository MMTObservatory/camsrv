"""
Interface to the F/5-hecto WFS hardware via the waveserv MSG server
"""
import logging
from enum import Enum

from saomsg.client import MSGClient

logger = logging.getLogger("")
logger.setLevel(logging.INFO)


class Power(Enum):
    on = "on"
    off = "off"


class F5WFS_Power(MSGClient):
    """
    Interface to the MSG server that operates the networked power switch that feeds
    the F/5 WFS hardware.
    """
    def __init__(self, host="localhost", port=4447):
        super(F5WFS_Power, self).__init__(host=host, port=port)
        self.switches = {
            "computer": "wfs_control",
            "drives": "wfs_drive"
        }

    @property
    async def power(self, switch):
        """
        Get the power status for specified switch
        """
        if switch not in self.switches:
            logging.error(f"Unsupported switch {switch}.")
            return
        state = await self.get(self.switches[switch])
        logging.debug(f"Got {state} for wfs_control from WFS power switch server")
        return Power[state]

    @power.setter
    async def power(self, switch, state):
        """
        Set switch power state where state is a member of the Power class.
        """
        if switch not in self.switches:
            logging.error(f"Unsupported switch {switch}.")
            return
        status = await self.run(self.switches[switch], state.value)
        if status:
            logging.debug(f"Successfully set {self.switches[switch]} to {state.value} on WFS power switch server")
        else:
            logging.debug(f"Unable to set {self.switches[switch]} to {state.value} on WFS power switch server")
        return status
