"""
Sanity checks to make sure applications can be instantiated
"""
from ..camsrv import CAMsrv
from ..f9wfs import F9WFSsrv
from ..matcam import MATsrv
from ..ratcam import RATsrv


def test_base():
    app = CAMsrv()
    assert(app is not None)


def test_f9():
    app = F9WFSsrv()
    assert(app is not None)


def test_mat():
    app = MATsrv()
    assert(app is not None)


def test_rat():
    app = RATsrv()
    assert(app is not None)
