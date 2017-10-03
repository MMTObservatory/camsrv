"""
MMTO Mount Aligment Telescope interface
"""

import tornado

from camsrv.matcam import MATsrv

port = 8786

if __name__ == "__main__":
    application = MATsrv()

    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(port)

    print("MATcam server running at http://127.0.0.1:%d/" % port)
    print("Press Ctrl+C to quit")

    tornado.ioloop.IOLoop.instance().start()
