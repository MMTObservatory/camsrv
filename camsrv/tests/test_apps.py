"""
Sanity checks to make sure applications can be instantiated
"""
import tornado
from tornado.testing import AsyncHTTPTestCase, gen_test
import time
import signal

from ..camsrv import CAMsrv, SIMSRVPORT
from ..f9wfs import F9WFSsrv, F9WFSPORT
from ..matcam import MATsrv, MATCAMPORT
from ..ratcam import RATsrv, RATCAMPORT


class TestSimSrv(AsyncHTTPTestCase):
    def get_app(self):
        app = CAMsrv(connect=False)
        return app

    @gen_test
    def test_homepage(self):
        response = yield self.http_client.fetch(self.get_url('/'))
        self.assertEqual(response.code, 200)


class TestF9Srv(TestSimSrv):
    def get_app(self):
        app = F9WFSsrv(connect=False)
        return app


class TestMATSrv(TestSimSrv):
    def get_app(self):
        app = MATsrv(connect=False)
        return app


class TestRATSrv(TestSimSrv):
    def get_app(self):
        app = RATsrv(connect=False)
        return app
