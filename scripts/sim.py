"""
INDI CCD simulator interface
"""

import tornado

from camsrv.camsrv import CAMsrv

port = 8786

if __name__ == "__main__":
    application = CAMsrv()

    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(port)

    print("Simulator server running at http://127.0.0.1:%d/" % port)
    print("Press Ctrl+C to quit")

    tornado.ioloop.IOLoop.instance().start()
