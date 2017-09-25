"""
MMTO Mount Aligment Telescope interface
"""

import tornado

from camsrv.matcam import MATServ

port = 8786

if __name__ == "__main__":
    application = MATServ()

    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(port)

    print("http://127.0.0.1:%d/" % port)
    print("Press Ctrl+C to quit")

    tornado.ioloop.IOLoop.instance().start()
