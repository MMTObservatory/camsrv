"""
Sanity checks to make sure applications can be instantiated
"""
from tornado.testing import AsyncHTTPTestCase, gen_test

from ..camsrv import CAMsrv
from ..f9wfs import F9WFSsrv
from ..matcam import MATsrv
from ..ratcam import RATsrv


class TestSimSrv(AsyncHTTPTestCase):
    def get_app(self):
        app = CAMsrv(connect=False)
        return app

    @gen_test
    def test_homepage(self):
        response = yield self.http_client.fetch(self.get_url('/'))
        self.assertEqual(response.code, 200)


class TestConnected(AsyncHTTPTestCase):
    def get_app(self):
        app = CAMsrv(connect=True)
        return app

    def test_read_then_disconnect(self):
        response = self.fetch('/status')
        self.assertEqual(response.code, 200)
        self.assertIn(b"temperature", response.body)

        response = self.fetch('/disconnect')
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
