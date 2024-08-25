#! /usr/bin/env python

from http.server import ThreadingHTTPServer
from requestHandler import RequestHandler


# NOTE: if you get an SSL Certificate error on OSX (Macs) then you need to install
# the SSL certificates manually by calling the appropriate Python script. It is at
# /Applications/Python\ 3.12/Install\ Certificates.command

# NOTE: had to install Pillow image library using "pip install pillow"
# NOTE: had to install webscraper "pip install html-table-parser-python3"


def start_webserver():
    """Starts the webserver and then just waits forever"""
    server = ThreadingHTTPServer(('', 8080), RequestHandler)

    # Respond to requests until process is killed
    server.serve_forever()


# Actually start the webserver
start_webserver()
