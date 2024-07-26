#! /usr/bin/env python
import gzip
import io
from io import BytesIO
from urllib.parse import parse_qs
from urllib.parse import urlparse
from wsgiref import simple_server
# Python's bundled WSGI server
from wsgiref import util

import getJson
import queryGoogle
from audio import get_wav_file
from imageProcessor import load_and_process_image


# NOTE: if you get an SSL Certificate error on OSX (Macs) then you need to install
# the SSL certificates manually by calling the appropriate Python script. It is at
# /Applications/Python\ 3.12/Install\ Certificates.command

# NOTE: had to install Pillow image library using "pip install pillow"
# NOTE: had to install webscraper "pip install html-table-parser-python3"


def wav_response(wav_data, start_response, http_accept_encoding):
    """
    Creates a http response for a wav audio file. Can return either compressed
    or uncompressed data, depending on the request Content-Encoding header.
    :param wav_data: IOBytes the data, in compressed format, to be returned
    :param start_response:
    :param http_accept_encoding: so can determine if should reply with compression or not
    :return: IOBytes containing the data bytes for the full reply
    """
    if wav_data is None:
        return error_response("Could not load image", start_response)

    status = '200 OK'
    response_headers = [('Content-Type', 'audio/wav')]
    wav_data.seek(0)
    return_data = wav_data

    # If gzip compression is accepted then send back already compressed wav data
    if 'gzip' in http_accept_encoding:
        # Using compression
        response_headers.append(('Content-Encoding', 'gzip'))
    else:
        # Request not accepting compressed data so need to need to uncompress the compressed wav data
        # and use it as return_data
        uncompressed_bytes = gzip.decompress(wav_data.read())
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
        case '/speciesList':
            # Returns in json a list of all species
            return json_response(getJson.get_species_list_json(), start_response)
        case '/imageDataForSpecies':
            # Returns in json a list of image urls for the species. The client app can
            # then determine which one to use
            return json_response(getJson.get_image_urls_for_search_json(parsed_qs), start_response)
        case '/audioDataForSpecies':
            # Returns in json a list of wav file urls for the species. The client app can
            # then determine which ones to load.
            return json_response(getJson.get_audio_data_json(parsed_qs), start_response)
        case '/randomImage':
            # Returns png file for specified google image search query. This command might get
            # deprecated because really think the client should get all possible image urls and
            # then decide which one to retrieve using /getImage
            image = queryGoogle.get_random_image_for_query(parsed_qs)
            return image_response(image, start_response)
        case '/image':
            # Returns png file for the specified URL. Query string should specify 'url' and 's' for species.
            image = load_and_process_image(parsed_qs)
            return image_response(image, start_response)
        case '/wavFile':
            # Loads wav file for specified url and species
            http_accept_encoding = environ['HTTP_ACCEPT_ENCODING'] if 'HTTP_ACCEPT_ENCODING' in environ else ''
            return wav_response(get_wav_file(parsed_qs), start_response, http_accept_encoding)
        case _:
            # In case unknown command specified
            return error_response('No such command ' + parsed_url.path, start_response)


# If run as main, then start the webserver
if __name__ == "__main__":
    # Instantiate the server
    httpd = simple_server.make_server(
        # 'localhost',  # The host name
        '192.168.0.85',  # If want other device on local network to access then need to use local IP, not localhost
        8080,  # A port number where to wait for the request
        handle_request  # The application object name, in this case a function
    )

    # Respond to requests until process is killed
    httpd.serve_forever()
