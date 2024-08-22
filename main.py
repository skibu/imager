#! /usr/bin/env python
import logging
import os
from http.server import ThreadingHTTPServer
from requestHandler import RequestHandler

# NOTE: if you get an SSL Certificate error on OSX (Macs) then you need to install
# the SSL certificates manually by calling the appropriate Python script. It is at
# /Applications/Python\ 3.12/Install\ Certificates.command

# NOTE: had to install Pillow image library using "pip install pillow"
# NOTE: had to install webscraper "pip install html-table-parser-python3"


logger = logging.getLogger()


def start_webserver():
    """Starts the webserver and then just waits forever"""
    server = ThreadingHTTPServer(('', 8080), RequestHandler)

    # Respond to requests until process is killed
    server.serve_forever()


# If run as main, then start the webserver
if __name__ == "__main__":
    logging_dir = '/tmp/imagerCache/logs/'
    os.makedirs(logging_dir, mode=0o777, exist_ok=True)
    logging.basicConfig(filename=logging_dir + 'imager.log', level=logging.DEBUG,
                        format='%(asctime)s.%(msecs)03d - %(levelname)s : %(message)s',
                        datefmt='%m/%d/%y %H:%M:%S')

    logger.info('====================== Starting imager =============================')
    
    start_webserver()
