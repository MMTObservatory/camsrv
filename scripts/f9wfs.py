"""
F/9 WFS camera interface
"""

import tornado

from camsrv.f9wfs import F9WFSsrv

port = 8787

if __name__ == "__main__":
    application = F9WFSsrv()

    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(port)

    print("F/9 WFS camera server running at http://127.0.0.1:%d/" % port)
    print("Press Ctrl+C to quit")

    tornado.ioloop.IOLoop.instance().start()
