#! /usr/bin/env python
import gzip
import io
from io import BytesIO
from urllib.parse import parse_qs
from urllib.parse import urlparse
from wsgiref import simple_server
# Python's bundled WSGI server
from wsgiref import util

import cache
from audio import get_wav_file
from ebird import ebird
from imageProcessor import load_and_process_image


# NOTE: if you get an SSL Certificate error on OSX (Macs) then you need to install
# the SSL certificates manually by calling the appropriate Python script. It is at
# /Applications/Python\ 3.12/Install\ Certificates.command

# NOTE: had to install Pillow image library using "pip install pillow"
# NOTE: had to install webscraper "pip install html-table-parser-python3"


def wav_response(compressed_wav_data, start_response, http_accept_encoding):
    """
    Creates a http response for a wav audio file. Can return either compressed
    or uncompressed data, depending on the request Content-Encoding header.
    :param compressed_wav_data: IOBytes the data, in compressed format, to be returned
    :param start_response:
    :param http_accept_encoding: so can determine if should reply with compression or not
    :return: IOBytes containing the data bytes for the full reply
    """
    if compressed_wav_data is None:
        return error_response("Could not load image", start_response)

    status = '200 OK'
    response_headers = [('Content-Type', 'audio/wav')]
    compressed_wav_data.seek(0)

    # If gzip compression is accepted then send back already compressed wav data
    if 'gzip' in http_accept_encoding:
        # Using compression
        response_headers.append(('Content-Encoding', 'gzip'))
        return_data = compressed_wav_data
    else:
        # Request not accepting compressed data so need to uncompress the compressed wav data
        # and use it as return_data
        uncompressed_bytes = gzip.decompress(compressed_wav_data.read())
        return_data = io.BytesIO(uncompressed_bytes)

    # Finish up the response headers
    content_length = return_data.getbuffer().nbytes
    response_headers.append(('Content-Length', str(content_length)))

    # Deal with the response
    start_response(status, response_headers)
    return return_data


def json_response(msg, start_response):
    # If no msg then return error
    if len(msg) == 0:
        return error_response('No data for that query', start_response)

    # If the msg is a string then convert to bytes
    response_body = bytes(msg, 'utf-8') if isinstance(msg, str) else msg

    status = '200 OK'
    response_headers = [
        ('Content-Type', 'text/json'),
        ('Content-Length', str(len(response_body)))
    ]
    start_response(status, response_headers)

    return [response_body]


def error_response(msg, start_response):
    response_body = bytes(msg, 'utf-8')
    status = '404 Not Found'
    response_headers = [
        ('Content-Type', 'text/plain'),
        ('Content-Length', str(len(response_body)))
    ]
    start_response(status, response_headers)

    return [response_body]


def image_response(image, start_response):
    """
    Returns an http response for a png image
    """

    # Return object as a PNG (though should already be a PNG)
    img_bytes = BytesIO()
    image.save(img_bytes, 'PNG')
    img_bytes.seek(0)
    content_length = img_bytes.getbuffer().nbytes

    status = '200 OK'
    response_headers = [
        ('Content-Type', 'image/png'),
        ('Content-Length', str(content_length))
    ]
    start_response(status, response_headers)

    return img_bytes


def handle_request(environ, start_response):
    """ Handles each request """

    uri = util.request_uri(environ, include_query=True)
    parsed_url = urlparse(uri)

    # Determine the query string to use for the Google API.
    # Found that get more appropriate pics if also specify "black and white" and "bird flying"
    parsed_qs = parse_qs(parsed_url.query, keep_blank_values=True)
    match parsed_url.path:
        case '/allSpeciesList':
            # Returns in json a list of all species
            return json_response(ebird.get_species_list_json(), start_response)
        case '/groupsList':
            # Returns in json a list of all species
            return json_response(ebird.get_group_list_json(), start_response)
        case '/speciesForGroup':
            return json_response(ebird.get_species_for_group_json(parsed_qs['g'][0]), start_response)
        case '/dataForSpecies':
            # Returns in json a list of image urls for the species. The client app can
            # then determine which one to use
            return json_response(ebird.get_species_info(parsed_qs['s'][0]), start_response)
        case '/pngFile':
            # Returns png file for the specified URL. Query string should specify 'url' and 's' for species.
            image = load_and_process_image(parsed_qs)
            return image_response(image, start_response)
        case '/wavFile':
            # Loads wav file for specified url and species
            http_accept_encoding = environ['HTTP_ACCEPT_ENCODING'] if 'HTTP_ACCEPT_ENCODING' in environ else ''
            return wav_response(get_wav_file(parsed_qs), start_response, http_accept_encoding)
        case '/eraseCache':
            # Gets rid of all the *Cache.json files so that new data will be used
            cache.erase_cache()
            return json_response('Cache cleared', start_response)
        case _:
            # In case unknown command specified
            return error_response('No such command ' + parsed_url.path, start_response)


# If run as main, then start the webserver
if __name__ == "__main__":
    # Instantiate the server
    httpd = simple_server.make_server(
        # 'localhost',  # The host name
        # '192.168.4.27',  # If want other device on local network to access then need to use local IP, not localhost
        '',  # Seems to be the usual way to specify the host so it works with default IP address
        8080,  # A port number where to wait for the request
        handle_request  # The application object name, in this case a function
    )

    # Respond to requests until process is killed
    httpd.serve_forever()
