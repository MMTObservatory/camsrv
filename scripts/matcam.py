"""
MMTO Mount Aligment Telescope interface
"""

from camsrv.matcam import MATServ

if __name__ == "__main__":
    application = MATServ()

    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(8786)

    print("http://127.0.0.1:8786/")
    print("Press Ctrl+C to quit")

    tornado.ioloop.IOLoop.instance().start()
