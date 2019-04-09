"""
MMTO Mount Aligment Telescope interface
"""

import tornado

from camsrv.ratcam import RATsrv

port = 8789

if __name__ == "__main__":
    application = RATsrv()

    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(port)

    print("RATcam server running at http://127.0.0.1:%d/" % port)
    print("Press Ctrl+C to quit")

    tornado.ioloop.IOLoop.instance().start()
